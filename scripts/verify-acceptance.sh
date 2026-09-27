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

# Helper to run curl directly inside the container network
api_curl() {
  docker exec equitest-backend-prod curl -s "$@"
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
ROOT_STATUS=$(api_curl -o /dev/null -w "%{http_code}" http://localhost:8000/health)
V1_STATUS=$(api_curl -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
if [ "$ROOT_STATUS" = "200" ] && [ "$V1_STATUS" = "200" ]; then
  log_pass "AC-10: Both /health and /api/v1/health responded with HTTP 200"
else
  log_fail "AC-10: Health endpoints failed (root: $ROOT_STATUS, v1: $V1_STATUS)"
fi

# AC-03: Ingestion via Yahoo Finance
log_info "Testing AC-03: Remote Market Data Ingestion..."
INGEST_RESP=$(api_curl -X POST "http://localhost:8000/api/v1/data/ingest" \
  -H "Content-Type: application/json" \
  -d '{"start":"2023-01-01","end":"2023-01-31","symbols":["INFY"]}')
STATUS=$(echo "$INGEST_RESP" | jq -r '.status // empty')
if [ "$STATUS" = "completed" ] || [ "$STATUS" = "partial" ]; then
  log_pass "AC-03: Successfully executed remote ingestion (status: $STATUS)"
else
  log_fail "AC-03: Ingestion failed: $INGEST_RESP"
fi

# AC-04: Coverage Table
log_info "Testing AC-04: Coverage API Verification..."
COV_COUNT=$(api_curl http://localhost:8000/api/v1/data/coverage | jq '.items | length')
if [ "$COV_COUNT" -gt 0 ]; then
  log_pass "AC-04: Coverage API reports $COV_COUNT symbols"
else
  log_fail "AC-04: Coverage API returned empty list"
fi

# AC-05: Backtest Execution & Persistence
log_info "Testing AC-05: Backtest Execution & Persistence..."
BT_RESP=$(api_curl -X POST "http://localhost:8000/api/v1/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{"strategy_name":"momentum_high_52w","start_date":"2023-01-01","end_date":"2023-01-31","initial_capital":1000000,"symbols":["INFY","RELIANCE"]}')
RUN_ID=$(echo "$BT_RESP" | jq -r '.run_id // empty')
if [ -n "$RUN_ID" ]; then
  sleep 3
  docker compose -f docker-compose.prod.yml restart backend >/dev/null 2>&1
  sleep 5
  PERSIST=$(api_curl "http://localhost:8000/api/v1/backtest/runs" | jq -r ".[] | select(.run_id == \"$RUN_ID\") | .run_id")
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
RUN_COUNT=$(api_curl "http://localhost:8000/api/v1/backtest/runs" | jq '. | length')
if [ "$RUN_COUNT" -le 6 ]; then
  log_pass "AC-06: Retained runs count ($RUN_COUNT) within limit"
else
  log_fail "AC-06: Retained runs count ($RUN_COUNT) exceeds MAX_BACKTEST_RUNS"
fi

# AC-07: Documentation Files Presence
log_info "Testing AC-07: 11 Documentation Files in data/containerization/..."
DOC_COUNT=$(find data/containerization -maxdepth 1 -name "*.md" | wc -l)
if [ "$DOC_COUNT" -ge 11 ]; then
  log_pass "AC-07: Found $DOC_COUNT markdown files in data/containerization/"
else
  log_fail "AC-07: Only found $DOC_COUNT markdown files (expected 11)"
fi

# AC-08: Quantitative Strategy Invariants
log_info "Testing AC-08: Quantitative Strategy Invariant Tests..."
if ./backend/.venv/bin/pytest backend/tests/test_engine_execution.py \
                              backend/tests/test_engine_constraints.py \
                              backend/tests/test_indicators_pipeline.py \
                              -o addopts="" -q >/dev/null 2>&1; then
  log_pass "AC-08: Quant invariant test suite passed"
else
  log_fail "AC-08: Quant invariant tests failed"
fi

# AC-09: WeasyPrint PDF Export
log_info "Testing AC-09: PDF Generation Engine..."
PDF_HEADER=$(api_curl "http://localhost:8000/api/v1/reports/${RUN_ID:-dummy}/pdf" | head -c 4 || true)
if [ "$PDF_HEADER" = "%PDF" ]; then
  log_pass "AC-09: Generated PDF begins with valid %PDF header"
else
  log_fail "AC-09: PDF generation failed or returned invalid header: $PDF_HEADER"
fi

echo "=================================================================="
echo -e " Summary: ${GREEN}$PASSED_COUNT Passed${NC}, ${RED}$FAILED_COUNT Failed${NC}"
echo "=================================================================="
test "$FAILED_COUNT" -eq 0
