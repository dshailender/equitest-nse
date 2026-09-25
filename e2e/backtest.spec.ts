import { expect, test } from "@playwright/test";

test.describe("Backtest Simulation Engine E2E Flow", () => {
  test("navigates to /backtest, runs simulation with default parameters, and verifies KPIs and trades ledger", async ({
    page,
  }) => {
    // 1. Navigate to /backtest
    await page.goto("/backtest");
    await expect(page.locator("h1")).toContainText("Backtest Simulation Engine");

    // 2. Assert form inputs are visible with default parameters
    const startInput = page.locator('[data-testid="input-start-date"]');
    const endInput = page.locator('[data-testid="input-end-date"]');
    const corpusInput = page.locator('[data-testid="input-corpus"]');
    const riskInput = page.locator('[data-testid="input-risk"]');
    const slInput = page.locator('[data-testid="input-sl"]');

    await expect(startInput).toHaveValue("2020-06-01");
    await expect(endInput).toHaveValue("2022-04-29");
    await expect(corpusInput).toHaveValue("500000");
    await expect(riskInput).toHaveValue("2");
    await expect(slInput).toHaveValue("7");

    // 3. Trigger backtest simulation
    const runBtn = page.locator('[data-testid="btn-run-backtest"]');
    await runBtn.click();

    // 4. Wait for simulation to finish and summary cards to populate
    const finalCapitalElem = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCapitalElem).toBeVisible({ timeout: 30000 });
    // Final capital should reflect universe constituents (₹630,365.73)
    await expect(finalCapitalElem).toContainText("630,365");

    const totalTradesElem = page.locator('[data-testid="total-trades-value"]');
    await expect(totalTradesElem).toHaveText("87");

    const winRateElem = page.locator('[data-testid="win-rate-value"]');
    await expect(winRateElem).toHaveText("41.4%");

    // 5. Verify Equity Chart is displayed
    const chartContainer = page.locator('[data-testid="equity-chart-container"]');
    await expect(chartContainer).toBeVisible();

    // 6. Verify Trade Ledger table contains universe constituent trades with exit reasons
    const tradesTable = page.locator('[data-testid="trades-table"]');
    await expect(tradesTable).toBeVisible();
    await expect(tradesTable).toContainText("FEDERALBNK");
    await expect(tradesTable).toContainText("Exit Signal");
  });
});

