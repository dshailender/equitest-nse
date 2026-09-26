# Phase 3: SimulationEngine Service

> **Phase ID**: 3
> **One-Line Summary**: Combine Indicators, Signals, Risk, and Backtest modules into a single equitest-engine-service to avoid distributed network latency over iterations.

---

## Goal and Rationale

Combine Indicators, Signals, Risk, and Backtest modules into a single `equitest-engine-service` to avoid distributed network latency over iterations. This service runs the core loop: calculating indicators, screening signals, managing risk parameters, and chronologically executing the backtest simulation to generate the trade ledger.

**Architectural Note (from Reviewer):** The original plan proposed 4 separate microservices for these domains. The reviewer identified this as a distributed-monolith anti-pattern: the backtest simulation engine iterates through time-series data chronologically, and if it must make network calls to evaluate indicators, signals, and risk constraints for every stock on every session, network latency will obliterate performance. These four domains are merged into a single service to maintain local in-memory computation speeds.

---

## In-Scope Items

- Flyway migrations for `equitest_engine` (storing backtest configs, runs, and trade ledgers).
- Internal Java modules for Indicators (EMAs, 52W High), Signals, and Risk inside the single engine service.
- The chronological Simulation loop (T close signal, T+1 open execution).
- Exact replication of legacy math (floors, 10bps slippage, Pandas EMA equivalents).

### `backtest.completed` v1 Event Emission

Upon successful backtest completion, the engine **must** publish a `backtest.completed` event to the `equitest.events` topic exchange conforming to the **v1 schema** defined in Phase 0:

```
{
  "event_version": "1.0",
  "event_type": "backtest.completed",
  "idempotency_key": "<UUID v4 — unique per emission>",
  "timestamp_utc": "<ISO 8601 UTC>",
  "run_id": "<backtest run UUID>",
  "sweep_id": "<sweep UUID or null>",
  "status": "completed | failed",
  "provenance": {
    "engine_git_sha": "<injected at build via git-commit-id-plugin>",
    "data_snapshot_id": "<SHA-256 from Data Service>",
    "config_json_canonical": "<keys sorted, compact, nulls explicit>",
    "engine_version": "<Maven artifact version>"
  },
  "result_summary": {
    "final_capital": <exact to paisa>,
    "total_trades": <integer>,
    "sessions_processed": <integer>
  }
}
```

**Config JSON Canonicalization**: Serialize `StrategyConfig` with keys sorted alphabetically (recursive), no whitespace, numeric values without trailing zeros, null values explicitly included. Two runs with identical configs must produce identical `config_json_canonical`.

**Message Properties**: `delivery_mode: 2` (persistent), `content_type: application/json`, W3C `traceparent`/`tracestate` headers injected for OpenTelemetry propagation.

### "Reports Not Ready" Protocol

The engine's synchronous `/api/v1/backtest/run` endpoint returns the `run_id` and simulation results **immediately**. It does **not** wait for downstream consumers (reports, validation, sweep) to process the `backtest.completed` event. The following endpoints may return HTTP 404 or `{"status": "processing"}` until their respective consumers complete:

- `/api/v1/reports/{run_id}/summary`
- `/api/v1/reports/{run_id}/monthly`
- `/api/v1/reports/{run_id}/export`
- `/api/v1/backtest/{run_id}/audit`
- `/api/v1/validation/{run_id}/{symbol}`

---

## Explicit Out-of-Scope Items

- Generating PDF reports.
- Parameter sweeping (orchestrating multiple backtests).
- TradingView validation logic.
- Consuming RabbitMQ messages (this service only **publishes**).

---

## Prerequisites

- Phase 2 Data Service successfully running and returning exact `adj_close` datasets.
- Phase 1 RabbitMQ container running with durable queues and DLX configured.
- Phase 0 `backtest.completed` v1 schema and "reports not ready" protocol.

---

## Inputs

- OHLCV REST payloads from Data Service (including `data_snapshot_id` — the Parquet SHA-256 fingerprint).
- Strategy rules and specific mathematical definitions for Pandas-equivalent EMAs and rolling max.
- `backtest.completed` v1 schema from Phase 0.

---

## Outputs

