import { test } from "file:///C:/Users/DarkZhen/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright/test.mjs";
import { mkdir, writeFile } from "node:fs/promises";

const routes = [
  ["/", "dashboard"],
  ["/classes", "classes"],
  ["/submissions", "submissions"],
  ["/reports", "reports"],
  ["/admin/class-records", "class-records"],
  ["/students", "students"],
  ["/teachers", "teachers"],
  ["/users", "users"],
  ["/academics", "academics"],
  ["/grading-config", "grading-config"],
  ["/settings", "settings"],
  ["/audit-log", "audit-log"],
];

const modes = [
  { name: "desktop", viewport: { width: 1440, height: 1000 }, isMobile: false, hasTouch: false },
  { name: "mobile", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
];

for (const mode of modes) {
  test(`${mode.name} portal audit`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: mode.viewport,
      isMobile: mode.isMobile,
      hasTouch: mode.hasTouch,
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    const badResponses = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400) badResponses.push({ status: response.status(), url: response.url() });
    });

    await page.goto("/login");
    await page.screenshot({ path: `.ui-audit/${mode.name}-login.png`, fullPage: true });
    const loginLayout = await page.evaluate(() => ({
      viewport: { width: innerWidth, height: innerHeight },
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
    }));

    await page.locator('input[autocomplete="username"]').fill(`_ui_audit_${mode.name}`);
    await page.locator('input[autocomplete="current-password"]').fill("AuditOnly-2026!");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL((url) => !url.pathname.includes("login"), { timeout: 15000 });

    const results = [];
    for (const [route, name] of routes) {
      consoleErrors.length = 0;
      pageErrors.length = 0;
      badResponses.length = 0;
      await page.goto(route);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(500);
      await page.screenshot({ path: `.ui-audit/${mode.name}-${name}.png`, fullPage: true });
      results.push(await page.evaluate(({ route, consoleErrors, pageErrors, badResponses }) => {
        const visible = (element) => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        };
        const smallTargets = [...document.querySelectorAll("button, a, input, select")]
          .filter(visible)
          .map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              text: (element.innerText || element.getAttribute("aria-label") || element.getAttribute("title") || element.tagName).trim().slice(0, 80),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
          })
          .filter((target) => target.width < 40 || target.height < 40)
          .slice(0, 30);
        return {
          requestedRoute: route,
          finalUrl: location.pathname,
          title: document.querySelector("h1")?.textContent?.trim() || null,
          viewport: { width: innerWidth, height: innerHeight },
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
          sidebarVisible: [...document.querySelectorAll("aside")].some(visible),
          smallTargets,
          consoleErrors,
          pageErrors,
          badResponses,
        };
      }, { route, consoleErrors: [...consoleErrors], pageErrors: [...pageErrors], badResponses: [...badResponses] }));
    }

    await mkdir(".ui-audit", { recursive: true });
    await writeFile(`.ui-audit/${mode.name}-results.json`, JSON.stringify({ loginLayout, results }, null, 2));
    await context.close();
  });
}
