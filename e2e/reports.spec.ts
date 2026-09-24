import fs from "fs";
import { expect, test } from "@playwright/test";

test.describe("Strategy Reports & Analytics E2E Flow", () => {
  test("runs backtest, navigates to detailed report, verifies KPIs, charts, and exports non-zero files", async ({
    page,
  }) => {
    // 1. Navigate to /backtest and run default simulation
    await page.goto("/backtest");
    await expect(page.locator("h1")).toContainText("Backtest Simulation Engine");

    const runBtn = page.locator('[data-testid="btn-run-backtest"]');
    await runBtn.click();

    // 2. Wait for simulation to finish
    const finalCapitalBacktest = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCapitalBacktest).toBeVisible({ timeout: 20000 });
    await expect(finalCapitalBacktest).toContainText("482,707");

    // 3. Click "View Detailed Report & Analytics"
    const viewReportBtn = page.locator('[data-testid="btn-view-report"]');
    await expect(viewReportBtn).toBeVisible();
    await viewReportBtn.click();

    // 4. Assert navigation to /reports/[runId]
    await expect(page).toHaveURL(/\/reports\/.+/);
    await expect(page.locator("h1")).toContainText("Strategy Performance Report");

    // 5. Verify Core KPI metrics
    const finalCapMetric = page.locator('[data-testid="metric-final-capital"]');
    await expect(finalCapMetric).toBeVisible();
    await expect(finalCapMetric).toContainText("482,707");

    const totalTradesMetric = page.locator('[data-testid="metric-total-trades"]');
    await expect(totalTradesMetric).toHaveText("2");

    const winRateMetric = page.locator('[data-testid="metric-win-rate"]');
    await expect(winRateMetric).toHaveText("0.00%");

    // 6. Verify Advanced KPI metrics
    const cagrMetric = page.locator('[data-testid="metric-cagr"]');
    await expect(cagrMetric).toBeVisible();

    const maxDdMetric = page.locator('[data-testid="metric-max-drawdown"]');
    await expect(maxDdMetric).toBeVisible();

    const sharpeMetric = page.locator('[data-testid="metric-sharpe"]');
    await expect(sharpeMetric).toBeVisible();

    const sortinoMetric = page.locator('[data-testid="metric-sortino"]');
    await expect(sortinoMetric).toBeVisible();

    const calmarMetric = page.locator('[data-testid="metric-calmar"]');
    await expect(calmarMetric).toBeVisible();

    const pfMetric = page.locator('[data-testid="metric-profit-factor"]');
    await expect(pfMetric).toBeVisible();

    const expMetric = page.locator('[data-testid="metric-expectancy"]');
    await expect(expMetric).toBeVisible();

    // 7. Verify Visualizations & Monthly Table
    await expect(page.locator('[data-testid="chart-drawdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="chart-histogram"]')).toBeVisible();
    await expect(page.locator('[data-testid="table-monthly-returns"]')).toBeVisible();

    // 8. Test CSV Export Download
    const [csvDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-csv"]').click(),
    ]);
    expect(csvDownload.suggestedFilename()).toMatch(/\.csv$/i);
    const csvPath = await csvDownload.path();
    expect(csvPath).toBeTruthy();
    if (csvPath) {
      const csvStats = fs.statSync(csvPath);
      expect(csvStats.size).toBeGreaterThan(0);
      const csvContent = fs.readFileSync(csvPath, "utf-8");
      expect(csvContent).toContain("Metric,Value");
    }

    // 9. Test XLSX Export Download
    const [xlsxDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-xlsx"]').click(),
    ]);
    expect(xlsxDownload.suggestedFilename()).toMatch(/\.xlsx$/i);
    const xlsxPath = await xlsxDownload.path();
    expect(xlsxPath).toBeTruthy();
    if (xlsxPath) {
      const xlsxStats = fs.statSync(xlsxPath);
      expect(xlsxStats.size).toBeGreaterThan(0);
    }

    // 10. Test ZIP Export Download
    const [zipDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-zip"]').click(),
    ]);
    expect(zipDownload.suggestedFilename()).toMatch(/\.zip$/i);
    const zipPath = await zipDownload.path();
    expect(zipPath).toBeTruthy();
    if (zipPath) {
      const zipStats = fs.statSync(zipPath);
      expect(zipStats.size).toBeGreaterThan(0);
    }
  });
});
