const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  // Stable hardware id of this machine, sent as X-Device-Id so the backend
  // can attribute revenue to a terminal.
  getDeviceId: () => ipcRenderer.invoke('get-device-id'),
  // Reads a .css file inside the app bundle; used by printing to inline the
  // compiled stylesheet into self-contained print documents on file://.
  readAppCss: (filePath) => ipcRenderer.invoke('read-app-css', filePath),
  // Prints a self-contained HTML document with explicit page options
  // (80mm receipt roll or A4 portrait) instead of printer-driver defaults.
  printHtml: (payload) => ipcRenderer.invoke('print-html', payload),
  // Asks the main process to look for a newer release on the school's server.
    // interactive = the user pressed "Check for updates": the app then pops
    // the question up. The silent background check passes nothing.
    checkForUpdates: (interactive) => ipcRenderer.invoke('check-for-updates', !!interactive),

  // Progress of the update download (phase: available | downloading | ready
  // | current | error). Returns an unsubscribe function.
  onUpdateStatus: (callback) => {
    const handler = (_event, payload) => callback(payload)
    ipcRenderer.on('update-status', handler)
    return () => ipcRenderer.removeListener('update-status', handler)
  },
  // Caches the school name/logo for the next launch's splash screen.
  cacheSplashBrand: (brand) => ipcRenderer.send('splash-brand', brand),
})