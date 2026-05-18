# Implementation status — v0.25.0 shadow-ready SDK sign-only baseline

## Implemented source-level items

- Two-plane pre-live boundary: Python control plane + Rust execution plane.
- Server-authoritative execution service scaffold.
- PostgreSQL-backed store scaffolding for core execution data.
- Sign-only lifecycle API, store path, query path, and idempotency field.
- Sign-only lifecycle PostgreSQL concurrency proof for `client_event_id` replay, mismatch rejection, and terminal-state rejection.
- Runtime worker observation and heartbeat store scaffolding.
- Runtime heartbeat lease persistence path that writes local worker health,
  reads persisted candidates, elects lease ownership, and records fail-closed
  runtime observations with in-memory and PostgreSQL-backed tests.
- Non-live cancel/reconcile lifecycle event recording.
- Persistent cancel/reconcile order lifecycle hardening for
  `RECONCILE_UNKNOWN`, same-correlation replay, and correlation-id mismatch
  rejection across in-memory and PostgreSQL stores.
- Admin audit cursor pagination and filter behavior with in-memory and
  PostgreSQL-backed tests.
- Typed non-live order-event payload constructors for cancel, reconcile, and
  lifecycle divergence records.
- Lifecycle and admin audit query APIs.
- Redacted lifecycle payload envelope at public API/model level.
- v0.25 shadow-ready SDK sign-only baseline gate runner, static guards, version guard, and docs/evidence governance guard.
- Runtime worker loop/tick models for heartbeat lease, resource refresh,
  reconcile backlog, WebSocket liveness, geoblock, and worker crash recovery.
- Order lifecycle event query API and per-order correlation trace field.
- PostgreSQL migration ledger with checksum-bound forward migrations through
  `0003_order_event_trace`.
- Shadow execution would-submit drill runs by default in current gates and
  remains non-posting/non-signing.
- Reconciliation drift drill covers open, missing, repeated-missing, and
  unknown remote observations with fail-closed/operator escalation evidence.
- Rollback/kill-switch drill covers runtime degraded, SDK failure, PostgreSQL
  unavailable, geoblock blocked, low resource, and remote-unknown freeze
  fallback behavior.
- Shadow and rollback drill safety guards validate non-posting/non-signing
  behavior, hashed identifiers, sensitive-env redaction, required rollback
  scenarios, and fallback modes without requiring network access.
- First Rust module governance split keeps behavior stable while separating
  service sign-only lifecycle/standard construction and PostgreSQL
  audit/execution-lifecycle persistence modules.
- SDK adapter mapping helpers were split into normalization and validation
  modules while preserving the public mapping function and sign-only behavior.
- SDK error normalization was split out of adapter liveness into a feature-gated
  internal module without changing public exports.
- PostgreSQL runtime worker persistence was split into heartbeat, observation,
  and status-query implementation modules.
- PostgreSQL repository tests now split runtime-worker health/status and
  order-lifecycle coverage into smaller focused modules.
- PostgreSQL sign-only lifecycle PG tests now live in a focused test module
  with the same idempotency and no-remote-side-effect assertions.
- PostgreSQL admin audit and submit idempotency PG tests now live in focused
  test modules while preserving the same pagination, replay, conflict, and
  in-progress assertions.
- PostgreSQL schema, receipt/reservation, execution lifecycle, and runtime-state
  PG tests now live in focused modules; the parent PG test file now only holds
  shared setup helpers and module declarations.
- In-memory store tests now live in focused modules for common helpers,
  admin/sign-only behavior, runtime observations, runtime worker health, and
  order lifecycle.
- Service flow and sign-only orchestration tests now live in focused modules
  while preserving submit blocking, object-graph conflict, lifecycle sequence,
  standard sign-only digest, and malformed digest assertions.
- Service runtime-worker basic, heartbeat lease/continuous tick, and non-live
  order lifecycle tests now live in focused modules while preserving
  fail-closed, PG parity, cancel/reconcile, and divergence assertions.
- The parent `pmx-service` service test file now only holds shared helpers and
  module declarations; all service tests have moved to focused modules.
- HTTP PostgreSQL API E2E tests now live in focused modules for smoke,
  object-graph/plan-hash rejection, runtime-state gating, and admin-audit
  coverage; the parent file only keeps shared helpers and module declarations.
- Official SDK adapter tests now live in focused modules for canary/config,
  sign-only lifecycle/profile behavior, plan mapping, liveness/error redaction,
  and feature-gated smoke/typecheck coverage; the parent file only keeps shared
  helpers and module declarations.
- Runtime model tests now live in focused modules for breakdown/loop behavior
  and capability evaluations; the parent runtime test file now only keeps
  module declarations.
- HTTP fake/in-memory API E2E tests now live in focused modules for auth/smoke,
  scaffolded non-live lifecycle coverage, and negative startup/object-graph
  behavior; the parent file now only keeps shared helpers and module
  declarations.
- Observability evidence guard binds correlation id, redacted payload, order
  event trace, admin audit query, shadow trace, reconcile trace, and rollback
  fallback evidence.
- Live canary rehearsal has an expanded blocked dry-run stage model covering
  whitelist, caps, operator approval, reservation, idempotency, reconcile,
  remote-unknown freeze, post-submit reconcile, cancel-unknown escalation, and
  cancel-only fallback checks.

## Intentionally blocked

- Live submit.
- Live cancel.
- Production deployment.
- Python-side access to signing or CLOB secrets.
- Public exposure of raw signed payloads or signed order envelopes.

## Current validation evidence

The current canonical evidence manifest records passing full gates for Rust,
PostgreSQL, SDK, credentialed non-trading smoke, sign-only dry-run, release
artifact, shadow execution, observability, and governance checks:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Current release status remains `shadow-ready SDK sign-only candidate`; live submit/cancel and
production deployment are still intentionally blocked.
