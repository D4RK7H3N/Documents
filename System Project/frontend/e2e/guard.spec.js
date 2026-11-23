const { test, expect } = require('@playwright/test')

// A signed-out visitor is redirected to the login screen.
test.use({ storageState: { cookies: [], origins: [] } })

test('unauthenticated users land on the login screen', async ({ page }) => {
  await page.goto('/#/students')
  await expect(page).toHaveURL(/login/, { timeout: 30000 })
  await expect(page.getByPlaceholder('Enter your username')).toBeVisible({ timeout: 30000 })
})

test('the login screen carries the school branding', async ({ page }) => {
  await page.goto('/#/login')
  await expect(page.getByText(/USAT COLLEGE SAGAY CITY, INC./i).first()).toBeVisible({ timeout: 30000 })
})
