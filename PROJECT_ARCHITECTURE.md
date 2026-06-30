# Project architecture — current baseline

Status: v0.28 production-live-candidate architecture baseline.

## Baseline

The current architecture keeps the v0.3 split as the design baseline. The
integration repository pins the two implementation planes as submodules:

```text
hermes-polymarket-executor-adapter  -> Python Hermes-compatible executor adapter
polymarket-execution-engine -> Rust execution plane
```

The split is intentional. The Python adapter may prepare typed executor API
requests, expose Hermes-compatible tool/report wrappers, and render safe
reports. The execution plane owns validation, lifecycle truth, idempotency,
runtime state, signing-boundary isolation, and any future funds-moving
authority.

## Trust boundary

Allowed across the public adapter/executor API boundary:

- trade intents and normalized intent references;
- decision, snapshot, and plan identifiers;
- submit requests by `execution_id`, `plan_hash`, and `idempotency_key`;
- redacted lifecycle/audit records;
- admin commands that remain non-live or locally state-changing only.

Forbidden across the public boundary:

- private keys;
- CLOB API secrets;
- raw signed payloads;
- signed order envelopes;
- direct database writes;
- direct live CLOB post/cancel operations.

## Component versioning

The integration suite, execution engine, and Hermes adapter may evolve
independently. The suite release pins exact component commits and records the
compatibility matrix; it does not require the component repositories to keep
identical version numbers forever. See `COMPONENT_COMPATIBILITY.md`.

## Rust execution crates

```text
pmx-core       domain types and state transitions
pmx-policy     deterministic constraint evaluation
pmx-authz      service/admin authorization policy
pmx-gateway    signer/CLOB gateway traits and fake gateway
pmx-store      in-memory and PostgreSQL stores
pmx-runtime    worker signal and store-write scaffolding
pmx-service    server-authoritative orchestration layer
pmx-api        Axum API boundary
pmx-release    release/version scaffold
```

## DDD and ports/adapters boundary

The Rust execution engine follows a conservative DDD/Clean Architecture shape:

```text
Domain model and policy:       pmx-core, pmx-policy, pmx-authz
Application orchestration:     pmx-service, pmx-runtime
Internal ports:                pmx-gateway
Persistence/API infrastructure: pmx-store, pmx-api
External SDK infrastructure:   adapters/pmx-official-sdk-adapter
```

Dependency direction is inward. Domain, policy, store, service, and public API
crates must not import `polymarket_client_sdk_v2` or SDK adapter types. Future
SDK-backed execution must enter through a project-owned gateway port, with the
official SDK kept as an infrastructure implementation behind explicit
compile-time and runtime gates.

This means the official SDK adapter is intentionally not a standard/default
workspace dependency today. Making it a first-class execution dependency would
collapse the adapter boundary before the port contract, runtime truth,
reconciliation, custody, rollback, alerting, and reviewed operator decision are
artifact-bound.

## Conservative pre-live policy

v0.28.0 is the production-live-candidate baseline. It is still non-live by
default and does not approve production deployment or general funds-moving
execution.
Runtime worker `DEGRADED`, `STALE`, or `UNKNOWN` status must not be treated as
live-trading safe. Live submit/cancel remain blocked unless current gates,
artifact/evidence binding, one-time approval consumption, human-reviewed
BUY/GTC post-only market selection, runtime/reconcile checks,
balance/allowance checks, and a reviewed `go` decision all pass.

Future real gateway, production submit/cancel, and generic live-read
architecture is specified in
`polymarket-execution-engine/docs/PRODUCTION_LIVE_GATEWAY_SECURITY_DESIGN.md`.
It is not current production wiring.
