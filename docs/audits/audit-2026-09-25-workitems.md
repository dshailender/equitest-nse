=== AUDIT ARTIFACT ===
# EquiTest NSE — Audit Work Items Backlog
Date: 2026-09-25
Audited SHA: 63a8154cade19039f9f7ce45c8ccedfaa0d8ba13

---

### AUD-A-001
- **ID**: AUD-A-001
- **Title**: Fix backtest simulation defaulting to mock synthetic universe (ALPHA, BETA, GAMMA) instead of NSE 101–750
- **Domain**: A
- **Category**: Correctness
- **Severity**: Blocker
- **Reproducibility**: Always
- **Description**: When a user triggers a backtest via the UI or API without explicitly supplying a custom symbol list, the backend execution worker defaults to loading synthetic fixture stocks `['ALPHA', 'BETA', 'GAMMA']` from `data/fixtures/tiny_universe/`. Across a 5-year simulation, this results in only 2 closed trades total, 100% concentrated in synthetic symbol 'ALPHA', rather than evaluating the authentic active NSE 101–750 constituent universe.
- **Expected**: Per REQ-1.1 and REQ-5.1, when `symbols` is omitted in the backtest request, the engine must resolve and execute across the full active NSE 101–750 equity constituent universe (650 symbols).
- **Actual**: Backend loads `['ALPHA', 'BETA', 'GAMMA']` if `tiny_universe/ALPHA.parquet` exists on disk. Total trades executed over 5 years is exactly 2, exclusively in ALPHA.
- **Evidence**:
  - `docs/audits/evidence/domain-a/backtest_5y_run1.json`
  - `docs/audits/evidence/domain-a/trade_verification.txt`
- **Suspected root cause**: `backend/app/api/v1/backtest.py:79-81`
- **Suggested fix**: Remove the conditional branch that checks for `tiny_universe/ALPHA.parquet` in production backtest dispatching, and ensure `get_universe` resolves the full 650 constituent tickers.
- **Acceptance criteria**:
  - Backtest triggered with default parameters evaluates real universe constituents.
  - Closed trades ledger contains trades from authentic NSE mid/small-cap universe symbols.
  - Trade count over 5 years reflects normal market opportunities (> 50 trades).
- **Suggested conversation**: Phase 5 engine fix
- **Effort**: M
- **Blocks**: AUD-A-002, AUD-H-001
- **Blocked by**: None

---

### AUD-A-002
- **ID**: AUD-A-002
- **Title**: Prevent silent truncation of 10-year and 15-year backtest date ranges when historical data is absent
- **Domain**: A
- **Category**: Data Integrity
- **Severity**: Critical
- **Reproducibility**: Always
- **Description**: Requesting a 10-year (2014–2024) or 15-year (2009–2024) backtest silently truncates the simulation window to the narrow fixture dates (2020–2022, 500 trading days) without returning any error or warning. The engine then annualizes CAGR over 500 days instead of the requested 10 or 15 calendar years, falsely presenting a 2-year result as a 15-year performance record.
- **Expected**: If historical price data does not cover the requested horizon, the engine must return a 422 Unprocessable Entity or an explicit warning object detailing the truncated date boundaries.
- **Actual**: 10-year and 15-year runs return identical status with exactly 500 equity curve points, 2 trades, and identical CAGR (-1.83%).
- **Evidence**:
  - `docs/audits/evidence/domain-a/backtest_10y.json`
  - `docs/audits/evidence/domain-a/backtest_15y.json`
- **Suspected root cause**: `backend/app/engine/backtest.py:246-253` and `backend/app/engine/result.py:80-92`
- **Suggested fix**: Validate requested start date against data coverage boundaries before simulation execution; if missing, return a validation error or return explicit date coverage warnings in the response payload.
- **Acceptance criteria**:
  - Requesting dates prior to available data coverage raises a validation error or returns a warning in `BacktestResult`.
  - CAGR calculation uses the full user-requested time horizon or explicitly warns of truncation.
- **Suggested conversation**: Phase 5 engine fix
- **Effort**: M
- **Blocks**: None
- **Blocked by**: AUD-A-001

---

