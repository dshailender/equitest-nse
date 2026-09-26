# Phase 5: Reports Service

> **Phase ID**: 5
> **One-Line Summary**: Extract performance metrics calculation and PDF generation into the equitest-reports-service, consuming backtest.completed v1 events with idempotent processing.

---

## Goal and Rationale

Extract performance metrics calculation and PDF generation into the `equitest-reports-service`. This unblocks the SimulationEngine from heavy I/O and visual generation tasks.

---

## In-Scope Items

- Flyway migrations for `equitest_reports`.
- Listening to `reports.backtest.completed.queue` to trigger async metric pre-calculation.
- Async PDF generation worker queue (`reports.pdf.jobs.queue`).
- Endpoints for monthly returns, summaries, and exporting.

### "Reports Not Ready" Protocol Implementation

This service **must** implement the "Reports Not Ready" protocol defined in Phase 0:

| Endpoint | Before Processing Complete | After Processing Complete |
|---|---|---|
| `GET /api/v1/reports/{run_id}/summary` | HTTP 404 or `{"status": "processing"}` | Full metrics JSON |
| `GET /api/v1/reports/{run_id}/monthly` | HTTP 404 or `{"status": "processing"}` | Monthly returns matrix |
| `GET /api/v1/reports/{run_id}/export` | HTTP 404 or `{"status": "processing"}` | Binary file download |
| `GET /api/v1/reports/{run_id}/preview.png` | HTTP 404 | PNG image |
| `POST /api/v1/reports/{run_id}/export/pdf/async` | HTTP 202 + `job_id` (always) | HTTP 202 + `job_id` |
| `GET /api/v1/reports/jobs/{job_id}` | `{"status": "pending\|processing"}` | `{"status": "completed\|failed"}` |

### Idempotent Consumer Requirements

This service consumes from `reports.backtest.completed.queue`. It **must**:
- Deduplicate on `idempotency_key` from the `backtest.completed` v1 payload. If a message with a previously-seen key arrives, skip processing and ACK.
- Store seen `idempotency_key` values in the `equitest_reports` database.
- Use `data_snapshot_id` and `provenance` fields from the event payload for audit correlation.
- ACK messages only after successful processing. On failure, allow RabbitMQ retry (3x exponential backoff) before DLX routing.

---

## Explicit Out-of-Scope Items

- Frontend chart rendering.

---

## Prerequisites

- Phase 3 Engine Service running and providing trade ledgers.
- Phase 0 `backtest.completed` v1 schema and "reports not ready" protocol.

---

## Inputs

- `backtest.completed` v1 RabbitMQ payload containing `run_id`, `idempotency_key`, `provenance`.
- Data fetched from Engine via REST to calculate metrics.

---

## Outputs

- `equitest-reports-service` with idempotent consumer and "reports not ready" protocol.

---

## Acceptance Gates

- PDF export job endpoints correctly return a job ID and eventually the binary PDF.
- Summary and monthly metrics perfectly match legacy output numbers.
- Duplicate `backtest.completed` messages (same `idempotency_key`) are silently deduplicated.
- Reports endpoints return 404/"processing" before the consumer has finished, and full data after.
- Failed message processing routes to DLX after 3 retries.

---

## Test Requirements

- Contract test for RabbitMQ event consumption against v1 schema.
- Golden test comparing exact metrics against Python `empyrical` equivalents.
- Idempotency test: Send the same `backtest.completed` message twice; verify metrics are computed only once.
- "Reports not ready" test: Query reports endpoints before consumer processes; verify 404/processing response.
- DLX test: Simulate a processing failure and verify the message reaches `equitest.dead-letters` after 3 retries.

---

## Risks and Mitigations

- *Risk*: PDF generation memory bloat in Java.
- *Mitigation*: Use lightweight PDF libraries (e.g., OpenPDF or Flying Saucer) and stream data rather than loading all trades into memory.

---

## Rollback Strategy

- Revert code and `equitest_reports` DB schema.

---

## Hand-off to Next Phase

- Reporting engine ready for gateway routing, with "reports not ready" protocol verified.

**Checklist for Phase 7 implementer to confirm before starting:**
- [ ] Reports service health endpoint returns 200
- [ ] GET `/api/v1/reports/{run_id}/summary` returns correct metrics (after consumer processes)
- [ ] GET `/api/v1/reports/{run_id}/monthly` returns compounded returns matrix
- [ ] Export endpoints (CSV, XLSX, ZIP, PDF) produce valid files
- [ ] Async PDF job lifecycle works end-to-end
- [ ] "Reports not ready" protocol: 404/processing before consumer completes
- [ ] Idempotent consumer correctly deduplicates on `idempotency_key`

---

## Invariant Checklist

- **INV-10: Paisa-Level Determinism** — Metrics must not alter or round trades incorrectly. Golden backtest yields ₹482,707.20 exactly.

---

## Contract Checklist

- `GET /api/v1/reports/{run_id}/summary` (async — may 404 until processed)
- `GET /api/v1/reports/{run_id}/monthly` (async — may 404 until processed)
- `GET /api/v1/reports/{run_id}/export` (async — may 404 until processed)
- `POST /api/v1/reports/{run_id}/export/pdf/async` (returns 202 immediately)
- `GET /api/v1/reports/jobs/{job_id}`
- `GET /api/v1/reports/jobs/{job_id}/download`
- `GET /api/v1/reports/{run_id}/preview.png` (async — may 404 until processed)

