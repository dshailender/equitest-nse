# Phase 10: E2E, Performance & Resilience Testing

> **Phase ID**: 10
> **One-Line Summary**: Validate the new microservices architecture meets or exceeds legacy performance and correctly handles failures without violating invariants.

---

## Goal and Rationale

Validate that the new microservices architecture meets or exceeds the legacy system's performance and correctly handles failures without corrupting data or violating invariants.

---

## In-Scope Items

- Golden test script automation (CI/CD pipeline integration).
- Load testing (Gatling/JMeter) on the `/api/v1/backtest/run` endpoint.
- Resilience testing (killing RabbitMQ or a DB node mid-flight).
- Idempotency verification under concurrent load (duplicate `backtest.completed` messages).
- "Reports not ready" protocol verification under race conditions.

---

## Explicit Out-of-Scope Items

- Long-term infrastructure capacity planning.

---

## Prerequisites

- Phase 9 fully operational stack (with observability).

---

## Inputs

- Legacy performance baselines.
- Known golden test inputs and outputs (₹482,707.20).
- Phase 0 contract test suite.

---

## Outputs

- Test reports.
- Hardened service configurations (tuning connection pools, timeouts).

---

## Acceptance Gates

- 100% pass rate on the ₹482,707.20 golden test under concurrent load.
- DLX successfully captures and retries messages when the Reports service is artificially downed.
- Idempotent consumers correctly dedup under concurrent duplicate message delivery.
- Phase 0 contract test suite passes 100%.

---

## Test Requirements

- Chaos engineering scripts, Gatling load simulations.
- Concurrent idempotency stress test.
- Contract test suite regression.

---

## Risks and Mitigations

- *Risk*: DB connection pool exhaustion under load.
- *Mitigation*: Tune HikariCP settings and ensure all Spring Data JDBC connections are promptly released.

---

## Rollback Strategy

- Iterative code/config fixes based on test findings.

---

## Hand-off to Next Phase

- Hardened system.

**Checklist for Phase 11 implementer to confirm before starting:**
- [ ] Golden test passes 100% under concurrent load
- [ ] Load test reports show acceptable latency and throughput
- [ ] DLX captures messages correctly during service outages
- [ ] Circuit breakers activate gracefully on downstream failures
- [ ] Idempotent consumers verified under concurrent duplicate delivery
- [ ] All 10 invariants validated dynamically during test runs

---

## Invariant Checklist

- **ALL 10 Invariants** must be validated dynamically during tests:
  - INV-1: Zero Look-Ahead
  - INV-2: Survivorship Bias Prevention
  - INV-3: Top 100 Exclusion
  - INV-4: Overnight Gap-Down Realism
  - INV-5: Momentum Candidate Ranking
  - INV-6: Risk Allocation & Lot Sizing
  - INV-7: Transaction Frictions
  - INV-8: Corporate Action Normalization
  - INV-9: Cryptographic Run Provenance (with canonicalized config JSON)
  - INV-10: Paisa-Level Determinism (₹482,707.20)

---

## Contract Checklist

- ALL contracts tested under load, including "reports not ready" async behavior.

