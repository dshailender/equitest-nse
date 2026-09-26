---
title: "09 - Recovery & Operations Runbook"
description: "Operational runbook, rollback procedures, volume management, SQLite maintenance, logging, and offline recovery for EquiTest NSE containers."
date: 2026-09-26
status: active
suite_id: "09-rollback-and-operations"
related_docs:
  - "file:///home/shailender/projects/equitest-nse/data/containerization/README.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/01-current-state-assessment.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/02-containerization-plan.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/03-remote-data-ingestion-plan.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/08-acceptance-criteria.md"
  - "file:///home/shailender/projects/equitest-nse/data/containerization/10-open-questions-and-risks.md"
---

# Recovery & Operations Runbook

## Purpose
This document provides production operators, quantitative researchers, and DevOps engineers with standardized operational procedures for managing, debugging, backing up, and rolling back containerized **EquiTest NSE** environments.

---

## 1. Rollback Procedures

When deploying container updates, configuration changes, or new strategy logic, unexpected regressions or failed database migrations may require immediate rollback to a known stable release.

### 1.1 Git-Level Code Rollback
If a regression was introduced via recent Git commits:

```bash
# 1. Stop running containers to prevent write operations during checkout
docker compose -f docker-compose.prod.yml down

# 2. Check commit history and identify the last known good commit/tag
git log --oneline -n 10

# 3. Checkout the target stable commit or release tag (e.g., v1.0.0)
git checkout v1.0.0
# Alternatively, to hard-reset the branch:
# git reset --hard <STABLE_COMMIT_SHA>

# 4. Rebuild images with no-cache to eliminate corrupted build layers
docker compose -f docker-compose.prod.yml build --no-cache

# 5. Launch containers
docker compose -f docker-compose.prod.yml up -d

# 6. Verify health endpoints
curl -sf http://localhost:8000/health && echo "Backend operational"
curl -sf -I http://localhost:3000 | head -n 1
```

### 1.2 Configuration & Compose State Rollback
If environment variable changes or compose file modifications caused container crashes:

```bash
# 1. Revert compose files or .env files from git
git checkout HEAD -- docker-compose.yml docker-compose.prod.yml .env

# 2. Re-create containers to pick up the restored configuration
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

> [!WARNING]
> **Database Schema Compatibility**:
> If a rollback steps back across a database schema change, the running backend may encounter missing or extraneous columns in SQLite. If schema migrations were applied, restore the SQLite database volume from a pre-migration snapshot as detailed in [Section 3](#3-volume-backup--restore-procedures).

---

## 2. Docker Volume Management

EquiTest NSE isolates state into dedicated Docker named volumes:

| Volume Name | Target Path Inside Container | Purpose | Persistence Policy |
|:---|:---|:---|:---|
| `equitest_data` | `/app/data` | SQLite primary DB (`dev.db` / `prod.db`), cached parquet snapshots | Persistent across container recreation |
| `equitest_backtests` | `/app/data/backtests` | Backtest run execution payloads, metrics JSON, audit hashes | Retained via `MAX_BACKTEST_RUNS` policy |
| `equitest_reports` | `/app/data/reports` | Generated WeasyPrint PDF tear-sheets, CSV trades, XLSX exports | Persistent |
| `postgres_data` | `/var/lib/postgresql/data` | Optional PostgreSQL storage (used only with `--profile with-db`) | Persistent |

### 2.1 Volume Inspection Commands
```bash
# List all project volumes
docker volume ls --filter "name=equitest"

# Inspect volume metadata and host mountpoint
docker volume inspect equitest_data

# Measure actual disk space consumed by Docker volumes
docker system df -v | grep -E "equitest|VOLUME NAME"
```

### 2.2 Volume Pruning & Deletion
To completely reset database state back to clean initial condition:
```bash
# CAUTION: This permanently deletes all stored market data and backtest results!
docker compose -f docker-compose.prod.yml down -v

# Prune unattached dangling volumes
docker volume prune -f
```

---

## 3. Volume Backup & Restore Procedures

Because containers run as an unprivileged user (`appuser:1001`), backing up volume files directly from the host filesystem can trigger permission warnings. The safest and most portable method uses a lightweight **Alpine Linux** container to archive and restore volumes.

### 3.1 Hot Backup Script: `backup-volumes.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "=== Backing up EquiTest NSE Volumes to $BACKUP_DIR ==="

