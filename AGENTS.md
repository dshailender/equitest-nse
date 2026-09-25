# EquiTest NSE Agent Guide

This repository is a quantitative backtesting and analytics monorepo for Indian equities. The backend is FastAPI-based and the frontend is Next.js/App Router. Start with the project overview in [README.md](README.md) and the detailed system documentation in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 1. Repository map

- Backend service: [backend/app](backend/app)
  - API layer: [backend/app/api](backend/app/api)
  - Core config and middleware: [backend/app/core](backend/app/core)
  - Data ingestion and universe logic: [backend/app/data](backend/app/data)
  - Strategy and risk engines: [backend/app/strategy](backend/app/strategy), [backend/app/risk](backend/app/risk)
  - Backtest simulation: [backend/app/engine](backend/app/engine)
  - Reporting and validation: [backend/app/reports](backend/app/reports), [backend/app/validation](backend/validation)
- Frontend app: [frontend/app](frontend/app)
  - UI pages and dashboards: [frontend/app](frontend/app)
  - Shared client/schema code: [frontend/lib](frontend/lib)
- Data and fixtures: [data](data)
- Docs and specs: [docs](docs)
- Monorepo automation: [Makefile](Makefile)

## 2. Critical repo conventions

This project is not a generic app. Several rules are explicit and must be preserved:

- Zero look-ahead: indicators use session $T$ data and trade execution occurs at $T+1$ market open.
- Survivorship bias prevention: use point-in-time constituent tracking and tag survivorship-biased fallbacks explicitly.
- Top 100 exclusion: NIFTY 50 is an external regime filter, not a trade universe; stocks ranked 1–100 are excluded from trade allocations.
- Overnight gap-down realism: stop-loss execution should reflect market-open gap-down behavior, not artificially improved fills.
- Backtest provenance and auditability: all runs should preserve config, git metadata, and data fingerprints.

These conventions are documented in [README.md](README.md), [docs/STRATEGY.md](docs/STRATEGY.md), [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Prefer those docs over ad hoc assumptions.

## 3. Common commands

Use the project’s automation layer rather than bespoke commands. In this repo, prefer the local wrapper at [bin/make](bin/make) so the bundled tooling and environment are used consistently:

```bash
# install dependencies and generate OpenAPI artifacts
./bin/make install

# run local app stack
./bin/make run-local

# backend unit tests with coverage gate
./bin/make test-backend

# frontend tests
./bin/make test-frontend

# Playwright e2e tests
./bin/make test-e2e

# full project checks
./bin/make test

# lint and static checks
./bin/make lint
```

For direct scripts:

```bash
# root scripts
npm test
npm run lint
```

## 4. Engineering expectations

- Backend tests use Pytest with a minimum coverage gate of 80% and are run from [backend/tests](backend/tests).
- Frontend tests use Vitest and MSW; E2E acceptance tests live in [e2e](e2e).
- Keep changes scoped to the relevant subsystem and preserve the monorepo boundaries between backend, frontend, and docs.
- Prefer small, evidence-based changes that match the existing architecture and documented strategy invariants.
- When changing quantitative logic, validate the exact behavior against the docs and relevant tests before finalizing.

## 5. Useful docs to consult before risky edits

- [README.md](README.md): quickstart, commands, and product overview
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): architecture, subsystem boundaries, and invariants
- [docs/STRATEGY.md](docs/STRATEGY.md): strategy rules and signal logic
- [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md): defaults and design tradeoffs
- [docs/RUNBOOK.md](docs/RUNBOOK.md): local operations, troubleshooting, and workflow guidance
- [docs/data.md](docs/data.md): data model, ingestion, and corporate action handling
- [TRACEABILITY.md](TRACEABILITY.md): requirements coverage and validation matrix

## 6. Working style

- Link to existing docs instead of duplicating them.
- Keep agent instructions concise and action-oriented.
- If a task spans backend and frontend, keep the change aligned with the OpenAPI contract and API schema generation flow.
- Do not remove or weaken repo-level safety checks, especially around data integrity, fairness, and audit logging.
