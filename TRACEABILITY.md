# Requirements Traceability Matrix

This document tracks requirement implementation, validation status, and associated code and test artifacts for the EquiTest NSE quantitative backtesting platform.

## Summary Status

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Discovery, Definitions, Invariants & Architecture | ✅ Completed |
| **Phase 1** | Data Ingestion and Universe Construction | ✅ Completed |
| **Phase 2** | Technical Indicator Computation & Preview Engine | ✅ Completed |
| **Phase 3** | Entry, Exit, and Signal Rules | ✅ Completed |
| **Phase 4** | Risk, Position Sizing, and Stop Loss | ✅ Completed |
| **Phase 5** | Backtest Simulation Engine | ✅ Completed |
| **Phase 6** | Parameter and Scenario Testing | ✅ Completed |
| **Phase 7** | Reporting and Analytics | ✅ Completed |
| **Phase 8** | Validation, Acceptance, and Handoff | ✅ Completed |
| **Phase 9** | PDF Report Export | ✅ Completed |

---

## Detailed Requirement Traceability

### Phase 0: Discovery, Definitions, Assumptions
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-0.1** | Look-Ahead & Survivorship Bias Prevention | `backend/app/data/universe.py`, `backend/app/api/v1/data.py` | `backend/tests/test_universe.py`, `backend/tests/test_api_data.py::test_prices_no_lookahead_leak` | ✅ Verified |
| **REQ-0.2** | Corporate Action Adjustments (`adj_close`) | `backend/app/data/ingest.py`, `data/fixtures/RELIANCE.parquet` | `backend/tests/test_ingest.py`, `e2e/data.spec.ts` | ✅ Verified |
| **REQ-0.3** | Transaction Frictions & Costs | `backend/app/risk/slippage.py::apply_costs` | `backend/tests/test_risk_costs.py::test_apply_costs_buy_side`, `test_apply_costs_sell_side` | ✅ Verified |

### Phase 1: Data Ingestion & Universe Construction
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-1.1** | Universe Selection (NSE 101–750) | `backend/app/data/universe.py`, `data/fixtures/constituents.parquet` | `backend/tests/test_universe.py::test_universe_with_point_in_time_fixture` | ✅ Verified |
| **REQ-1.2** | Base Data Ingestion (OHLCV) | `backend/app/data/ingest.py`, `backend/app/data/source.py` | `backend/tests/test_ingest.py`, `backend/tests/test_data_source.py` | ✅ Verified |
| **REQ-1.3** | NIFTY Benchmark Ingestion | `backend/app/data/source.py`, `data/fixtures/NIFTY50.parquet` | `backend/tests/test_ingest.py`, `backend/tests/test_data_source.py` | ✅ Verified |

### Phase 2: Indicator & Signal Engine
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-2.1** | Stock EMAs (20, 50, 150, 200) on Adjusted Close | `backend/app/indicators/ema.py`, `backend/app/indicators/pipeline.py`, `backend/app/api/v1/indicators.py` | `backend/tests/test_indicators_ema.py` (Golden file vs TA-Lib tolerance $\le 10^{-6}$ & Hypothesis), `e2e/indicators.spec.ts` | ✅ Verified |
| **REQ-2.2** | NIFTY EMAs (50, 200) on Benchmark Close | `backend/app/indicators/pipeline.py::compute_nifty_indicators`, `GET /api/v1/indicators/nifty` | `backend/tests/test_indicators_pipeline.py::test_compute_nifty_indicators`, `backend/tests/test_api_indicators.py::test_api_indicators_nifty` | ✅ Verified |
| **REQ-2.3** | 52-Week Rolling High (lookback=252, shifted by 1) | `backend/app/indicators/high_52w.py`, `backend/app/indicators/pipeline.py` | `backend/tests/test_indicators_52w.py` (Synthetic test asserting bar $N = \max(high[N-252:N])$ excluding $N$) | ✅ Verified |