### AUD-A-003
- **ID**: AUD-A-003
- **Title**: Local offline Parquet price fixtures only provide 1 midcap constituent (MIDCAP_STOCK_101)
- **Domain**: A
- **Category**: Data Completeness
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: When running in offline or fixture mode (`DATA_SOURCE=CSV`), the backtest simulation resolves all 650 constituent tickers for ranks 101–750 (`MIDCAP_STOCK_101` through `MIDCAP_STOCK_750`), but the local fixture directory `data/fixtures/` only contains historical price parquet data for a single midcap constituent: `MIDCAP_STOCK_101.parquet`. The remaining 649 tickers have no fixture price files on disk, limiting offline simulation execution across the 650-stock universe to this single stock.
- **Expected**: Offline test and simulation environments should contain price parquet files for a representative sample of active midcap/smallcap constituents (e.g. 20–50 liquid stocks) to enable realistic multi-asset simulation, portfolio rebalancing, and concurrent position competition.
- **Actual**: `data/fixtures/` contains price files for 4 large-caps (`HDFCBANK`, `INFY`, `RELIANCE`, `TATAMOTORS` — all excluded from trading by REQ-1.1), 1 benchmark index (`^NSEI`), and only 1 midcap constituent (`MIDCAP_STOCK_101`). All default offline backtests trade exclusively `MIDCAP_STOCK_101`.
- **Evidence**:
  - `data/fixtures/` directory listing showing only `MIDCAP_STOCK_101.parquet` among midcap constituents
  - `backend/app/api/v1/backtest.py:101-109` price loading loop finding only 1 symbol on disk
- **Suspected root cause**: `data/fixtures/` fixture set only generated price history for `MIDCAP_STOCK_101`
- **Suggested fix**: Generate or ingest sample OHLCV price parquet fixtures for a representative subset of universe constituents (e.g. `MIDCAP_STOCK_101`..`150`) in `data/fixtures/`.
- **Acceptance criteria**:
  - `data/fixtures/` contains OHLCV price parquet files for multiple universe constituents.
  - Backtest simulation with default parameters loads multiple symbols and executes trades across diverse midcap stocks.
- **Suggested conversation**: Phase 1 data ingestion & fixture expansion
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-A-004
- **ID**: AUD-A-004
- **Title**: Pre-2020 universe fallback (sample_midcaps) lacks local Parquet price files
- **Domain**: A
- **Category**: Data Integrity
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: For backtest periods starting prior to 2020-01-01, `backend/app/data/universe.py::get_universe()` falls back to `sample_midcaps` (`IDEA`, `YESBANK`, `SUZLON`, `RCOM`, `JPPOWER`, etc.) because `constituents.parquet` only covers 2020-01-01 onwards. None of these fallback tickers exist as parquet files in `data/fixtures/`, causing offline backtests requested with start dates before 2020 to encounter 0 available price records for universe constituents, resulting in 0 trades.
- **Expected**: Pre-2020 universe fallback constituents should have corresponding offline price parquet fixtures, or `constituents.parquet` point-in-time constituent coverage should be extended back to 2018 alongside matching price fixtures.
- **Actual**: Simulations with `start < 2020-01-01` in offline mode encounter 0 price files on disk and execute 0 trades.
- **Evidence**:
  - `backend/app/data/universe.py:129-149` (pre-2020 fallback generating `sample_midcaps` tokens)
  - Absence of `IDEA.parquet`, `YESBANK.parquet`, etc. in `data/fixtures/`
- **Suspected root cause**: `backend/app/data/universe.py:129-149` and lack of pre-2020 price fixtures in `data/fixtures/`
- **Suggested fix**: Provide offline price parquet fixtures for `sample_midcaps` tickers or extend `constituents.parquet` point-in-time constituent coverage back to 2018 alongside price fixtures.
- **Acceptance criteria**:
  - Pre-2020 backtest runs in offline mode find valid constituent price series and execute trades without returning empty series.
