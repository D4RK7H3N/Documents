const { test, expect } = require('@playwright/test')

test('tuition records load and respond to search', async ({ page }) => {
  await page.goto('/#/tuition')
  await expect(page.getByPlaceholder('Search student or LRN...')).toBeVisible({ timeout: 120000 })
  // The reset state: every student owes their full fee.
  await expect(page.getByText(/Total Outstanding Balance/i)).toBeVisible({ timeout: 60000 })
  await page.getByPlaceholder('Search student or LRN...').fill('Zamora')
  await expect(page.getByText(/Zamora/i).first()).toBeVisible({ timeout: 60000 })
  await expect(page.getByText(/Zamora/i)).not.toHaveCount(0)
})
