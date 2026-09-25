import fs from "fs";
import { expect, test } from "@playwright/test";

test.describe("Institutional Acceptance Suite (REQ-8.5)", () => {
  test.setTimeout(90000);

  test("1. System Health: verifies backend health API and frontend status page", async ({
    page,
    request,
  }) => {
    // Backend health endpoint
    const apiHealth = await request.get("http://127.0.0.1:8000/health");
    expect(apiHealth.ok()).toBeTruthy();
    const data = await apiHealth.json();
    expect(data.status).toBe("ok");
    expect(data.version).toBe("0.1.0");

    // Frontend health UI
    await page.goto("/api-health");
    await expect(page.locator("h1")).toContainText("API Health Diagnostic");
    const statusElem = page.locator('[data-testid="health-status"]');
    await expect(statusElem).toBeVisible({ timeout: 15000 });
    await expect(statusElem).toHaveText("ok");
    await expect(page.locator('[data-testid="health-version"]')).toHaveText("0.1.0");
    await expect(page.locator('[data-testid="health-badge-ok"]')).toBeVisible();
    await expect(page.locator('[data-testid="health-badge-ok"]')).toContainText("Operational");
  });

  test("2. Baseline Backtest: executes simulation and asserts financial invariants and KPIs", async ({
    page,
  }) => {
    await page.goto("/backtest");
    await expect(page.locator("h1")).toContainText("Backtest Simulation Engine");

    const runBtn = page.locator('[data-testid="btn-run-backtest"]');
    await runBtn.click();

    // Verify baseline results
    const finalCapitalElem = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCapitalElem).toBeVisible({ timeout: 25000 });
    await expect(finalCapitalElem).toContainText("496,264");

    const totalTradesElem = page.locator('[data-testid="total-trades-value"]');
    await expect(totalTradesElem).toHaveText("11");

    const winRateElem = page.locator('[data-testid="win-rate-value"]');
    await expect(winRateElem).toHaveText("36.4%");

    // Verify Trade Ledger contains universe constituent trades with exit signal
    const tradesTable = page.locator('[data-testid="trades-table"]');
    await expect(tradesTable).toBeVisible();
    await expect(tradesTable).toContainText("MIDCAP_STOCK_101");
    await expect(tradesTable).toContainText("Exit Signal");
  });

  test("3. Extended Backtest: executes multi-year date simulation via API contract", async ({
    request,
  }) => {
    // Run backtest across extended range
    const runResp = await request.post("http://127.0.0.1:8000/api/v1/backtest/run", {
      data: {
        start: "2020-06-01",
        end: "2022-04-29",
        config: {
          capital: 500000,
          risk_pct: 0.02,
          sl_pct: 0.07,
        },
      },
    });

    expect(runResp.status()).toBe(202);
    const { run_id } = await runResp.json();
    expect(run_id).toBeTruthy();

    let status = "pending";
    let runResult: any = null;
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 500));
      const res = await request.get(`http://127.0.0.1:8000/api/v1/backtest/${run_id}`);
      if (res.ok()) {
        runResult = await res.json();
        status = runResult.status;
        if (status === "completed" || status === "failed") break;
      }
    }
    expect(status).toBe("completed");
    expect(runResult.final_capital).toBeGreaterThan(0);
  });

  test("4. Parameter Sweep: executes 2D grid sweep and verifies sensitivity heatmap", async ({
    page,
  }) => {
    await page.goto("/sweep");
    await expect(page.locator("h1")).toContainText("Parameter & Scenario Sweep");

    const runBtn = page.locator('[data-testid="btn-run-sweep"]');
    await runBtn.click();

    const runsTable = page.locator('[data-testid="sweep-runs-table"]');
    await expect(runsTable).toBeVisible({ timeout: 45000 });
    await expect(page.locator("text=Sweep Status: completed")).toBeVisible({ timeout: 45000 });
    await expect(page.locator("text=4 / 4 completed")).toBeVisible();

    await expect(
      page.locator("text=Sensitivity Heatmap (CAGR % by sl_pct vs risk_pct)")
    ).toBeVisible();
  });

  test("5. Comprehensive Reporting & Provenance Audit: verifies metrics, charts, exports, and audit trail", async ({
    page,
  }) => {
    // Navigate to backtest and execute to get run ID
    await page.goto("/backtest");
    await page.locator('[data-testid="btn-run-backtest"]').click();

    const finalCap = page.locator('[data-testid="final-capital-value"]');
    await expect(finalCap).toBeVisible({ timeout: 25000 });

    // Open detailed report
    await page.locator('[data-testid="btn-view-report"]').click();
    await expect(page).toHaveURL(/\/reports\/.+/);
    await expect(page.locator("h1")).toContainText("Strategy Performance Report");

    // Verify KPI Cards
    await expect(page.locator('[data-testid="metric-final-capital"]')).toContainText("496,264");
    await expect(page.locator('[data-testid="metric-total-trades"]')).toHaveText("11");
    await expect(page.locator('[data-testid="metric-cagr"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-max-drawdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-sharpe"]')).toBeVisible();

    // Verify Charts & Monthly Matrix
    await expect(page.locator('[data-testid="chart-drawdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="chart-histogram"]')).toBeVisible();
    await expect(page.locator('[data-testid="table-monthly-returns"]')).toBeVisible();

    // Verify Audit Provenance Panel (REQ-8.2)
    const auditPanel = page.locator('[data-testid="audit-panel"]');
    await expect(auditPanel).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="audit-git-sha"]')).toBeVisible();
    const gitShaText = await page.locator('[data-testid="audit-git-sha"]').innerText();
    expect(gitShaText.trim().length).toBeGreaterThanOrEqual(7);

    await expect(page.locator('[data-testid="audit-data-hash"]')).toBeVisible();
    const dataHashText = await page.locator('[data-testid="audit-data-hash"]').innerText();
    expect(dataHashText.trim().length).toBe(64); // SHA-256

    await expect(page.locator('[data-testid="audit-versions"]')).toBeVisible();

    // Export CSV
    const [csvDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-csv"]').click(),
    ]);
    const csvPath = await csvDownload.path();
    expect(csvPath).toBeTruthy();
    if (csvPath) {
      expect(fs.statSync(csvPath).size).toBeGreaterThan(0);
      const content = fs.readFileSync(csvPath, "utf-8");
      expect(content).toContain("symbol,entry_date");
    }

    // Export XLSX
    const [xlsxDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-xlsx"]').click(),
    ]);
    const xlsxPath = await xlsxDownload.path();
    expect(xlsxPath).toBeTruthy();
    if (xlsxPath) {
      expect(fs.statSync(xlsxPath).size).toBeGreaterThan(0);
    }

    // Export ZIP
    const [zipDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-export-zip"]').click(),
    ]);
    const zipPath = await zipDownload.path();
    expect(zipPath).toBeTruthy();
    if (zipPath) {
      expect(fs.statSync(zipPath).size).toBeGreaterThan(0);
    }
  });

  test("6. TradingView Cross-Check: verifies visual diff table and CSV exporter (REQ-8.1)", async ({
    page,
  }) => {
    await page.goto("/validation");
    await expect(page.locator("h1")).toContainText("TradingView Cross-Check Verification");

    // Wait for table rows to load and populate
    const rows = page.locator('[data-testid="cross-check-row"]');
    await expect(rows.first()).toBeVisible({ timeout: 20000 });

    // Assert session count stat is populated and > 0
    const sessionsStat = page.locator('[data-testid="stat-sessions"]');
    await expect(sessionsStat).toBeVisible();
    await expect(sessionsStat).not.toHaveText("0", { timeout: 5000 });
    const sessionCount = parseInt(await sessionsStat.innerText(), 10);
    expect(sessionCount).toBeGreaterThan(0);

    // Verify CSV Download
    const [tvDownload] = await Promise.all([
      page.waitForEvent("download"),
      page.locator('[data-testid="btn-download-tv"]').click(),
    ]);
    expect(tvDownload.suggestedFilename()).toMatch(/cross_check.*\.csv$/i);
    const tvCsvPath = await tvDownload.path();
    expect(tvCsvPath).toBeTruthy();
    if (tvCsvPath) {
      const tvStats = fs.statSync(tvCsvPath);
      expect(tvStats.size).toBeGreaterThan(0);
      const tvContent = fs.readFileSync(tvCsvPath, "utf-8");
      expect(tvContent).toContain("date,close,ema_20,ema_50,ema_150,ema_200,high_52w,entry,exit");
    }
  });

  test("7. In-App Documentation: verifies architecture, PRD §2 strategy rules, and PRD §4 open questions (REQ-8.4)", async ({
    page,
  }) => {
    await page.goto("/docs");
    await expect(page.locator("h1")).toContainText("EquiTest NSE Documentation & Knowledge Base");

    // Overview Tab
    await expect(page.locator("text=Clone to Execution in < 15 Minutes")).toBeVisible();
    await expect(page.locator("text=Zero Look-Ahead Guarantee")).toBeVisible();

    // Architecture Tab
    await page.locator('[data-testid="tab-architecture"]').click();
    await expect(page.locator("text=System Architecture & Monorepo Boundaries")).toBeVisible();
    await expect(page.locator("text=Backend Subsystems")).toBeVisible();
    await expect(page.locator("text=Frontend Subsystems")).toBeVisible();

    // Strategy Rules Tab
    await page.locator('[data-testid="tab-strategy"]').click();
    await expect(page.locator("text=Quantitative Strategy Rules (Verbatim from PRD §2)")).toBeVisible();
    await expect(page.locator("text=1. Market Regime Filter")).toBeVisible();
    await expect(page.locator("text=2. Stock Trend Filter")).toBeVisible();
    await expect(page.locator("text=3. 52-Week High Proximity Filter")).toBeVisible();
    await expect(page.locator("text=4. Entry Crossover Trigger & Execution")).toBeVisible();
    await expect(page.locator("text=5. Risk Allocation & Sizing")).toBeVisible();

    // Assumptions Tab (PRD §4 Open Questions)
    await page.locator('[data-testid="tab-assumptions"]').click();
    await expect(page.locator('[data-testid="content-assumptions"]')).toBeVisible();
    await expect(page.locator("text=Open Question #1: Universe Boundaries & Top 100 Exclusion")).toBeVisible();
    await expect(page.locator("text=Open Question #2: Overnight Gap-Down Stop-Loss Resolution")).toBeVisible();
    await expect(page.locator("text=Open Question #3: Candidate Ranking Rule Under Capital Limits")).toBeVisible();
    await expect(page.locator("text=Open Question #4: Cash Equities Lot Sizing")).toBeVisible();
    await expect(page.locator("text=Open Question #5: Corporate Actions & Rolling 52-Week Ceiling")).toBeVisible();
    await expect(page.locator("text=Open Question #6: Friction & Slippage Cost Modeling")).toBeVisible();

    // Runbook Tab
    await page.locator('[data-testid="tab-runbook"]').click();
    await expect(page.locator("text=How to Change a Strategy Parameter Walkthrough")).toBeVisible();
    await expect(page.locator("text=Update Backend Schema:")).toBeVisible();
  });
});