- **Suggested conversation**: Phase 1 universe & data ingestion
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-B-001
- **ID**: AUD-B-001
- **Title**: Add human-readable stock names to universe constituent API and UI views
- **Domain**: B
- **Category**: UX
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: `GET /api/v1/universe` and the frontend Universe Explorer on `/data` return only raw ticker strings (e.g. `MIDCAP_STOCK_101` or `IDEA`), omitting human-readable company names. Institutional analysts and users cannot identify what companies are being traded without external ticker mapping.
- **Expected**: The universe API and explorer should return company names (e.g. 'Vodafone Idea Ltd'), market capitalization rank, and sector along with ticker symbols.
- **Actual**: `UniverseResponse` contains only `tickers: list[str]`. The frontend renders a dense list of badges with no company names, search, or pagination.
- **Evidence**:
  - `docs/audits/evidence/domain-b/universe_today.json`
  - `docs/audits/evidence/domain-b/universe_names_gap.txt`
- **Suspected root cause**: `backend/app/api/v1/schemas.py:57-74` and `backend/app/data/universe.py:104-127`
- **Suggested fix**: Extend `UniverseResponse` schema to include `details: list[ConstituentDetail]` with `symbol`, `name`, `rank`, and `sector`, and update `/data` to render a paginated, searchable data table.
- **Acceptance criteria**:
  - `GET /api/v1/universe` returns `name` field for each constituent.
  - `/data` UI displays company names in a searchable, paginated table.
- **Suggested conversation**: Phase 1 universe enhancement
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-B-002
- **ID**: AUD-B-002
- **Title**: Replace synthetic dummy symbols (MIDCAP_STOCK_101..750) with authentic historical NSE constituent mappings
- **Domain**: B
- **Category**: Data Integrity
- **Severity**: Critical
- **Reproducibility**: Always
- **Description**: In `data/fixtures/constituents.parquet`, constituent ranks 101 to 750 are populated with synthetic dummy string tokens (`MIDCAP_STOCK_101` through `MIDCAP_STOCK_750`) rather than genuine NSE tickers. For dates prior to 2020-01-01, the fallback constituents generator repeats sample midcaps with suffix increments (`IDEA_1`, `YESBANK_1`), generating fictitious symbols.
- **Expected**: Per REQ-1.1, the trading universe must represent authentic Indian equity tickers listed on the National Stock Exchange ranked 101 to 750 by market capitalization.
- **Actual**: `constituents.parquet` contains synthetic placeholders `MIDCAP_STOCK_101..750` and fallback generates fictitious `_cycle` symbols.
- **Evidence**:
  - `docs/audits/evidence/domain-b/sampled_tickers_check.txt`
  - `docs/audits/evidence/domain-b/universe_frozen_check.txt`
- **Suspected root cause**: `backend/app/data/universe.py:88-96` and `data/fixtures/constituents.parquet`
- **Suggested fix**: Replace `constituents.parquet` with authentic historical NSE Midcap 150, Smallcap 250, and Microcap 250 constituent membership records.
- **Acceptance criteria**:
  - All constituent symbols in ranks 101–750 correspond to real NSE-listed equity tickers.
  - No synthetic placeholder tokens (`MIDCAP_STOCK_101`, `IDEA_1`) appear in universe responses.
- **Suggested conversation**: Phase 1 universe data
- **Effort**: L
- **Blocks**: None
- **Blocked by**: None

---

### AUD-B-003
- **ID**: AUD-B-003
- **Title**: Deduplicate ticker symbol 'TATACOMM' in sample_midcaps fallback list
- **Domain**: B
- **Category**: Data Integrity
- **Severity**: Minor
- **Reproducibility**: Always
- **Description**: In `backend/app/data/universe.py::get_default_fallback_constituents()`, the `sample_midcaps` list includes ticker symbol `"TATACOMM"` twice: once at line 27 and again at line 74. When constituent ranks are cycled across the list, this duplication leads to redundant constituent slot assignments and uneven cycle offsets.
- **Expected**: `sample_midcaps` constituent list should only contain unique equity ticker symbols.
- **Actual**: `"TATACOMM"` appears twice in the array (indices 9 and 56).
- **Evidence**:
  - `backend/app/data/universe.py:27` and `backend/app/data/universe.py:74`
- **Suspected root cause**: Redundant entry in `sample_midcaps` list in `backend/app/data/universe.py:17-86`
- **Suggested fix**: Remove the duplicate `"TATACOMM"` entry at line 74 and replace with a distinct midcap constituent or trim the list.
- **Acceptance criteria**:
  - `len(sample_midcaps) == len(set(sample_midcaps))`
