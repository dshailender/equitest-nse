# Phase 2: Data Service

> **Phase ID**: 2
> **One-Line Summary**: Implement the equitest-data-service to handle OHLCV data, universe definitions, and corporate action normalizations.

---

## Goal and Rationale

Implement the `equitest-data-service` to handle OHLCV data, universe definitions, and corporate action normalizations. As the foundation for the simulation, this service must ensure data correctness, strict date monotonicity, and point-in-time constituent accuracy.

---

## In-Scope Items

- Flyway migrations for `equitest_data` (OHLCV tables, universe constituents).
- `/api/v1/data/ingest` implementation (reading Parquet fixtures and persisting to Postgres).
- Endpoints for querying universe and price data.
- Implementation of Survivorship Bias flagging and corporate action adjustments (yielding `adj_close`).
- Computing and exposing `data_snapshot_id` (SHA-256 fingerprint of all input Parquet files) for downstream provenance propagation.

---

## Explicit Out-of-Scope Items

- Any indicator calculations (EMA, 52W high).
- Simulation or execution logic.
- Cross-database queries (data must be served over REST).

---

## Prerequisites

- Phase 1 dev skeleton and running Postgres `equitest_data` DB.
- Original Parquet fixture files from legacy system.

---

## Inputs

- `constituents.parquet` and OHLCV `.parquet` files.
- Swagger definition for `/api/v1/data/*` and `/api/v1/universe`, `/api/v1/prices/{symbol}`.

---

## Outputs

- Fully implemented `equitest-data-service`.
- Ingestion logic verified against the Parquet files.
- `data_snapshot_id` (SHA-256 fingerprint) available for downstream services.

---

## Acceptance Gates

- POST to `/api/v1/data/ingest` successfully populates Postgres.
- GET `/api/v1/universe` returns exactly the NSE 101-750 constituents with proper `survivorship_bias: true/false` flags.
- GET `/api/v1/prices/RELIANCE` returns strictly monotonic dates, positive prices, and correct `adj_close` calculations.
- `data_snapshot_id` is deterministic: same Parquet files always produce same SHA-256.

---

## Test Requirements

- Unit tests: Date monotonicity validation, null rejection.
- Integration tests: End-to-end ingestion from sample Parquet to DB.
- Property-based tests: Verify `adj_close` is never negative and `high >= low`.
- Contract tests: Validate against golden fixtures from Phase 0.

---

## Risks and Mitigations

- *Risk*: Slow data ingestion due to high row counts in Parquet files.
- *Mitigation*: Use Spring Data JDBC bulk inserts/batching (`jdbcTemplate.batchUpdate`).

---

## Rollback Strategy

- Revert service code and rollback `equitest_data` Flyway migrations using `flyway:undo` or dropping the schema.

---

## Hand-off to Next Phase

- Running Data Service serving clean OHLCV data on port 8081.
- Verified state: `equitest_data` populated with fixtures. SimulationEngine will assume it can fetch clean price arrays via HTTP and receive `data_snapshot_id` for provenance.

**Checklist for Phase 3 implementer to confirm before starting:**
- [ ] Data Service health endpoint returns 200
- [ ] POST `/api/v1/data/ingest` successfully populates database
- [ ] GET `/api/v1/universe` returns NSE 101-750 constituents
- [ ] GET `/api/v1/prices/{symbol}` returns monotonic, adj_close-corrected data
- [ ] Survivorship bias flags are correctly set
- [ ] `data_snapshot_id` is available and deterministic

---

## Invariant Checklist

- **INV-2: Survivorship Bias Prevention** — Point-in-time constituent records; fallback tagged `survivorship_bias: true`.
- **INV-8: Corporate Action Normalization** — Indicators on `adj_close`; 52W high normalized. (Data ingestion aspect only: ensuring `adj_close` is correctly computed and stored.)

---

## Contract Checklist

- `POST /api/v1/data/ingest`
- `GET /api/v1/data/coverage`
- `GET /api/v1/universe`
- `GET /api/v1/prices/{symbol}`

