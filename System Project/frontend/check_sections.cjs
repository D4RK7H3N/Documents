const { chromium } = require('@playwright/test')
const fs = require('fs')
const path = require('path')

const token = fs.readFileSync(path.join(__dirname, 'e2e', '.auth', 'token.txt'), 'utf8').trim()

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)))
  await page.addInitScript(([t, u]) => {
    window.localStorage.setItem('authToken', t)
    window.localStorage.setItem('user', u)
  }, [token, JSON.stringify({ username: 'e2e-tester', is_superuser: true })])

  for (const [route, label] of [['/sections', 'Sections'], ['/students', 'Students']]) {
    await page.goto('https://sms.darkzhub.asia/#' + route, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(6000)
    const body = await page.locator('body').innerText()
    // only the part under the page header
    const cut = body.indexOf('Section')
    console.log(`--- ${label} ---`)
    console.log(body.slice(cut, cut + 320).replace(/\n+/g, ' | '))
  }
  console.log('errors:', errors.length ? errors.join(' | ') : '(none)')
  await browser.close()
})()
