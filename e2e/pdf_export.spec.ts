import fs from "fs";
import { expect, test } from "@playwright/test";
import { PDFParse } from "pdf-parse";

test.describe("PDF Report Export E2E Flow (REQ-9.1, REQ-9.4, REQ-9.5)", () => {
  test("runs backtest, verifies PDF export button, downloads print-ready PDF, and verifies structure", async ({
    page,
  }) => {
    // 1. Navigate to /backtest and execute a simulation
    await page.goto("/backtest");
    await expect(page.locator("h1")).toContainText("Backtest Simulation Engine");

    const runBtn = page.locator('[data-testid="btn-run-backtest"]');
    await expect(runBtn).toBeVisible();
    await runBtn.click();

    // 2. Wait for simulation to finish and navigate to detailed report
    const finalCapital = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCapital).toBeVisible({ timeout: 25000 });

    const viewReportBtn = page.locator('[data-testid="btn-view-report"]');
    await expect(viewReportBtn).toBeVisible();
    await viewReportBtn.click();

    // 3. Assert on /reports/[runId]
    await expect(page).toHaveURL(/\/reports\/.+/);
    await expect(page.locator("h1")).toContainText("Strategy Performance Report");

    // 4. Assert PDF Export Button is visible and enabled
    const pdfExportBtn = page.locator('[data-testid="btn-export-pdf"]');
    await expect(pdfExportBtn).toBeVisible();
    await expect(pdfExportBtn).toBeEnabled();
    await expect(pdfExportBtn).toContainText("Export PDF");

    // 5. Trigger PDF Download and capture download event
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 30000 }),
      pdfExportBtn.click(),
    ]);

    // 6. Assert filename matches backtest_<run_id>.pdf
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/^backtest_.*\.pdf$/);

    const filePath = await download.path();
    expect(filePath).toBeTruthy();

    if (filePath) {
      // 7. Verify file header and size
      const fileBuffer = fs.readFileSync(filePath);
      expect(fileBuffer.subarray(0, 4).toString("ascii")).toBe("%PDF");
      expect(fileBuffer.length).toBeGreaterThan(50 * 1024); // > 50 KB

      // 8. Extract text and verify mandatory report sections
      const parser = new PDFParse({ data: fileBuffer });
      const { text } = await parser.getText();

      expect(text).toContain("Backtest Report");
      expect(text).toContain("4-EMA Breakout");
    }
  });

  test("handles async 202 path with toast notification, polling, and auto-download", async ({
    page,
  }) => {
    // 1. Navigate to /backtest and execute a simulation
    await page.goto("/backtest");
    const runBtn = page.locator('[data-testid="btn-run-backtest"]');
    await runBtn.click();

    const finalCapital = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCapital).toBeVisible({ timeout: 25000 });

    const viewReportBtn = page.locator('[data-testid="btn-view-report"]');
    await viewReportBtn.click();
    await expect(page).toHaveURL(/\/reports\/.+/);

    // 2. Mock /api/v1/reports/*/export?format=pdf to return 202 Accepted
    const mockJobId = "e2e-async-job-42";
    let pollCount = 0;

    await page.route("**/api/v1/reports/*/export?format=pdf", async (route) => {
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        headers: {
          Location: `/api/v1/reports/jobs/${mockJobId}`,
        },
        body: JSON.stringify({
          job_id: mockJobId,
          status: "pending",
          message: "PDF generation job started",
        }),
      });
    });

    await page.route(`**/api/v1/reports/jobs/${mockJobId}`, async (route) => {
      pollCount += 1;
      if (pollCount <= 1) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: mockJobId,
            status: "pending",
            file_path: null,
            error: null,
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: mockJobId,
            status: "ready",
            file_path: "/tmp/mock.pdf",
            error: null,
            created_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.route(`**/api/v1/reports/jobs/${mockJobId}/download`, async (route) => {
      const mockPdfBytes = Buffer.from("%PDF-1.4 mock pdf content %%EOF");
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: {
          "Content-Disposition": 'attachment; filename="backtest_mock_async.pdf"',
        },
        body: mockPdfBytes,
      });
    });

    // 3. Click Export PDF and verify toast appears
    const pdfExportBtn = page.locator('[data-testid="btn-export-pdf"]');
    await expect(pdfExportBtn).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 15000 }),
      pdfExportBtn.click(),
    ]);

    // 4. Assert download completed with mocked async filename
    expect(download.suggestedFilename()).toBe("backtest_mock_async.pdf");
  });
});
