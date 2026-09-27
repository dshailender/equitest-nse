---
title: "01: Current State Assessment — Codebase Inspection Findings"
description: "Comprehensive audit and technical inspection of EquiTest NSE containerization state, Dockerfiles, compose topologies, path resolution bugs, local host dependencies, database sprawl, and build context bloat."
date: "2026-09-26"
category: "Containerization & Portability"
status: "Active"
authors:
  - "EquiTest Platform Engineering Team"
tags:
  - current-state
  - docker
  - docker-compose
  - path-resolution
  - dependency-audit
  - sqlite
  - infrastructure
---

# Current State Assessment: Codebase Inspection Findings

## Purpose

This document provides a comprehensive, rigorous technical audit of the current containerization, infrastructure, and deployment architecture of the EquiTest NSE platform. The primary objective is to catalog every local-machine dependency, path traversal flaw, configuration mismatch, and database synchronization hazard that currently prevents the application from executing cleanly on a pristine machine from a fresh `git clone`.

All findings and subsequent remediation blueprints strictly preserve the platform's core quantitative finance invariants:
- **Zero Look-Ahead Bias**: Session $T$ indicators computed strictly before session $T+1$ execution at market open.
- **Survivorship Bias Prevention**: Accurate point-in-time universe constituents tracked across rebalance periods; static fallbacks explicitly tagged with `survivorship_bias: true`.
- **Top 100 Large-Cap Exclusion**: Stocks ranked 1–100 excluded from trade allocations; NIFTY 50 (`^NSEI`) acts exclusively as an external regime filter.
- **Overnight Gap-Down Realism**: Stop-loss fills executed at the open of session $T+1$ when gapping below threshold, preventing artificially optimistic fills.
- **Complete Backtest Provenance**: Immutable cryptographic fingerprints of input market data, engine versions, configuration parameters, and Git commit metadata.

---

## 1. Docker Infrastructure & Topology Inventory

The repository currently contains two container definitions and two Compose configurations:

### 1.1 Backend Dockerfile ([backend/Dockerfile](file:///home/shailender/projects/equitest-nse/backend/Dockerfile))

The backend image is defined as a two-stage Debian-based build (`python:3.11-slim`):

```dockerfile
# Stage 1: Dependency builder
FROM python:3.11-slim AS builder
WORKDIR /app
# Installs build-essential, creates /opt/venv, installs pyproject.toml dependencies

# Stage 2: Production runner
FROM python:3.11-slim AS runner
WORKDIR /app
# Installs runtime libraries for WeasyPrint PDF generation
# Copies /opt/venv from builder
# Creates non-root user appuser (UID 1001, GID 1001)
# Copies app/ to /app/app/
# Creates /app/data/backtests and /app/data/fixtures
USER appuser
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Inspection Findings & Deficiencies:
1. **Hardcoded Data Source**: Line 27 sets `ENV DATA_SOURCE=CSV`. This forces containerized runs into local Parquet fixture mode by default, preventing live remote data ingestion unless manually overridden.
2. **Hardcoded Git Commit SHA**: Line 29 hardcodes `ARG GIT_SHA="45391fbd9b001161b500a4c5e92a22170daee4b9"`. Builds from subsequent commits retain this stale hash, corrupting the backtest provenance audit trail.
3. **Incomplete Directory Initialization**: Line 56 creates `/app/data/backtests` and `/app/data/fixtures`, but omits `/app/data/reports` (where PDF tear-sheets are generated) and `/app/data/cache`.
4. **App Nesting Anomaly**: Line 52 executes `COPY app/ ./app/` while `WORKDIR /app` is active, placing application modules at `/app/app/`. This triggers the severe 4x parent path resolution bug detailed in [Section 3](#3-path-resolution-analysis-the-4x-parent-bug).

### 1.2 Frontend Dockerfile ([frontend/Dockerfile](file:///home/shailender/projects/equitest-nse/frontend/Dockerfile))

The frontend image uses a 3-stage build based on Alpine Linux (`node:20-alpine`):

```dockerfile
# Stage 1: deps (installs npm dependencies from package.json)
# Stage 2: builder (copies deps, executes npm run build)
# Stage 3: runner (copies .next and node_modules, runs as nextjs:nodejs UID/GID 1001)
HEALTHCHECK CMD curl -f http://localhost:3000 || exit 1
CMD ["npm", "start"]
```

#### Inspection Findings & Deficiencies:
1. **Host `node_modules` Overwrite**: In the builder stage (line 11), `COPY . .` executes after copying `/app/node_modules` from the deps stage. In the absence of a `.dockerignore` file, this copies the host machine's `frontend/node_modules` directly into the Alpine builder container.
2. **Binary ABI Incompatibility**: If the host machine is Linux glibc (Ubuntu, Debian, Fedora) or macOS, copying host native binaries into Alpine Linux (which uses musl libc) causes subtle native runtime crashes (e.g., in SWC, Turbopack, or Sharp).
3. **Missing Public Directory Handling**: Line 30 uses a fallback copy (`COPY --from=builder /app/public ./public 2>/dev/null || true`) because `frontend/public` is missing from the repository, creating an empty stub.

### 1.3 Docker Compose Configurations

The repository provides two separate Compose files:

#### Development Compose: [docker-compose.yml](file:///home/shailender/projects/equitest-nse/docker-compose.yml)
- **Backend Service**:
  - Ports: `8000:8000`
  - Volumes: `- ./backend/app:/app/app:ro` (read-only bind mount for hot reload).
  - Environment: `APP_ENV=development`, `DATABASE_URL=sqlite:///./dev.db`, `LOG_LEVEL=INFO`.
  - Healthcheck: polls `http://localhost:8000/health`.
