const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 300000,
  expect: { timeout: 45000 },
  // The import test brings in 720 students; this removes them again so the
  // roster is left exactly as the suite found it.
  globalTeardown: './e2e/global-teardown.js',
  // The heavy pages (720-row rosters through the tunnel) are slow enough that
  // parallel workers starve each other - one at a time keeps the runs honest.
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'https://sms.darkzhub.asia',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    actionTimeout: 30000,
    navigationTimeout: 60000,
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.js/ },
    {
      name: 'app',
      dependencies: ['setup'],
      use: { storageState: 'e2e/.auth/state.json' },
      testIgnore: /auth\.setup\.js/,
    },
  ],
})
