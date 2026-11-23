const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')
const os = require('os')

const isWindows7 = os.release().startsWith('6.1')
if (isWindows7) {
  app.disableHardwareAcceleration()
  app.commandLine.appendSwitch('--no-sandbox')
  app.commandLine.appendSwitch('--disable-gpu')
  app.commandLine.appendSwitch('--disable-gpu-compositing')
  app.commandLine.appendSwitch('--disable-gpu-rasterization')
  app.commandLine.appendSwitch('--disable-gpu-sandbox')
}

const isDev = !app.isPackaged
const appStartTime = Date.now()

// Set when the user answers the "update available" pop-up with "Download and
// install": the app then restarts as soon as the installer is there, instead
// of asking a second time.
let updateAccepted = false

// The dev build and the installed app have the same app name, so they end up
// sharing one profile folder (%APPDATA%\school-management-system). While the
// dev build holds that folder, the installed app cannot create its disk cache
// and every window fails to load with "ERR_FAILED (-2)". Give the dev build
// its own profile so both can run at the same time.
if (isDev) {
  try {
    app.setPath('userData', path.join(app.getPath('temp'), 'sms-dev-profile'))
  } catch (e) {
    console.error('[Main] Could not set the dev profile path:', e.message)
  }
}

const SPLASH_MIN_MS = 20000
const SPLASH_FALLBACK_MS = 15000

let mainWindow = null
let splashWindow = null
let windowShown = false
const splashTimers = []

// ---- splash branding ------------------------------------------------------
// The splash paints before the renderer boots, so it cannot read School Config
// from the app. The renderer caches the school name and logo here after every
// successful config load, and the splash reads it on the next launch. Absent
// (first ever run) the splash falls back to the built-in seal.
const BRAND_FILE = 'splash-brand.json'

function brandFilePath() {
  return path.join(app.getPath('userData'), BRAND_FILE)
}

function readBrand() {
  try {
    const raw = fs.readFileSync(brandFilePath(), 'utf8')
    const parsed = JSON.parse(raw)
    return {
      schoolName: typeof parsed.schoolName === 'string' ? parsed.schoolName : '',
      logoUrl: typeof parsed.logoUrl === 'string' ? parsed.logoUrl : '',
    }
  } catch (e) {
    return { schoolName: '', logoUrl: '' }
  }
}

function writeBrand(brand) {
  try {
    const clean = {
      schoolName: String(brand?.schoolName || '').slice(0, 160),
      logoUrl: String(brand?.logoUrl || '').slice(0, 500),
      updatedAt: new Date().toISOString(),
    }
    if (!clean.schoolName && !clean.logoUrl) return
    fs.mkdirSync(path.dirname(brandFilePath()), { recursive: true })
    fs.writeFileSync(brandFilePath(), JSON.stringify(clean, null, 2), 'utf8')
  } catch (e) {
    console.error('[Splash] Could not cache brand:', e.message)
  }
}

// Push a real load stage into the splash. Keeps the progress bar and the
// status line honest instead of cycling through invented messages on a timer.
const SPLASH_STAGES = {
  boot:    { pct: 15, label: 'Starting up' },
  window:  { pct: 35, label: 'Opening workspace' },
  loading: { pct: 55, label: 'Loading interface' },
  loaded:  { pct: 80, label: 'Interface loaded' },
  ready:   { pct: 95, label: 'Finishing up' },
}

function setSplashStage(stage) {
  const s = SPLASH_STAGES[stage]
  if (!s || !splashWindow || splashWindow.isDestroyed()) return
  try {
    splashWindow.webContents.executeJavaScript(
      `window.__splash && window.__splash.stage(${stage}, ${s.pct}, ${JSON.stringify(s.label)})`
    ).catch(() => {})
  } catch (e) {}
}

const lock = app.requestSingleInstanceLock()
if (!lock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
}

function clearSplashTimers() {
  while (splashTimers.length) {
    clearTimeout(splashTimers.pop())
  }
}

function scheduleSplashClose(delay) {
  const id = setTimeout(() => {
    showMainWindow()
  }, delay)
  splashTimers.push(id)
  return id
}

