# Phase 0: Legacy Contract Extraction & Behavioral Freeze

> **Phase ID**: 0
> **One-Line Summary**: Extract the actual legacy handler behavior from the Python/FastAPI monolith and freeze it as a versioned contract test suite before any migration work begins.

---

## Goal and Rationale

Before building any microservice, extract the **exact behavioral contracts** of every legacy REST endpoint and freeze them as executable test fixtures. This guarantees that every subsequent phase can verify behavioral equivalence against the known-correct Python monolith, and that no endpoint behavior is lost or subtly altered during the migration.

This phase also establishes two critical cross-cutting contracts that every subsequent phase depends on:

1. **"Reports Not Ready" Protocol** — the explicit async handshake between `backtest/run` (synchronous simulation) and downstream consumers (reports, validation, sweep).
2. **Versioned `backtest.completed` Event Schema** — the canonical RabbitMQ message contract with provenance, idempotency, and durability guarantees.

---

## In-Scope Items

### A. Legacy Endpoint Contract Extraction

For every endpoint in the frozen `/api/v1/*` surface:

1. **Record exact request/response pairs** against the running Python monolith for a representative set of inputs (including edge cases: empty universe, zero-trade backtest, gap-down-only run, max-sweep grid).
2. **Capture response schemas** (status codes, JSON shapes, header values, content types for binary exports).
3. **Freeze as golden fixtures**: Save request/response pairs as JSON files under `data/migration/contracts/` for use as contract tests in every subsequent phase.
4. **Document the "reports not ready" behavior**: The legacy `/api/v1/backtest/run` endpoint returns the `run_id` and simulation results synchronously. It does **not** return PDF, validation, or report data inline. Reports endpoints (`/api/v1/reports/{run_id}/summary`, `/monthly`, `/export`) may return HTTP 404 or a `status: "processing"` response until async report generation completes. This behavior must be preserved and formalized.

### B. "Reports Not Ready" Protocol Specification

Define the explicit protocol for async report availability:

| Endpoint | Behavior When Reports Not Ready |
|---|---|
| `GET /api/v1/reports/{run_id}/summary` | Returns `HTTP 404` or `{"status": "processing", "run_id": "..."}` until metrics are computed |
| `GET /api/v1/reports/{run_id}/monthly` | Same as above |
| `GET /api/v1/reports/{run_id}/export` | Same as above |
| `POST /api/v1/reports/{run_id}/export/pdf/async` | Returns `HTTP 202 Accepted` with `job_id` immediately |
| `GET /api/v1/reports/jobs/{job_id}` | Returns `{"status": "pending|processing|completed|failed"}` |
| `GET /api/v1/reports/{run_id}/preview.png` | Returns `HTTP 404` until PDF generation completes |
| `GET /api/v1/backtest/{run_id}/audit` | Returns `HTTP 404` until validation service processes `backtest.completed` |
| `GET /api/v1/validation/{run_id}/{symbol}` | Returns `HTTP 404` until validation service processes `backtest.completed` |

The Angular frontend must poll these endpoints or use a notification mechanism. It must **never** assume reports/validation are immediately available after `POST /api/v1/backtest/run` returns.

### C. Versioned `backtest.completed` Event Schema

Define the canonical RabbitMQ event contract. All producers and consumers in subsequent phases must conform to this schema exactly.

**Schema: `backtest.completed` v1**

```
{
  "event_version": "1.0",
  "event_type": "backtest.completed",
  "idempotency_key": "<UUID v4 — unique per event emission, used by consumers for dedup>",
  "timestamp_utc": "<ISO 8601 UTC timestamp of event emission>",
  "run_id": "<backtest run UUID>",
  "sweep_id": "<sweep UUID or null if standalone run>",
  "status": "completed | failed",
  "provenance": {
    "engine_git_sha": "<Git commit SHA of equitest-engine-service at build time>",
    "data_snapshot_id": "<SHA-256 fingerprint of all input Parquet files used>",
    "config_json_canonical": "<Canonical JSON of StrategyConfig — keys sorted, no whitespace, deterministic>",
    "engine_version": "<Maven artifact version of equitest-engine-service>"
  },
  "result_summary": {
    "final_capital": <numeric — exact to paisa>,
    "total_trades": <integer>,
    "sessions_processed": <integer>
  }
}
```

