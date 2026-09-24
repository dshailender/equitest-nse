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
| **Phase 7** | Reporting and Analytics | ⏳ Pending |
| **Phase 8** | Validation, Acceptance, and Handoff | ⏳ Pending |

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

---

## API Endpoint Matrix

| Method | Endpoint | Description | Phase | Test Coverage |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health status | Phase 0 | `tests/test_health.py`, `tests/health.test.tsx`, `e2e/health.spec.ts` |
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
| `POST` | `/api/v1/backtest/run` | Triggers asynchronous backtest simulation execution | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}` | Retrieves execution status and summary metrics | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}/trades` | Retrieves trade ledger of closed round trips | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest/{run_id}/equity` | Retrieves mark-to-market daily equity curve points | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx`, `e2e/backtest.spec.ts` |
| `GET` | `/api/v1/backtest` | Lists historical persisted backtest simulation runs | Phase 5 | `tests/test_api_backtest.py`, `frontend/tests/backtest.test.tsx` |
| `POST` | `/api/v1/backtest/sweep` | Triggers asynchronous multi-parameter Cartesian sweep | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts` |
| `GET` | `/api/v1/backtest/sweep/{sweep_id}` | Retrieves sweep execution status and child runs breakdown | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts` |
| `GET` | `/api/v1/backtest/compare` | Compares multiple backtest runs with aligned metrics & curves | Phase 6 | `tests/test_sweep_engine.py`, `frontend/tests/sweep.test.tsx`, `e2e/sweep.spec.ts` |



