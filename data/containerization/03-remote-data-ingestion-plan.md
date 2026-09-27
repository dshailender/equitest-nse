---
title: "Remote Data Ingestion Plan: Yahoo Finance & NSE India"
description: "Architectural strategy for live and historical market data acquisition via Yahoo Finance, ticker normalization, corporate actions, rate limiting, provenance fingerprinting, and point-in-time constituent generation."
date: "2026-09-26"
category: "Containerization & Portability"
status: "Active / Planned"
authors:
  - "EquiTest Quantitative Engineering Team"
tags:
  - data-ingestion
  - yfinance
  - nse-india
  - corporate-actions
  - survivorship-bias
  - quantitative-finance
---

# Remote Data Ingestion Plan: Yahoo Finance & NSE India

## Purpose

This document defines the quantitative architecture, data models, error resilience, and audit provenance mechanisms for streaming and persisting Indian equity and index market data within containerized EquiTest NSE deployments. By migrating from static local parquet fixtures to an automated remote ingestion model, the system achieves portability across host environments while enforcing non-negotiable financial modeling invariants:

1. **Zero Look-Ahead**: Indicators are calculated strictly on session $T$ close data; execution occurs at $T+1$ market open.
2. **Top 100 Exclusion**: NIFTY 50 acts strictly as an external regime filter; equities ranked 1–100 by market cap are excluded from candidate trade allocations.
3. **Survivorship Bias Prevention**: Universe constituent membership uses point-in-time snapshots rather than retrospective survivor lists.
4. **Overnight Gap-Down Realism**: Preserves unadjusted close and open prices so stop-losses reflect realistic overnight gap-downs rather than smoothed fills.
5. **Backtest Provenance**: All market data ingested remotely is fingerprinted with cryptographic SHA-256 hashes to guarantee mathematical auditability.

---

## 1. Yahoo Finance Source Architecture & Implementation Analysis

### 1.1 Existing Codebase Capability
A key architectural asset of EquiTest NSE is that remote ingestion is **already fully implemented** in the backend service. The class [`YFinanceSource`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L164-L250) in [source.py](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py) adheres to the abstract [`PriceSource`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L10-L40) interface, and the dependency `yfinance>=0.2.40` is declared in `pyproject.toml` (resolving to `yfinance 1.7.0` at container build time).

```
                      +-----------------------------+
                      |   PriceSource (Abstract)    |
                      +-----------------------------+
                                     ^
                                     |
                +--------------------+--------------------+
                |                                         |
    +-----------------------+                 +-----------------------+
    |       CSVSource       |                 |     YFinanceSource    |
    | (data/fixtures/*.pq)  |                 |  (Remote yf.download) |
    +-----------------------+                 +-----------------------+
```

### 1.2 Factory Selection Mechanism
In [source.py](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L251-L257), the factory function [`get_price_source()`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L251) evaluates the environment variable `DATA_SOURCE`:

```python
def get_price_source(source_type: str | None = None) -> PriceSource:
    """Factory returning configured PriceSource instance."""
    stype = (source_type or settings.DATA_SOURCE).strip().upper()
    if stype in ["CSV", "PARQUET", "FIXTURE", "FIXTURES"]:
        return CSVSource()
    return YFinanceSource()
```