function showMainWindow() {
  if (windowShown) return
  windowShown = true
  clearSplashTimers()
  setSplashStage('ready')

  setTimeout(() => {
    try {
      if (splashWindow && !splashWindow.isDestroyed()) {
        splashWindow.hide()
        setTimeout(() => {
          try {
            if (splashWindow && !splashWindow.isDestroyed()) {
              splashWindow.close()
            }
            splashWindow = null
          } catch (e) {}
        }, 300)
      }
    } catch (e) {
      splashWindow = null
    }
    try {
      if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.isMinimized()) mainWindow.restore()
        mainWindow.show()
        mainWindow.maximize()
        mainWindow.focus()
      }
    } catch (e) {
      console.error('[Main] Show error:', e.message)
    }
  }, 200)
}

function resolveResourcePath(...segments) {
  const candidates = []
  if (!isDev) {
    candidates.push(path.join(app.getAppPath(), ...segments))
    if (process.resourcesPath) {
      candidates.push(path.join(process.resourcesPath, 'app', ...segments))
      candidates.push(path.join(process.resourcesPath, ...segments))
    }
  }
  candidates.push(path.join(__dirname, ...segments))
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) return candidate
    } catch (e) {}
  }
  return candidates[0]
}

function getSplashPath() {
  if (isDev) return path.join(__dirname, 'splash.html')
  return resolveResourcePath('electron', 'splash.html')
}

function getIndexPath() {
  if (isDev) return null
  return resolveResourcePath('dist', 'index.html')
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 520,
    height: 360,
    frame: false,
    resizable: false,
    movable: true,
    center: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    show: false,
    paintWhenInitiallyHidden: true,
    backgroundColor: '#1a3a5c',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const splashPath = getSplashPath()
  console.log('[Splash] Loading from:', splashPath)

  // Version and cached branding are injected at load: splash.html is static,
  // so it cannot know either on its own.
  const brand = readBrand()
  const splashQuery = new URLSearchParams({
    v: app.getVersion(),
    school: brand.schoolName,
    logo: brand.logoUrl,
  })
  splashWindow.loadFile(splashPath, { query: Object.fromEntries(splashQuery) }).catch(err => {
    console.error('[Splash] Failed to load:', err.message)
  })

  splashWindow.once('ready-to-show', () => {
    splashWindow.show()
    splashWindow.focus()
  })

  splashWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc) => {
    console.error('[Splash] did-fail-load:', errorCode, errorDesc)
  })
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 640,
    frame: true,
    show: false,
    paintWhenInitiallyHidden: true,
    backgroundColor: '#f9fafb',
    icon: path.join(__dirname, '../build/icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
      backgroundThrottling: false,
    },
  })

  app.setAppUserModelId('com.sms.schoolmanagementsystem')

  scheduleSplashClose(SPLASH_FALLBACK_MS)

  setSplashStage('window')
  setSplashStage('loading')

  if (isDev) {
    // The SMS Vite dev server binds IPv6 loopback by default; binding an
    // unrelated project's dev server to 127.0.0.1:5173 would otherwise make
    // "localhost" resolve to the wrong app (404 /api and /src pages).
    mainWindow.loadURL('http://[::1]:5173')
  } else {
    const indexPath = getIndexPath()
    console.log('[Main] Loading from:', indexPath)
    mainWindow.loadFile(indexPath).catch(err => {
      console.error('[Main] loadFile failed:', err.message)
      setSplashStage('ready')
      showMainWindow()
    })
  }

  mainWindow.webContents.on('did-finish-load', () => {
    console.log('[Main] did-finish-load fired')
    setSplashStage('loaded')
    const elapsed = Date.now() - appStartTime
    const remaining = Math.max(0, SPLASH_MIN_MS - elapsed)
    if (remaining <= 0) {
      setSplashStage('ready')
      showMainWindow()
    } else {
      scheduleSplashClose(remaining)
    }
  })

  mainWindow.once('ready-to-show', () => {
    setSplashStage('ready')
  })

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc) => {
    console.error('[Main] did-fail-load:', errorCode, errorDesc)
    setSplashStage('ready')
    showMainWindow()
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    try {
      const parsedUrl = new URL(url)
      if (parsedUrl.origin !== 'http://[::1]:5173' && !url.startsWith('file://')) {
        event.preventDefault()
        shell.openExternal(url)
      }
    } catch (e) {}
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })

  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown') return
    if (
      input.key === 'F12' ||
      (input.control && input.shift && (input.key === 'I' || input.key === 'i'))
    ) {
      mainWindow.webContents.toggleDevTools()
    }
  })

  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'false' })
  }

  return mainWindow
}