**Config JSON Canonicalization Rule**: The `config_json_canonical` field must be produced by serializing the `StrategyConfig` object with:
- Keys sorted alphabetically (recursive)
- No whitespace (compact)
- Numeric values without trailing zeros
- Null values explicitly included (not omitted)

This guarantees that two runs with identical configurations produce identical `config_json_canonical` values, enabling deterministic provenance comparison.

### D. Messaging Infrastructure Contract

| Property | Specification |
|---|---|
| **Exchange** | `equitest.events` (type: `topic`, durable: `true`) |
| **Routing Key** | `backtest.completed` |
| **Queues** | `reports.backtest.completed.queue`, `validation.backtest.completed.queue`, `sweep.backtest.completed.queue` — all **durable** |
| **Dead-Letter Exchange** | `equitest.dlx` (type: `direct`, durable: `true`) |
| **Dead-Letter Queue** | `equitest.dead-letters` (durable: `true`) |
| **Retry Policy** | 3 retries with exponential backoff (1s, 5s, 25s) before routing to DLX |
| **Consumer Idempotency** | Every consumer must deduplicate on `idempotency_key`. If a message with a previously-seen `idempotency_key` arrives, the consumer must skip processing and ACK the message. Dedup state stored in the consumer's own database. |
| **Message Persistence** | `delivery_mode: 2` (persistent) — messages survive broker restart |
| **Trace Headers** | `traceparent` and `tracestate` W3C headers injected into AMQP message properties for OpenTelemetry propagation |

---

## Explicit Out-of-Scope Items

- Building any microservice (that's Phase 1+).
- Modifying the legacy system.
- Writing migration code.

---

## Prerequisites

- Running legacy Python/FastAPI monolith with seeded fixtures.
- Access to all Parquet fixture files.

---

## Inputs

- Running legacy system at `localhost:8000`.
- Complete frozen `/api/v1/*` endpoint list.
- Legacy golden test fixtures (₹482,707.20 backtest).

---

## Outputs

- `data/migration/contracts/` directory containing golden request/response pairs for every endpoint.
- `data/migration/contracts/backtest-completed-schema.json` — the formal JSON Schema for the `backtest.completed` event.
- `data/migration/contracts/reports-not-ready-protocol.md` — the formalized async handshake specification.
- Updated phase documents referencing these contracts.

---

## Acceptance Gates

- Every `/api/v1/*` endpoint has at least one golden request/response fixture captured.
- The `backtest.completed` JSON Schema validates against the specification above.
- The "reports not ready" protocol is documented with exact HTTP status codes and response bodies.
- The golden backtest fixture (₹482,707.20) is captured as a contract test.

---

## Test Requirements

- Contract test suite (language-agnostic, e.g., JSON-based) that can be executed against any backend implementation.
- Schema validation test for `backtest.completed` events.

---

## Risks and Mitigations

- *Risk*: Legacy system behavior is undocumented or inconsistent for edge cases.
- *Mitigation*: Run the legacy system with verbose logging enabled and capture actual behavior, even if it differs from documentation. Document discrepancies.

---

## Rollback Strategy

- This phase produces only test fixtures and specifications. No system changes to roll back.

---

## Hand-off to Next Phase

- Contract test suite ready for Phase 1+ to validate against.
- Verified state: every endpoint's behavior is frozen as a golden fixture.

**Checklist for Phase 1 implementer to confirm before starting:**
- [ ] `data/migration/contracts/` directory exists with golden fixtures
- [ ] `backtest.completed` schema is formally specified
- [ ] "Reports not ready" protocol is documented
- [ ] Golden backtest (₹482,707.20) is captured as a contract fixture
- [ ] Config JSON canonicalization rule is specified

---

## Invariant Checklist

- **INV-10: Paisa-Level Determinism** — The golden backtest contract fixture must capture ₹482,707.20 exactly.
- **INV-9: Cryptographic Run Provenance** — The `backtest.completed` schema must include all provenance fields.

---

## Contract Checklist

- ALL endpoints in the frozen `/api/v1/*` surface — this phase extracts their behavioral contracts.