### Phase 3: Entry, Exit, and Signal Rules
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-3.1** | Market Regime Filter (`NIFTY > EMA50 & EMA200`) | `backend/app/strategy/signals.py::market_regime_ok`, `backend/app/strategy/config.py` | `backend/tests/test_strategy_signals.py::test_market_regime_ok_synthetic`, `test_regime_filter_override_blocks_all_entries` | ✅ Verified |
| **REQ-3.2** | Trend Filter (`EMA 20 > 50 > 150 > 200`) | `backend/app/strategy/signals.py::trend_ok` | `backend/tests/test_strategy_signals.py::test_trend_ok_synthetic`, `test_trend_ok_on_fixture` | ✅ Verified |
| **REQ-3.3** | 52W High Proximity Filter (`Close > 0.85 * 52W High`) | `backend/app/strategy/signals.py::near_52w_high` | `backend/tests/test_strategy_signals.py::test_near_52w_high_synthetic`, `test_near_52w_high_on_fixture` | ✅ Verified |
| **REQ-3.4** | Entry Trigger Crossover (`Close_T > EMA20_T & Close_T-1 < EMA20_T-1`) & Universe Screen | `backend/app/strategy/signals.py::entry_signal`, `GET /api/v1/signals/screen` | `backend/tests/test_strategy_signals.py::test_handcrafted_10_bar_signals`, `test_no_lookahead_truncation_guard`, `backend/tests/test_api_signals.py::test_api_signals_screen_fixture_date` | ✅ Verified |
| **REQ-3.5** | Exit Trigger (`Close_T < EMA20_T`) & Symbol Signals API | `backend/app/strategy/signals.py::exit_signal`, `GET /api/v1/signals/{symbol}`, `frontend/app/signals/page.tsx` | `backend/tests/test_strategy_signals.py::test_handcrafted_10_bar_signals`, `backend/tests/test_api_signals.py`, `frontend/tests/signals.test.tsx`, `e2e/signals.spec.ts` | ✅ Verified |

### Phase 4: Risk, Position Sizing, and Stop Loss
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-4.1** | Stop Loss Calculation & Overnight Gap Resolution | `backend/app/risk/position.py::stop_loss_price`, `backend/app/risk/gap.py::resolve_stop_exit` | `backend/tests/test_risk_stop_loss.py::test_stop_loss_price_calculation`, `test_gap_down_exit_semantics` | ✅ Verified |
| **REQ-4.2** | Dynamic Risk Allocation & Slippage Cost Modeling | `backend/app/risk/position.py::risk_amount`, `backend/app/risk/slippage.py::apply_costs` | `backend/tests/test_risk_costs.py::test_dynamic_risk_amount_calculation`, `test_apply_costs_buy_side`, `test_apply_costs_sell_side` | ✅ Verified |
| **REQ-4.3** | Position Sizing & Exposure Allocation Constraints | `backend/app/risk/position.py::position_size`, `capital_required`, `can_allocate` | `backend/tests/test_risk_position.py` (Unit tests + Hypothesis property test: `qty*entry*sl_pct <= risk_amount`) | ✅ Verified |
| **REQ-4.4** | Risk REST API & Interactive Sizing Dashboard | `backend/app/api/v1/risk.py`, `frontend/app/risk/page.tsx`, `frontend/lib/api.ts` | `backend/tests/test_api_risk.py`, `frontend/tests/risk.test.tsx`, `e2e/risk.spec.ts` | ✅ Verified |

### Phase 5: Backtest Simulation Engine
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-5.1** | Simulation Engine State Machine & BacktestResult | `backend/app/engine/result.py`, `backend/app/engine/backtest.py` | `backend/tests/test_engine_core.py` (Deterministic golden test on tiny universe, final capital ₹482,707.20 to the paisa, idempotency verified) | ✅ Verified |
| **REQ-5.2** | Next-Day Open Execution & Period Limits | `backend/app/engine/backtest.py` | `backend/tests/test_engine_execution.py` (Session T open execution with slippage, date range filtering, strict cutoff D truncation guard) | ✅ Verified |
| **REQ-5.3** | Capital Constraints, Ranking Rule & Rejections | `backend/app/engine/backtest.py::DefaultRanker`, `docs/ASSUMPTIONS.md` | `backend/tests/test_engine_constraints.py` (Concurrent position rejection logging, momentum sorting rule, pluggable Ranker protocol) | ✅ Verified |
| **REQ-5.4** | Persistence, REST API & Backtest Dashboard | `backend/app/api/v1/backtest.py`, `backend/app/db/models.py`, `frontend/app/backtest/page.tsx`, `frontend/lib/api.ts` | `backend/tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` | ✅ Verified |

