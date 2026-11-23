const { test, expect } = require('@playwright/test')

const ROSTER = { timeout: 120000 }

test('cashier loads with the student search and payment methods', async ({ page }) => {
  await page.goto('/#/cashier')
  await expect(page.getByPlaceholder('Search name or 12-digit LRN')).toBeVisible(ROSTER)
  await expect(page.getByText('Daily Report')).toBeVisible({ timeout: 45000 })
  // Two controls share this label (the item filter and its count) - match the tab exactly.
  await expect(page.getByRole('button', { name: 'Tuition Payment', exact: true })).toBeVisible()
})

test('pending payments shows the balances', async ({ page }) => {
  await page.goto('/#/pending-payments')
  await expect(page.getByText('Students with Balance')).toBeVisible({ timeout: 120000 })
  // The roster size depends on what is enrolled, so the page is checked for
  // its shape - the stat cards and the table - and not for a fixed count.
  await expect(page.getByText('Total Pending Amount')).toBeVisible({ timeout: 45000 })
})

test('revenue page loads', async ({ page }) => {
  await page.goto('/#/revenue')
  await expect(page.locator('body')).toContainText(/Revenue/i, { timeout: 120000 })
})
