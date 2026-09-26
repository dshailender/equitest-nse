# Phase 9: Observability Stack

> **Phase ID**: 9
> **One-Line Summary**: Introduce enterprise-grade observability (OpenTelemetry, Jaeger, Prometheus, Grafana, Loki) with trace propagation across HTTP and RabbitMQ boundaries.

---

## Goal and Rationale

Introduce enterprise-grade observability (OpenTelemetry, Jaeger, Prometheus, Grafana, Loki) into the architecture to ensure traces span across HTTP and RabbitMQ boundaries.

---

## In-Scope Items

- Update `docker-compose.yml` to include the full observability stack under the default profile.
- Configure OpenTelemetry Java Agents in all Spring Boot services.
- Configure trace context injection/extraction for RabbitMQ messages (W3C `traceparent`/`tracestate` headers as specified in Phase 0 messaging contract).
- Grafana dashboards for JVM metrics and log aggregation.

---

## Explicit Out-of-Scope Items

- Alerting/PagerDuty integration.

---

## Prerequisites

- The entire application functioning correctly (Phase 1 infrastructure running).

---

## Inputs

- Existing Docker configurations.
- Phase 0 messaging contract (trace header requirements).

---

## Outputs

- Tracing, metrics, and logging infrastructure.

---

## Acceptance Gates

- A single backtest run creates a unified Jaeger trace showing the gateway entry, simulation engine HTTP handling, DB queries, RabbitMQ fanout, and the downstream async report generation.
- Trace context is preserved across RabbitMQ boundaries (same trace ID from engine publish to reports/validation consume).

---

## Test Requirements

- Manual validation of Jaeger UI and Grafana dashboards during load generation.
- Automated verification that `traceparent` headers are present in RabbitMQ message properties.

---

## Risks and Mitigations

- *Risk*: Trace context lost over RabbitMQ boundaries.
- *Mitigation*: Utilize `spring-rabbit` tracing integrations and explicitly ensure `traceparent` headers are propagated in the message properties.

---

## Rollback Strategy

- Run using the `lite` profile. Remove OpenTelemetry JVM arguments.

---

## Hand-off to Next Phase

- A fully observable distributed system ready for load and failure testing.

**Checklist for Phase 10 implementer to confirm before starting:**
- [ ] Jaeger UI shows traces for backtest requests
- [ ] Traces span HTTP → RabbitMQ → downstream consumers
- [ ] Prometheus scrapes JVM metrics from all services
- [ ] Grafana dashboards are pre-provisioned and functional
- [ ] Loki aggregates structured logs from all containers

---

## Invariant Checklist

- N/A (Observability infrastructure only).

---

## Contract Checklist

- N/A (Observability infrastructure only).