- **Frontend Service**:
  - Ports: `3000:3000`
  - Environment: `NEXT_PUBLIC_API_URL=http://backend:8000` (**FATAL DEFECT**).
  - Depends On: `backend: condition: service_healthy`.
- **Postgres Service**: Optional (`image: postgres:16-alpine`), activated via `--profile with-db`.

> [!CAUTION]
> **The `NEXT_PUBLIC_API_URL` DNS Mismatch**:
> In `docker-compose.yml`, setting `NEXT_PUBLIC_API_URL=http://backend:8000` breaks browser interactions. `NEXT_PUBLIC_*` variables are compiled directly into client-side JavaScript executed by the user's web browser on the host machine. The host browser cannot resolve the Docker container hostname `backend`, resulting in `net::ERR_NAME_NOT_RESOLVED` on all client fetch requests (such as the "Start Ingestion" button). For browser execution, the URL must be `http://localhost:8000`.

#### Production Compose: [docker-compose.prod.yml](file:///home/shailender/projects/equitest-nse/docker-compose.prod.yml)
- **Backend Service**:
  - Ports: `8000:8000`
  - Build args: `GIT_SHA: "${GIT_SHA:-45391fbd9b001161b500a4c5e92a22170daee4b9}"`
  - Environment: `APP_ENV=production`, `DATA_SOURCE=CSV`, `DATABASE_URL=sqlite:////app/data/prod.db`, `LOG_LEVEL=INFO`.
  - Volumes:
    - `- ./data/fixtures:/app/data/fixtures:ro` (**CRITICAL HOST DEPENDENCY**).
    - `backtest_data:/app/data/backtests` (named volume).
- **Frontend Service**:
  - Ports: `3000:3000`
  - Environment: `NEXT_PUBLIC_API_URL=http://localhost:8000` (correct for host browsers).
  - Healthcheck: polls `http://localhost:3000`.
- **Networks**: `equitest-network` (bridge).

> [!IMPORTANT]
> **Production Compose Blockers**:
> 1. It explicitly bind-mounts `./data/fixtures`, making production container deployment entirely impossible on a fresh host lacking pre-existing fixture files.
> 2. `DATABASE_URL=sqlite:////app/data/prod.db` writes to `/app/data/prod.db`. While `backtest_data` is mounted to `/app/data/backtests`, `/app/data/` itself is NOT a mounted volume! Every time the container is recreated, `prod.db` is destroyed.
> 3. No volume mount exists for `/app/data/reports`, meaning all WeasyPrint PDF tear-sheets are wiped upon container restart.

---

## 2. Missing Infrastructure Files

A complete scan of the repository reveals critical infrastructure files that are currently missing:

