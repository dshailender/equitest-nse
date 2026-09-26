# Phase 4: Sweep Service

> **Phase ID**: 4
> **One-Line Summary**: Implement the equitest-sweep-service to manage parameter grid searches, dispatching multiple backtests and aggregating results.

---

## Goal and Rationale

Implement the `equitest-sweep-service` to manage parameter grid searches. This service acts as an orchestrator, dispatching multiple backtest requests to the SimulationEngine and aggregating the final results for comparative analysis.

---

## In-Scope Items

- Flyway migrations for `equitest_sweep`.
- `/api/v1/backtest/sweep` endpoint to generate combinations of risk/indicator parameters.
- Orchestration logic to asynchronously call SimulationEngine or track completed runs via the `backtest.completed` RabbitMQ queue.
- Aggregation logic to compare metrics across runs.

### Idempotent Consumer Requirements

This service consumes from `sweep.backtest.completed.queue`. It **must**:
- Deduplicate on `idempotency_key` from the `backtest.completed` v1 payload. If a message with a previously-seen key arrives, skip processing and ACK.
- Store seen `idempotency_key` values in the `equitest_sweep` database.
- Extract `sweep_id` from the payload to correlate child runs to parent sweeps.
- ACK messages only after successful processing. On failure, allow RabbitMQ retry (3x exponential backoff) before DLX routing.

---

## Explicit Out-of-Scope Items

- Actual simulation execution (delegated to Engine).
- Visual report generation.

---

## Prerequisites

- Phase 3 Engine Service running, publishing `backtest.completed` v1 events.
- Phase 0 `backtest.completed` v1 schema.

---

## Inputs

- Parameter grid JSON payload.
- `backtest.completed` v1 messages from RabbitMQ.

---

## Outputs

- Completed `equitest-sweep-service` with idempotent consumer.

---

## Acceptance Gates

- POSTing a sweep configuration successfully creates multiple backtests and returns a sweep ID.
- GET `/api/v1/backtest/sweep/{sweep_id}` shows status of all children runs.
- Duplicate `backtest.completed` messages (same `idempotency_key`) are silently deduplicated.
- Failed message processing routes to DLX after 3 retries.

---

## Test Requirements

- Integration tests: Verify the sweep service correctly parses grid permutations and manages state based on RabbitMQ events.
- Idempotency test: Send the same `backtest.completed` message twice; verify the sweep state is updated only once.
- DLX test: Simulate a processing failure and verify the message reaches `equitest.dead-letters` after 3 retries.

---

## Risks and Mitigations

- *Risk*: Overwhelming the SimulationEngine with too many concurrent requests during a sweep.
- *Mitigation*: Implement rate limiting or a concurrency-bounded worker pool within the Sweep Service when calling the Engine.

---

## Rollback Strategy

- Revert code and DB migrations for the sweep service.

---

## Hand-off to Next Phase

- Fully functioning sweep orchestrator with idempotent consumer.

**Checklist for Phase 7 implementer to confirm before starting:**
- [ ] Sweep service health endpoint returns 200
- [ ] POST `/api/v1/backtest/sweep` creates child runs correctly
- [ ] GET `/api/v1/backtest/sweep/{sweep_id}` returns correct child statuses
- [ ] GET `/api/v1/backtest/compare` returns aligned metrics
- [ ] Idempotent consumer correctly deduplicates on `idempotency_key`
- [ ] Failed messages route to DLX after 3 retries

---

## Invariant Checklist

- **INV-10: Paisa-Level Determinism** — Aggregations must maintain exact fidelity. Golden backtest yields ₹482,707.20 exactly.

---

## Contract Checklist

- `POST /api/v1/backtest/sweep`
- `GET /api/v1/backtest/sweep/{sweep_id}`
- `GET /api/v1/backtest/compare`

