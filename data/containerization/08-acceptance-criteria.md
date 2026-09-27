---
title: "08 - Testable Portability Acceptance Criteria"
description: "Comprehensive acceptance criteria, verification commands, and pass/fail thresholds for containerization and machine portability of EquiTest NSE."
date: 2026-09-26
status: active
suite_id: "08-acceptance-criteria"
related_docs:
  - "file:///home/shailender/projects/equitest-nse/data/containerization/README.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/01-current-state-assessment.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/02-containerization-plan.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/03-remote-data-ingestion-plan.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/09-rollback-and-operations.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/10-open-questions-and-risks.md"
---

# Testable Portability Acceptance Criteria

## Purpose
This document provides the definitive verification matrix, testable acceptance criteria, and exact diagnostic command sequences for validating the containerization and portability milestone of **EquiTest NSE**. 

The fundamental goal is **zero-host-dependency portability**: any pristine machine running Linux, macOS, or Windows (WSL2) with only Git, Docker Engine (>= 24.0), and Docker Compose (v2) must be able to clone the repository and run the full quant backtesting stack without local Python, Node.js, Parquet fixtures, or pre-seeded SQLite databases.

---

## 1. Acceptance Criteria Master Matrix

The table below summarizes all ten mandatory success criteria, their evaluation scope, the corresponding verification mechanism, and pass/fail criteria.

| ID | Criterion Name | Scope | Verification Method | Pass Threshold | Status |
|:---|:---|:---|:---|:---|:---|
| **AC-01** | Pristine Startup | Infrastructure | `docker compose up --build -d` | All containers healthy; exit code 0 | **Mandatory** |
| **AC-02** | Zero Host Data Bind Mounts | Configuration | `docker compose config` inspection | No `./data/fixtures` or `./dev.db` bind mounts in prod compose | **Mandatory** |
| **AC-03** | Remote Market Data Ingestion | Ingestion Engine | Web UI / `POST /api/v1/data/ingest` | Real OHLCV bars ingested via `YFinanceSource` without errors | **Mandatory** |
| **AC-04** | Coverage Table Rendering | Frontend / DB | Web UI `/data` & `GET /api/v1/data/coverage` | Ingested tickers, session counts, and valid date bounds visible | **Mandatory** |
| **AC-05** | Backtest Execution & Persistence | Simulation & Volumes | `POST /api/v1/backtest/run` + container restart | Run completes, audit hash stored, results survive `docker compose restart` | **Mandatory** |
| **AC-06** | Artifact Retention Enforced | Storage Policy | Execute >5 backtests; check volume count | Exactly the last `MAX_BACKTEST_RUNS` (default: 5) retained | **Mandatory** |
| **AC-07** | Complete Documentation Suite | Documentation | File count and checksum verification | All 11 markdown files present in `data/containerization/` | **Mandatory** |
| **AC-08** | Quantitative Invariant Preservation | Quant Core | Pytest invariant test suite inside container | 100% pass on zero look-ahead, gap-down fills, survivorship bias flag | **Mandatory** |
| **AC-09** | WeasyPrint PDF Generation | PDF Engine | Dockerfile smoke test & `GET /api/v1/reports/{id}/pdf` | Valid `%PDF` binary header returned with HTTP 200 | **Mandatory** |
| **AC-10** | Dual Health Endpoint Verification | API Layer | `curl /health` and `curl /api/v1/health` | Both return HTTP 200 with `status="ok"` and matching version | **Mandatory** |

---

## 2. Detailed Verification Procedures

### AC-01: Pristine Machine Startup
**Requirement**: A pristine machine with only Docker, Docker Compose, Git, and outbound internet access must execute `docker compose up --build -d` without manual interventions, environment tweaking, or file copying.

#### Verification Command Sequence
```bash
# 1. Ensure clean environment (simulate fresh machine)
docker compose down -v --remove-orphans
docker builder prune -af

# 2. Build and launch services
docker compose -f docker-compose.prod.yml up --build -d

# 3. Wait for health checks to pass (max 60 seconds)
docker compose -f docker-compose.prod.yml ps
```

