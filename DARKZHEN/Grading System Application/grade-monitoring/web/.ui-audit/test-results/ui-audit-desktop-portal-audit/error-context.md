# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-audit.spec.js >> desktop portal audit
- Location: .ui-audit\ui-audit.spec.js:25:3

# Error details

```
TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e6]:
      - paragraph [ref=e7]: Grade Monitoring
      - paragraph [ref=e8]: Sagay National High School
    - generic [ref=e9]:
      - heading "Every grade, one source of truth." [level=2] [ref=e10]: Every grade,one source of truth.
      - paragraph [ref=e11]: Score entry, automatic computation per DepEd Order No. 8, s. 2015, and a full audit trail — computed once on the server, identical on every device.
    - paragraph [ref=e12]: Faculty and administrator portal
  - generic [ref=e14]:
    - generic [ref=e15]:
      - heading "Sign in" [level=1] [ref=e16]
      - paragraph [ref=e17]: Use the account issued by your administrator.
      - generic [ref=e18]:
        - generic [ref=e19]:
          - generic [ref=e20]: Username
          - textbox "Username" [ref=e21]: _ui_audit_desktop
        - generic [ref=e22]:
          - generic [ref=e23]: Password
          - textbox "Password" [ref=e24]: AuditOnly-2026!
        - button "login Signing in…" [disabled]:
          - generic: login
          - text: Signing in…
    - paragraph [ref=e25]: Students view their grades in the mobile app
```

# Test source

```ts
  1   | import { test } from "file:///C:/Users/DarkZhen/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright/test.mjs";
  2   | import { mkdir, writeFile } from "node:fs/promises";
  3   | 
  4   | const routes = [
  5   |   ["/", "dashboard"],
  6   |   ["/classes", "classes"],
  7   |   ["/submissions", "submissions"],
  8   |   ["/reports", "reports"],
  9   |   ["/admin/class-records", "class-records"],
  10  |   ["/students", "students"],
  11  |   ["/teachers", "teachers"],
  12  |   ["/users", "users"],
  13  |   ["/academics", "academics"],
  14  |   ["/grading-config", "grading-config"],
  15  |   ["/settings", "settings"],
  16  |   ["/audit-log", "audit-log"],
  17  | ];
  18  | 
  19  | const modes = [
  20  |   { name: "desktop", viewport: { width: 1440, height: 1000 }, isMobile: false, hasTouch: false },
  21  |   { name: "mobile", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  22  | ];
  23  | 
  24  | for (const mode of modes) {
  25  |   test(`${mode.name} portal audit`, async ({ browser }) => {
  26  |     const context = await browser.newContext({
  27  |       viewport: mode.viewport,
  28  |       isMobile: mode.isMobile,
  29  |       hasTouch: mode.hasTouch,
  30  |       deviceScaleFactor: 1,
  31  |     });
  32  |     const page = await context.newPage();
  33  |     const consoleErrors = [];
  34  |     const pageErrors = [];
  35  |     const badResponses = [];
  36  |     page.on("console", (message) => {
  37  |       if (message.type() === "error") consoleErrors.push(message.text());
  38  |     });
  39  |     page.on("pageerror", (error) => pageErrors.push(error.message));
  40  |     page.on("response", (response) => {
  41  |       if (response.status() >= 400) badResponses.push({ status: response.status(), url: response.url() });
  42  |     });
  43  | 
  44  |     await page.goto("/login");
  45  |     await page.screenshot({ path: `.ui-audit/${mode.name}-login.png`, fullPage: true });
  46  |     const loginLayout = await page.evaluate(() => ({
  47  |       viewport: { width: innerWidth, height: innerHeight },
  48  |       documentWidth: document.documentElement.scrollWidth,
  49  |       bodyWidth: document.body.scrollWidth,
  50  |     }));
  51  | 
  52  |     await page.locator('input[autocomplete="username"]').fill(`_ui_audit_${mode.name}`);
  53  |     await page.locator('input[autocomplete="current-password"]').fill("AuditOnly-2026!");
  54  |     await page.getByRole("button", { name: "Sign in" }).click();
> 55  |     await page.waitForURL((url) => !url.pathname.includes("login"), { timeout: 15000 });
      |                ^ TimeoutError: page.waitForURL: Timeout 15000ms exceeded.
  56  | 
  57  |     const results = [];
  58  |     for (const [route, name] of routes) {
  59  |       consoleErrors.length = 0;
  60  |       pageErrors.length = 0;
  61  |       badResponses.length = 0;
  62  |       await page.goto(route);
  63  |       await page.waitForLoadState("networkidle");
  64  |       await page.waitForTimeout(500);
  65  |       await page.screenshot({ path: `.ui-audit/${mode.name}-${name}.png`, fullPage: true });
  66  |       results.push(await page.evaluate(({ route, consoleErrors, pageErrors, badResponses }) => {
  67  |         const visible = (element) => {
  68  |           const rect = element.getBoundingClientRect();
  69  |           const style = getComputedStyle(element);
  70  |           return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  71  |         };
  72  |         const smallTargets = [...document.querySelectorAll("button, a, input, select")]
  73  |           .filter(visible)
  74  |           .map((element) => {
  75  |             const rect = element.getBoundingClientRect();
  76  |             return {
  77  |               text: (element.innerText || element.getAttribute("aria-label") || element.getAttribute("title") || element.tagName).trim().slice(0, 80),
  78  |               width: Math.round(rect.width),
  79  |               height: Math.round(rect.height),
  80  |             };
  81  |           })
  82  |           .filter((target) => target.width < 40 || target.height < 40)
  83  |           .slice(0, 30);
  84  |         return {
  85  |           requestedRoute: route,
  86  |           finalUrl: location.pathname,
  87  |           title: document.querySelector("h1")?.textContent?.trim() || null,
  88  |           viewport: { width: innerWidth, height: innerHeight },
  89  |           documentWidth: document.documentElement.scrollWidth,
  90  |           bodyWidth: document.body.scrollWidth,
  91  |           horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
  92  |           sidebarVisible: [...document.querySelectorAll("aside")].some(visible),
  93  |           smallTargets,
  94  |           consoleErrors,
  95  |           pageErrors,
  96  |           badResponses,
  97  |         };
  98  |       }, { route, consoleErrors: [...consoleErrors], pageErrors: [...pageErrors], badResponses: [...badResponses] }));
  99  |     }
  100 | 
  101 |     await mkdir(".ui-audit", { recursive: true });
  102 |     await writeFile(`.ui-audit/${mode.name}-results.json`, JSON.stringify({ loginLayout, results }, null, 2));
  103 |     await context.close();
  104 |   });
  105 | }
  106 | 
```