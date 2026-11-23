$pw = (Get-Content 'e2e\.auth\password.txt' -Raw).Trim()
$env:E2E_PASSWORD = $pw
npx playwright test 2>&1 | Select-Object -Last 45
