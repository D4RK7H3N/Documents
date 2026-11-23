import { storage } from '../services/storage'

// The staff display name for printed documents ("Prepared by" / cashier
// line). Prefers the profile name maintained on the Profile page; falls
// back to the login username and then a neutral label so a receipt never
// prints "undefined".
export function staffName() {
  try {
    const u = JSON.parse(storage.getSync('user') || '{}')
    const first = u.first_name || u.firstName || ''
    const last = u.last_name || u.lastName || ''
    const name = `${first} ${last}`.trim()
    if (name) return name
    return u.username || 'Staff'
  } catch {
    return 'Staff'
  }
}
