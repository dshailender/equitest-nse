import { expect, test } from "@playwright/test";

test.describe("Strategy Signals & Execution E2E Flow", () => {
  test("navigates to /signals, filters date range, verifies entry signal row and universe screening", async ({
    page,
  }) => {
    // 1. Navigate to /signals
    await page.goto("/signals");
    await expect(page.locator("h1")).toContainText(
      "Trading Signals & Strategy Rules"
    );

    // 2. Select MIDCAP_STOCK_101 and set date range containing known entry signals
    const symbolSelect = page.locator('[data-testid="signal-symbol-select"]');
    await expect(symbolSelect).toBeVisible();
    await symbolSelect.selectOption("MIDCAP_STOCK_101");

    await page.fill('[data-testid="signal-start-date"]', "2020-06-01");
    await page.fill('[data-testid="signal-end-date"]', "2020-07-31");

    // 3. Confirm signals table is loaded
    const table = page.locator('[data-testid="signals-table"]');
    await expect(table).toBeVisible({ timeout: 15000 });

    const rows = table.locator('[data-testid="signal-row"]');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });

    // 4. Toggle "Only Entries" filter
    const entriesToggle = page.locator('[data-testid="only-entries-toggle"]');
    await expect(entriesToggle).toBeVisible();
    await entriesToggle.click();

    // 5. Assert entry badge appears with date 2020-06-25
    const entryBadge = page.locator('[data-testid="entry-badge"]').first();
    await expect(entryBadge).toBeVisible({ timeout: 10000 });
    await expect(entryBadge).toContainText("BUY / ENTRY");

    const entryRow = page.locator('[data-testid="signal-row"]', {
      hasText: "2020-06-25",
    });
    await expect(entryRow).toBeVisible();

    // 6. Test Universe Screening for 2020-06-25
    await page.fill('[data-testid="screen-date-input"]', "2020-06-25");
    const screenBtn = page.locator('[data-testid="screen-button"]');
    await screenBtn.click();

    const screenCard = page.locator('[data-testid="screen-results-card"]');
    await expect(screenCard).toBeVisible({ timeout: 15000 });
    await expect(screenCard).toContainText("BALKRISIND");
  });
});