app.whenReady().then(() => {
  createSplashWindow()
  createMainWindow()
  if (!isDev) {
    Menu.setApplicationMenu(null)
    setupContentSecurityPolicy()
    setupAutoUpdate()
  }
})

// ---------------------------------------------------------------------------
// Content Security Policy for the packaged app
// ---------------------------------------------------------------------------
// The renderer loads only its own bundled files, talks to the two API origins
// and nothing else. Locking that down stops a tampered page from shipping
// data anywhere else. In development the policy is left off because Vite's
// HMR client needs inline/eval scripts.
function setupContentSecurityPolicy() {
  const { session } = require('electron')
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https: http:",
    // The Inter webfont is bundled with the app (src/assets/fonts), so it is
    // loaded from the app's own files - no request to fonts.googleapis.com,
    // which this policy blocks anyway.
    "font-src 'self' data: file:",
    "connect-src 'self' https://sms.darkzhub.asia",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ].join('; ')

  try {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      callback({
        responseHeaders: {
          ...details.responseHeaders,
          'Content-Security-Policy': [csp],
        },
      })
    })
  } catch (err) {
    console.error('[CSP] could not apply the policy:', err.message)
  }
}

// ---------------------------------------------------------------------------
// Auto update (self-hosted feed on the school's own server)
// ---------------------------------------------------------------------------
// The installer and latest.yml are stored on the school's server and served
// from https://sms2-api.darkzhub.asia/releases/ - the school controls its own
// update channel and a slow third-party upload can never strand the school
// on an old build. GitHub Releases is kept as a mirror for the clients that
// were built before this switch (they still look for their feed there).
//
// electron-updater compares the version in latest.yml with the running app,
// so every new build must bump the version in package.json, and the release
// files on the server must be replaced with the new ones.
function setupAutoUpdate() {
  let autoUpdater
  try {
    ({ autoUpdater } = require('electron-updater'))
  } catch (err) {
    console.error('[Update] electron-updater unavailable:', err.message)
    return
  }

  // The update is downloaded in the background, but only installed when the
  // user accepts (or silently on the next quit).
  //
  // autoDownload must stay false: with it turned off electron-updater only
  // DETECTS an update - checkForUpdates() resolves without downloading
  // anything ("downloadPromise: autoDownload ? downloadUpdate() : null"), so
  // the app used to announce an update that was never fetched. The download
  // is therefore started explicitly when an update is found.
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true
  autoUpdater.logger = {
    info: (m) => console.log('[Update]', m),
    warn: (m) => console.warn('[Update]', m),
    error: (m) => console.error('[Update]', m),
    debug: (m) => console.log('[Update]', m),
  }

  const sendStatus = (payload) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('update-status', payload)
    }
  }

  autoUpdater.on('update-available', (info) => {
    console.log('[Update] available:', info?.version)
    sendStatus({ phase: 'available', version: info?.version })
    // Fetch it now so it is ready when the app is closed. electron-updater
    // reuses an already downloaded file, so a second check costs nothing.
    autoUpdater.downloadUpdate().catch((err) => {
      console.error('[Update] download failed:', err?.message)
      sendStatus({ phase: 'error', message: err?.message })
    })
  })

  autoUpdater.on('download-progress', (progress) => {
    sendStatus({
      phase: 'downloading',
      version: progress?.version,
      percent: Math.round(progress?.percent || 0),
      transferred: progress?.transferred,
      total: progress?.total,
    })
  })

  autoUpdater.on('update-not-available', () => {
    console.log('[Update] already up to date')
    sendStatus({ phase: 'current' })
  })

  autoUpdater.on('update-downloaded', async (info) => {
    console.log('[Update] downloaded:', info?.version)
    sendStatus({ phase: 'ready', version: info?.version })
    // The user answered the pop-up with "Download and install" - restart now.
    // Otherwise the update waits for the next quit (autoInstallOnAppQuit) and
    // the Settings page says it is ready. No second dialog.
    if (updateAccepted) {
      autoUpdater.quitAndInstall(false, true)
    }
  })

  autoUpdater.on('error', (err) => {
    // A missing/broken feed must never block the app from starting.
    console.error('[Update] check failed:', err?.message)
    sendStatus({ phase: 'error', message: err?.message })
  })

  // Give the app a moment to finish loading before checking.
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((err) => {
      console.error('[Update] check failed:', err?.message)
    })
  }, 8000)
}