| Missing File | Intended Location | Operational Impact |
|--------------|-------------------|-------------------|
| `.dockerignore` | Repository root | Root-level builds (if invoked) send git history, databases, and local caches to the daemon. |
| `backend/.dockerignore` | `backend/` | Docker daemon context transfer sends `backend/dev.db` (389MB–415MB), `backend/.venv` (~500MB), `.pytest_cache`, and `.hypothesis` on every build. |
| `frontend/.dockerignore` | `frontend/` | Docker daemon transfers `frontend/node_modules` (610MB) and `frontend/.next` (241MB)—over 850MB of context—overwriting clean container builds with host binaries. |
| `.env.example` | Repository root & `backend/` | Fresh clones provide zero guidance on configurable environment variables, leading to configuration guessing and runtime misalignments. |

---

## 3. Path Resolution Analysis: The 4x Parent Bug

A critical path resolution defect exists across multiple core Python backend modules when executed inside containers.

### 3.1 The Flawed Code Traversal

In the local host repository, files reside at:
`<repo_root>/backend/app/data/source.py`

To find the repository root `<repo_root>` from `source.py`, the code walks 4 levels up:
1. `parent` (1) -> `<repo_root>/backend/app/data`
2. `parent` (2) -> `<repo_root>/backend/app`
3. `parent` (3) -> `<repo_root>/backend`
4. `parent` (4) -> `<repo_root>`

This logic was hardcoded across multiple backend modules using either `.parent.parent.parent.parent` or `.parents[4]`:

| Source File | Exact Traversal Code | Intended Target |
|-------------|----------------------|-----------------|
| [`backend/app/api/v1/backtest.py`](file:///home/shailender/projects/equitest-nse/backend/app/api/v1/backtest.py#L72) | `Path(__file__).resolve().parents[4]` | Repository root `/app` |
| [`backend/app/api/v1/backtest.py`](file:///home/shailender/projects/equitest-nse/backend/app/api/v1/backtest.py#L137) | `blob_path = repo_root / "data" / "backtests" / f"{run_id}.json"` | Target JSON save path |
| [`backend/app/data/source.py`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L49) | `base = Path(__file__).resolve().parent.parent.parent.parent` | Repository root `/app` |
| [`backend/app/data/universe.py`](file:///home/shailender/projects/equitest-nse/backend/app/data/universe.py#L143) | `base = Path(__file__).resolve().parent.parent.parent.parent` | Repository root `/app` |
| [`backend/app/data/ingest.py`](file:///home/shailender/projects/equitest-nse/backend/app/data/ingest.py#L179) | `base = Path(__file__).resolve().parent.parent.parent.parent` | Repository root `/app` |
| [`backend/app/reports/pdf.py`](file:///home/shailender/projects/equitest-nse/backend/app/reports/pdf.py#L39) | `REPO_ROOT = Path(__file__).resolve().parents[3]` | Repository root `/app` |
| [`backend/app/reports/metrics.py`](file:///home/shailender/projects/equitest-nse/backend/app/reports/metrics.py#L141) | `repo_root = Path(__file__).resolve().parent.parent.parent.parent` | Repository root `/app` |
| [`backend/app/validation/audit.py`](file:///home/shailender/projects/equitest-nse/backend/app/validation/audit.py#L99) | `repo_root = Path(__file__).resolve().parents[3]` | Repository root `/app` |

### 3.2 The Container Geometry Collapse

Inside the Docker container built by [backend/Dockerfile](file:///home/shailender/projects/equitest-nse/backend/Dockerfile):
- Working Directory is set to: `WORKDIR /app`
- App code is copied via: `COPY app/ ./app/`
- Therefore, the file path inside the container is: `/app/app/data/source.py` (and `/app/app/api/v1/backtest.py`).

Notice that the intermediate `backend/` directory does not exist inside the container! The directory depth is reduced by one level:

```
Container Directory Hierarchy:
/                               <-- parents[4] or 4x parent resolves HERE (root filesystem!)
└── app/                        <-- parents[3] (Expected repo root!)
    └── app/                    <-- parents[2]
        ├── api/                <-- parents[1]
        │   └── v1/             <-- parents[0]
        │       └── backtest.py
        └── data/               <-- parents[0]
            └── source.py
```

### 3.3 Runtime Consequences & Permission Failure

When this traversal executes inside the backend container:

1. **Root File System Saturation**:
   `Path(__file__).resolve().parent.parent.parent.parent` evaluates to `/` (the Linux root filesystem).
2. **Invalid Fixture Target**:
   `self.fixtures_dir = base / "data" / "fixtures"` resolves to `/data/fixtures`. The container's initialized fixtures directory is at `/app/data/fixtures`. As a result, `CSVSource` fails to find any Parquet files.
3. **Fatal Permission Denied Crash on Backtest Save**:
   In [`backend/app/api/v1/backtest.py`](file:///home/shailender/projects/equitest-nse/backend/app/api/v1/backtest.py#L137):
   ```python
   repo_root = Path(__file__).resolve().parents[4]  # Resolves to "/"!
   blob_path = repo_root / "data" / "backtests" / f"{run_id}.json"  # -> "/data/backtests/<id>.json"
   blob_path.parent.mkdir(parents=True, exist_ok=True)
   ```
   The backend container runs as unprivileged user `appuser:appgroup` (UID 1001). The Linux root directory `/` is owned by `root:root` with permissions `0755`. When `appuser` attempts to execute `mkdir` in `/data/backtests`, the Linux kernel denies the operation:
   ```
   PermissionError: [Errno 13] Permission denied: '/data/backtests'
   ```
   This prevents any backtest execution result from being saved in Docker!

---

## 4. Local Machine Dependencies Matrix

The following matrix catalogs all host-bound dependencies, their locations, storage sizes, and fresh-machine impact:

| Dependency / Asset | Exact Host Path | Size / Count | Consumed By | In Git? | In Docker? | Fresh Clone Impact & Blocker Status |
|--------------------|-----------------|--------------|-------------|---------|------------|-----------------------------------|
| **Price Fixtures** | `data/fixtures/*.parquet` | 88 files (~50MB) | `CSVSource`, Unit Tests | ✅ Yes (tracked) | ❌ Only if bind-mounted | **Critical Blocker** if `DATA_SOURCE=CSV` is used in container. |
| **Universe Snapshot** | `data/fixtures/constituents.parquet` | ~2.1MB | `seed_universe_constituents()`, `get_universe()` | ✅ Yes (tracked) | ❌ Only if bind-mounted | **High Blocker**: If unmounted and path resolution fails, initial database seeding fails. |
| **Root SQLite DB** | `./dev.db` | 396MB (415MB unvac) | FastAPI backend when started from root | ❌ No (.gitignored) | ❌ No | **High Blocker**: Fresh clone has no database; fails if runtime expects pre-existing tables. |
| **Backend SQLite DB** | `./backend/dev.db` | 389MB (406MB unvac) | Backend when started from `backend/` dir | ❌ No (.gitignored) | ❌ No | **Confusion Hazard**: Out-of-sync dual database state. |
| **Python Virtualenv** | `backend/.venv/` | ~550MB | Local `run-local`, `Makefile` | ❌ No (.gitignored) | ❌ Container has `/opt/venv` | None for Docker; required for local native mode. |
| **Node Modules** | `frontend/node_modules/` | 610MB | Local frontend dev | ❌ No (.gitignored) | ⚠️ Overwrites container build | **High Risk**: Causes native binary mismatch in Alpine container. |
| **Next.js Build Cache**| `frontend/.next/` | 241MB | Next.js SSR and build output | ❌ No (.gitignored) | ⚠️ Overwrites container build | **High Risk**: Stale build cache copied into Docker context. |
| **Backtest JSON Runs** | `data/backtests/*.json` | 5,367 files (387MB) | Backtest history, audit logs, PDF tear-sheets | ❌ No (.gitignored) | ⚠️ Volume in prod, none in dev | **High Risk**: Lost on dev container recreation; 4x parent bug blocks creation. |
| **Generated Reports** | `data/reports/*.pdf` | 5 files (~1.3MB) | PDF download API, WeasyPrint | ✅ Tracked | ❌ No volume mapped | **Medium Risk**: Generated PDFs disappear when container stops. |

---

## 5. Missing `.dockerignore` Impact Analysis

Because neither the repository root, `backend/`, nor `frontend/` contains a `.dockerignore` file, Docker build contexts transfer enormous volumes of unnecessary, host-polluted data to the Docker daemon.

### 5.1 Backend Build Context Bloat

When `docker compose build backend` executes with context `./backend`:
- The daemon sends the entire `./backend/` directory over the Unix domain socket.
- `backend/dev.db` (389MB) is packaged into the build context.
- `backend/.venv` (~550MB of host-specific Python libraries and binary extensions) is packaged.
- `.pytest_cache/`, `.hypothesis/`, and `.ruff_cache/` are packaged.
- **Total context payload transferred**: **~1.0 GB**!
- **Consequences**:
  - Build initialization takes 30–90 seconds merely transferring context before Dockerfile instructions execute.
  - Huge Docker layer cache invalidation on any local SQLite query or test run.
  - Potential security exposure if temporary test tokens or secrets reside in `.venv` or test artifacts.

### 5.2 Frontend Build Context & Binary Collision

When `docker compose build frontend` executes with context `./frontend`:
- The daemon packages `frontend/node_modules/` (610MB) and `frontend/.next/` (241MB)—over **851 MB** of context.
- Inside [frontend/Dockerfile](file:///home/shailender/projects/equitest-nse/frontend/Dockerfile):
  ```dockerfile
  FROM node:20-alpine AS builder
  WORKDIR /app
  COPY --from=deps /app/node_modules ./node_modules
  COPY . .
  ```
  `COPY . .` copies the host's `node_modules` on top of the Alpine Linux `node_modules` compiled in the `deps` stage!
- **Consequences**:
  - If the host runs macOS (Darwin ARM64/x86_64) or glibc-based Linux, host-specific native bindings (such as `next/dist/compiled/@next/swc-linux-x64-gnu`) overwrite the container's Alpine-compatible bindings (`swc-linux-x64-musl`).
  - Next.js build fails during `RUN npm run build` with cryptic `SWC binary failed to load` or `segmentation fault` errors.

---

## 6. Missing `.env.example` Gap

Currently, the repository does not provide a `.env.example` or `.env.template` file in any directory. 

### 6.1 Configuration Discrepancy Matrix

A developer attempting to configure the application has no unified reference for how environment variables interact across local runs, development containers, and production containers:

| Environment Variable | Default in `app/core/config.py` | Local `run-local` Value | `docker-compose.yml` (Dev) | `docker-compose.prod.yml` (Prod) |
|----------------------|---------------------------------|-------------------------|----------------------------|----------------------------------|
| `APP_ENV` | `"development"` | Not set (`development`) | `"development"` | `"production"` |
| `DATA_SOURCE` | `"yfinance"` | `CSV` (line 23) | Not set (`yfinance` via default) | `CSV` |
| `DATABASE_URL` | `"sqlite:///./dev.db"` | Not set (`./dev.db`) | `"sqlite:///./dev.db"` | `"sqlite:////app/data/prod.db"` |
| `LOG_LEVEL` | `"INFO"` | Not set (`INFO`) | `"INFO"` | `"INFO"` |
| `NEXT_PUBLIC_API_URL` | N/A (Frontend only) | N/A (`http://localhost:8000`) | `"http://backend:8000"` (Broken) | `"http://localhost:8000"` |
| `GIT_SHA` | N/A | Current Git commit | Not set | Hardcoded fallback SHA |

### 6.2 The Fresh Machine Failure Mode
On a pristine machine, without documentation or an example template:
1. The developer does not know whether Postgres is required or if SQLite is standard.
2. The developer does not know that setting `DATA_SOURCE=CSV` without mounting fixtures triggers immediate backtest failures.
3. The developer cannot easily configure external API keys or proxies if required.

---

## 7. Database State Analysis: Dual SQLite Sprawl & `session.py`

Inspection of the filesystem reveals two independent, massive SQLite database files:
1. Root `dev.db` (396MB / 415MB allocated): Contains 203 backtest runs, 249 sweeps, 2,734,625 price records, and 2,250 universe records.
2. `backend/dev.db` (389MB / 406MB allocated): Contains 2,660 backtest runs, 232 sweeps, 2,734,625 price records, and 2,250 universe records.

### 7.1 Root Cause of Dual Database Files

In [backend/app/core/config.py](file:///home/shailender/projects/equitest-nse/backend/app/core/config.py#L9):
```python
DATABASE_URL: str = "sqlite:///./dev.db"
```

In [backend/app/db/session.py](file:///home/shailender/projects/equitest-nse/backend/app/db/session.py#L8-L16):
```python
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)
```

The database connection string `sqlite:///./dev.db` is a **relative path**. Python's SQLite driver resolves `./dev.db` relative to the current working directory (`os.getcwd()`) of the running process:
- When starting the app via `./run-local` from the repository root, the process CWD is `/home/shailender/projects/equitest-nse`. The engine connects to `./dev.db` in the repository root.
- When executing tests or running Uvicorn from inside the `backend/` directory (`cd backend && uvicorn app.main:app`), the process CWD is `/home/shailender/projects/equitest-nse/backend`. The engine connects to `./backend/dev.db`.
- When running in Docker where `WORKDIR /app`, the relative path connects to `/app/dev.db`, an ephemeral file inside the container.

This divergence has caused 2,457 backtest runs to exist exclusively in `backend/dev.db` while other runs exist only in the root `dev.db`, creating confusing data drift.

### 7.2 Database Seeding & Migration Behavior in `session.py`

In [backend/app/db/session.py](file:///home/shailender/projects/equitest-nse/backend/app/db/session.py#L19-L73), the function `init_db()` runs on FastAPI startup:
1. Calls `SQLModel.metadata.create_all(engine)` to create tables.
2. Performs lightweight schema migrations on the `backtest_runs` table, adding `config_version`, `sweep_id`, `cagr`, and `max_drawdown_pct` if missing.
3. Checks price record coverage:
   ```python
   cursor.execute("SELECT count(DISTINCT symbol) FROM prices")
   sym_count = cursor.fetchone()[0]
   if sym_count < 650:
       from app.data.ingest import seed_price_coverage
       seed_price_coverage(conn.connection)
   ```
4. Checks universe membership:
   ```python
   cursor.execute("SELECT count(*) FROM universe_membership WHERE symbol LIKE 'MIDCAP_STOCK_%' OR symbol LIKE 'TOP_%'")
   synthetic_count = cursor.fetchone()[0]
   cursor.execute("SELECT count(*) FROM universe_membership")
   total_univ_count = cursor.fetchone()[0]
   if synthetic_count > 0 or total_univ_count < 2250:
       from app.data.ingest import seed_universe_constituents
       seed_universe_constituents(conn.connection)
   ```

> [!WARNING]
> **Container Seeding Hazard**:
> On a fresh container start without persistent volumes:
> 1. A new, empty database `/app/dev.db` is created.
> 2. `init_db()` triggers `seed_universe_constituents()`.
> 3. `seed_universe_constituents()` attempts to load `constituents.parquet` using the broken 4x parent path traversal (`/data/fixtures/constituents.parquet`).
> 4. The container startup either crashes with `FileNotFoundError` or seeds a degraded synthetic universe.

---

## 8. Data & Fixture Asset Inventory

An exhaustive filesystem scan catalogs the following assets:

| Data Category | Location | Metric / File Count | Disk Footprint | Format & Notes |
|---------------|----------|---------------------|----------------|----------------|
| **Parquet Price Fixtures** | `data/fixtures/` | 88 Parquet files | ~50 MB | Daily OHLCV data for 85+ individual NSE tickers, tiny universe fixtures, and index benchmarks (`^NSEI`). |
| **Universe Constituents** | `data/fixtures/constituents.parquet` | 1 Parquet file | 2.1 MB | Historical point-in-time constituent lists (NSE 101–750 and NIFTY 50/100). |
| **Backtest Run Outputs** | `data/backtests/` | 5,367 JSON files | 387 MB | Full backtest trade logs, equity curves, configuration dumps, and audit SHA fingerprints. |
| **PDF Reports** | `data/reports/` | 5 PDF files | 1.3 MB | Formatted WeasyPrint PDF strategy tear-sheets (`backtest_run_*.pdf`). |
| **Root Database** | `./dev.db` | 1 SQLite file | 396 MB | 203 runs, 2.73M OHLCV rows, 2,250 universe records. |
| **Backend Database** | `backend/dev.db` | 1 SQLite file | 389 MB | 2,660 runs, 2.73M OHLCV rows, 2,250 universe records. |

---

## 9. Docker Directory Placeholder Anomalies

A physical inspection of the `docker/` directory in the repository root uncovered a set of corrupted placeholder artifacts:

```bash
$ ls -la docker/
total 0
drwxr-xr-x. 1 nobody nobody 32 Sep 26 19:01 .
drwxr-xr-x. 1 nobody nobody 40 Sep 26 19:01 postgres
drwxr-xr-x. 1 nobody nobody 58 Sep 26 19:01 rabbitmq

$ file docker/postgres/* docker/rabbitmq/*
docker/postgres/01-init-databases.sh: directory
docker/rabbitmq/definitions.json:     directory
docker/rabbitmq/rabbitmq.conf:        directory
```

### 9.1 Root Cause: The Docker Bind-Mount Fallback Trap

Notice that `01-init-databases.sh`, `definitions.json`, and `rabbitmq.conf` are **directories**, not regular files, and are owned by `nobody:nobody`!

This occurs due to standard Docker Engine behavior:
1. A developer previously attempted to configure Docker Compose with volume mounts such as:
   ```yaml
   volumes:
     - ./docker/postgres/01-init-databases.sh:/docker-entrypoint-initdb.d/01-init-databases.sh
     - ./docker/rabbitmq/definitions.json:/etc/rabbitmq/definitions.json
     - ./docker/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf
   ```
2. When Docker starts a container with a host bind mount where the host file **does not exist**, the Docker daemon automatically creates a **directory** at that path on the host, owned by root/nobody!
3. These phantom directories now block any attempt to create proper initialization scripts or configuration files under those filenames until explicitly deleted with root privileges (`sudo rm -rf docker/`).

---

## 10. Summary of Critical Blockers & Remediation Roadmap

The codebase inspection identifies 10 critical issues that must be addressed to achieve complete, single-command portability:

| # | Critical Blocker | Severity | Subsystem | Target Remediation |
|---|------------------|----------|-----------|--------------------|
| **1** | **4x Parent Path Bug** | **P0 (Crash)** | Backend Python | Replace `.parent.parent.parent.parent` and `.parents[4]` with `Path(settings.BASE_DIR)` or environment variable `APP_DATA_DIR`. |
| **2** | **`NEXT_PUBLIC_API_URL` Mismatch** | **P0 (UI Broken)** | Frontend / Compose | Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in Compose or implement Next.js API route rewrites. |
| **3** | **Hardcoded `DATA_SOURCE=CSV`** | **P1 (Portability)** | Backend Dockerfile & Compose | Change default to `DATA_SOURCE=yfinance` in Dockerfile and Compose; enable autonomous remote fetching. |
| **4** | **Missing `.dockerignore` Files** | **P1 (Performance)** | Root, Backend, Frontend | Create `.dockerignore` in root, `backend/` (ignoring `.venv`, `dev.db`), and `frontend/` (ignoring `node_modules`, `.next`). |
| **5** | **Missing Database Volume Persistence**| **P1 (Data Loss)** | Docker Compose | Establish named volume `equitest_db` mounted to `/app/data/equitest.db` across dev and prod compose. |
| **6** | **Missing Reports Volume Mount** | **P2 (Data Loss)** | Docker Compose | Add named volume `equitest_reports` mounted to `/app/data/reports`. |
| **7** | **Missing `.env.example`** | **P2 (Usability)** | Root Documentation | Author unified `.env.example` documenting all configuration keys and defaults. |
| **8** | **Dual SQLite File Sprawl** | **P2 (Data Drift)** | Architecture / Config | Standardize SQLite path to absolute path derived from project root or `DATABASE_URL` volume. |
| **9** | **Hardcoded Git Commit SHA** | **P2 (Provenance)** | Backend Dockerfile | Replace hardcoded SHA in Dockerfile with dynamic Git build argument (`ARG GIT_SHA`). |
| **10**| **Corrupted `docker/` Phantom Dirs** | **P3 (Hygiene)** | Infrastructure Repo | Delete phantom directories created by Docker daemon and replace with valid config files or stubs. |
