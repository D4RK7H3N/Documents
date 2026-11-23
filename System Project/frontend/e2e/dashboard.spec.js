const { test, expect } = require('@playwright/test')
const fs = require('fs')
const path = require('path')

test('dashboard renders the stat cards and system status', async ({ page }) => {
  await page.goto('/#/dashboard')
  await expect(page.getByText('Quick Actions')).toBeVisible({ timeout: 60000 })
  await expect(page.getByText('Total Students')).toBeVisible()
  await expect(page.getByText('System Status')).toBeVisible()
  await expect(page.getByText('Database')).toBeVisible()
})

test('dashboard counts the enrolled students', async ({ page }) => {
  await page.goto('/#/dashboard')
  await expect(page.getByText('Total Students')).toBeVisible({ timeout: 60000 })
  // The card carries a number - how many depends on what is enrolled, so the
  // count is compared with the API instead of a fixed number.
  const token = fs.readFileSync(path.join(__dirname, '.auth', 'token.txt'), 'utf8').trim()
  const res = await fetch('https://sms.darkzhub.asia/api/students/?page_size=1', {
    headers: { Authorization: `Token ${token}` },
  })
  const data = await res.json()
  const count = Array.isArray(data) ? data.length : data.count
  await expect(page.locator('body')).toContainText(count.toLocaleString(), { timeout: 30000 })
})