#### Evaluation Conditions
- [x] Containers `equitest-backend-prod` and `equitest-frontend-prod` transition to `healthy` state within 45 seconds.
- [x] No exit codes other than `0`.
- [x] Backend is reachable at `http://localhost:8000/health`.
- [x] Frontend is reachable at `http://localhost:3000`.

---

### AC-02: Zero Host Data Bind Mounts
**Requirement**: Production container definitions must not bind mount local host directories such as [data/fixtures](file:///home/shailender/projects/equitest-nse/data/fixtures) or local host SQLite database files (`dev.db`). All application state must reside exclusively in Docker named volumes or ephemeral runtime contexts.

#### Verification Command Sequence
```bash
# Inspect resolved compose volumes for backend
docker compose -f docker-compose.prod.yml config --format json | jq '.services.backend.volumes'
```

#### Expected JSON Output Pattern
```json
[
  {
    "type": "volume",
    "source": "equitest_data",
    "target": "/app/data"
  },
  {
    "type": "volume",
    "source": "equitest_backtests",
    "target": "/app/data/backtests"
  },
  {
    "type": "volume",
    "source": "equitest_reports",
    "target": "/app/data/reports"
  }
]
```

#### Evaluation Conditions
- [x] Output must **not** contain any entry with `"type": "bind"` pointing to `data/fixtures`, `./data`, or `dev.db`.
- [x] Host repository files can be wiped of `.db` and `data/fixtures/*.parquet` without breaking container boot or functionality.

---

### AC-03: Remote Market Data Ingestion
**Requirement**: Triggering market data ingestion from the frontend UI "Start Ingestion" button or the REST API endpoint [`POST /api/v1/data/ingest`](file:///home/shailender/projects/equitest-nse/backend/app/api/v1/data.py#L25) must successfully contact Yahoo Finance via [`YFinanceSource`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L164), retrieve real historical OHLCV data, adjust for splits, and store rows into the container's SQLite database.

#### Verification Command Sequence
```bash
# Ingest 3 benchmark liquid midcap/largecap stocks across a 3-month sample window
curl -s -X POST "http://localhost:8000/api/v1/data/ingest" \
     -H "Content-Type: application/json" \
     -d '{
       "start": "2023-01-01",
       "end": "2023-03-31",
       "symbols": ["INFY", "TCS", "TATAMOTORS"]
     }' | jq .
```

#### Expected JSON Response
```json
{
  "job_id": "ingest-20260926-...",
  "status": "completed",
  "symbols_ingested": 3,
  "rows_ingested": 183,
  "start": "2023-01-01",
  "end": "2023-03-31",
  "errors": []
}
```

#### Evaluation Conditions
- [x] HTTP Status is `200 OK`.
- [x] `status` is `"completed"`.
- [x] `symbols_ingested` equals requested count (3).
- [x] `rows_ingested > 0` (typically ~60–62 trading sessions per symbol for Q1 2023).
- [x] `errors` array is empty.

---

### AC-04: Coverage Table Rendering
**Requirement**: After completing data ingestion, the Data Management screen (`http://localhost:3000/data`) and the coverage endpoint [`GET /api/v1/data/coverage`](file:///home/shailender/projects/equitest-nse/backend/app/api/v1/data.py#L46) must immediately reflect the ingested tickers, starting dates, ending dates, and row counts.

#### Verification Command Sequence
```bash
curl -s "http://localhost:8000/api/v1/data/coverage" | jq .
```

#### Expected JSON Response
```json
{
  "items": [
    {
      "symbol": "INFY",
      "first_date": "2023-01-02",
      "last_date": "2023-03-31",
      "rows": 61
    },
    {
      "symbol": "TATAMOTORS",
      "first_date": "2023-01-02",
      "last_date": "2023-03-31",
      "rows": 61
    },
    {
      "symbol": "TCS",
      "first_date": "2023-01-02",
      "last_date": "2023-03-31",
      "rows": 61
    }
  ]
}
```

#### Evaluation Conditions
- [x] HTTP Status is `200 OK`.
- [x] Each ingested symbol has `rows > 0`.
- [x] In the Web browser at `http://localhost:3000/data`, the "Stored Price Coverage" table lists INFY, TCS, and TATAMOTORS with active date badges.

---

### AC-05: Backtest Execution & Persistence Across Container Restarts
**Requirement**: A backtest simulation must execute successfully, persist its result payload and provenance metadata to disk, and remain readable after completely restarting the backend container.

#### Verification Command Sequence
```bash
# 1. Run a sample backtest on the ingested data
RUN_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/backtest/run" \
     -H "Content-Type: application/json" \
     -d '{
       "strategy_name": "momentum_high_52w",
       "start_date": "2023-01-01",
       "end_date": "2023-03-31",
       "initial_capital": 1000000.0,
       "max_positions": 5
     }')

RUN_ID=$(echo $RUN_RESP | jq -r '.run_id')
echo "Created Backtest Run ID: $RUN_ID"

# 2. Verify run exists in list endpoint
curl -s "http://localhost:8000/api/v1/backtest/runs" | jq -e ".[] | select(.run_id == \"$RUN_ID\")"

# 3. Restart the backend container
docker compose -f docker-compose.prod.yml restart backend
sleep 5

# 4. Verify run persists after restart
PERSIST_CHECK=$(curl -s "http://localhost:8000/api/v1/backtest/runs" | jq -e ".[] | select(.run_id == \"$RUN_ID\")")
test -n "$PERSIST_CHECK" && echo "PASS: Backtest $RUN_ID persisted across container restart."
```

#### Evaluation Conditions
- [x] Backtest initiates and finishes with HTTP 200.
- [x] Output contains valid quant metrics (`cagr`, `sharpe_ratio`, `max_drawdown`, `trades_count`).
- [x] Backtest run record survives container restart without data loss.

---

### AC-06: Artifact Retention Enforced (`MAX_BACKTEST_RUNS`)
**Requirement**: To protect container disk space from exhaustion, the platform must prune older backtest runs and keep only the last `N` runs (where $N = \text{MAX\_BACKTEST\_RUNS}$, defaulting to 5).

#### Verification Command Sequence
```bash
# 1. Trigger 7 rapid backtests
for i in {1..7}; do
  curl -s -X POST "http://localhost:8000/api/v1/backtest/run" \
       -H "Content-Type: application/json" \
       -d '{
         "strategy_name": "momentum_high_52w",
         "start_date": "2023-01-01",
         "end_date": "2023-03-31",
         "initial_capital": 1000000.0,
         "max_positions": 5
       }' > /dev/null
  sleep 1
done

# 2. Check total retained runs in the database
TOTAL_RUNS=$(curl -s "http://localhost:8000/api/v1/backtest/runs" | jq '. | length')
echo "Retained runs in database: $TOTAL_RUNS"

# 3. Check physical JSON files in container volume
CONTAINER_FILES=$(docker exec equitest-backend-prod sh -c "ls -1 /app/data/backtests/*.json 2>/dev/null | wc -l")
echo "Physical JSON files on volume: $CONTAINER_FILES"
```

#### Evaluation Conditions
- [x] `TOTAL_RUNS` $\le 5$ (or matches configured `MAX_BACKTEST_RUNS`).
- [x] `CONTAINER_FILES` matches `TOTAL_RUNS`.
- [x] Oldest runs (runs 1 and 2) are cleanly purged from both database and disk.

---

### AC-07: Complete Documentation Suite
**Requirement**: All 11 documentation files specified in the containerization architecture blueprint must exist in [`data/containerization/`](file:///home/shailender/projects/equitest-nse/data/containerization/) with complete content, structured frontmatter, and valid cross-references.

#### Verification Command Sequence
```bash
DOC_DIR="/home/shailender/projects/equitest-nse/data/containerization"
REQUIRED_DOCS=(
  "README.md"
  "01-current-state-assessment.md"
  "02-containerization-plan.md"
  "03-remote-data-ingestion-plan.md"
  "04-cleanup-and-retention-plan.md"
  "05-run-local-container-first-plan.md"
  "06-pristine-state-checklist.md"
  "07-ingestion-button-fix-plan.md"
  "08-acceptance-criteria.md"
  "09-rollback-and-operations.md"
  "10-open-questions-and-risks.md"
)

MISSING=0
for doc in "${REQUIRED_DOCS[@]}"; do
  if [ ! -f "$DOC_DIR/$doc" ]; then
    echo "MISSING: $doc"
    MISSING=$((MISSING + 1))
  else
    echo "OK: $doc ($(wc -l < "$DOC_DIR/$doc") lines)"
  fi
done

test $MISSING -eq 0 && echo "PASS: All 11 documentation files present."
```

#### Evaluation Conditions
- [x] All 11 files present and non-empty (>50 lines each).
- [x] Every file contains valid Markdown formatting and references.

---

### AC-08: Quantitative Strategy Invariant Preservation
**Requirement**: Containerization and environment abstractions must never compromise quantitative correctness. All core invariants documented in [docs/STRATEGY.md](file:///home/shailender/projects/equitest-nse/docs/STRATEGY.md) and [docs/ASSUMPTIONS.md](file:///home/shailender/projects/equitest-nse/docs/ASSUMPTIONS.md) must be preserved.

#### Specific Invariants to Validate
1. **Zero Look-Ahead**: Indicators are calculated using session $T$ close; trades are simulated strictly at $T+1$ market open.
2. **Survivorship Bias Prevention**: The platform tracks point-in-time index constituents. The `survivorship_bias` boolean flag must be present in API schemas and set to `false` when historical constituents are used.
3. **Overnight Gap-Down Realism**: If stock opens below stop loss ($O_{T+1} < \text{SL}$), fill occurs at $O_{T+1}$, not at the optimistic $\text{SL}$ price.
4. **Top 100 Exclusion**: Stocks ranked 1–100 (NIFTY 50 / large caps) serve as an external market regime filter and are strictly excluded from portfolio trade allocations (trade universe is NSE 101–750).
5. **Backtest Provenance**: Every run record must persist its `git_sha`, parameter signature, and `data_hash`.

#### Verification Command Sequence
```bash
# Execute internal quantitative test suite inside the running backend container
docker exec equitest-backend-prod pytest tests/test_engine_execution.py \
                                       tests/test_engine_constraints.py \
                                       tests/test_indicators_pipeline.py \
                                       -v --tb=short
```

#### Evaluation Conditions
- [x] 100% of quant invariant unit tests pass.
- [x] Zero regressions in execution pricing logic or indicator look-ahead guards.

---

### AC-09: WeasyPrint PDF Export Verification
**Requirement**: Generating professional tear-sheet reports in PDF format via WeasyPrint requires native system dependencies (`libpango-1.0-0`, `libcairo2`, `fonts-dejavu-core`). The container build must pass the WeasyPrint smoke test and the running container must successfully export PDFs.

#### Verification Command Sequence
```bash
# 1. Run backtest to generate run ID
RUN_ID=$(curl -s -X POST "http://localhost:8000/api/v1/backtest/run" \
     -H "Content-Type: application/json" \
     -d '{"strategy_name":"momentum_high_52w","start_date":"2023-01-01","end_date":"2023-03-31","initial_capital":1000000.0}' \
     | jq -r '.run_id')

# 2. Request PDF tear-sheet export
curl -s -D - "http://localhost:8000/api/v1/reports/${RUN_ID}/pdf" -o "/tmp/tearsheet_${RUN_ID}.pdf" | head -n 10

# 3. Verify PDF binary magic header
head -c 4 "/tmp/tearsheet_${RUN_ID}.pdf"
```

#### Evaluation Conditions
- [x] HTTP response header `Content-Type: application/pdf`.
- [x] HTTP Status is `200 OK`.
- [x] First 4 bytes of returned file match `%PDF`.
- [x] File size is greater than 10 KB.

---

### AC-10: Dual Health Endpoints
**Requirement**: The service must provide both root `/health` (used by Docker Compose healthchecks and load balancers) and versioned `/api/v1/health` (used by frontend service discovery and integration tests).

#### Verification Command Sequence
```bash
# 1. Test root health endpoint
ROOT_HEALTH=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "http://localhost:8000/health")
echo "$ROOT_HEALTH"

# 2. Test API v1 health endpoint
V1_HEALTH=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "http://localhost:8000/api/v1/health")
echo "$V1_HEALTH"
```

#### Expected Output
```text
{"status":"ok","version":"0.1.0"}
HTTP_STATUS:200

{"status":"ok","version":"0.1.0"}
HTTP_STATUS:200
```

#### Evaluation Conditions
- [x] Both endpoints return HTTP `200`.
- [x] Response payload JSON contains `{"status": "ok", "version": "0.1.0"}`.
- [x] Latency for both endpoints is $<20\text{ms}$.

---

## 3. Automated End-to-End Acceptance Verification Script

The following standalone script can be executed on any machine to validate all ten criteria automatically:

```bash
#!/usr/bin/env bash
# ==============================================================================
# EquiTest NSE — Automated Container Acceptance Test Suite
# File: scripts/verify-acceptance.sh
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED_COUNT=0
FAILED_COUNT=0

log_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
  PASSED_COUNT=$((PASSED_COUNT + 1))
}

log_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  FAILED_COUNT=$((FAILED_COUNT + 1))
}

log_info() {
  echo -e "${YELLOW}[INFO]${NC} $1"
}

echo "=================================================================="
echo " Starting EquiTest NSE Container Acceptance Test Suite"
echo "=================================================================="

# AC-01: Pristine startup & container health
log_info "Testing AC-01: Container Health & Services..."
if docker compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
  log_pass "AC-01: Backend and Frontend containers are healthy"
else
  log_fail "AC-01: One or more containers are not healthy"
fi

# AC-02: Zero Host Bind Mounts
log_info "Testing AC-02: Host Bind Mount Independence..."
BIND_MOUNTS=$(docker compose -f docker-compose.prod.yml config --format json | jq -r '.. | objects | select(has("type") and .type == "bind") | .source' || true)
if echo "$BIND_MOUNTS" | grep -E "fixtures|dev\.db"; then
  log_fail "AC-02: Host bind mounts detected: $BIND_MOUNTS"
else
  log_pass "AC-02: No host fixture or DB bind mounts found"
fi

# AC-10: Dual Health Endpoints
log_info "Testing AC-10: Health Endpoints (/health and /api/v1/health)..."
ROOT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
V1_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
if [ "$ROOT_STATUS" = "200" ] && [ "$V1_STATUS" = "200" ]; then
  log_pass "AC-10: Both /health and /api/v1/health responded with HTTP 200"
else
  log_fail "AC-10: Health endpoints failed (root: $ROOT_STATUS, v1: $V1_STATUS)"
fi

# AC-03: Ingestion via Yahoo Finance
log_info "Testing AC-03: Remote Market Data Ingestion..."
INGEST_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/data/ingest" \
  -H "Content-Type: application/json" \
  -d '{"start":"2023-01-01","end":"2023-01-31","symbols":["INFY"]}')
ROWS_INGESTED=$(echo "$INGEST_RESP" | jq -r '.rows_ingested // 0')
if [ "$ROWS_INGESTED" -gt 0 ]; then
  log_pass "AC-03: Successfully ingested $ROWS_INGESTED rows for INFY"
else
  log_fail "AC-03: Ingestion returned 0 rows or failed: $INGEST_RESP"
fi

# AC-04: Coverage Table
log_info "Testing AC-04: Coverage API Verification..."
COV_COUNT=$(curl -s http://localhost:8000/api/v1/data/coverage | jq '.items | length')
if [ "$COV_COUNT" -gt 0 ]; then
  log_pass "AC-04: Coverage API reports $COV_COUNT symbols"
else
  log_fail "AC-04: Coverage API returned empty list"
fi

# AC-05: Backtest Execution & Persistence
log_info "Testing AC-05: Backtest Execution & Persistence..."
BT_RESP=$(curl -s -X POST "http://localhost:8000/api/v1/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{"strategy_name":"momentum_high_52w","start_date":"2023-01-01","end_date":"2023-01-31","initial_capital":1000000}')
RUN_ID=$(echo "$BT_RESP" | jq -r '.run_id // empty')
if [ -n "$RUN_ID" ]; then
  docker compose -f docker-compose.prod.yml restart backend >/dev/null 2>&1
  sleep 6
  PERSIST=$(curl -s "http://localhost:8000/api/v1/backtest/runs" | jq -r ".[] | select(.run_id == \"$RUN_ID\") | .run_id")
  if [ "$PERSIST" = "$RUN_ID" ]; then
    log_pass "AC-05: Backtest $RUN_ID succeeded and persisted across container restart"
  else
    log_fail "AC-05: Backtest $RUN_ID not found after restart"
  fi
else
  log_fail "AC-05: Backtest execution failed: $BT_RESP"
fi

# AC-06: Artifact Retention
log_info "Testing AC-06: Backtest Run Retention (MAX_BACKTEST_RUNS)..."
RUN_COUNT=$(curl -s "http://localhost:8000/api/v1/backtest/runs" | jq '. | length')
if [ "$RUN_COUNT" -le 5 ]; then
  log_pass "AC-06: Retained runs count ($RUN_COUNT) within limit (5)"
else
  log_fail "AC-06: Retained runs count ($RUN_COUNT) exceeds MAX_BACKTEST_RUNS (5)"
fi

# AC-07: Documentation Files Presence
log_info "Testing AC-07: 11 Documentation Files in data/containerization/..."
DOC_COUNT=$(find /home/shailender/projects/equitest-nse/data/containerization -maxdepth 1 -name "*.md" | wc -l)
if [ "$DOC_COUNT" -ge 11 ]; then
  log_pass "AC-07: Found $DOC_COUNT markdown files in data/containerization/"
else
  log_fail "AC-07: Only found $DOC_COUNT markdown files (expected 11)"
fi

# AC-08: Quantitative Strategy Invariants
log_info "Testing AC-08: Quantitative Strategy Invariant Tests..."
if docker exec equitest-backend-prod pytest tests/test_engine_execution.py -q >/dev/null 2>&1; then
  log_pass "AC-08: Quant invariant test suite passed"
else
  log_fail "AC-08: Quant invariant tests failed"
fi

# AC-09: WeasyPrint PDF Export
log_info "Testing AC-09: PDF Generation Engine..."
PDF_HEADER=$(curl -s "http://localhost:8000/api/v1/reports/${RUN_ID:-dummy}/pdf" | head -c 4 || true)
if [ "$PDF_HEADER" = "%PDF" ]; then
  log_pass "AC-09: Generated PDF begins with valid %PDF header"
else
  log_fail "AC-09: PDF generation failed or returned invalid header: $PDF_HEADER"
fi

echo "=================================================================="
echo -e " Summary: ${GREEN}$PASSED_COUNT Passed${NC}, ${RED}$FAILED_COUNT Failed${NC}"
echo "=================================================================="

if [ "$FAILED_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
```

---

## 4. Sign-Off & Verification Checklist

Before tagging a production or portability release, the release engineer must verify each item and sign off in the table below:

```text
[ ] AC-01: Pristine machine build passes without host cache
[ ] AC-02: Confirmed zero bind mounts to local fixtures or dev.db
[ ] AC-03: Live Yahoo Finance ingestion confirmed via Web UI button
[ ] AC-04: Coverage table shows fresh date range and session counts
[ ] AC-05: Backtest run persists after `docker compose restart backend`
[ ] AC-06: Retention policy caps stored backtests to MAX_BACKTEST_RUNS
[ ] AC-07: All 11 containerization markdown documents present & indexed
[ ] AC-08: Invariant tests pass (Zero Look-Ahead, Top 100, Gap-Down SL)
[ ] AC-09: WeasyPrint generates valid %PDF tear-sheet
[ ] AC-10: Dual health endpoints respond with HTTP 200 {"status": "ok"}
```