ipcMain.handle('check-for-updates', async (event, interactive) => {
  if (isDev) return { ok: false, message: 'Updates are disabled in development.' }
  try {
    const { autoUpdater } = require('electron-updater')
    const result = await autoUpdater.checkForUpdates()
    const info = result?.updateInfo
    if (!info || !info.version) {
      return { ok: true, status: 'current', version: autoUpdater.currentVersion }
    }
    if (info.version === autoUpdater.currentVersion) {
      return { ok: true, status: 'current', version: autoUpdater.currentVersion }
    }

    // A new version is there. The silent background check just lets the
    // download run; the check the user asked for pops the question up right
    // away instead of making them wait for the download to finish.
    if (interactive) {
      const { dialog } = require('electron')
      const choice = await dialog.showMessageBox(mainWindow, {
        type: 'info',
        buttons: ['Download and install', 'Later'],
        defaultId: 0,
        cancelId: 1,
        title: 'Update available',
        message: `School Management System ${info.version} is available.`,
        detail: 'Download it and restart now, or choose Later - it will be installed the next time you close the app.',
      })
      if (choice.response === 0) {
        updateAccepted = true
        autoUpdater.downloadUpdate().catch((err) => {
          console.error('[Update] download failed:', err?.message)
          sendStatus({ phase: 'error', message: err?.message })
        })
      }
    }
    // The download also runs in the background (the update-available handler
    // starts it), so "Later" still installs the update at the next quit.
    return {
      ok: true,
      status: 'available',
      version: info.version,
    }
  } catch (err) {
    return { ok: false, message: err?.message || 'Could not check for updates.' }
  }
})

app.on('window-all-closed', () => {
  app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    windowShown = false
    clearSplashTimers()
    createMainWindow()
  }
})

ipcMain.on('window-minimize', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize()
})

ipcMain.on('window-maximize', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow.maximize()
    }
  }
})

ipcMain.on('window-close', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close()
})

ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url)
})

ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

// ---- device identity --------------------------------------------------------
// Cashier machines identify themselves with a stable hardware id so revenue
// can be reported per terminal.
//
// The id is a random UUID stored in the app's userData folder:
//   * it survives an app reinstall on the same PC (userData persists),
//   * two PCs cloned from the same disk image get DIFFERENT ids - the
//     Windows MachineGuid is duplicated by disk cloning, which would merge
//     two registers' sales into one row.
//
// The OS machine GUID is kept as a fallback when the id file cannot be
// written, and the previous id is reported once so the backend can move the
// existing terminal's history onto the new id.
const DEVICE_ID_FILE = 'device-id.txt'
const PREVIOUS_DEVICE_ID_FILE = 'device-id.previous.txt'

let cachedDeviceId = null

function readMachineGuid() {
  const { execFileSync } = require('child_process')
  try {
    const out = execFileSync(
      'reg',
      ['query', 'HKLM\\SOFTWARE\\Microsoft\\Cryptography', '/v', 'MachineGuid'],
      { encoding: 'utf8', timeout: 5000 }
    )
    const m = out.match(/MachineGuid\s+REG_SZ\s+(\S+)/)
    if (m) return m[1]
  } catch (e) {}
  try {
    const out = execFileSync('wmic', ['csproduct', 'get', 'UUID'], {
      encoding: 'utf8',
      timeout: 8000,
    })
    const line = out
      .split(/\r?\n/)
      .map((s) => s.trim())
      .find((s) => s && !/^UUID$/i.test(s))
    if (line) return line
  } catch (e) {}
  return ''
}

// Returns { id, previousId }. previousId is the id this machine used before
// (the OS machine GUID on the first run of the new scheme) and is sent once
// so the backend can keep the terminal's history.
function getDeviceIdentity() {
  if (cachedDeviceId) return cachedDeviceId
  const crypto = require('crypto')
  const dir = app.getPath('userData')
  const file = path.join(dir, DEVICE_ID_FILE)
  const prevFile = path.join(dir, PREVIOUS_DEVICE_ID_FILE)

  let previousId = ''
  try {
    previousId = fs.existsSync(prevFile) ? fs.readFileSync(prevFile, 'utf8').trim() : ''
  } catch (e) {}

  try {
    const existing = fs.existsSync(file) ? fs.readFileSync(file, 'utf8').trim() : ''
    if (existing) {
      cachedDeviceId = { id: existing, previousId }
      return cachedDeviceId
    }
    // First run of the new scheme: remember the id this machine used before
    // so the backend can move the existing terminal row onto the new id.
    const legacy = readMachineGuid()
    if (legacy && legacy !== previousId) {
      previousId = legacy
      fs.writeFileSync(prevFile, legacy, 'utf8')
    }
    const id = crypto.randomUUID().replace(/-/g, '')
    fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(file, id, 'utf8')
    cachedDeviceId = { id, previousId }
    return cachedDeviceId
  } catch (e) {
    console.error('[Device] could not persist the device id:', e.message)
    // Fall back to the machine GUID so the terminal is still identified.
    const guid = readMachineGuid()
    cachedDeviceId = { id: guid, previousId: '' }
    return cachedDeviceId
  }
}

