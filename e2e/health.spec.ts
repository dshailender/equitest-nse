import { expect, test } from "@playwright/test";

test.describe("Health Check E2E Flow", () => {
  test("landing page renders title and navigates to health page", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Backtesting Framework");

    // Click link to health page via navbar
    await page.click('header nav >> text="API Health"');
    await page.waitForURL("**/api-health");
    await expect(page.locator("h1")).toContainText("API Health Diagnostic");
  });

  test("loads api-health and asserts backend health shows ok and version", async ({ page }) => {
    await page.goto("/api-health");

    // Wait for the backend health status element to render
    const statusLocator = page.locator('[data-testid="health-status"]');
    await expect(statusLocator).toBeVisible({ timeout: 15000 });
    await expect(statusLocator).toHaveText("ok");

    // Assert version is rendered
    const versionLocator = page.locator('[data-testid="health-version"]');
    await expect(versionLocator).toBeVisible();
    await expect(versionLocator).toHaveText("0.1.0");

    // Assert operational badge is rendered
    const badgeLocator = page.locator('[data-testid="health-badge-ok"]');
    await expect(badgeLocator).toBeVisible();
    await expect(badgeLocator).toContainText("Operational");
  });
});
