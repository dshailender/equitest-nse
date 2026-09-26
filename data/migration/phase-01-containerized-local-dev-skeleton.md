# Phase 1: Containerized Local Dev Skeleton

> **Phase ID**: 1
> **One-Line Summary**: Establish the foundational local development environment (Docker Compose) and empty Spring Boot multi-module project structure.

---

## Goal and Rationale

Establish the foundational local development environment (Docker Compose) and empty Spring Boot multi-module project structure. This guarantees a "Container-First, Local-First" workflow where all dependent infrastructure (Postgres, RabbitMQ) and basic service skeletons can be spun up with a single command.

---

## In-Scope Items

- Maven multi-module structure for Spring Boot 4.1.1 and Java 27.
- `docker-compose.yml` with `lite` profile (excluding heavy observability for now).
- PostgreSQL 16 container with initialization scripts for 5 isolated logical databases (`equitest_data`, `equitest_engine`, `equitest_sweep`, `equitest_reports`, `equitest_validation`).
- RabbitMQ 3.13 container with:
  - `equitest.events` topic exchange (durable: true)
  - `equitest.dlx` dead-letter exchange (durable: true, type: direct)
  - Durable queues: `reports.backtest.completed.queue`, `validation.backtest.completed.queue`, `sweep.backtest.completed.queue`, `reports.pdf.jobs.queue`, `equitest.dead-letters`
  - Retry policy: 3 retries with exponential backoff (1s, 5s, 25s) before routing to DLX
  - Message persistence: `delivery_mode: 2`
- Empty Spring Boot service modules for Data, SimulationEngine, Sweep, Reports, Validation, and Gateway.
- Base `/health` and `/api/v1/health` endpoints implemented across skeletons.

---

## Explicit Out-of-Scope Items

- Any domain logic or real API endpoints (other than health).
- Frontend setup.
- OpenTelemetry instrumentation (deferred to Phase 9).

---

## Prerequisites

- Phase 0 contract extraction completed: golden fixtures exist under `data/migration/contracts/`, `backtest.completed` v1 schema is finalized, "reports not ready" protocol is documented.
- Target OS with Docker and Docker Compose V2 installed.
- Java 27 JDK and Maven.

---

## Inputs

- Original project architecture directives.
- `data/migration/contracts/backtest-completed-schema.json` (from Phase 0) — defines exchange topology, queue bindings, and DLX configuration.

---

## Outputs

- Multi-module Maven repository.
- `docker-compose.yml`.
- SQL init scripts for database schemas.
- RabbitMQ definitions file (with durable queues, DLX, and bindings matching Phase 0 spec).

---

## Acceptance Gates

- `docker compose --profile lite up` successfully boots PostgreSQL, RabbitMQ, and all 6 Spring Boot skeletons without errors.
- `curl localhost:<port>/health` returns 200 OK for every service.
- 5 distinct PostgreSQL logical databases are accessible.
- RabbitMQ management UI is accessible, showing the configured exchanges, all durable queues, and DLX bindings.

---

## Test Requirements

- Integration test checking database connection pool acquisition on context load for each service skeleton.
- Integration test confirming RabbitMQ connection factory loads correctly.
- Verification that all queues declared in Phase 0's messaging contract exist and are durable.

---

## Risks and Mitigations

- *Risk*: Memory exhaustion on local developer machines from running many JVMs.
- *Mitigation*: Configure explicit JVM memory limits (e.g., `-Xmx256m` for skeletons) in the docker-compose environment variables.

---

## Rollback Strategy

- Revert Git commit. This is the initial phase, so fallback is an empty repository.

---

## Hand-off to Next Phase

- A running local dev environment.
- Verified state: All databases, message brokers (with durable queues and DLX), and empty service containers are up. Next phase (Data Service) assumes it can write Flyway migrations against `equitest_data` and connect to it.

**Checklist for Phase 2 implementer to confirm before starting:**
- [ ] `docker compose --profile lite up` runs cleanly
- [ ] All 6 service health endpoints return 200
- [ ] `equitest_data` database exists and is accessible
- [ ] RabbitMQ management UI shows `equitest.events` exchange (durable)
- [ ] RabbitMQ management UI shows `equitest.dlx` exchange (durable)
- [ ] All 5 durable queues exist with correct bindings
- [ ] Dead-letter queue `equitest.dead-letters` exists

---

## Invariant Checklist

- None directly applicable to boilerplate infra.

---

## Contract Checklist

- `GET /health`
- `GET /api/v1/health`