### 1.3 Transitioning to Remote Ingestion
To transition containerized environments from local parquet fixtures to live remote data, **zero code changes are required in the core ingestion logic**. The system simply requires setting:
```bash
DATA_SOURCE=yfinance
```
in the container environment (via `docker-compose.yml` or `docker-compose.prod.yml`). The API router ([ingest.py](file:///home/shailender/projects/equitest-nse/backend/app/data/ingest.py)) and frontend UI triggers invoke `get_price_source()`, routing all requests directly through `YFinanceSource`.

---

## 2. NSE Ticker Normalization & Benchmark Mapping

Indian equities listed on the National Stock Exchange (NSE) require specific ticker formatting to query Yahoo Finance's global ticker database.

### 2.1 Ticker Normalization Logic
Normalization is encapsulated within [`YFinanceSource._normalize_ticker()`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L167-L177):

```python
def _normalize_ticker(self, symbol: str, is_index: bool = False) -> str:
    s = symbol.strip().upper()
    if is_index:
        if s in ["NIFTY", "NIFTY50", "NIFTY_50", "^NSEI"]:
            return "^NSEI"
        return s if s.startswith("^") else f"^{s}"
    else:
        if s.endswith(".NS") or s.endswith(".BO"):
            return s
        return f"{s}.NS"
```

| Ingestion Input Symbol | Target Asset Type | Normalized Yahoo Ticker | Description |
|---|---|---|---|
| `RELIANCE` | Equity | `RELIANCE.NS` | Reliance Industries Ltd (NSE) |
| `HDFCBANK` | Equity | `HDFCBANK.NS` | HDFC Bank Ltd (NSE) |
| `INFY.NS` | Equity | `INFY.NS` | Infosys Ltd (Idempotent suffix) |
| `TCS.BO` | Equity | `TCS.BO` | Tata Consultancy Services (BSE) |
| `NIFTY` | Benchmark Index | `^NSEI` | NIFTY 50 Benchmark |
| `NIFTY50` / `NIFTY_50` | Benchmark Index | `^NSEI` | Canonical NIFTY 50 identifier |
| `^NSEI` | Benchmark Index | `^NSEI` | Standard Yahoo index identifier |

### 2.2 Top 100 Exclusion & Regime Invariant
In accordance with [docs/STRATEGY.md](file:///home/shailender/projects/equitest-nse/docs/STRATEGY.md), the NIFTY 50 index (`^NSEI`) serves strictly as a **macro market regime filter**:
- **Regime Bull Condition**: $\text{Close}_{\text{NIFTY}} > \text{EMA}_{50}(\text{NIFTY}) \text{ AND } \text{Close}_{\text{NIFTY}} > \text{EMA}_{200}(\text{NIFTY})$
- **Universe Restriction**: Stocks ranked 1–100 by market capitalization (including NIFTY 50 constituents) are **strictly excluded** from trade candidate rankings.
- **Data Isolation**: In [`ingest_market_data()`](file:///home/shailender/projects/equitest-nse/backend/app/data/ingest.py#L140-L175), index data is committed exclusively to the `index_prices` table, while equities are committed to `prices`. This separation guarantees that benchmark index rows can never contaminate the equity backtest universe.

---

## 3. Corporate Actions & Price Realism Invariants

Handling corporate actions—stock splits, bonus issues, and cash dividends—is critical to preventing backtest distortion while preserving execution realism.

### 3.1 The `auto_adjust=False` Invariant
In [`YFinanceSource._fetch_from_yfinance()`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L181-L187), the download call explicitly configures:
```python
df = yf.download(
    ticker,
    start=start,
    end=end,
    progress=False,
    auto_adjust=False,
)
```

> [!IMPORTANT]
> If `auto_adjust=True` were used, Yahoo Finance would overwrite the raw `Open`, `High`, `Low`, and `Close` with dividend- and split-adjusted values. This destroys overnight gap-down realism!

### 3.2 Dual Price Model: Indicators vs. Execution

The backend stores both unadjusted `close` and split/dividend-adjusted `adj_close`:

```
                       +-----------------------------+
                       |      YFinance Download      |
                       |    (auto_adjust = False)    |
                       +-----------------------------+
                                      |
                     +----------------+----------------+
                     |                                 |
           [Raw OHLCV Series]                 [Adjusted Close Series]
                     |                                 |
         +-----------------------+         +-----------------------+
         |   Execution Engine    |         |    Signal Engine      |
         | - Overnight gap-down  |         | - EMA 20/50/150/200   |
         | - Realistic stop-loss |         | - 52-week High/Low    |
         | - Session Open fills  |         | - Momentum Percentile |
         +-----------------------+         +-----------------------+
```

1. **Signal Generation (Adjusted)**:
   - Technical indicators—such as Exponential Moving Averages ($\text{EMA}_{20}$, $\text{EMA}_{50}$, $\text{EMA}_{150}$, $\text{EMA}_{200}$) and 52-week breakout highs—must evaluate continuous price series.
   - For example, if a stock executes a 2:1 stock split (such as RELIANCE on 2021-06-01), the pre-split unadjusted prices drop overnight by 50%. Calculating EMAs across unadjusted values would trigger a false catastrophic breakdown signal. Using `adj_close` eliminates split distortion.
2. **Trade Execution & Gap Realism (Unadjusted)**:
   - Orders trigger and fill at $T+1$ market open based on unadjusted prices.
   - Stop-loss exits use unadjusted prices to capture real overnight gaps. If an adverse event causes a stock to gap down 8% below the stop-loss price at market open, the fill price must reflect the actual market open, not an artificial fill at the exact stop-loss threshold.

### 3.3 Data Integrity Validation
Prior to database insertion, all remote dataframes pass through [`validate_ohlcv_dataframe()`](file:///home/shailender/projects/equitest-nse/backend/app/data/ingest.py#L10-L60):
- **Monotonic Ascending Dates**: Verifies dates are sorted chronologically with no duplicates (guarantees Zero Look-Ahead).
- **Price Consistency**: Validates $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$.
- **Non-Negativity**: Validates $\text{Volume} \ge 0$ and $\text{Adj Close} > 0$.
- **Null Safety**: Prohibits `NaN` or `Inf` values across all required price columns.

---

## 4. Rate Limiting, Resilience & Error Handling

Yahoo Finance provides a free, unauthenticated endpoint subject to dynamic IP throttling and rate limiting.

### 4.1 Rate Limits & Failure Modes
- **Observed Limits**: Approximately 2,000 requests per rolling hour per IP address.
- **Burst Limits**: Rapid bursts exceeding 5–10 requests per second trigger HTTP `429 Too Many Requests` or empty DataFrame responses (`df.empty == True`).
- **Network Timeouts**: Long date ranges across hundreds of symbols can encounter socket dropouts.

### 4.2 Recommended Resilience Architecture

To make `YFinanceSource` enterprise-ready for containerized environments, the following resilience wrapper should be introduced:

```python
import time
from functools import wraps
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class ResilientYFinanceClient:
    """Resilient wrapper for Yahoo Finance downloads with exponential backoff and rate limiting."""
    
    def __init__(self, requests_per_second: float = 1.5, max_retries: int = 4):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self.max_retries = max_retries

    def _throttle(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def fetch_symbol(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        self._throttle()
        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            timeout=30
        )
        if df is None:
            raise ConnectionError(f"Received null response from yfinance for {ticker}")
        return df
```

### 4.3 Batch Download Optimization
For bulk universe ingestion (e.g. ingesting 50 symbols at once), sequential downloads increase connection overhead. `yf.download` supports passing a list of tickers:
```python
tickers = [f"{s}.NS" for s in symbol_list]
batch_df = yf.download(tickers, start=start, end=end, group_by="ticker", threads=True)
```
Batching reduces the HTTP handshake count by up to 80%, avoiding burst-rate penalties.

---

## 5. Local Caching & SHA-256 Provenance Fingerprinting

In [audit.py](file:///home/shailender/projects/equitest-nse/backend/app/validation/audit.py#L86-L160), the function [`compute_data_snapshot_hash()`](file:///home/shailender/projects/equitest-nse/backend/app/validation/audit.py#L86) currently calculates a SHA-256 digest of static `.parquet` files located in `/data/fixtures`. 

When switching to `DATA_SOURCE=yfinance`, local parquet files are not present on disk. Without an updated fingerprinting mechanism, `audit.py` returns `empty_fixtures` or `no_fixtures_directory`, compromising backtest auditability.

### 5.1 Remote Data Provenance Architecture

```
[Remote Yahoo Finance Ingestion]
                |
                v
       [Clean DataFrame]
                |
       +--------+--------+
       |                 |
       v                 v
[SQLite Prices]  [Local Parquet Cache] (/app/data/cache/yfinance/<sym>.parquet)
                         |
                         v
        [Deterministic Canonical SHA-256 Digest]
                         |
                         v
      [Backtest Provenance Metadata (audit.py)]
```

### 5.2 Deterministic SHA-256 Hashing Algorithm
1. **Cache Persistence**: Whenever `YFinanceSource` fetches a valid dataset, the resulting DataFrame is written to `/app/data/cache/yfinance/{symbol}.parquet` (persisted on the `equitest_db` named volume).
2. **Canonical Record Digest**: If hashing in-memory data directly, compute the SHA-256 digest against the canonical CSV byte representation (sorted ascending by date):
   ```python
   def compute_dataframe_hash(df: pd.DataFrame) -> str:
       """Computes deterministic SHA-256 hash across normalized price dataframe."""
       hasher = hashlib.sha256()
       # Canonical subset and order
       cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
       ordered = df[cols].sort_values("date").reset_index(drop=True)
       hasher.update(ordered.to_csv(index=False).encode("utf-8"))
       return hasher.hexdigest()
   ```
3. **Audit Payload Integration**: In [`record_run_audit()`](file:///home/shailender/projects/equitest-nse/backend/app/validation/audit.py#L161-L214), the record includes:
   ```json
   {
     "run_id": "sweep-run-101",
     "git_sha": "b73a812",
     "data_source": "yfinance",
     "data_hash": "a1b2c3d4e5f6...7890",
     "ingestion_timestamp": "2026-09-26T21:00:00Z",
     "versions": {
       "yfinance": "0.2.40",
       "pandas": "2.2.0",
       "numpy": "1.26.4"
     }
   }
   ```

---

## 6. Point-in-Time Universe Constituents Strategy

A quantitative backtest must evaluate only stocks that were legitimate members of the tradeable universe at historical rebalance dates.

### 6.1 Current Dependency on `constituents.parquet`
Currently, [`get_universe_tickers()`](file:///home/shailender/projects/equitest-nse/backend/app/data/universe.py#L300-L396) checks:
1. The `universe_membership` table in the database.
2. `data/fixtures/constituents.parquet` (if DB rows are missing).
3. If neither is available, it falls back to [`get_default_fallback_constituents()`](file:///home/shailender/projects/equitest-nse/backend/app/data/universe.py#L391) and sets `survivorship_bias = True`.

### 6.2 Architectural Options Analysis

| Strategy | Implementation Details | Advantages | Drawbacks | Recommendation |
|---|---|---|---|---|
| **Option (a): Embed File in Image** | `COPY data/fixtures/constituents.parquet /app/data/fixtures/` in Dockerfile. | Simple to configure; zero runtime startup delay. | Commits binary files to container images; difficult to update without rebuilding. | Not Recommended |
| **Option (b): Generate at Runtime via Code** | Execute `generate_constituents()` from [generate_fixtures.py](file:///home/shailender/projects/equitest-nse/backend/app/data/generate_fixtures.py#L70) during `init_db()`. | **Zero binary files in Docker image**; 100% self-contained Python code; deterministic. | ~100ms startup latency on initial database creation. | **RECOMMENDED** |
| **Option (c): Remote Fetch from NSE** | Fetch CSV master lists from the NSE website dynamically at startup. | Always reflects latest index changes. | High failure rate due to NSE anti-scraping blocks; breaks air-gapped/offline runs. | Rejected |

### 6.3 Implementation of Option (b) (Recommended)
In [constituents.py](file:///home/shailender/projects/equitest-nse/backend/app/data/constituents.py), the repository maintains curated lists:
- `TOP_100_CONSTITUENTS`: 100 authentic large-cap tickers (ranks 1–100, excluded from trading).
- `AUTHENTIC_NSE_CONSTITUENTS`: 650 mid- and small-cap tickers (ranks 101–750, tradeable candidate universe).

The logic in [`generate_constituents()`](file:///home/shailender/projects/equitest-nse/backend/app/data/generate_fixtures.py#L70-L97) generates point-in-time constituent snapshots across three dates: `2020-01-01`, `2022-01-01`, and `2024-01-01`:

```python
# Integration into backend/app/db/session.py: init_db()
def seed_constituents_from_code(session: Session) -> None:
    """Seeds universe_membership directly from authentic constituent lists."""
    from app.data.generate_fixtures import generate_constituents
    from app.db.models import UniverseMembership
    
    df = generate_constituents()
    for _, row in df.iterrows():
        existing = session.get(UniverseMembership, (row["date"], row["symbol"]))
        if not existing:
            session.add(UniverseMembership(
                date=row["date"],
                symbol=row["symbol"],
                rank=int(row["rank"])
            ))
    session.commit()
```
This guarantees that whenever a fresh container starts with an empty named volume, `init_db()` automatically populates the 2,250 constituent rows without requiring any external file mounts.

---

## 7. Survivorship Bias Mitigation & Explicit Tagging

Survivorship bias occurs when a backtest selects historical trade candidates using today's successful companies, ignoring companies that were subsequently delisted, merged, or demoted.

### 7.1 Selection Mechanism
When a backtest executes for date $T$:
1. The universe engine queries `universe_membership` for the most recent constituent snapshot where $\text{Snapshot Date} \le T$.
2. It filters for symbols where $101 \le \text{Rank} \le 750$.
3. If valid records exist, the engine returns `(tickers, False, details)` where `survivorship_bias = False`.

### 7.2 Fallback Trigger & Explicit Tagging
If no constituent records cover date $T$:
```python
# universe.py line 390
fallback = get_default_fallback_constituents(start_rank=start_rank, end_rank=end_rank)
tickers = [item["symbol"] for item in fallback]
return tickers, True, fallback  # True explicitly tags survivorship_bias
```

> [!WARNING]
> When `survivorship_bias = True`:
> - The API response includes `"survivorship_bias": true` in the run metadata.
> - The frontend UI renders an amber warning banner:
>   * *"Survivorship Bias Warning: Point-in-time constituent data was unavailable for this date. The current stock universe was used as a fallback."*
> - The WeasyPrint PDF report attaches a compliance disclaimer.
> 
> This invariant must **never be suppressed or masked**.

---

## 8. NSE India Direct API Alternative Evaluation

Consideration was given to whether EquiTest NSE should query NSE India (`nseindia.com`) directly or utilize third-party Python wrappers such as `nsepython` or `jugaad-data`.

### 8.1 Comparison Matrix

| Evaluation Dimension | Yahoo Finance (`yfinance`) | Official NSE India API | Scraper Libraries (`nsepython` / `jugaad-data`) |
|---|---|---|---|
| **Package Installed?** | ✅ Yes (`yfinance>=0.2.40`) | ❌ No | ❌ No |
| **Authentication** | None (public endpoint) | Dynamic session cookies (`nserequest`) | Automated header spoofing |
| **Rate Limit Resilience** | Moderate (~2000 req/hr) | Extremely Aggressive (IP bans within minutes) | Fragile; subject to frequent Akamai blocks |
| **Historical Depth** | 15+ years of continuous OHLCV | Limited historical access (often < 1 year) | Variable; relies on fragile page scraping |
| **Corporate Action Split Data** | Handled natively via `adj_close` | Requires manual scraping of corporate action circulars | Inconsistent |
| **Terms of Service (ToS)** | Permitted for personal / research use | Commercial license required for automated API access | **High risk of ToS violation** |

### 8.2 Strategic Recommendation

> [!CAUTION]
> Integrating `nsepython` or `jugaad-data` is **strongly discouraged**:
> 1. Neither package is included in the project's pinned dependencies.
> 2. The NSE India website utilizes Akamai Bot Manager and regularly invalidates session cookies and header user-agents, causing sudden test and pipeline failures.
> 3. Scraping NSE India without a commercial license violates the NSE terms of service.
> 
> **Decision**: Standardize exclusively on `yfinance` for remote market data ingestion.

---

## 9. First Startup Data Provisioning Strategy

When launching the container stack on a clean developer workstation or CI/CD runner, the database named volume (`equitest_db`) is initially empty.

### 9.1 Evaluation of Provisioning Modes

| Provisioning Option | Initial Startup Behavior | User Experience | Network / CI Impact | Recommendation |
|---|---|---|---|---|
| **Option A: Auto-Ingest on Startup** | The backend lifespan hook automatically issues `yfinance` download calls for the default 50 symbols. | Zero setup required; instant charts upon browser open. | Increases startup time by 60–120 seconds; crashes if running offline or in restricted corporate networks. | Not Recommended |
| **Option B: Empty State + UI Trigger (Recommended)** | `init_db()` seeds only the database tables and point-in-time constituents (ranks 1–750). Market OHLCV data is empty. | UI guides the user to `/data` with a 1-click "Start Ingestion" action. | Instant container startup (< 5s); 100% resilient in offline environments. | **RECOMMENDED** |

### 9.2 Recommended Hybrid Workflow
1. **Container Cold Boot**:
   - `init_db()` executes schema migrations.
   - `seed_constituents_from_code()` populates the 2,250 constituent snapshot rows (ensuring `survivorship_bias = False`).
   - Container healthcheck passes in < 5 seconds.
2. **User Guidance**:
   - When a user opens `http://localhost:3000`, the dashboard detects zero OHLCV rows and displays:
     > *"Welcome to EquiTest NSE. No local market data detected. Click Ingest to fetch the default equity and benchmark dataset."*
3. **Targeted Ingestion**:
   - A single click on the UI triggers `POST /api/v1/data/ingest` with the core reference symbols:
     `["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS", "NIFTY50"]`.
   - Data is downloaded via `YFinanceSource`, validated via `validate_ohlcv_dataframe()`, and committed to SQLite.

---

## 10. Operational Runbook, API Validation & Troubleshooting

### 10.1 Environment Configuration
Ensure `.env` contains:
```ini
DATA_SOURCE=yfinance
DATABASE_URL=sqlite:////app/data/prod.db
LOG_LEVEL=INFO
YFINANCE_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 10.2 Verification Commands

```bash
# 1. Trigger remote ingestion for benchmark and core midcaps (2023 H1)
curl -X POST http://localhost:8000/api/v1/data/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "start": "2023-01-01",
    "end": "2023-06-30",
    "symbols": ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS"]
  }' | jq .

# Expected Response:
# {
#   "job_id": "...",
#   "status": "completed",
#   "symbols_ingested": ["RELIANCE", "HDFCBANK", "INFY", "TATAMOTORS"],
#   "rows_ingested": 496,
#   "errors": []
# }

# 2. Verify coverage endpoint reflects remote data
curl -s http://localhost:8000/api/v1/data/coverage | jq .

# 3. Verify prices endpoint delivers unadjusted and adjusted closes
curl -s "http://localhost:8000/api/v1/prices/RELIANCE?limit=3" | jq .
```

### 10.3 Troubleshooting Common Ingestion Issues

| Symptom | Probable Root Cause | Corrective Action |
|---|---|---|
| `yfinance` returns empty DataFrame | Ticker symbol lacks `.NS` suffix or market was closed for the requested range. | Check [`_normalize_ticker()`](file:///home/shailender/projects/equitest-nse/backend/app/data/source.py#L167). Verify symbol is listed on NSE. |
| Ingestion fails with `HTTP 429` | Rate limit exceeded due to concurrent requests. | Implement request throttling (1.5 req/sec) and exponential backoff retry. |
| Backtest shows `survivorship_bias = True` | `universe_membership` table lacks records for the backtest start date. | Ensure `init_db()` called `seed_universe_constituents()` or run runtime generator. |
| Indicator values jump erratically | Indicators computed on unadjusted `close` across a split date. | Verify technical indicators use `adj_close` while execution uses `open`/`close`. |
