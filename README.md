# EquiTest NSE - Quantitative Backtesting Framework

> **Indian Equities (NSE 101–750) Quantitative Trend-Following & Backtesting Engine**  
> Status: **Production Ready (Phase 8: Validation, Acceptance, and Handoff Complete)**

---

## 1. Overview & Architecture

EquiTest NSE is an institutional-grade, event-driven quantitative backtesting platform built specifically for Indian equities (NSE 101–750 constituents). The platform enforces institutional research standards:
- **Zero Look-Ahead Guarantee**: Indicators evaluated on session $T$ close; trades executed at session $T+1$ Market Open. Rolling 52W high is strictly shifted by 1 bar.
- **Survivorship Bias Prevention**: Dynamic point-in-time tracking of NSE 101–750 constituents. Survivorship-biased fallbacks are explicitly tagged.
- **Top 100 Large-Cap Exclusion**: NIFTY 50 serves solely as an external market regime filter; equities ranked 1–100 are excluded from trade allocations.
- **Overnight Gap-Down Realism**: Stop loss orders gap-down below the 7% threshold execute at Market Open price, recording actual market drawdown without artificial price improvement.
- **Momentum Candidate Ranking**: When capital constraints limit new entries, candidates are prioritized by `(Close - EMA20) / EMA20` descending.
- **Cartesian Grid Sweep Engine**: Multi-dimensional parameter optimization with 2D heatmap visualization and multi-run comparative overlays.
- **Empyrical Cross-Validation**: Core metrics validated to within $\pm 10^{-6}$ precision against Quantopian's `empyrical` benchmark.
- **Run Provenance & Audit Logging**: Cryptographic data fingerprinting (SHA-256), git commit tracking, and environment metadata stored for every execution.
- **TradingView Cross-Check Tooling**: Visual inspection and automated CSV diffing against TradingView reference calculations.
- **Production Containerization**: Multi-stage Dockerfiles (`appuser:1001` / `nextjs:1001`), curl healthchecks, and production compose configurations.

---

## 2. Documentation Hub

