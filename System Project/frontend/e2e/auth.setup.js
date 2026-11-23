// Creates the authenticated session for every other test.
//
// The session is built by injecting a real API token into localStorage (the
// same keys the app's AuthContext uses) instead of posting the login form -
// the login endpoint is throttled to 10/hour, and a suite that logs in on
// every run locks itself out within minutes. The login screen itself is
// covered by guard.spec.js.
const { test, expect } = require('@playwright/test')
const fs = require('fs')
const path = require('path')

const token = fs.readFileSync(path.join(__dirname, '.auth', 'token.txt'), 'utf8').trim()
const statePath = path.join(__dirname, '.auth', 'state.json')

test('create the authenticated session', async ({ page }) => {
  const user = JSON.stringify({ username: 'e2e-tester', is_superuser: true })
  await page.addInitScript(([t, u]) => {
    window.localStorage.setItem('authToken', t)
    window.localStorage.setItem('user', u)
  }, [token, user])

  await page.goto('/#/dashboard')
  // The app accepted the token and rendered the signed-in dashboard.
  await expect(page.getByText('Quick Actions')).toBeVisible({ timeout: 90000 })
  await expect(page.getByText('e2e-tester').first()).toBeVisible()

  await page.context().storageState({ path: statePath })
})
