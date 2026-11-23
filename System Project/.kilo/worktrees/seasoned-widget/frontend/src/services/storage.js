import { Capacitor } from '@capacitor/core'
import { Preferences } from '@capacitor/preferences'

const isNative = Capacitor.isNativePlatform()

export const storage = {
  async get(key) {
    if (isNative) {
      const { value } = await Preferences.get({ key })
      return value ?? null
    }
    try { return localStorage.getItem(key) } catch { return null }
  },
  getSync(key) {
    // Synchronous fallback for web environments only (React initial state)
    if (isNative) return null
    try { return localStorage.getItem(key) } catch { return null }
  },
  async set(key, value) {
    if (isNative) {
      await Preferences.set({ key, value })
      return
    }
    try { localStorage.setItem(key, value) } catch { /* noop */ }
  },
  async remove(key) {
    if (isNative) {
      await Preferences.remove({ key })
      return
    }
    try { localStorage.removeItem(key) } catch { /* noop */ }
  },
  async keys() {
    if (isNative) {
      const { keys } = await Preferences.keys()
      return keys
    }
    try { return Object.keys(localStorage) } catch { return [] }
  },
}
