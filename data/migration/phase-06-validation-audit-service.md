# Phase 6: Validation & Audit Service

> **Phase ID**: 6
> **One-Line Summary**: Implement the equitest-validation-service for TradingView cross-checks and provenance auditing, consuming backtest.completed v1 events idempotently.

---

## Goal and Rationale

Implement the `equitest-validation-service` to handle TradingView cross-checks and provenance auditing, ensuring complete transparency and compliance for every run.

---

## In-Scope Items

- Flyway migrations for `equitest_validation`.
- Listening to `validation.backtest.completed.queue` to store audit trails.
- Extracting provenance from `backtest.completed` v1 payload: `engine_git_sha`, `data_snapshot_id`, `config_json_canonical`, `engine_version`.
- Persisting the provenance audit record in `equitest_validation` database.
- TradingView validation logic (comparing internal engine prices to external references).

### Idempotent Consumer Requirements

This service consumes from `validation.backtest.completed.queue`. It **must**:
- Deduplicate on `idempotency_key` from the `backtest.completed` v1 payload. If a message with a previously-seen key arrives, skip processing and ACK.
- Store seen `idempotency_key` values in the `equitest_validation` database.
- Extract all provenance fields from the event payload — the validation service does **not** need to compute provenance itself; it receives it from the engine via the event.
- ACK messages only after successful processing. On failure, allow RabbitMQ retry (3x exponential backoff) before DLX routing.

### "Reports Not Ready" Protocol

The following endpoints may return HTTP 404 or `{"status": "processing"}` until the consumer has processed the `backtest.completed` event:

- `GET /api/v1/backtest/{run_id}/audit`
- `GET /api/v1/validation/{run_id}/{symbol}`

---

## Explicit Out-of-Scope Items

- Core simulation.

---

## Prerequisites

- Engine Service and Data Service active.
- Phase 0 `backtest.completed` v1 schema.

---

## Inputs

- `backtest.completed` v1 RabbitMQ payload with full provenance.
- Engine configurations and Data Service file states.

---

## Outputs

- `equitest-validation-service` with idempotent consumer.

---

## Acceptance Gates

- `/api/v1/backtest/{run_id}/audit` returns the exact provenance record: `engine_git_sha`, `data_snapshot_id` (Parquet SHA-256), `config_json_canonical`, `engine_version`.
- TradingView validation endpoint effectively flags discrepancies.
- Duplicate `backtest.completed` messages (same `idempotency_key`) are silently deduplicated.
- Endpoints return 404/"processing" before the consumer has finished.
- Failed message processing routes to DLX after 3 retries.

---

## Test Requirements

- Integration testing of SHA-256 hash verification against known files.
- Unit testing validation rules.
- Idempotency test: Send the same `backtest.completed` message twice; verify audit is stored only once.
- "Not ready" test: Query audit endpoint before consumer processes; verify 404/processing response.
- Provenance round-trip test: Verify that `data_snapshot_id` from the event matches the Data Service's actual Parquet hash.

---

## Risks and Mitigations

- *Risk*: Determining the correct Git SHA at runtime in a container.
- *Mitigation*: The engine injects Git SHA at build time (via `git-commit-id-plugin`) and propagates it in the `backtest.completed` v1 payload. The validation service reads it from the event, not from its own runtime.

---

## Rollback Strategy

- Revert service code.

---

## Hand-off to Next Phase

- Validation service running. All 5 backend domain services are now complete. Next phase builds the API Gateway in front of them.

**Checklist for Phase 7 implementer to confirm before starting:**
- [ ] Validation service health endpoint returns 200
- [ ] GET `/api/v1/backtest/{run_id}/audit` returns provenance from `backtest.completed` v1 event
- [ ] GET `/api/v1/validation/{run_id}/{symbol}` returns TradingView cross-check data
- [ ] Idempotent consumer correctly deduplicates on `idempotency_key`
- [ ] All 5 backend domain services (Data, Engine, Sweep, Reports, Validation) are running

---

## Invariant Checklist

- **INV-9: Cryptographic Run Provenance** — Git SHA, canonicalized config JSON, Parquet SHA-256 (`data_snapshot_id`). All received from `backtest.completed` v1 event and persisted.

---

## Contract Checklist

- `GET /api/v1/backtest/{run_id}/audit` (async — may 404 until processed)
- `GET /api/v1/validation/{run_id}/{symbol}` (async — may 404 until processed)