function getDeviceId() {
  return getDeviceIdentity().id
}

ipcMain.handle('get-device-id', () => getDeviceIdentity())

// ---- print css fallback ------------------------------------------------------
// When the packaged app loads from file://, the renderer cannot read the
// contents of <link> stylesheets (opaque origins), so printNode asks the main
// process for the CSS text. Restricted to .css files inside the app bundle.
ipcMain.handle('read-app-css', (event, filePath) => {
  try {
    if (typeof filePath !== 'string' || !filePath.endsWith('.css')) return null
    const cleaned = decodeURIComponent(
      filePath.replace(/^file:\/\/\//, '').split('?')[0].split('#')[0]
    )
    const roots = [path.resolve(app.getAppPath())]
    if (process.resourcesPath) roots.push(path.resolve(process.resourcesPath))
    const resolved = path.resolve(cleaned)
    if (!roots.some((r) => resolved.startsWith(r))) return null
    return fs.readFileSync(resolved, 'utf8')
  } catch (e) {
    return null
  }
})

// ---- printing ----------------------------------------------------------------
// Receipts were coming out of the Electron print dialog in landscape on the
// printer's default paper: the dialog starts from driver defaults and
// @media print CSS cannot override it. This pipeline loads the exact document
// in a hidden window and prints with explicit options, so receipts default to
// an 80mm portrait roll and reports to A4 portrait.
const PRINT_PAGE_SIZES = {
  receipt: { width: 80000, height: 297000 }, // 80mm roll, microns
  A4: 'A4',
}

ipcMain.handle('print-html', async (event, payload) => {
  if (event?.sender !== mainWindow?.webContents) {
    return { ok: false, error: 'print request must come from the main window' }
  }
  const { html, pageSize = 'A4', landscape = false, title = 'Document' } = payload || {}
  if (typeof html !== 'string' || !html.trim()) {
    return { ok: false, error: 'Nothing to print' }
  }
  let printWindow = null
  let tempFile = null
  try {
    // Chromium rejects data: URLs beyond ~2MB (ERR_INVALID_URL), and revenue
    // reports with a full transactions table exceed that. Write the document
    // to a temp file and load it from disk instead; it is deleted right after
    // the print dialog closes.
    const { writeFile } = require('fs/promises')
    const path = require('path')
    tempFile = path.join(app.getPath('temp'), `sms-print-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.html`)
    await writeFile(tempFile, html, 'utf8')
    printWindow = new BrowserWindow({
      show: false,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    })
    await printWindow.loadFile(tempFile)
    const options = {
      silent: false,
      printBackground: true,
      landscape: !!landscape,
      margins:
        pageSize === 'receipt'
          ? { marginType: 'custom', top: 0.16, bottom: 0.16, left: 0.16, right: 0.16 }
          : { marginType: 'default' },
    }
    options.pageSize = PRINT_PAGE_SIZES[pageSize] || pageSize
    await new Promise((resolve, reject) => {
      printWindow.webContents.print(options, (success, failureReason) => {
        if (success) resolve()
        else reject(new Error(failureReason || 'Print cancelled'))
      })
    })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Print failed' }
  } finally {
    try {
      if (printWindow && !printWindow.isDestroyed()) printWindow.destroy()
    } catch (e) {}
    try {
      if (tempFile) require('fs').unlink(tempFile, () => {})
    } catch (e) {}
  }
})

// Renderer hands over the School Config branding so the next launch can
// paint the splash with the real school instead of the generic seal.
ipcMain.on('splash-brand', (event, brand) => {
  if (event?.sender !== mainWindow?.webContents) return
  writeBrand(brand)
})