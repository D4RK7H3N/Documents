const { test, expect } = require('@playwright/test')

const ROSTER = { timeout: 120000 }

test('sections are grouped by year level', async ({ page }) => {
  await page.goto('/#/sections')
  await expect(page.getByText('Amos').first()).toBeVisible(ROSTER)

  for (const group of ['Grade 11', 'Grade 12', '1st Year', '2nd Year']) {
    await expect(page.locator('h3', { hasText: group }).first()).toBeVisible()
  }
  // The bundled classes must sit under their year level, not under "Other".
  const others = page.locator('h3', { hasText: /^Other$/i })
  expect(await others.count()).toBe(0)
})

test('the import dialog opens with the layout guide', async ({ page }) => {
  await page.goto('/#/sections')
  await expect(page.getByText('Amos').first()).toBeVisible(ROSTER)
  await page.getByRole('button', { name: 'Import Students' }).click()
  await expect(page.getByText('Import Students by Strand')).toBeVisible({ timeout: 45000 })
  await expect(page.locator('input[type="file"]')).toBeVisible()
})

test('the add-section dialog opens', async ({ page }) => {
  await page.goto('/#/sections')
  await expect(page.getByText('Amos').first()).toBeVisible(ROSTER)
  await page.getByRole('button', { name: 'Add Section' }).click()
  await expect(page.getByPlaceholder('e.g. STEM-A')).toBeVisible({ timeout: 45000 })
})
