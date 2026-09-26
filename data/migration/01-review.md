# Model A (Reviewer) — Critical Review & Instructions to Planner

> **Produced by**: Migration Reviewer (Model A)
> **Role**: Principal architect and migration reviewer
> **Date**: 2026-09-26

---

## Review

**Critical Analysis of the Microservices Migration Plan**

While the target stack (Java 27, Spring Boot, Angular 22+, RabbitMQ, PostgreSQL) is robust for enterprise applications, the proposed microservice decomposition introduces severe architectural risks for a high-performance, deterministic quantitative backtesting engine.

*   **Microservice Decomposition & Distributed Monolith Risk:** 
    *   **Critical Flaw:** Splitting `Indicator`, `Signal`, `Risk`, and `Backtest` into distinct microservices is a textbook distributed monolith anti-pattern for this specific domain. The `Backtest` simulation engine iterates through time-series data chronologically. If it must make network calls over HTTP or RabbitMQ to evaluate indicators, signals, and risk constraints for *every stock on every session*, network latency will obliterate the simulation's performance. 
    *   **Recommendation:** These four domains (Indicator, Signal, Risk, Backtest) must be merged into a single `EngineService` or `CoreSimulationService` to maintain local in-memory computation speeds. `Data`, `Sweep` (which orchestrates multiple engine runs), `Reports`, and `Validation` are excellent candidates for independent services.
*   **Data Consistency & Provenance (INV-9):** 
    *   The provenance audit requires recording the exact Git SHA and data hash. In a microservices architecture, you must define *which* service's Git SHA is recorded, or aggregate the SHAs of all participating services. 
    *   Propagating the original dataset hash (from the `Data` service) down to the `Backtest` and `Validation` services requires strict correlation IDs and payload immutability.
*   **Contract Preservation:** 
    *   The API Gateway can theoretically map the frozen `/api/v1/*` surface, but the routing must be seamless. Endpoints like `/api/v1/indicators/preview` (dynamic indicators) and `/api/v1/backtest/run` (synchronous execution) must not suffer from gateway timeout limits if downstream processing takes longer due to the new network hops.
*   **Container-First Local Dev Realism:** 
    *   Running 14 containers (8 Spring Boot services, Gateway, Angular UI, Postgres, RabbitMQ, plus an extensive OpenTelemetry/Jaeger/Grafana/Loki observability stack) on a local developer machine is highly memory-intensive. "Hot reload" across multiple Java containers is notoriously resource-heavy. 
    *   The plan must include memory limits and potentially a "lite" docker-compose profile that omits the heavy observability stack for everyday UI/Engine work.
*   **Observability:** 
    *   While OpenTelemetry is specified, trace context *must* be injected into the RabbitMQ headers for async flows (e.g., `backtest.completed` fanout) to ensure a single backtest run can be traced from API request -> DB -> Simulation -> Report generation.
*   **Testing & Determinism (INV-10):** 
    *   The plan lacks a specific strategy for "Golden Testing" against the Python legacy system. To guarantee the exact ₹482,707.20 final equity, the Java system must output the exact same trade ledger. Floating-point math differences between Python/Pandas and Java (even with `BigDecimal`) are highly likely and must be explicitly managed, especially for the 10 bps slippage and EMA calculations.

---

## Instructions to Planner

You are the Planner model. Your task is to produce a detailed, phase-by-phase migration breakdown based on the architecture context and the review constraints above. 

**Strict Constraints:**
1.  **Do NOT write code.** You may only use brief (1-3 lines) illustrative snippets if absolutely necessary to explain a contract. No implementation details.
2.  **Do NOT modify the frozen API contract (`/api/v1/*`).**
3.  **Do NOT modify the 10 quantitative invariants.**
4.  **Incorporate Review Findings:** Adjust the proposed architecture to merge the `Indicator`, `Signal`, `Risk`, and `Backtest` components into a single `SimulationEngine` service to avoid the distributed monolith latency trap.

**Deliverable Requirements:**

1.  **File Layout:** Specify the exact file structure under `data/migration/`. It must include a `README.md` (overview and phase index with dependency arrows) and individual phase files (e.g., `00-overview.md`, `phase-01-local-dev-setup.md`, etc.).
2.  **Phase Breakdown:** Break the migration into logical, sequentially executable phases (e.g., Infra/Gateway -> Data -> Engine -> Async Workers -> UI).
3.  **Self-Contained Phase Documents:** Each phase document must be written so that a developer can implement it with zero prior context. You must explicitly restate the specific invariants, API contracts, and domain rules relevant *only* to that phase.
4.  **Document Structure:** Every phase document MUST contain the following exact sections:
    *   **Goal:** High-level objective.
    *   **Scope:** What is being built.
    *   **Out-of-Scope:** What is explicitly deferred to later phases.
    *   **Prerequisites:** Required prior phases or existing state.
    *   **Inputs:** Data, configurations, or contracts required to start.
    *   **Outputs:** The exact deliverables of this phase.
    *   **Contract Preservation:** How this phase maintains the existing Python monolith's behaviors/APIs.
    *   **Acceptance Gates:** Measurable criteria to pass (e.g., "Golden test matches Python output to 6 decimal places").
    *   **Test Requirements:** Specific testing strategies (Testcontainers, E2E, Contract tests).
    *   **Rollback Strategy:** How to revert if the phase fails.
    *   **Hand-off to Next Phase:** Explicit contract defining what the next phase assumes is complete and verified.

Generate the complete planning instructions and directory structure following these mandates.