- **Suggested conversation**: Phase 1 universe enhancement
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

---

### AUD-C-001
- **ID**: AUD-C-001
- **Title**: Remove Large-Cap (Nifty 50) presets from /signals, /indicators, and /validation pages
- **Domain**: C
- **Category**: Correctness
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: Multiple frontend pages hardcode large-cap stocks (ranks 1–100: RELIANCE, HDFCBANK, INFY, TATAMOTORS) as primary demo preset symbols in `/signals` (lines 11–17), `/indicators` (lines 39–45), and `/validation` (line 17). This directly violates REQ-1.1 and ASSUMPTIONS.md Section 1, which explicitly exclude large-cap stocks (ranks 1–100) from the strategy trading universe.
- **Expected**: Preset selection lists and default symbols on strategy pages must only contain stocks belonging to the strategy's defined trading universe (ranks 101–750).
- **Actual**: Large-caps are presented as default options across `/signals`, `/indicators`, and `/validation`.
- **Evidence**:
  - `docs/audits/evidence/domain-c/stocks_outside_universe.txt`
- **Suspected root cause**: `frontend/app/signals/page.tsx:11-17`, `frontend/app/indicators/page.tsx:39-45`, `frontend/app/validation/page.tsx:17`
- **Suggested fix**: Update preset symbol lists in frontend components to use valid mid/small-cap tickers from the active universe.
- **Acceptance criteria**:
  - Preset symbol arrays contain only stocks ranked 101–750.
  - Default selected symbol on `/signals` and `/validation` is an active universe constituent.
- **Suggested conversation**: Phase 3 signals / UI pass
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

---

### AUD-C-002
- **ID**: AUD-C-002
- **Title**: Inject point-in-time universe provider into Backtest engine during simulation run
- **Domain**: C
- **Category**: Bias
- **Severity**: Critical
- **Reproducibility**: Always
- **Description**: In `backend/app/api/v1/backtest.py:115-119`, the `Backtest` simulation is instantiated without passing the `universe_provider` argument. As a result, the engine falls back to `active_universe_set = set(self.prices.keys())` on every session T-1, completely bypassing point-in-time universe rebalancing and introducing survivorship bias.
- **Expected**: Per REQ-0.1, REQ-1.1, and ASSUMPTIONS.md Section 1.3, the engine must resolve constituent membership dynamically on session T-1 using historical point-in-time records.
- **Actual**: `Backtest` is called without `universe_provider`, freezing candidate selection to the initial static price dictionary keys.
- **Evidence**:
  - `docs/audits/evidence/domain-c/lookback_leak_audit.txt`
- **Suspected root cause**: `backend/app/api/v1/backtest.py:115-119`
- **Suggested fix**: Pass a callable `universe_provider` wrapping `get_universe` into `Backtest(...)` inside `_execute_backtest_task`.
- **Acceptance criteria**:
  - `Backtest` executes with `universe_provider` active.
  - T-1 entry screening calls `universe_provider(prev_date)` on each trading session.
- **Suggested conversation**: Phase 5 engine fix
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-D-001
- **ID**: AUD-D-001
- **Title**: Fix severe horizontal overflow on mobile (375px) and tablet (768px) viewports across all pages
- **Domain**: D
- **Category**: UX
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: Automated Playwright audits across five viewports revealed that every page in the application suffers from severe horizontal scrolling on mobile (375px width: +517px scrollWidth overflow) and tablet (768px width: +132px scrollWidth overflow). Fixed-width navigation bars, multi-column KPI grids, and uncollapsed tables exceed viewport boundaries.
- **Expected**: Layout must be fully responsive across mobile (375px), tablet (768px), and desktop viewports with zero horizontal document scrolling (`scrollWidth <= innerWidth`).
- **Actual**: `scrollWidth 892px > innerWidth 375px` (+517px) across all 9 pages; `scrollWidth 900px > innerWidth 768px` (+132px) across all 9 pages.
- **Evidence**:
  - `docs/audits/evidence/domain-d/responsive_overflow_audit.txt`
  - `docs/audits/evidence/domain-d/backtest-375.png`
  - `docs/audits/evidence/domain-d/data-375.png`
  - `docs/audits/evidence/domain-d/signals-375.png`
