# EquiTest NSE - Quantitative Backtesting Framework

> **Indian Equities (NSE 101–750) Quantitative Trend-Following & Backtesting Engine**  
> Current Milestone: **Phase 1: Data Ingestion and Universe Construction** (Phase 0 Foundation Complete).

---

## 1. Overview & Architecture

EquiTest NSE is a quantitative research and backtesting framework designed for Indian equities. The platform eliminates common backtesting pitfalls (look-ahead bias, survivorship bias, and unadjusted split distortions) by enforcing:
- **Point-in-Time Universe Resolution**: Dynamic tracking of NSE 101–750 constituents by market cap with explicit survivorship bias detection.
- **Corporate Action Adjustments**: Daily adjusted close series (`adj_close`) for continuous indicator calculation across splits, bonuses, and rights issues (detailed in [`docs/data.md`](file:///home/shailender/projects/equitest-nse/docs/data.md)).
- **Financial Invariant Validation**: Strict mathematical checks on ingested OHLCV bars (monotonic dates, no NaNs, High $\ge$ Low, session boundaries).
- **Swappable Data Sources**: Seamless switching between live Yahoo Finance feeds (`DATA_SOURCE=yfinance`) and offline parquet datasets (`DATA_SOURCE=CSV`).
- **Full-Stack Monorepo**: FastAPI backend, Next.js 14 App Router frontend with Recharts visualization, and a 3-layer test harness (Pytest, Vitest + MSW, Playwright E2E).

---

## 2. Repository Layout

```
/backend
  /app
    main.py                 # FastAPI app factory, CORS, Request ID middleware
    /api/v1/
      __init__.py           # Versioned router mounting health and data endpoints
      data.py               # Ingest, coverage, universe, and prices endpoints
      schemas.py            # Pydantic request/response contract models
    /core/
      config.py             # Pydantic Settings (APP_ENV, DATABASE_URL, DATA_SOURCE)
      logging.py            # Structured JSON logger and correlation middleware
    /data/
      source.py             # PriceSource abstraction (CSVSource & YFinanceSource)
      universe.py           # Point-in-time universe resolver (NSE 101–750)
      ingest.py             # Invariant validator and idempotent ingestion engine
      generate_fixtures.py  # Synthetic test data fixture generator
    /db/
      models.py             # SQLModel tables: prices, index_prices, universe_membership
      session.py            # SQLite engine and dependency injection
  /tests
    conftest.py             # Pytest fixtures (isolated in-memory DB, async client)
    test_health.py          # Service health and logging tests
    test_universe.py        # Universe resolver & survivorship bias unit tests
    test_ingest.py          # Idempotency and corporate-action split tests
    test_validation.py      # Hypothesis property-based OHLCV invariant tests
    test_api_data.py        # REST API endpoints & look-ahead leak prevention tests
  pyproject.toml            # Ruff, Black, Pytest (>=80% coverage)
  Dockerfile                # Python 3.11 container definition
/frontend
  /app
    layout.tsx              # Root App Router layout with TanStack Query provider
    page.tsx                # Landing page: "Backtesting Framework"
    /api-health/page.tsx    # Backend health diagnostic page
    /data/page.tsx          # Data status page (ingest, coverage, universe, Recharts)
  /lib/
    api.ts                  # Typed client with Zod schemas and OpenAPI types
    schema.d.ts             # Auto-generated TypeScript definitions
    utils.ts                # Tailwind cn helper
  /tests/
    setup.ts                # MSW mock handlers for all v1 endpoints
    health.test.tsx         # Health diagnostic component test
    data.test.tsx           # Coverage table pagination and bias badge tests
  vitest.config.ts          # Vitest configuration with jsdom
  playwright.config.ts      # Playwright E2E configuration
  package.json              # Next.js 14, React 18, Tailwind, TanStack Query, Recharts
  Dockerfile                # Multi-stage production container for Next.js
/e2e
  health.spec.ts            # E2E test verifying backend health
  data.spec.ts              # E2E test verifying ingest -> coverage -> Recharts graph
/data/fixtures/             # Parquet datasets for equities, Nifty benchmark, and constituents
docker-compose.yml          # Backend (:8000) + Frontend (:3000) + Postgres (:5432)
Makefile                    # Unified automation targets
.github/workflows/ci.yml    # GitHub Actions workflow
README.md
docs/data.md                # Corporate actions and data integrity guide
```

---

## 3. Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- GNU Make

### 1. Install Dependencies
```bash
make install
# or if make is not installed: ./bin/make install
```
Initializes the Python virtual environment in `backend/.venv`, installs all backend packages in editable dev mode, installs frontend npm dependencies, generates parquet fixtures, and compiles TypeScript types from the OpenAPI schema.

### 2. Single Command Local Run (`run-local`)
Run both backend and frontend concurrently with a single command:
```bash
./run-local
```
*(Alternatively: `make run-local`, `npm run run-local`, or `make dev`)*

This single command:
- Automatically verifies virtual environments and dependencies.
- Synchronizes OpenAPI schemas and TypeScript definitions.
- Inspects port availability (`:8000` and `:3000`).
- Launches FastAPI backend at [http://localhost:8000](http://localhost:8000) (Interactive Swagger docs at [`/docs`](http://localhost:8000/docs)).
- Launches Next.js frontend at [http://localhost:3000](http://localhost:3000) (Data dashboard at [`/data`](http://localhost:3000/data)).
- Gracefully terminates both processes when pressing `Ctrl+C`.

To run against live Yahoo Finance instead of local fixture parquet files:
```bash
DATA_SOURCE=yfinance ./run-local
```

### 3. Generate OpenAPI Schema & Types
```bash
make openapi
```
Exports `frontend/openapi.json` from the live FastAPI application and generates `frontend/lib/schema.d.ts`.

---

## 4. API Endpoints (v1)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service operational health and version (`0.1.0`) |
| `POST` | `/api/v1/data/ingest` | Trigger idempotent market data ingestion for start/end dates |
| `GET` | `/api/v1/data/coverage` | Returns available date ranges and session counts per symbol |
| `GET` | `/api/v1/universe?date=YYYY-MM-DD` | Returns NSE 101–750 tickers with survivorship bias flag |
| `GET` | `/api/v1/prices/{symbol}?start=&end=` | Returns chronological OHLCV bars (404 for unknown symbols) |

---

## 5. Three-Layer Test Harness

```bash
# Run all test suites
make test

# Or run individual layers:
make test-backend    # Pytest with coverage gate >= 80% (includes Hypothesis property tests)
make test-frontend   # Vitest component tests with MSW mocking
make test-e2e        # Playwright E2E integration test
```

### Swappable Data Source Testing
By default, tests execute with `DATA_SOURCE=CSV`, reading from `/data/fixtures/*.parquet` without external network dependencies.
```bash
DATA_SOURCE=CSV make test
```

---

## 6. Code Quality & Linting

```bash
make lint
```
- Backend: `ruff check backend` and `black --check backend`
- Frontend: `next lint` and `tsc --noEmit` (TypeScript strict mode)

---

## 7. Phase 1 Acceptance Criteria Verification

- [x] Data source abstraction (`PriceSource`, `CSVSource`, `YFinanceSource`) swappable via `DATA_SOURCE`
- [x] Universe resolver (`get_universe`) returning tickers ranked 101–750 with `survivorship_bias` flag
- [x] Idempotent ingestion job storing into `prices`, `index_prices`, and `universe_membership` tables
- [x] Financial invariant validation (monotonic dates, no NaNs, High $\ge$ Low, session limits)
- [x] Corporate action adjustments (`adj_close` populated and documented in `docs/data.md`)
- [x] FastAPI v1 endpoints with complete Pydantic response models
- [x] Next.js `/data` page featuring date pickers, paginated coverage table, universe inspector, and Recharts prices drilldown
- [x] Unit tests: universe resolver with point-in-time fixture across 3 historical dates
- [x] Unit tests: ingestion idempotency (running twice produces identical row counts)
- [x] Property-based tests (Hypothesis): invariant verification on randomized OHLCV frames
- [x] API tests: `/universe`, `/prices`, `/coverage` schemas, 404 for unknown symbols, and look-ahead leak checks
- [x] Frontend Vitest tests: coverage table pagination and survivorship bias badge visibility
- [x] Playwright E2E test: Ingest button trigger $\to$ coverage table populates $\to$ prices chart renders
- [x] `DATA_SOURCE=CSV make test` passes end-to-end with fixtures
- [x] OpenAPI JSON and TypeScript client types regenerated
