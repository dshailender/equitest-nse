# EquiTest NSE — Operations Runbook & Parameter Walkthrough

This runbook provides actionable deployment, data ingestion, parameter modification, and troubleshooting instructions for operators and quantitative engineers.

---

## 1. Quickstart (< 15 Minutes Setup)

### Prerequisites
- Python 3.11+ (tested on Python 3.11 & 3.14)
- Node.js 20+ & npm 10+
- Git & Make

### Installation & Launch
```bash
# 1. Clone repository
git clone https://github.com/equitest/equitest-nse.git
cd equitest-nse

# 2. Automated dependency installation and schema generation
make install

# 3. Launch both backend (:8000) and frontend (:3000)
make dev
```
Navigate to `http://localhost:3000` to access the interactive web application.

---

## 2. Walkthrough: "How to Change a Strategy Parameter"

This walkthrough demonstrates how to add, modify, or tune a quantitative strategy parameter end-to-end across the backend engine, OpenAPI schema, and frontend UI.

### Step 1: Update the Pydantic Strategy Configuration
Edit `backend/app/strategy/config.py`:
```python
class StrategyConfig(BaseModel):
    # Existing parameters...
    capital: float = Field(default=500000.0, gt=0)
    risk_pct: float = Field(default=0.02, gt=0, lt=1)
    sl_pct: float = Field(default=0.07, gt=0, lt=1)

    # Example: Add a new ATR multiplier for dynamic trailing stop
    atr_multiplier: float = Field(
        default=2.5,
        gt=0,
        description="ATR multiple applied for volatility trailing exit"
    )
```

### Step 2: Implement Parameter Logic in Strategy Engine
Consume the new parameter in `backend/app/strategy/signals.py` or `backend/app/engine/backtest.py`:
```python
# In backend/app/engine/backtest.py:
trailing_stop = entry_price - (atr_val * self.config.atr_multiplier)
```

### Step 3: Regenerate OpenAPI Schema & TypeScript Types
Run the monorepo make target:
```bash
make openapi
```
This automatically:
1. Re-exports `frontend/openapi.json` from the FastAPI application.
2. Regenerates `frontend/lib/schema.d.ts` with strict TypeScript types.

### Step 4: Expose Parameter in Frontend UI
Add the state hook and form input to `frontend/app/backtest/page.tsx` (and `frontend/app/sweep/page.tsx` for grid sweeps):
```tsx
const [atrMult, setAtrMult] = useState<string>("2.5");

// Include in execution request:
await runBacktest({
  config: {
    capital: Number(corpus),
    risk_pct: Number(riskPct) / 100,
    sl_pct: Number(slPct) / 100,
    atr_multiplier: Number(atrMult),
  }
});
```

### Step 5: Verify with Automated Tests & Lint
```bash
make lint
make test-backend
make test-frontend
make test-e2e
```

---

## 3. Data Ingestion Operations

### Market Data Ingestion
To download and refresh historical price data for the active universe:
```bash
# Ingest 2020-2024 price history via REST API
curl -X POST http://localhost:8000/api/v1/data/ingest \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2020-01-01", "end_date": "2024-01-01"}'
```

### Regenerating Local Fixtures
To generate deterministic synthetic test parquets and golden reference files:
```bash
backend/.venv/bin/python backend/app/data/generate_fixtures.py
```

---

## 4. Production Deployment with Docker

### Launching the Production Stack
```bash
# Build and run non-root, multi-stage containers with healthchecks
docker compose -f docker-compose.prod.yml up -d --build

# Verify healthy service state
docker compose -f docker-compose.prod.yml ps
```

### Viewing Logs
```bash
# Backend simulation engine logs
docker compose -f docker-compose.prod.yml logs -f backend

# Frontend application logs
docker compose -f docker-compose.prod.yml logs -f frontend
```

---

## 5. Troubleshooting & FAQ

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **`StarletteDeprecationWarning`** | Harmless warning from FastAPI TestClient using httpx | Ignored by pytest filter; does not affect runtime |
| **Tests fail with 404 on data** | `DATA_SOURCE` env var not set to `CSV` | Run tests with `DATA_SOURCE=CSV make test` |
| **Playwright timeout on port 3000** | Background frontend not warmed up | Ensure port 3000 is open before running e2e tests |
| **Unique constraint error in DB** | Reusing deterministic run ID in SQLite | Use dynamic UUID for run IDs in test fixtures |
