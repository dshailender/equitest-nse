import { expect, test } from "@playwright/test";

test.describe("Technical Indicators Preview E2E Flow", () => {
  test("navigates to /indicators, loads BALKRISIND chart, renders 4 EMAs, and toggles EMA-150", async ({
    page,
  }) => {
    // 1. Navigate to /indicators
    await page.goto("/indicators");
    await expect(page.locator("h1")).toContainText(
      "Technical Indicators & EMA Preview"
    );

    // 2. Select BALKRISIND and specify date range
    const symbolSelect = page.locator('[data-testid="indicator-symbol-select"]');
    await expect(symbolSelect).toBeVisible();
    await symbolSelect.selectOption("BALKRISIND");

    await page.fill('[data-testid="indicator-start-date"]', "2021-01-01");
    await page.fill('[data-testid="indicator-end-date"]', "2022-12-31");

    // 3. Confirm chart container is visible
    const chartCard = page.locator('[data-testid="indicator-chart-card"]');
    await expect(chartCard).toBeVisible({ timeout: 15000 });
    await expect(chartCard).toContainText("BALKRISIND");

    const chart = page.locator('[data-testid="indicator-chart"]');
    await expect(chart).toBeVisible({ timeout: 15000 });

    // 4. Assert 4 EMA lines render in the SVG
    const emaLines = chart.locator(".ema-line");
    await expect(emaLines).toHaveCount(4, { timeout: 15000 });

    // 5. Toggle EMA-150 off
    const toggleEma150 = page.locator('[data-testid="toggle-ema-150"]');
    await expect(toggleEma150).toBeVisible();
    await toggleEma150.click();

    // 6. Assert exactly 3 EMA lines remain in the SVG
    await expect(emaLines).toHaveCount(3, { timeout: 10000 });
    await expect(toggleEma150).toHaveClass(/line-through/);
  });
});
