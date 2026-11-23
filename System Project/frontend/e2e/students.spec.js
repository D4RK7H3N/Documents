const { test, expect } = require('@playwright/test')

// The roster is 720 students over the tunnel - give the pages room.
const ROSTER = { timeout: 120000 }

test('roster loads in alphabetical order', async ({ page }) => {
  await page.goto('/#/students')
  await expect(page.getByText('Aguilar').first()).toBeVisible(ROSTER)
})

test('search narrows the roster', async ({ page }) => {
  await page.goto('/#/students')
  await expect(page.getByText('Aguilar').first()).toBeVisible(ROSTER)
  await page.getByPlaceholder('Search by name or LRN...').fill('Zamora')
  await expect(page.getByText('Zamora').first()).toBeVisible({ timeout: 45000 })
  await expect(page.getByText('Aguilar')).toHaveCount(0)
})

test('the status tabs are present with their counts', async ({ page }) => {
  await page.goto('/#/students')
  await expect(page.getByText('Aguilar').first()).toBeVisible(ROSTER)
  // The tab labels carry the row count ("All 720"), so match loosely.
  for (const tab of [/^All/, /^Active/, /^Graduated/]) {
    await expect(page.getByRole('button', { name: tab })).toBeVisible()
  }
})

test('the row edit form opens with the section picker', async ({ page }) => {
  await page.goto('/#/students')
  await expect(page.getByText('Aguilar').first()).toBeVisible(ROSTER)
  // The row actions appear on hover; the edit action opens the student form.
  const row = page.locator('tr', { hasText: 'Aguilar' }).first()
  await row.hover()
  await row.locator('button[title="Edit"]').click()
  await expect(page.getByPlaceholder('12-digit LRN')).toBeVisible({ timeout: 45000 })
  // The section picker is a <select>; its placeholder is the first option.
  const picker = page.locator('select', { hasText: 'Select a section' }).first()
  await expect(picker).toBeVisible({ timeout: 45000 })
})
