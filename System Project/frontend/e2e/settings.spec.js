const { test, expect } = require('@playwright/test')

test('settings shows the license and maintenance controls', async ({ page }) => {
  await page.goto('/#/settings')
  await expect(page.getByText('Notification Settings')).toBeVisible({ timeout: 60000 })
  await expect(page.getByText('Proprietary')).toBeVisible()
  await expect(page.getByText('Maintenance Mode').first()).toBeVisible()
})

test('school config carries the school identity', async ({ page }) => {
  await page.goto('/#/school-config')
  await expect(page.locator('body')).toContainText(/USAT COLLEGE SAGAY CITY, INC./i, { timeout: 60000 })
})
