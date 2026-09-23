import { expect, test } from "@playwright/test";

test.describe("Data Ingestion and Status E2E Flow", () => {
  test("triggers ingest, populates coverage, and opens prices chart", async ({ page }) => {
    // 1. Navigate to /data page
    await page.goto("/data");
    await expect(page.locator("h1")).toContainText("Data Pipeline & Market Universe");

    // 2. Set date range and trigger ingestion
    await page.fill('[data-testid="ingest-start"]', "2020-01-01");
    await page.fill('[data-testid="ingest-end"]', "2021-12-31");
    await page.click('[data-testid="ingest-button"]');

    // 3. Confirm ingestion status banner completes
    const banner = page.locator('[data-testid="ingest-status-banner"]');
    await expect(banner).toBeVisible({ timeout: 20000 });
    await expect(banner).toContainText(/Ingested.*rows across.*symbols/i);

    // 4. Verify coverage table contains ingested symbols
    const relianceRow = page.locator('[data-testid="coverage-row-RELIANCE"]');
    await expect(relianceRow).toBeVisible({ timeout: 10000 });
    await expect(relianceRow).toContainText("RELIANCE");

    // 5. Click row to drill down into prices
    await relianceRow.click();

    // 6. Assert prices drilldown card and Recharts graph render
    const chartCard = page.locator('[data-testid="prices-drilldown-card"]');
    await expect(chartCard).toBeVisible();
    await expect(chartCard).toContainText("RELIANCE");

    const chart = page.locator('[data-testid="prices-chart"]');
    await expect(chart).toBeVisible();
    // Recharts renders SVG containers inside the chart element
    await expect(chart.locator("svg.recharts-surface").first()).toBeVisible({ timeout: 10000 });

    // 7. Verify universe explorer renders constituents
    const tickersContainer = page.locator('[data-testid="universe-tickers"]');
    await expect(tickersContainer).toBeVisible();
    await expect(tickersContainer.locator("span")).not.toHaveCount(0);
  });
});