# 1. Flush SQLite WAL to disk inside backend container before backup
if docker ps --format '{{.Names}}' | grep -q "equitest-backend"; then
  echo "Checkpointing SQLite WAL..."
  docker exec equitest-backend sqlite3 /app/data/dev.db "PRAGMA wal_checkpoint(TRUNCATE);" || true
fi

# 2. Archive equitest_data
echo "Archiving volume: equitest_data..."
docker run --rm \
  -v equitest_data:/source:ro \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar -czf "/backup/equitest_data_${TIMESTAMP}.tar.gz" -C /source .

# 3. Archive equitest_backtests
echo "Archiving volume: equitest_backtests..."
docker run --rm \
  -v equitest_backtests:/source:ro \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar -czf "/backup/equitest_backtests_${TIMESTAMP}.tar.gz" -C /source .

# 4. Generate SHA-256 checksums
cd "$BACKUP_DIR"
sha256sum "equitest_data_${TIMESTAMP}.tar.gz" "equitest_backtests_${TIMESTAMP}.tar.gz" > "backup_${TIMESTAMP}.sha256"

echo "=== Backup completed successfully at $TIMESTAMP ==="
ls -lh "$BACKUP_DIR"/*"${TIMESTAMP}"*
```

### 3.2 Volume Restore Script: `restore-volumes.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

DATA_ARCHIVE="${1:?Usage: $0 <path-to-equitest_data.tar.gz> [path-to-equitest_backtests.tar.gz]}"
BT_ARCHIVE="${2:-}"

echo "=== Restoring EquiTest NSE Volumes ==="

# 1. Stop active containers
echo "Stopping services..."
docker compose -f docker-compose.prod.yml down

# 2. Ensure target volume exists
docker volume create equitest_data >/dev/null

# 3. Wipe and restore equitest_data
echo "Restoring equitest_data from $DATA_ARCHIVE..."
docker run --rm \
  -v equitest_data:/target \
  -v "$(cd "$(dirname "$DATA_ARCHIVE")" && pwd)":/backup \
  alpine sh -c "
    rm -rf /target/* &&
    tar -xzf /backup/$(basename "$DATA_ARCHIVE") -C /target &&
    chown -R 1001:1001 /target
  "

# 4. Restore equitest_backtests if provided
if [ -n "$BT_ARCHIVE" ] && [ -f "$BT_ARCHIVE" ]; then
  echo "Restoring equitest_backtests from $BT_ARCHIVE..."
  docker volume create equitest_backtests >/dev/null
  docker run --rm \
    -v equitest_backtests:/target \
    -v "$(cd "$(dirname "$BT_ARCHIVE")" && pwd)":/backup \
    alpine sh -c "
      rm -rf /target/* &&
      tar -xzf /backup/$(basename "$BT_ARCHIVE") -C /target &&
      chown -R 1001:1001 /target
    "
fi

# 5. Restart containers
echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo "=== Restore completed. Running health checks... ==="
sleep 5
curl -sf http://localhost:8000/health && echo "Service healthy!"
```

---

## 4. Direct SQLite DB Inspection Inside Container

Direct database inspection is crucial for troubleshooting data gaps, schema lockups, or verification of price series without installing Python/SQLite on the host.

### 4.1 Quick Inspection One-Liners
```bash
# Check database integrity
docker exec equitest-backend-prod sqlite3 /app/data/prod.db "PRAGMA integrity_check;"

# Check WAL (Write-Ahead Logging) mode
docker exec equitest-backend-prod sqlite3 /app/data/prod.db "PRAGMA journal_mode;"

# Check table list and sizes
docker exec equitest-backend-prod sqlite3 /app/data/prod.db "
  SELECT name FROM sqlite_master WHERE type='table';
"

# Count stored price bars grouped by symbol
docker exec equitest-backend-prod sqlite3 /app/data/prod.db "
  SELECT symbol, COUNT(*) AS bars, MIN(date) AS start, MAX(date) AS end
  FROM prices
  GROUP BY symbol
  ORDER BY bars DESC
  LIMIT 10;
"

# Inspect latest backtest runs
docker exec equitest-backend-prod sqlite3 /app/data/prod.db "
  SELECT run_id, strategy_name, start_date, end_date, cagr, sharpe_ratio, created_at
  FROM backtest_runs
  ORDER BY created_at DESC
  LIMIT 5;
"
```

### 4.2 Interactive SQLite Shell
```bash
# Launch interactive SQLite console inside container
docker exec -it equitest-backend-prod sqlite3 /app/data/prod.db
```
Common interactive commands:
- `.tables` — show all tables
- `.schema prices` — show full CREATE TABLE statement
- `.mode column` / `.headers on` — format output as aligned columns
- `.quit` — exit

### 4.3 Diagnosing SQLite Lock Contention
If the backend throws `sqlite3.OperationalError: database is locked`:
1. Check if multiple processes or threads are attempting concurrent writes.
2. Force a WAL checkpoint to flush locks:
   ```bash
   docker exec equitest-backend-prod sqlite3 /app/data/prod.db "PRAGMA wal_checkpoint(FULL);"
   ```
3. Verify that the SQLite timeout in `session.py` is configured with `timeout=30.0` or higher to handle concurrent reads during ingestion.

---

## 5. Container Logs Inspection & Live Debugging

### 5.1 Real-Time Log Streaming
```bash
# Stream combined logs for all services
docker compose -f docker-compose.prod.yml logs -f

# Follow backend logs with timestamps
docker compose -f docker-compose.prod.yml logs -f --timestamps backend

# View the last 100 lines of frontend logs
docker compose -f docker-compose.prod.yml logs --tail=100 frontend
```

### 5.2 Structured JSON Log Filtering
Because EquiTest NSE uses structured logging with request IDs, use `jq` or `grep` to filter operational anomalies:

```bash
# Filter backend errors
docker compose logs backend | grep -i "ERROR"

# Filter logs for a specific request ID
docker compose logs backend | grep "req_abc123"

# Live monitor incoming HTTP access requests
docker compose logs -f backend | grep "POST /api/v1/"
```

### 5.3 Live Container Resource Monitoring
```bash
# Monitor CPU, memory, and I/O consumption
docker stats --no-stream equitest-backend-prod equitest-frontend-prod
```

### 5.4 Opening a Debugging Shell
```bash
# Backend container bash shell (as appuser)
docker exec -it equitest-backend-prod /bin/bash

# Backend container as root (for troubleshooting system packages/permissions)
docker exec -u 0 -it equitest-backend-prod /bin/bash

# Frontend container sh shell
docker exec -it equitest-frontend-prod /bin/sh
```

---

## 6. Offline Fallback Procedure

In scenarios where outbound internet connectivity is unavailable, Yahoo Finance is blocked, or the platform must run in an air-gapped demo environment, switch to the **Offline Fixture Mode**.

### 6.1 Switching to Offline Fixture Mode

1. **Verify Local Parquet Fixtures**:
   Confirm that [data/fixtures](file:///home/shailender/projects/equitest-nse/data/fixtures) contains valid sample Parquet files:
   ```bash
   ls -la data/fixtures/*.parquet
   # Should list: constituents.parquet, INFY.parquet, RELIANCE.parquet, etc.
   ```

2. **Launch with Offline Compose Override**:
   Create a temporary override or run with local bind mounts enabled:
   ```bash
   # Run with CSV price source and mounted fixtures
   DATA_SOURCE=CSV \
   FIXTURES_DIR=/app/data/fixtures \
   docker compose -f docker-compose.yml up -d
   ```

3. **Verify Seed Execution**:
   On startup, the backend will detect `DATA_SOURCE=CSV` and automatically read prices directly from `/app/data/fixtures` without making outbound internet requests.

4. **Verify Offline Health**:
   ```bash
   # Check coverage loaded from local fixtures
   curl -s http://localhost:8000/api/v1/data/coverage | jq .
   ```

### 6.2 Restoring Online Mode
To return to remote ingestion mode:
```bash
# Reset DATA_SOURCE to yfinance
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 7. Emergency Incident Checklist

| Symptom | Probable Cause | Immediate Remediation |
|:---|:---|:---|
| **Backend crash on boot: `PermissionError`** | Host volume owned by root instead of UID 1001 | Run `docker run --rm -v equitest_data:/v alpine chown -R 1001:1001 /v` |
| **Ingestion fails: `HTTP 429 Too Many Requests`** | Yahoo Finance IP throttling | Pause ingestion for 15 mins; ingest symbols in batches of 5; see [10-open-questions-and-risks.md](./10-open-questions-and-risks.md) |
| **PDF export fails: `OSError: cannot load library 'pango'`** | Missing system dependencies | Ensure runner stage in `backend/Dockerfile` includes `libpango-1.0-0` |
| **Frontend cannot contact API (`Failed to fetch`)** | Browser connecting to `backend:8000` instead of `localhost:8000` | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` for client-side JS |
| **Database disk full warning** | Accumulation of unpruned backtests or logs | Run `VACUUM;` in sqlite3 and verify `MAX_BACKTEST_RUNS` pruning |
