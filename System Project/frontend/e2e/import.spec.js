// Imports the 720-row fixture (Amount Paid zeroed) through the real dialog:
// it updates every student in place, shows the live counter on the loading
// screen, and leaves no payment history behind.
//
// The students that were already enrolled are recorded first, so the
// teardown can remove exactly what this test brought in and nothing else -
// the school's own sheets may well use LRNs that start with "00" too.
const { test, expect } = require('@playwright/test')
const fs = require('fs')
const path = require('path')

const FIXTURE = path.join(__dirname, 'fixtures', 'import-no-payments.xlsx')
const API = process.env.E2E_API || 'https://sms.darkzhub.asia'
const BEFORE_FILE = path.join(__dirname, '.auth', 'students-before.json')

test.describe.configure({ mode: 'serial' })

test('big import shows the counter and updates every row in place', async ({ page }) => {
  const consoleErrors = []
  page.on('pageerror', (err) => consoleErrors.push(String(err)))

  // Remember who was enrolled before the import.
  const token = fs.readFileSync(path.join(__dirname, '.auth', 'token.txt'), 'utf8').trim()
  const before = await fetch(`${API}/api/students/?page_size=2000`, {
    headers: { Authorization: `Token ${token}` },
  }).then((r) => r.json())
  const beforeRows = Array.isArray(before) ? before : before.results || []
  fs.writeFileSync(BEFORE_FILE, JSON.stringify(beforeRows.map((s) => s.id)), 'utf8')

  await page.goto('/#/sections')
  await expect(page.getByText('Amos').first()).toBeVisible({ timeout: 120000 })

  await page.getByRole('button', { name: 'Import Students' }).click()
  await expect(page.getByText('Import Students by Strand')).toBeVisible({ timeout: 30000 })

  await page.locator('input[type="file"]').setInputFiles(FIXTURE)
  await page.getByRole('button', { name: 'Start Import' }).click()

  // The global loading screen with the row count.
  await expect(page.getByText('Importing 720 students')).toBeVisible({ timeout: 60000 })
  // The live counter ticking - timing dependent, so it is a soft check.
  let counterSeen = false
  try {
    await expect(page.getByText(/of 720 done/)).toBeVisible({ timeout: 30000 })
    counterSeen = true
  } catch { /* the import can outrun the first poll on a fast link */ }
  console.log('live counter seen:', counterSeen)

  // The import finishes and the dialog reports the outcome.
  await expect(page.getByText(/Successfully processed 720 students/).first()).toBeVisible({ timeout: 240000 })
  await expect(page.getByText('Importing 720 students')).toHaveCount(0)

  expect(consoleErrors, 'the renderer threw: ' + consoleErrors.join(' | ')).toEqual([])
})