Detailed documentation is available in [`docs/`](file:///home/shailender/projects/equitest-nse/docs/) and directly in the application at [`/docs`](http://localhost:3000/docs):
- [**Architecture & System Design**](file:///home/shailender/projects/equitest-nse/docs/ARCHITECTURE.md): Monorepo subsystem boundaries, data flow pipelines, Mermaid sequence diagrams, and technology stack.
- [**Quantitative Strategy Rules**](file:///home/shailender/projects/equitest-nse/docs/STRATEGY.md): PRD §2 rules verbatim (Regime, Stock Trend, 52W Proximity, Crossover Triggers, Risk Sizing, and Exit Conditions).
- [**Assumptions & Design Decisions**](file:///home/shailender/projects/equitest-nse/docs/ASSUMPTIONS.md): PRD §4 Open Questions and chosen default rules (Top 100 exclusion, overnight gap resolution, momentum ranking, integer lots).
- [**Operations & Parameter Runbook**](file:///home/shailender/projects/equitest-nse/docs/RUNBOOK.md): Local development, deployment guide, troubleshooting, and a 5-step walkthrough on adding or modifying quantitative parameters.
- [**Data Integrity & Corporate Actions**](file:///home/shailender/projects/equitest-nse/docs/data.md): Parquet schema definitions, splits/bonus handling, and Yahoo Finance ingestion protocols.

---

## 3. Quickstart (< 15 Minutes)

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- GNU Make or `./bin/make`

### 1. Install & Setup
```bash
git clone https://github.com/equitest/equitest-nse.git
cd equitest-nse
make install
```
Initializes backend virtualenv (`backend/.venv`), installs dev dependencies, installs frontend packages, extracts parquet fixtures, and compiles TypeScript types from OpenAPI schemas.

### 2. Single-Command Local Run
```bash
./run-local
# or: make dev
```
Launches:
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000) (Swagger docs at `/docs`)
- **Next.js Frontend**: [http://localhost:3000](http://localhost:3000)

### 3. Production Deployment (Docker Compose)
```bash
docker compose -f docker-compose.prod.yml up --build -d
```
Runs production multi-stage containers with non-root security contexts (`appuser:1001` and `nextjs:1001`) and continuous healthchecks.

---

## 4. API Endpoints (v1)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status and version (`0.1.0`) |
| `GET` | `/api/v1/health` | API v1 operational health |
| `POST` | `/api/v1/data/ingest` | Idempotent market data ingestion engine |
| `GET` | `/api/v1/data/coverage` | Data coverage intervals and session counts |
| `GET` | `/api/v1/universe?date=YYYY-MM-DD` | Point-in-time NSE 101–750 constituent universe |
| `GET` | `/api/v1/prices/{symbol}` | Chronological OHLCV pricing series |
| `GET` | `/api/v1/indicators/{symbol}` | OHLCV augmented with EMAs (20, 50, 150, 200) and 52W high |
| `POST` | `/api/v1/indicators/preview` | Dynamic on-the-fly technical indicator calculations |
| `GET` | `/api/v1/signals/{symbol}` | Trend, regime, 52W proximity, and crossover signals |
| `GET` | `/api/v1/signals/screen` | Universe screening for active entry setups |
| `POST` | `/api/v1/risk/size` | Exact position sizing, lot constraints, and capital calculations |
| `POST` | `/api/v1/backtest/run` | Execute backtest simulation (sync or async) |
| `GET` | `/api/v1/backtest/{run_id}` | Backtest results, KPIs, equity curve, and trade ledger |
| `GET` | `/api/v1/backtest/{run_id}/audit` | Run provenance: git SHA, parquet hash, config, library versions |
| `POST` | `/api/v1/backtest/sweep` | 2D Cartesian parameter grid sweep execution |
| `GET` | `/api/v1/backtest/sweep/{sweep_id}`| Parameter sweep matrix, best run, and heatmap coordinates |
| `GET` | `/api/v1/reports/{run_id}/summary`| Comprehensive performance metrics cross-checked against empyrical |
| `GET` | `/api/v1/reports/{run_id}/monthly`| Compounded Month × Year returns matrix |
| `GET` | `/api/v1/reports/{run_id}/export` | Multi-format export engine (`format=csv\|xlsx\|zip`) |
| `GET` | `/api/v1/validation/{run_id}/{symbol}` | TradingView cross-check validation points (JSON or CSV) |

---

## 5. Frontend Pages & Dashboards

- **`/data`**: Ingestion controls, coverage table, and interactive historical price chart.
- **`/indicators`**: Vectorized EMA overlays (20, 50, 150, 200) and rolling 52W high viewer.
- **`/signals`**: Universe screener and real-time rule evaluation table.
- **`/risk`**: Interactive position sizing calculator and capital allocation modeler.
- **`/backtest`**: Backtest launcher, performance KPIs, equity curve, and trade log.
- **`/sweep`**: 2D Cartesian sweep heatmap, parameter scatter matrix, and comparative runner.
- **`/reports/[runId]`**: Institutional tear sheet, underwater drawdown chart, trade return histogram, monthly returns matrix, export actions (CSV/XLSX/ZIP), and provenance audit panel.
- **`/validation`**: TradingView visual diff inspection table, variance markers, and CSV exporter.
- **`/docs`**: Interactive in-app documentation browser (Architecture, Strategy Rules, Assumptions, Runbook).

---

## 6. Testing & Quality Assurance

The framework enforces a 3-layer test harness with strict coverage requirements ($\ge 80\%$):

```bash
# Run the complete test harness
make test

# Run individual layers:
make test-backend    # Pytest with coverage gate >= 80% (includes Hypothesis property tests)
make test-frontend   # Vitest unit and component tests with MSW
make test-e2e        # Playwright E2E acceptance suite
```

### Static Analysis & Linting
```bash
make lint
```
- Backend: `ruff check backend` and `black --check backend`
- Frontend: `next lint` and `tsc --noEmit`

---

## 7. License & Compliance
This software is built for institutional quantitative research on Indian equity markets. Backtesting metrics are simulated and do not guarantee future returns.