### Phase 6: Parameter and Scenario Testing
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-6.1** | Strategy Parameterization & Config Model | `backend/app/strategy/config.py`, `backend/app/engine/backtest.py` (Rankers), `backend/app/data/universe.py` | `backend/tests/test_strategy_config.py` (Pydantic model validation, alias mappings, rankers, universe bounds 101–750) | ✅ Verified |
| **REQ-6.2** | Parameter Sweep Cartesian Engine & Progress Reporting | `backend/app/api/v1/backtest.py`, `backend/app/db/models.py`, `POST /sweep`, `GET /sweep/{id}` | `backend/tests/test_sweep_engine.py::test_api_sweep_3x3_grid_and_status` (3x3 grid generates 9 child runs, partial status aggregation) | ✅ Verified |
| **REQ-6.3** | Multi-Run Scenario Comparison & Alignment | `backend/app/api/v1/backtest.py`, `backend/engine/result.py::cagr`, `GET /compare` | `backend/tests/test_sweep_engine.py::test_api_compare_endpoint`, `backend/tests/test_determinism.py` (Hypothesis property determinism) | ✅ Verified |
| **REQ-6.4** | Interactive Sensitivity Heatmap & Scenario Dashboard | `frontend/app/sweep/page.tsx`, `frontend/lib/api.ts` | `frontend/tests/sweep.test.tsx` (MSW unit tests for grid builder, heatmap, runs table, compare drawer), `e2e/sweep.spec.ts` (Playwright E2E 2x2 sweep) | ✅ Verified |

### Phase 7: Reporting and Analytics
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-7.1** | Core & Advanced Performance Metrics Engine | `backend/app/reports/metrics.py`, `backend/app/api/v1/schemas.py` | `backend/tests/test_reports_metrics.py` (Cross-validated against `empyrical` to within $10^{-6}$ for Sharpe, Sortino, MaxDD; decimal serialization verified) | ✅ Verified |
| **REQ-7.2** | Month x Year Compounded Returns Matrix | `backend/app/reports/monthly.py`, `GET /api/v1/reports/{run_id}/monthly` | `backend/tests/test_reports_monthly.py` (Multi-year compounded matrix test on golden fixture, synthetic edge-case handling) | ✅ Verified |
| **REQ-7.3** | Multi-Format Report Export Engine (CSV, XLSX, ZIP) | `backend/app/reports/export.py`, `GET /api/v1/reports/{run_id}/export` | `backend/tests/test_reports_export.py` (OpenXML SpreadsheetML validation without openpyxl dependency, multi-file ZIP archive, CSV format) | ✅ Verified |
| **REQ-7.4** | Interactive Reports Dashboard, Charts & Exports | `frontend/app/reports/[runId]/page.tsx`, `frontend/lib/api.ts` | `frontend/tests/reports.test.tsx` (MSW unit/component tests for KPI cards, underwater drawdown chart, trade histogram, heatmap table), `e2e/reports.spec.ts` (Playwright E2E simulation to report, CSV/XLSX/ZIP downloads >0 bytes) | ✅ Verified |