- **Suspected root cause**: Fixed min-widths and non-wrapping navbar in `frontend/app/layout.tsx` and absence of `overflow-x-auto` table wrappers.
- **Suggested fix**: Implement a collapsible mobile navigation menu, apply responsive grid break-points (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`), and wrap all data tables in scrollable containers.
- **Acceptance criteria**:
  - At 375px and 768px viewports, `document.documentElement.scrollWidth <= window.innerWidth` across all pages.
- **Suggested conversation**: Phase 11 — Responsive & UI pass
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-D-002
- **ID**: AUD-D-002
- **Title**: Remediate WCAG 2.1 AA accessibility violations (missing button names, unassociated form labels, low contrast)
- **Domain**: D
- **Category**: Accessibility
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: Axe-core audits executed across all application pages identified 23 accessibility violations, including critical button name deficiencies (icon buttons without discernible text), unassociated `<label>` elements on date inputs, select dropdowns without accessible names, and color contrast failures on secondary text.
- **Expected**: All interactive elements and textual content must comply with WCAG 2.1 AA standards.
- **Actual**: Critical and serious violations detected on `/data` (5), `/indicators` (4), `/signals` (4), `/sweep` (3), `/backtest` (2), `/reports` (2), and `/validation` (2).
- **Evidence**:
  - `docs/audits/evidence/domain-d/axe_accessibility_violations.json`
- **Suspected root cause**: Missing `aria-label` on icon-only buttons, form `<label>` tags not linking to input `id` attributes via `htmlFor`.
- **Suggested fix**: Add `aria-label` attributes to pagination buttons, associate form labels with input IDs, and ensure text color tokens meet 4.5:1 contrast ratio.
- **Acceptance criteria**:
  - Axe-core scan reports 0 critical or serious accessibility violations across all pages.
- **Suggested conversation**: Phase 11 — Accessibility pass
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-E-001
- **ID**: AUD-E-001
- **Title**: Only 5 symbols stored in SQLite coverage database covering 5 years (15-year data coverage absent)
- **Domain**: E
- **Category**: Data Integrity
- **Severity**: Critical
- **Reproducibility**: Always
- **Description**: `GET /api/v1/data/coverage` returns only 5 symbols (`HDFCBANK`, `INFY`, `MIDCAP_STOCK_101`, `RELIANCE`, `TATAMOTORS`), each spanning 1,305 trading sessions between 2019-01-01 and 2024-01-01 (5 calendar years). 10-year and 15-year continuous historical data is absent from both the SQLite database and offline parquet fixtures for 99% of universe constituents.
- **Expected**: Per PRD and DOMAIN E requirements, the system must provide continuous 15-year daily data for NSE 101–750 constituents to support 5, 10, and 15-year backtests.
- **Actual**: Data coverage is limited to 5 years (2019–2024) across only 5 symbols.
- **Evidence**:
  - `docs/audits/evidence/domain-e/data_coverage_full.json`
  - `docs/audits/evidence/domain-e/sample_symbols_continuity.txt`
- **Suspected root cause**: Market data ingestion fixture generator was only seeded with a 5-symbol sample fixture.
- **Suggested fix**: Ingest or bundle comprehensive historical OHLCV data for all NSE 101–750 constituents spanning 15+ years.
- **Acceptance criteria**:
  - `GET /api/v1/data/coverage` returns >= 650 symbols.
  - Symbols possess continuous historical sessions spanning 15+ years.
- **Suggested conversation**: Phase 1 data ingestion
- **Effort**: XL
- **Blocks**: None
- **Blocked by**: None

---

### AUD-E-002
- **ID**: AUD-E-002
- **Title**: Concurrent parameter sweep execution across Playwright workers causes SQLite lock contention and test timeout
- **Domain**: E
- **Category**: Concurrency / Performance
- **Severity**: Minor
- **Reproducibility**: Intermittent (under 8-worker parallel E2E test runs)
- **Description**: When Playwright executes the full 18-test E2E suite with 8 parallel workers, `acceptance.spec.ts` (test 4) and `sweep.spec.ts` trigger concurrent 2D parameter sweeps simultaneously against the single background FastAPI instance backed by SQLite. Under heavy disk I/O and synchronous database writes, job completion polling occasionally exceeds the 45-second test locator timeout.
- **Expected**: Concurrent sweeps should execute reliably or Playwright sweep tests should be isolated / backend should configure WAL mode and busy timeout for SQLite.
- **Actual**: Intermittent timeout waiting for `text=Sweep Status: completed` when multiple sweep test suites run concurrently.
- **Evidence**:
  - `docs/audits/evidence/preflight-2026-09-25.txt`
- **Suspected root cause**: SQLite default busy timeout and default rollback journal mode under concurrent background threads.
- **Suggested fix**: Enable SQLite WAL mode (`PRAGMA journal_mode=WAL;`), configure `timeout=30.0` on SQLite engine connection, or serialize sweep tests in Playwright config.
- **Acceptance criteria**:
  - 8-worker Playwright E2E suite passes reliably without parameter sweep locator timeouts.
- **Suggested conversation**: Phase 6 / 8 performance tuning
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

---

### AUD-F-001
- **ID**: AUD-F-001
- **Title**: YFinanceSource lacks get_coverage() implementation causing AttributeError when switched
- **Domain**: F
- **Category**: Correctness
- **Severity**: Critical
- **Reproducibility**: Always
- **Description**: When `DATA_SOURCE=yfinance` is configured in the environment, invoking `get_coverage()` on the resolved price source crashes with `AttributeError: 'YFinanceSource' object has no attribute 'get_coverage'`. The abstract class `PriceSource` does not define `get_coverage()`, violating the polymorphic source contract.
- **Expected**: All implementations of `PriceSource` must provide uniform methods for coverage inspection.
- **Actual**: `YFinanceSource` raises `AttributeError` when `get_coverage()` is called.
- **Evidence**:
  - `docs/audits/evidence/preflight-2026-09-25.txt`
- **Suspected root cause**: `backend/app/data/source.py:9-30`
- **Suggested fix**: Define `get_coverage()` as an abstract method in `PriceSource` and implement it in `YFinanceSource`.
- **Acceptance criteria**:
  - `get_price_source("yfinance").get_coverage()` executes cleanly without throwing an `AttributeError`.
- **Suggested conversation**: Phase 1 data source fix
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

---

### AUD-F-002
- **ID**: AUD-F-002
- **Title**: Lack of explicit transaction cost itemization (STT, GST, Exchange charges lumped into slippage)
- **Domain**: F
- **Category**: Correctness
- **Severity**: Minor
- **Reproducibility**: Always
- **Description**: The transaction cost model applies a single lumped 10 bps per side friction (`cost_bps=10.0`), as documented in ASSUMPTIONS.md Open Question #6. However, Indian cash equities incur mandatory statutory charges: STT (0.10% on delivery sell), Exchange turnover (0.00345%), SEBI charges (₹10/crore), Stamp duty (0.015% on buy), and 18% GST on brokerage+exchange. Lumping them into a symmetric 10 bps misses the asymmetric sell-side STT burden.
- **Expected**: For institutional credibility, cost modeling should either explicitly break down statutory taxes or calibrate slippage to reflect Indian statutory levies (~12–15 bps round-trip taxes alone).
- **Actual**: Symmetric 10 bps buy slippage and 10 bps sell slippage is applied without tax itemization.
- **Evidence**:
  - `docs/audits/evidence/domain-f/cost_model_breakdown.txt`
- **Suspected root cause**: `backend/app/risk/slippage.py`
- **Suggested fix**: Add optional statutory fee breakdown to `apply_costs` or calibrate default `cost_bps` to 25 bps to reflect real NSE delivery frictions.
- **Acceptance criteria**:
  - Trade ledger records itemized STT, GST, exchange fees, and execution slippage.
- **Suggested conversation**: Phase 4 risk / cost modeling
- **Effort**: M
- **Blocks**: None
- **Blocked by**: None

---

### AUD-G-001
- **ID**: AUD-G-001
- **Title**: PDF trade log silently caps at 5,000 trades without indication of omitted rows in table footer
- **Domain**: G
- **Category**: Observability
- **Severity**: Minor
- **Reproducibility**: Always
- **Description**: When generating PDF reports for backtests with more than 5,000 trades, the PDF template truncates the trade ledger to 5,000 rows. While an export disclaimer note is rendered, individual table footers do not state the exact number of excluded trades.
- **Expected**: Reports exceeding the row cap should explicitly state: "Showing 5,000 of N trades. Download full CSV/XLSX for complete ledger."
- **Actual**: Disclaimer is generic; table pagination counters do not indicate total omitted count.
- **Evidence**:
  - `docs/audits/evidence/domain-g/pdf_text_extraction.txt`
- **Suspected root cause**: `backend/app/reports/templates/report.html.j2:230-245`
- **Suggested fix**: Display dynamic count `trades[:5000]|length` of `total_trades` in trade ledger header and footer.
- **Acceptance criteria**:
  - PDF trade table header displays "Trades (showing 5,000 of X)".
- **Suggested conversation**: Phase 9 PDF export polish
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

---

### AUD-H-001
- **ID**: AUD-H-001
- **Title**: Reports lack NIFTY benchmark buy-and-hold comparison and alpha/beta analytics
- **Domain**: H
- **Category**: Correctness
- **Severity**: Major
- **Reproducibility**: Always
- **Description**: Institutional quant desks and risk committees require backtesting reports to evaluate performance relative to a benchmark index (e.g. NIFTY 50 or Nifty Midcap 150 Buy-and-Hold). The current report summary, performance metrics, and PDF exports only display standalone strategy metrics (CAGR, Sharpe, Max Drawdown) without benchmark return, excess return (Alpha), Beta, or an overlaid benchmark equity curve.
- **Expected**: Reports should compute and display Benchmark CAGR, Strategy Alpha, Beta, Information Ratio, and plot the benchmark equity curve alongside the strategy.
- **Actual**: `ReportSummaryResponse` and PDF charts have zero benchmark comparison metrics.
- **Evidence**:
  - `docs/audits/evidence/domain-h/benchmark_comparison_gap.txt`
- **Suspected root cause**: `backend/app/reports/metrics.py` and `backend/app/reports/charts.py`
- **Suggested fix**: Add `benchmark_return`, `alpha`, `beta`, `information_ratio` to `PerformanceMetrics` and overlay benchmark curve in `render_equity_curve`.
- **Acceptance criteria**:
  - UI report page and PDF include Benchmark Return, Alpha, Beta, and overlaid benchmark curve.
- **Suggested conversation**: New Phase 10 — Benchmark Comparison & Analytics
- **Effort**: L
- **Blocks**: None
- **Blocked by**: None

---

### AUD-H-002
- **ID**: AUD-H-002
- **Title**: Handoff Section 2 base SHA mismatch with git HEAD
- **Domain**: Preflight / Docs
- **Category**: Docs
- **Severity**: Minor
- **Reproducibility**: Always
- **Description**: `docs/handoffs/phase-9-handoff.md` Section 2 lists `Base Git SHA: a88c52954164c669ce70734cbe5820fcbd273e52`. However, `git rev-parse HEAD` returns `63a8154cade19039f9f7ce45c8ccedfaa0d8ba13`, which is the commit that added Phase 9 itself. The handoff recorded the parent base commit rather than the final Phase 9 release commit.
- **Expected**: Handoff documentation should explicitly clarify both the starting base commit and the finalized release commit SHA.
- **Actual**: Section 2 lists `a88c529` as Base Git SHA, differing from HEAD (`63a8154`).
- **Evidence**:
  - `docs/audits/evidence/preflight-2026-09-25.txt`
- **Suspected root cause**: `docs/handoffs/phase-9-handoff.md:13`
- **Suggested fix**: Update handoff template to clearly distinguish `Base Commit SHA` and `Release Commit SHA`.
- **Acceptance criteria**:
  - Handoff file clearly states base SHA and release SHA.
- **Suggested conversation**: Documentation & Handoff tooling
- **Effort**: S
- **Blocks**: None
- **Blocked by**: None

=== END AUDIT ARTIFACT ===

