# Phase 7: API Gateway & OpenAPI Aggregation

> **Phase ID**: 7
> **One-Line Summary**: Provide a unified, single-entry point for the frontend, routing /api/v1/* requests to the correct underlying microservices without altering the frozen contract.

---

## Goal and Rationale

Provide a unified, single-entry point for the frontend, routing `/api/v1/*` requests to the correct underlying microservices without altering the frozen contract.

---

## In-Scope Items

- Spring Cloud Gateway configuration (routes based on path predicates).
- Global CORS configuration for the Angular frontend.
- OpenAPI specification aggregation (Springdoc OpenAPI gateway integration) providing a unified swagger-ui.
- Correct propagation of "reports not ready" HTTP 404 responses from downstream services through the gateway without transformation.

---

## Explicit Out-of-Scope Items

- Modifying underlying service endpoints.
- Authorization/Authentication (assuming none specified in legacy).

---

## Prerequisites

- All 5 microservices running and exposing their local OpenAPI specs.
- Phase 0 contract test suite for validation.

---

## Inputs

- Routing map (e.g., `/api/v1/data/**` -> Data Service, `/api/v1/backtest/run` -> Engine Service, etc.).

---

## Outputs

- `api-gateway` service.
- Unified OpenAPI JSON available at the gateway level.

---

## Acceptance Gates

- HTTP requests sent to Gateway port correctly proxy to the underlying services and return expected payloads.
- The unified OpenAPI spec perfectly matches the legacy `README.md` API surface.
- Phase 0 contract test suite passes when run against the gateway.

---

## Test Requirements

- Contract tests: Ensure no API paths return 404 at the gateway level if they exist in the legacy contract (note: 404 from downstream "reports not ready" protocol is valid and must pass through).

---

## Risks and Mitigations

- *Risk*: Gateway timeout on long-running synchronous requests like `/api/v1/backtest/run`.
- *Mitigation*: Configure extended read/write timeouts specifically for the `/api/v1/backtest/run` and `/api/v1/indicators/preview` routes in the Gateway settings.

---

## Rollback Strategy

- Revert gateway configuration.

---

## Hand-off to Next Phase

- A fully functional, unified backend API on a single port. The Frontend phase inherits this single URL to build against.

**Checklist for Phase 8 implementer to confirm before starting:**
- [ ] Gateway health endpoint returns 200
- [ ] All `/api/v1/*` endpoints are reachable through the gateway
- [ ] Unified OpenAPI spec is available at the gateway
- [ ] No spurious 404s for any endpoint in the frozen contract
- [ ] "Reports not ready" 404s from downstream services pass through correctly
- [ ] Long-running endpoints (backtest/run, indicators/preview) do not timeout
- [ ] Phase 0 contract test suite passes against the gateway

---

## Invariant Checklist

- All endpoints must route correctly, maintaining all functional invariants.

---

## Contract Checklist

ALL endpoints listed in the frozen `/api/v1/*` contract (see `02-phase-index.md` for the complete list).

