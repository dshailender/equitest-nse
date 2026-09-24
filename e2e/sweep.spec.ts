import { expect, test } from "@playwright/test";

test.describe("Parameter & Scenario Sweep E2E Flow", () => {
  test("navigates to /sweep, executes 2x2 parameter sweep, verifies heatmap & runs table, and opens compare drawer", async ({
    page,
  }) => {
    test.setTimeout(60000);

    // 1. Navigate to /sweep
    await page.goto("/sweep");
    await expect(page.locator("h1")).toContainText("Parameter & Scenario Sweep");

    // 2. Assert builder inputs are visible with default parameters (2x2 = 4 runs)
    const startInput = page.locator('[data-testid="input-start-date"]');
    const endInput = page.locator('[data-testid="input-end-date"]');
    const capitalInput = page.locator('[data-testid="input-capital"]');

    await expect(startInput).toHaveValue("2020-06-01");
    await expect(endInput).toHaveValue("2022-04-29");
    await expect(capitalInput).toHaveValue("500000");
    await expect(page.locator("text=4 runs")).toBeVisible();

    // 3. Trigger parameter sweep
    const runBtn = page.locator('[data-testid="btn-run-sweep"]');
    await runBtn.click();

    // 4. Wait for sweep completion and runs table to populate
    const runsTable = page.locator('[data-testid="sweep-runs-table"]');
    await expect(runsTable).toBeVisible({ timeout: 40000 });

    // Verify completed status text in progress banner
    await expect(page.locator("text=Sweep Status: completed")).toBeVisible({ timeout: 40000 });
    await expect(page.locator("text=4 / 4 completed")).toBeVisible();

    // 5. Verify 2D Sensitivity Heatmap is rendered
    await expect(
      page.locator("text=Sensitivity Heatmap (CAGR % by sl_pct vs risk_pct)")
    ).toBeVisible();

    // 6. Select first two runs using checkboxes in the table
    const checkboxes = runsTable.locator('input[type="checkbox"]');
    await expect(checkboxes).toHaveCount(4);
    await checkboxes.nth(0).click();
    await checkboxes.nth(1).click();

    // 7. Verify Compare button is enabled with 2 runs selected
    const compareBtn = page.locator('[data-testid="btn-open-compare"]');
    await expect(compareBtn).toContainText("Compare Selected (2)");
    await compareBtn.click();

    // 8. Assert comparison drawer and overlaid equity chart render
    const compareDrawer = page.locator('[data-testid="compare-drawer"]');
    await expect(compareDrawer).toBeVisible({ timeout: 10000 });
    await expect(
      compareDrawer.locator("text=Multi-Run Comparison (2 runs)")
    ).toBeVisible();

    const compareChart = page.locator('[data-testid="compare-chart"]');
    await expect(compareChart).toBeVisible();

    // 9. Close compare drawer
    const closeBtn = page.locator('[data-testid="btn-close-compare"]');
    await closeBtn.click();
    await expect(compareDrawer).not.toBeVisible();
  });
});