### Phase 8: Validation, Acceptance, and Handoff
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-8.1** | TradingView Cross-Check Verification Engine & UI | `backend/app/validation/cross_check.py`, `backend/app/api/v1/validation.py`, `frontend/app/validation/page.tsx` | `backend/tests/test_validation_cross_check.py` (6 tests passing, golden comparison $\le 10^{-6}$ vs `reliance_ema20_expected`), `frontend/tests/validation.test.tsx` (4 tests), `e2e/acceptance.spec.ts` | ✅ Verified |
| **REQ-8.2** | Run Audit & Reproducibility Provenance Tracking | `backend/app/validation/audit.py`, `GET /api/v1/backtest/{run_id}/audit`, `frontend/components/AuditPanel.tsx` | `backend/tests/test_validation_audit.py` (6 tests passing, deterministic SHA-256 parquet hash, git SHA fallback), `frontend/tests/reports.test.tsx`, `e2e/acceptance.spec.ts` | ✅ Verified |
| **REQ-8.3** | Production Multi-Stage Containerization & Compose | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.prod.yml` | Multi-stage build stages, non-root users (`appuser:1001`, `nextjs:1001`), curl healthcheck validation, `docker compose config` syntax verification | ✅ Verified |
| **REQ-8.4** | Institutional Documentation Hub & In-App Viewer | `docs/ARCHITECTURE.md`, `docs/STRATEGY.md`, `docs/ASSUMPTIONS.md`, `docs/RUNBOOK.md`, `frontend/app/docs/page.tsx` | `frontend/tests/docs.test.tsx` (2 tests passing), in-app tabbed viewer across all sections, PRD §4 Open Questions and 5-step parameter walkthrough verified | ✅ Verified |
| **REQ-8.5** | Full End-to-End Acceptance Suite & Traceability | `e2e/acceptance.spec.ts`, `TRACEABILITY.md`, `README.md` | `e2e/acceptance.spec.ts` (7 end-to-end acceptance tests verifying health, baseline backtest, extended runs, sweeps, reports, audit, TradingView diff, docs), 100% CI pass | ✅ Verified |

### Phase 9: PDF Report Export
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-9.1** | PDF Report Export | `backend/app/reports/pdf.py`, `backend/app/api/v1/reports.py`, `backend/app/reports/templates/` | `backend/tests/test_reports_pdf.py::test_generate_pdf_fixture_run`, `test_export_pdf_small_run_streams_pdf`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` | ✅ Verified |
| **REQ-9.2** | PDF Template Configurability | `backend/app/core/branding.py`, `backend/app/reports/templates/report.html.j2`, `backend/app/reports/templates/report.css` | `backend/tests/test_reports_pdf.py::test_pdf_branding_config_override` | ✅ Verified |
| **REQ-9.3** | Server-Side Chart Rendering | `backend/app/reports/charts.py` | `backend/tests/test_reports_pdf.py::test_render_equity_curve_produces_png`, `test_render_drawdown_produces_png`, `test_render_monthly_heatmap_produces_png`, `test_charts_are_deterministic` | ✅ Verified |
| **REQ-9.4** | Async PDF Job for Large Runs | `backend/app/reports/jobs.py`, `backend/app/api/v1/reports.py` (`/jobs/{job_id}`, `/jobs/{job_id}/download`, `/export/pdf/async`) | `backend/tests/test_reports_pdf.py::test_export_pdf_large_run_returns_202`, `test_job_status_lifecycle`, `test_pdf_job_manager_cleanup_expired`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` | ✅ Verified |
| **REQ-9.5** | Deterministic PDF Output | `backend/app/reports/pdf.py` (`include_creation_date=False`), `charts.py` | `backend/tests/test_reports_pdf.py::test_pdf_is_deterministic`, `test_charts_are_deterministic` | ✅ Verified |
| **REQ-9.6** | Docker Runtime Dependencies | `backend/Dockerfile`, `backend/pyproject.toml` | `backend/Dockerfile` multi-stage build, WeasyPrint Debian libraries (`libpango-1.0-0`, `libcairo2`, `fonts-dejavu-core`), smoke test | ✅ Verified |
| **REQ-9.7** | CLI Wrapper for PDF Generation | `backend/app/reports/__main__.py`, `backend/app/reports/pdf.py` | `backend/tests/test_reports_pdf.py::test_cli_pdf_generation` | ✅ Verified |

---

## API Endpoint Matrix

| Method | Endpoint | Description | Phase | Test Coverage |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health status | Phase 0 | `tests/test_health.py`, `tests/health.test.tsx`, `e2e/health.spec.ts`, `e2e/acceptance.spec.ts` |
| `GET` | `/api/v1/health` | API v1 operational health | Phase 0 | `tests/test_health.py` |
| `POST` | `/api/v1/data/ingest` | Market data ingestion | Phase 1 | `tests/test_api_data.py`, `e2e/data.spec.ts` |
| `GET` | `/api/v1/data/coverage` | Stored symbol date ranges | Phase 1 | `tests/test_api_data.py`, `tests/data.test.tsx` |
| `GET` | `/api/v1/universe` | Point-in-time universe | Phase 1 | `tests/test_api_data.py`, `tests/test_universe.py` |
| `GET` | `/api/v1/prices/{symbol}` | OHLCV prices drilldown | Phase 1 | `tests/test_api_data.py`, `tests/data.test.tsx` |
| `GET` | `/api/v1/indicators/{symbol}` | Technical indicators (EMAs, 52W high) | Phase 2 | `tests/test_api_indicators.py`, `tests/indicators.test.tsx`, `e2e/indicators.spec.ts` |
| `GET` | `/api/v1/indicators/nifty` | NIFTY benchmark indicators | Phase 2 | `tests/test_api_indicators.py` |
| `POST` | `/api/v1/indicators/preview` | Custom indicator preview | Phase 2 | `tests/test_api_indicators.py` |
| `GET` | `/api/v1/signals/{symbol}` | Strategy trading signals & filter components | Phase 3 | `tests/test_api_signals.py`, `frontend/tests/signals.test.tsx`, `e2e/signals.spec.ts` |
| `GET` | `/api/v1/signals/screen` | Universe screening for active entry signals | Phase 3 | `tests/test_api_signals.py`, `frontend/tests/signals.test.tsx`, `e2e/signals.spec.ts` |
| `POST` | `/api/v1/risk/size` | Derives position size, capital, SL level, and monetary risk | Phase 4 | `tests/test_api_risk.py`, `frontend/tests/risk.test.tsx`, `e2e/risk.spec.ts` |
| `GET` | `/api/v1/risk/config` | Strategy baseline risk, capital, and cost parameters | Phase 4 | `tests/test_api_risk.py` |
| `POST` | `/api/v1/backtest/run` | Triggers asynchronous backtest simulation execution | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts`, `e2e/acceptance.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}` | Retrieves execution status and summary metrics | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}/trades` | Retrieves trade ledger of closed round trips | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}/equity` | Retrieves mark-to-market daily equity curve points | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest` | Lists historical persisted backtest simulation runs | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx` |
| `GET` | `/api/v1/backtest/{run_id}/audit` | Retrieves reproducibility & provenance record (git SHA, hash, versions) | Phase 8 | `tests/test_validation_audit.py`, `frontend/tests/reports.test.tsx`, `e2e/acceptance.spec.ts` |
| `POST` | `/api/v1/backtest/sweep` | Triggers asynchronous multi-parameter Cartesian sweep | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts`, `e2e/acceptance.spec.ts` |
| `GET` | `/api/v1/backtest/sweep/{sweep_id}` | Retrieves sweep execution status and child runs breakdown | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts` |
| `GET` | `/api/v1/backtest/compare` | Compares multiple backtest runs with aligned metrics & curves | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts` |
| `GET` | `/api/v1/reports/{run_id}/summary` | Retrieves comprehensive core and advanced performance metrics | Phase 7 | `tests/test_reports_export.py`, `tests/reports.test.tsx`, `e2e/reports.spec.ts`, `e2e/acceptance.spec.ts` |
| `GET` | `/api/v1/reports/{run_id}/monthly` | Retrieves Month x Year compounded returns matrix | Phase 7 | `tests/test_reports_export.py`, `tests/reports.test.tsx`, `e2e/reports.spec.ts`, `e2e/acceptance.spec.ts` |
| `GET` | `/api/v1/reports/{run_id}/export` | Multi-format export bundle download (CSV, XLSX, ZIP, PDF) | Phase 7 / 9 | `tests/test_reports_export.py`, `tests/test_reports_pdf.py`, `tests/reports.test.tsx`, `frontend/tests/export.test.tsx`, `e2e/reports.spec.ts`, `e2e/pdf_export.spec.ts` |
| `POST` | `/api/v1/reports/{run_id}/export/pdf/async` | Force asynchronous PDF report generation job | Phase 9 | `tests/test_reports_pdf.py` |
| `GET` | `/api/v1/reports/jobs/{job_id}` | PDF report export background job status | Phase 9 | `tests/test_reports_pdf.py`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` |
| `GET` | `/api/v1/reports/jobs/{job_id}/download` | Download completed PDF report from background job | Phase 9 | `tests/test_reports_pdf.py`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` |
| `GET` | `/api/v1/reports/{run_id}/preview.png` | First-page PNG thumbnail preview of backtest report PDF | Phase 9 | `tests/test_reports_pdf.py` |
| `GET` | `/api/v1/validation/{run_id}/{symbol}` | Retrieves aligned cross-check indicators and signals (JSON or CSV) | Phase 8 | `tests/test_validation_cross_check.py`, `frontend/tests/validation.test.tsx`, `e2e/acceptance.spec.ts` |
