# EquiTest NSE - Quantitative Backtesting Framework

> **Indian Equities (NSE 101–750) Quantitative Trend-Following & Backtesting Engine**  
> Current Milestone: **Phase 4: Risk, Position Sizing, and Stop Loss Complete**.

---

## 1. Overview & Architecture

EquiTest NSE is a quantitative research and backtesting framework designed for Indian equities. The platform eliminates common backtesting pitfalls (look-ahead bias, survivorship bias, and unadjusted split distortions) by enforcing:
- **Point-in-Time Universe Resolution**: Dynamic tracking of NSE 101–750 constituents by market cap with explicit survivorship bias detection.
- **Corporate Action Adjustments**: Daily adjusted close series (`adj_close`) for continuous indicator calculation across splits, bonuses, and rights issues (detailed in [`docs/data.md`](file:///home/shailender/projects/equitest-nse/docs/data.md)).
- **Financial Invariant Validation**: Strict mathematical checks on ingested OHLCV bars (monotonic dates, no NaNs, High $\ge$ Low, session boundaries).
- **Strategy & Signal Engine**: Multi-timeframe trend filters, market regime confirmation on NIFTY 50, and zero-lookahead EOD crossover execution.
- **Risk Management & Position Sizing**: Dynamic 2% corpus risk per trade, 7% stop loss derivation, gap-down overnight resolution, and 10 bps transaction frictions.
- **Swappable Data Sources**: Seamless switching between live Yahoo Finance feeds (`DATA_SOURCE=yfinance`) and offline parquet datasets (`DATA_SOURCE=CSV`).
- **Full-Stack Monorepo**: FastAPI backend, Next.js 14 App Router frontend with Recharts visualization, and a 3-layer test harness (Pytest, Vitest + MSW, Playwright E2E).

---

## 2. Repository Layout

```
/backend
  /app
    main.py                 # FastAPI app factory, CORS, Request ID middleware
    /api/v1/
      __init__.py           # Versioned router mounting data, indicators, signals, risk
      data.py               # Ingest, coverage, universe, and prices endpoints
      indicators.py         # Technical indicators and custom preview endpoints
      risk.py               # Position sizing and risk configuration endpoints
      schemas.py            # Pydantic request/response contract models
      signals.py            # Trading signals and universe screening endpoints
    /core/
      config.py             # Pydantic Settings (APP_ENV, DATABASE_URL, DATA_SOURCE)
      logging.py            # Structured JSON logger and correlation middleware
    /data/
      source.py             # PriceSource abstraction (CSVSource & YFinanceSource)
      universe.py           # Point-in-time universe resolver (NSE 101–750)
      ingest.py             # Invariant validator and idempotent ingestion engine
    /indicators/
      ema.py                # Vectorized EMA calculation (adjust=False, min_periods=span)
      high_52w.py           # Rolling 252-session peak high shifted by 1 bar
      pipeline.py           # Indicator calculation pipelines for stocks and benchmark
    /risk/
      gap.py                # Overnight gap-down resolution (Open <= SL -> exit at Open)
      position.py           # Stop loss price, risk amount, and position sizing algorithms
      slippage.py           # Transaction costs & slippage adjustments (10 bps/side)
    /strategy/
      config.py             # StrategyConfig dataclass and threshold invariants
      signals.py            # Regime, trend, 52W high, and entry/exit signal generators
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
    /indicators/page.tsx    # Multi-EMA and 52W high interactive Recharts viewer
    /risk/page.tsx          # Risk & position sizing interactive dashboard (REQ-4.1 - REQ-4.4)
    /signals/page.tsx       # Strategy signals table and universe screening page
  /lib/
    api.ts                  # Typed client with Zod schemas and OpenAPI types
    schema.d.ts             # Auto-generated TypeScript definitions
    utils.ts                # Tailwind cn helper
  /tests/
    setup.ts                # MSW mock handlers for all v1 endpoints
    health.test.tsx         # Health diagnostic component test
    data.test.tsx           # Coverage table pagination and bias badge tests
    indicators.test.tsx     # Technical indicator chart rendering and toggle tests
    risk.test.tsx           # Risk form, validation, and fixture calculation tests
    signals.test.tsx        # Signal filters, badge verification, and screening tests
  vitest.config.ts          # Vitest configuration with jsdom
  playwright.config.ts      # Playwright E2E configuration
  package.json              # Next.js 14, React 18, Tailwind, TanStack Query, Recharts
  Dockerfile                # Multi-stage production container for Next.js
/e2e
  data.spec.ts              # E2E test verifying ingest -> coverage -> Recharts graph
  health.spec.ts            # E2E test verifying backend health
  indicators.spec.ts        # E2E test verifying EMA visualization and toggles
  risk.spec.ts              # E2E test verifying risk form sizing and metrics
  signals.spec.ts           # E2E test verifying signals table and screening
/data/fixtures/             # Parquet datasets for equities, Nifty benchmark, and constituents
docker-compose.yml          # Backend (:8000) + Frontend (:3000) + Postgres (:5432)
Makefile                    # Unified automation targets
.github/workflows/ci.yml    # GitHub Actions workflow
README.md
docs/ASSUMPTIONS.md         # Strategy methodology, filter rules, and risk assumptions
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
- Launches Next.js frontend at [http://localhost:3000](http://localhost:3000) (Risk dashboard at [`/risk`](http://localhost:3000/risk), Signals dashboard at [`/signals`](http://localhost:3000/signals)).
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
| `GET` | `/api/v1/health` | API v1 health status |
| `POST` | `/api/v1/data/ingest` | Trigger idempotent market data ingestion for start/end dates |
| `GET` | `/api/v1/data/coverage` | Returns available date ranges and session counts per symbol |
| `GET` | `/api/v1/universe?date=YYYY-MM-DD` | Returns NSE 101–750 tickers with survivorship bias flag |
| `GET` | `/api/v1/prices/{symbol}?start=&end=` | Returns chronological OHLCV bars (404 for unknown symbols) |
| `GET` | `/api/v1/indicators/{symbol}` | Equity OHLCV augmented with EMAs (20, 50, 150, 200) and 52W high |
| `GET` | `/api/v1/indicators/nifty` | NIFTY 50 benchmark with EMAs (50, 200) |
| `POST` | `/api/v1/indicators/preview` | Dynamic on-the-fly technical indicator calculations |
| `GET` | `/api/v1/signals/{symbol}` | Chronological OHLCV with regime, trend, 52W high, and entry/exit signals |
| `GET` | `/api/v1/signals/screen?date=YYYY-MM-DD` | Screens active universe constituents for valid entry signals |
| `POST` | `/api/v1/risk/size` | Calculates integer share quantity, capital required, SL, and risk amount |
| `GET` | `/api/v1/risk/config` | Returns default risk, stop loss, capital, and cost basis points |

---

## 5. Risk Management, Sizing & Gap-Down Execution Rules

### 1. Position Sizing Formula (PRD §4)
Position sizing strictly bounds the maximum loss at the 7% stop loss level to 2% of the available portfolio corpus:
$$\text{Risk Amount} = \text{Corpus} \times \text{Risk \%} \quad (₹5,00,000 \times 0.02 = ₹10,000)$$
$$\text{SL Distance} = \text{Entry Price} \times \text{SL \%} \quad (₹100 \times 0.07 = ₹7.00)$$
$$\text{Quantity} = \left\lfloor \frac{\text{Risk Amount}}{\text{SL Distance} \times \text{Lot Size}} \right\rfloor \times \text{Lot Size} = \left\lfloor \frac{10000}{7 \times 1} \right\rfloor \times 1 = 1,428 \text{ shares}$$
$$\text{Capital Required} = \text{Quantity} \times \text{Entry Price} = 1,428 \times ₹100 = ₹1,42,800 \quad (\approx 28.56\% \text{ of corpus})$$

### 2. Gap-Down Semantics (Explicit Backtesting Assumption)
In live trading and end-of-day simulation:
- **Intraday Stop**: If $\text{Low}_T \le \text{SL Price} < \text{Open}_T$, the trade exits at the exact Stop Loss price level ($\text{Exit Price} = \text{SL Price}$, reason: `"stop_loss"`).
- **Overnight Gap-Down**: If the market opens below the stop loss level ($\text{Open}_T \le \text{SL Price}$), the order is executed at the session **Open price** ($\text{Exit Price} = \text{Open}_T$, reason: `"gap"`).
  - *Consequence:* The realized percentage loss strictly exceeds the nominal 7% stop loss ($\text{Loss} > 7\%$).
  - *Account Risk Impact:* The actual monetary loss strictly exceeds 2% of the portfolio corpus. The backtesting engine records and attributes this realistic slippage/gap risk without artificial capping.

### 3. Transaction Frictions & Slippage
- Standard discount brokerage and statutory transaction taxes (STT) are modeled at **10 basis points (0.10%) per side**:
  - Buy/Entry Price: $\text{Price} \times (1 + \frac{10}{10000}) = \text{Price} \times 1.0010$
  - Sell/Exit Price: $\text{Price} \times (1 - \frac{10}{10000}) = \text{Price} \times 0.9990$

### 4. Portfolio Allocation Constraints
- **Maximum Concurrent Positions**: Because each position at 2% risk and 7% SL requires allocating $\sim 28.5\%$ of capital, the system can hold a maximum of **3 to 4 concurrent positions** under the 100% exposure constraint:
  $$\text{Current Open Positions Value} + \text{Capital Required} \le \text{Corpus}$$

---

## 6. Three-Layer Test Harness

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

## 7. Code Quality & Linting

```bash
make lint
```
- Backend: `ruff check backend` and `black --check backend`
- Frontend: `next lint` and `tsc --noEmit` (TypeScript strict mode)

---

## 8. Phase 4 Acceptance Criteria Verification

- [x] Initial Stop Loss calculation (`stop_loss_price = entry * (1 - 0.07)`)
- [x] Dynamic 2% account risk sizing (`risk_amount = corpus * risk_pct`)
- [x] Integer position sizing derivation (`floor(risk_amount / (entry * sl_pct))`)
- [x] Property test (Hypothesis): `qty * entry * sl_pct <= risk_amount` for all positive prices
- [x] Overnight gap-down exit resolution (`Open <= SL -> exit at Open, loss > 7% and > 2%`)
- [x] Transaction friction cost model (`apply_costs` with 10 bps / 0.10% per side)
- [x] Portfolio exposure allocation constraint (`open_positions + required <= corpus`)
- [x] FastAPI REST endpoints (`POST /api/v1/risk/size` and `GET /api/v1/risk/config`) with input validation
- [x] Next.js `/risk` interactive dashboard with live calculation, Zod validation, and error states
- [x] Frontend Vitest component tests with MSW mock handlers
- [x] Playwright E2E test verifying full form interaction and results display
- [x] Position sizing math and gap-down semantics explicitly documented in `README.md` and `docs/ASSUMPTIONS.md`
- [x] Backend test coverage $\ge 80\%$ gate passed (88.40%)

