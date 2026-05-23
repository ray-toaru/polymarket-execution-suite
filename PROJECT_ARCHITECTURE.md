# Project architecture — current baseline

Status: v0.27 source-candidate architecture baseline.

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

## Conservative pre-live policy

v0.26.1 is the controlled real-funds canary source-candidate baseline.
Runtime worker `DEGRADED`, `STALE`, or `UNKNOWN` status must not be treated as
live-trading safe. Live submit/cancel remain blocked unless current gates,
artifact/evidence binding, one-time approval consumption, human-reviewed
BUY/GTC post-only market selection, runtime/reconcile checks,
balance/allowance checks, and a reviewed `go` decision all pass.
