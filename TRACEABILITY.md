# Requirements Traceability Matrix

This document tracks requirement implementation, validation status, and associated code and test artifacts for the EquiTest NSE quantitative backtesting platform.

## Summary Status

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Discovery, Definitions, Invariants & Architecture | ✅ Completed |
| **Phase 1** | Data Ingestion and Universe Construction | ✅ Completed |
| **Phase 2** | Technical Indicator Computation & Preview Engine | ✅ Completed |
| **Phase 3** | Entry, Exit, and Signal Rules | ⏳ Pending |
| **Phase 4** | Risk, Position Sizing, and Stop Loss | ⏳ Pending |
| **Phase 5** | Backtest Simulation Engine | ⏳ Pending |
| **Phase 6** | Parameter and Scenario Testing | ⏳ Pending |
| **Phase 7** | Reporting and Analytics | ⏳ Pending |
| **Phase 8** | Validation, Acceptance, and Handoff | ⏳ Pending |

---

## Detailed Requirement Traceability

### Phase 0: Discovery, Definitions, Assumptions
| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-0.1** | Look-Ahead & Survivorship Bias Prevention | `backend/app/data/universe.py`, `backend/app/api/v1/data.py` | `backend/tests/test_universe.py`, `backend/tests/test_api_data.py::test_prices_no_lookahead_leak` | ✅ Verified |
| **REQ-0.2** | Corporate Action Adjustments (`adj_close`) | `backend/app/data/ingest.py`, `data/fixtures/RELIANCE.parquet` | `backend/tests/test_ingest.py`, `e2e/data.spec.ts` | ✅ Verified |
| **REQ-0.3** | Transaction Frictions & Costs | Deferred to Phase 3+ | Strategy Engine integration | ⏳ Pending |

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
