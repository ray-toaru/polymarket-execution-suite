# Project architecture — v0.24.0

## Baseline

v0.24.0 keeps the v0.3 architectural split as the design baseline. The integration repository pins
the two implementation planes as submodules:

```text
hermes-polymarket-control  -> Python control plane
polymarket-execution-engine -> Rust execution plane
```

The split is intentional. The control plane may prepare intents, approvals, reports, and API calls, but the execution plane owns validation, lifecycle truth, idempotency, runtime state, signing-boundary isolation, and any future funds-moving authority.

## Trust boundary

Allowed across the public control-plane API:

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

v0.24.0 is shadow-ready baseline source-candidate work. Runtime worker `DEGRADED`, `STALE`, or `UNKNOWN` status must not be treated as live-trading safe. Live submit/cancel remain blocked until runtime freshness, audit redaction, idempotency, PostgreSQL lifecycle, SDK adapter, rollback, reconciliation, and production controls have formal evidence and a later release decision.
