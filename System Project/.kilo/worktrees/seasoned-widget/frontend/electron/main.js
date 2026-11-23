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
    mainWindow.loadURL('http://localhost:5173')
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
      if (parsedUrl.origin !== 'http://localhost:5173' && !url.startsWith('file://')) {
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

// Renderer hands over the School Config branding so the next launch can
// paint the splash with the real school instead of the generic seal.
ipcMain.on('splash-brand', (event, brand) => {
  if (event?.sender !== mainWindow?.webContents) return
  writeBrand(brand)
})