- Fully implemented `equitest-engine-service`.
- Functional backtest REST endpoints.
- RabbitMQ `backtest.completed` v1 messages published on completion.

---

## Acceptance Gates

- A POST to `/api/v1/backtest/run` triggers the engine, completes synchronously, returns a `run_id`, and publishes a `backtest.completed` v1 message to RabbitMQ.
- The published message conforms to the v1 schema: contains `event_version`, `idempotency_key`, `data_snapshot_id`, and canonical `config_json`.
- **Golden Test pass**: The exact legacy configuration must yield exactly **₹482,707.20** in final equity.
- Message appears in RabbitMQ management UI with `delivery_mode: 2` (persistent).

---

## Test Requirements

- Unit tests: EMA calculations matching Pandas exactly, 10 bps slippage logic, risk allocation.
- Golden tests: Complete backtest run matching the legacy trade ledger (₹482,707.20 final equity).
- Contract tests: Validate the published `backtest.completed` message against the v1 JSON Schema from Phase 0.
- Config canonicalization test: Two identical `StrategyConfig` instances produce byte-identical `config_json_canonical`.
- Idempotency key uniqueness test: Two successive runs produce distinct `idempotency_key` values.

---

## Risks and Mitigations

- *Risk*: Floating-point differences between Python/Pandas and Java causing divergent equity values.
- *Mitigation*: Utilize `BigDecimal` with strict rounding modes matching Python's float semantics where necessary, and ensure `adjust=False` equivalent is used in exponential smoothing algorithms.
- *Risk*: Config JSON canonicalization producing different output on different JVM versions.
- *Mitigation*: Use Jackson's `SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS` and explicit `ObjectMapper` configuration.

---

## Rollback Strategy

- Revert `equitest-engine-service` code and Flyway migrations.

---

## Hand-off to Next Phase

- A deterministic simulation engine that emits v1 events to RabbitMQ.
- Verified state: `backtest.completed` messages are routed to durable queues. Next phases will implement consumers.

**Checklist for Phase 4/5/6 implementers to confirm before starting:**
- [ ] Engine health endpoint returns 200
- [ ] POST `/api/v1/backtest/run` returns a valid `run_id`
- [ ] Golden test passes: final equity = ₹482,707.20 exactly
- [ ] `backtest.completed` v1 messages appear in RabbitMQ with correct schema
- [ ] Messages contain `idempotency_key`, `data_snapshot_id`, canonical `config_json`, `engine_git_sha`
- [ ] Messages are persistent (`delivery_mode: 2`)
- [ ] All indicator, signal, risk, and backtest endpoints return correct data

---

## Invariant Checklist

- **INV-1: Zero Look-Ahead** — Indicators on session T close; trades fill on session T+1 Market Open. Rolling 52W high shifted by 1 bar.
- **INV-3: Top 100 Exclusion** — Ranks 101–750 eligible; NIFTY 50 only as regime filter.
- **INV-4: Overnight Gap-Down Realism** — If Open_T <= SL Price, exit at Open_T × 0.9990.
- **INV-5: Momentum Candidate Ranking** — (Close_T - EMA20_T) / EMA20_T descending; alphabetical tie-breaker.
- **INV-6: Risk Allocation & Lot Sizing** — 2% corpus risk; 7% hard stop; integer shares floored.
- **INV-7: Transaction Frictions** — 10 bps per side.
- **INV-9: Cryptographic Run Provenance** — Git SHA, canonicalized config JSON, Parquet SHA-256 (`data_snapshot_id`). All embedded in `backtest.completed` v1 payload.
- **INV-10: Paisa-Level Determinism** — Golden backtest yields ₹482,707.20 exactly.

---

## Contract Checklist

- `GET /api/v1/indicators/{symbol}`
- `POST /api/v1/indicators/preview`
- `GET /api/v1/indicators/nifty`
- `GET /api/v1/signals/{symbol}`
- `GET /api/v1/signals/screen`
- `POST /api/v1/risk/size`
- `GET /api/v1/risk/config`
- `POST /api/v1/backtest/run`
- `GET /api/v1/backtest/{run_id}`
- `GET /api/v1/backtest/{run_id}/trades`
- `GET /api/v1/backtest/{run_id}/equity`
- `GET /api/v1/backtest`

