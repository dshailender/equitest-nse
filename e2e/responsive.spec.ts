import { expect, test } from "@playwright/test";

const pages = [
  { name: "home", path: "/" },
  { name: "data", path: "/data" },
  { name: "indicators", path: "/indicators" },
  { name: "signals", path: "/signals" },
  { name: "risk", path: "/risk" },
  { name: "backtest", path: "/backtest" },
  { name: "sweep", path: "/sweep" },
  { name: "reports", path: "/reports/test-run-123" },
  { name: "reports-index", path: "/reports" },
  { name: "validation", path: "/validation" },
  { name: "docs", path: "/docs" },
  { name: "api-health", path: "/api-health" },
];

const viewports = [
  { name: "mobile_375", width: 375, height: 667 },
  { name: "tablet_768", width: 768, height: 1024 },
];

test.describe("AUD-D-001 Responsive Horizontal Overflow Verification", () => {
  for (const vp of viewports) {
    for (const pageInfo of pages) {
      test(`${pageInfo.name} (${pageInfo.path}) has zero horizontal overflow at ${vp.name} (${vp.width}px)`, async ({
        page,
      }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(pageInfo.path, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(400);

        const { scrollWidth, innerWidth } = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
        }));

        expect(
          scrollWidth,
          `Expected ${pageInfo.name} scrollWidth (${scrollWidth}px) <= innerWidth (${innerWidth}px) at ${vp.name}`
        ).toBeLessThanOrEqual(innerWidth);
      });
    }
  }

  test("Navbar mobile hamburger menu toggles correctly at 375px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/", { waitUntil: "domcontentloaded" });

    const menuBtn = page.locator('[data-testid="btn-toggle-menu"]');
    await expect(menuBtn).toBeVisible();

    const mobileMenu = page.locator('[data-testid="mobile-menu"]');
    await expect(mobileMenu).not.toBeVisible();

    await menuBtn.click();
    await expect(mobileMenu).toBeVisible();
    await expect(mobileMenu.locator("text=Backtest")).toBeVisible();

    await menuBtn.click();
    await expect(mobileMenu).not.toBeVisible();
  });
});
