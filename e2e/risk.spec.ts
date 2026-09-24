import { expect, test } from "@playwright/test";

test.describe("Risk & Position Sizing E2E Flow", () => {
  test("navigates to /risk, submits default form, and verifies calculated position metrics", async ({
    page,
  }) => {
    // 1. Navigate to /risk
    await page.goto("/risk");
    await expect(page.locator("h1")).toContainText("Risk & Position Sizing");

    // 2. Assert form inputs are visible with default PRD values
    const corpusInput = page.locator('[data-testid="input-corpus"]');
    const entryInput = page.locator('[data-testid="input-entry"]');
    const slInput = page.locator('[data-testid="input-sl"]');
    const riskInput = page.locator('[data-testid="input-risk"]');

    await expect(corpusInput).toBeVisible();
    await expect(corpusInput).toHaveValue("500000");
    await expect(entryInput).toHaveValue("100");
    await expect(slInput).toHaveValue("7");
    await expect(riskInput).toHaveValue("2");

    // 3. Click submit / calculate button
    const calculateBtn = page.locator('[data-testid="btn-calculate"]');
    await calculateBtn.click();

    // 4. Assert position sizing results match fixture expectations
    const qtyElem = page.locator('[data-testid="result-qty"]');
    await expect(qtyElem).toBeVisible({ timeout: 10000 });
    await expect(qtyElem).toContainText("1,428");

    const capitalElem = page.locator('[data-testid="result-capital"]');
    await expect(capitalElem).toContainText("1,42,800");

    const slPriceElem = page.locator('[data-testid="result-sl-price"]');
    await expect(slPriceElem).toContainText("93");

    const riskAmtElem = page.locator('[data-testid="result-risk-amount"]');
    await expect(riskAmtElem).toContainText("10,000");

    // 5. Test updating form with alternative corpus ₹1,00,000
    await corpusInput.fill("100000");
    await calculateBtn.click();

    await expect(qtyElem).toContainText("285");
    await expect(capitalElem).toContainText("28,500");
    await expect(riskAmtElem).toContainText("2,000");
  });
});

