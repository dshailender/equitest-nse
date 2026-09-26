# Phase 8: Angular Frontend

> **Phase ID**: 8
> **One-Line Summary**: Migrate the Next.js 14 frontend to an Angular 22+ (Zoneless, Signals-first) SPA with Angular Material and Chart.js.

---

## Goal and Rationale

Migrate the Next.js 14 frontend to an Angular 22+ (Zoneless, Signals-first) SPA, utilizing Angular Material and Chart.js, binding exactly to the unified Gateway API.

---

## In-Scope Items

- Angular 22 workspace initialization.
- OpenAPI-based TypeScript client generation.
- Zoneless change detection setup and Signals-based state management.
- Implementation of all legacy UI views (Dashboard, Run Config, Sweep, Charts, Reports).
- Dockerfile for building and serving the UI via Nginx.
- **"Reports Not Ready" UI handling**: The UI must implement polling or notification for async endpoints (`/reports/*`, `/validation/*`, `/audit`). Display loading/processing states when these endpoints return 404 or `{"status": "processing"}`.

---

## Explicit Out-of-Scope Items

- Adding new UI features not present in the legacy system.
- Modifying the API to make UI development easier.

---

## Prerequisites

- Phase 7 API Gateway running locally.
- Phase 0 "reports not ready" protocol specification.

---

## Inputs

- Unified OpenAPI spec.
- Legacy UI visual requirements.
- Phase 0 "reports not ready" protocol (for async endpoint handling).

---

## Outputs

- Angular frontend application running locally in docker.

---

## Acceptance Gates

- The UI builds completely without `zone.js`.
- A user can configure a backtest, run it, and view the equity curve Chart.js visualization entirely through the UI.
- Reports page correctly shows loading/processing state and polls until reports are ready.

---

## Test Requirements

- Unit tests: Angular component tests using signal verification.
- E2E tests: Cypress or Playwright verifying key user journeys.
- Async polling test: Verify UI correctly handles 404/"processing" responses and transitions to displaying data when ready.

---

## Risks and Mitigations

- *Risk*: Signals/Zoneless architecture is new and may cause third-party library compatibility issues.
- *Mitigation*: Ensure Chart.js is wrapped correctly, manually triggering change detection or using effect hooks when chart data updates.

---

## Rollback Strategy

- Revert UI repository.

---

## Hand-off to Next Phase

- Complete end-to-end local stack (UI + Gateway + Services + DBs + Message Broker).

**Checklist for Phase 10 implementer to confirm before starting:**
- [ ] Angular app builds and serves without zone.js
- [ ] All legacy UI routes are implemented (/data, /indicators, /signals, /risk, /backtest, /sweep, /reports/[runId], /validation, /docs)
- [ ] Backtest can be configured, run, and results viewed through the UI
- [ ] Chart.js visualizations render correctly (equity curve, drawdown, heatmap)
- [ ] Responsive layout: zero horizontal overflow at 375px and 768px
- [ ] Reports page correctly handles async "not ready" states

---

## Invariant Checklist

- N/A for backend invariants, but UI must correctly display all deterministic outputs without rounding obfuscation.

---

## Contract Checklist

- N/A (Consumes all endpoints via generated TypeScript client).

