# Roadmap — v0.25.0 shadow-ready SDK sign-only baseline

## Immediate next validation

1. Run local/static checks.
2. Generate a clean package.
3. Run full Rust/SDK/PostgreSQL gates externally against the final package.
4. Bind current evidence to `evidence/current/manifest.json` and the final artifact SHA-256.

## Next source-hardening items

1. No remaining v0.25 source-hardening item is currently open. Continue with
   validation replay, release evidence refresh, and behavior-preserving Rust
   module governance before any new feature scope.

## Recently landed hardening

1. Sign-only lifecycle PostgreSQL concurrency and replay stress test for `client_event_id`, mismatched replay rejection, and terminal-state rejection.
2. Runtime heartbeat lease persistence proof: local heartbeat is written to `worker_health`, candidates are read back through `RuntimeWorkerStatusStore`, owner election is persisted to runtime observations, and both in-memory plus PostgreSQL-backed service tests cover the path.
3. Persistent cancel/reconcile lifecycle hardening: `RECONCILE_UNKNOWN`
   observations are durable local `order_events`, repeated same-correlation
   cancel/reconcile writes replay idempotently, and correlation id reuse with a
   different event is rejected in both in-memory and PostgreSQL stores.
4. Audit query pagination and typed per-event payload bodies: admin audit
   cursor/filter behavior is covered in in-memory and PostgreSQL stores, and
   non-live cancel/reconcile/divergence payloads are serialized from typed
   service-layer constructors without exposing raw signed material.
5. Shadow dry-run and rollback drill hardening: the shadow drill now has
   script-level invariant checks for non-posting, non-signing, hashed
   identifiers, and redacted sensitive-env handling; rollback drills now have
   scenario/fallback validation and a network-free guard captured in evidence.
6. Rust module governance first split: sign-only service lifecycle/standard
   construction and PostgreSQL audit/execution-lifecycle persistence were moved
   behind smaller module boundaries without public API changes.
7. SDK mapping module split: official SDK adapter mapping normalization and
   validation helpers now live behind smaller internal module boundaries without
   changing the public adapter API.
8. SDK liveness module split: SDK error normalization now lives behind a
   feature-gated internal module with public liveness exports preserved.
9. PostgreSQL runtime worker module split: worker heartbeat writes,
   observation writes, and status queries now live behind smaller store modules.
10. PostgreSQL repository test module split: runtime-worker health/status and
    order-lifecycle PG tests now live in focused test modules.
11. PostgreSQL sign-only test module split: sign-only lifecycle persistence and
    client-event idempotency tests now live in a focused PG test module.
12. PostgreSQL admin/idempotency test module split: admin audit pagination and
    submit idempotency replay/conflict tests now live in focused PG modules.
13. PostgreSQL remaining test split: schema, receipt/reservation, execution
    lifecycle, and runtime-state PG tests now live in focused modules.
14. In-memory store test module split: common helpers, admin/sign-only,
    runtime observation, runtime worker, and order lifecycle tests now live in
    focused modules.
15. Service flow/sign-only test module split: base flow and sign-only
    orchestration tests now live in focused service test modules.
16. Service runtime/order-lifecycle test module split: runtime-worker basic,
    heartbeat lease/continuous tick, and non-live order lifecycle tests now
    live in focused service test modules.
17. Service test parent-file cleanup: `pmx-service/src/service_tests.rs` now
    only keeps shared helpers and module declarations.
18. HTTP PostgreSQL API E2E module split: smoke, negative-path, runtime-state,
    and admin-audit coverage now live in focused test modules.
19. Official SDK adapter test module split: canary/config, sign-only, mapping,
    liveness/error, and feature-gated smoke/typecheck coverage now live in
    focused test modules.
20. Runtime model test module split: breakdown/loop and evaluation coverage now
    live in focused runtime test modules.
21. HTTP fake/in-memory API E2E module split: auth/smoke, scaffolded lifecycle,
    and negative startup/object-graph coverage now live in focused test
    modules.
22. Core domain test module split: intent normalization, lifecycle transition,
    and divergence coverage now live in focused test modules.
23. Gateway test module split: post/cancel, signer-provider, and read-only
    reconcile-reader coverage now live in focused test modules.
24. Service specialized runtime-worker test split: resource/reconcile,
    websocket/geoblock, and crash-recovery coverage now live in focused test
    modules.
25. Runtime breakdown/evaluation test split: capability grouping, worker-loop,
    provider-fed loop, lease/resource, reconcile/websocket/geoblock, and crash
    recovery coverage now live in focused test modules.
26. In-memory store admin/sign-only test split: admin-audit and sign-only
    lifecycle coverage now live in focused test modules.
27. HTTP fake scaffold helper extraction: the same E2E assertion flow now runs
    through local helper functions to reduce single-function complexity without
    changing behavior.
28. Service runtime-worker basic sub-split: provider state, runtime
    signals/ticks, and worker-status query coverage now live in finer-grained
    focused modules.
29. Service runtime-worker lease sub-split: continuous snapshots, lease
    election, and persisted/PostgreSQL owner parity now live in focused
    modules.
30. Service non-live lifecycle sub-split: cancel/reconcile recording and
    divergence escalation now live in focused modules.
31. Service sign-only sub-split: lifecycle sequencing and standard sign-only
    construction/redaction coverage now live in focused modules.
32. Service specialized runtime-worker sub-split: resource-refresh and
    reconcile-backlog coverage now live in separate focused modules.
33. HTTP fake scaffold phase split: compile, submit/sign-only, admin, and
    public-query helpers now live in focused modules while preserving one E2E
    entry test.
34. HTTP PostgreSQL smoke phase split: compile/submit, sign-only, admin
    lifecycle, and public-query helpers now live in focused modules while
    preserving one E2E entry test.
35. HTTP PostgreSQL runtime phase split: runtime-state/degraded checks and
    ready-plan/blocked-submit verification now live in focused modules while
    preserving one E2E entry test.
36. Core lifecycle module split: sign-only lifecycle, order-lifecycle
    transitions, and divergence/reconcile classification now live in focused
    modules.
37. Core plan module split: decision results, execution summaries/submit
    receipts, redaction envelopes, and control-plane request/receipt models now
    live in focused modules.
38. In-memory sign-only memory-test split: happy-path, idempotency, and
    reject-path coverage now live in focused modules.
39. Runtime breakdown capability split: blocking, capability-group, and
    store-write fail-closed coverage now live in focused modules.
40. PostgreSQL order-lifecycle test split: persistence, replay, and
    reconcile-backlog coverage now live in focused modules.
41. PostgreSQL sign-only test split: persistence and concurrent idempotency
    coverage now live in focused modules.
42. PostgreSQL runtime-state test split: state-loading/degradation and
    observation-write coverage now live in focused modules.
43. Service standard sign-only implementation split: request validation,
    digest/ref derivation, and lifecycle persistence/replay helpers now live in
    focused modules.
44. PostgreSQL order-lifecycle write split: upsert, replay/conflict handling,
    and event-apply SQL paths now live in focused modules.
45. Service heartbeat lease tick split: lease-election recording and
    store-backed heartbeat/status persistence now live in focused modules.
46. In-memory order-lifecycle test split: cancel-requested, replay/conflict,
    invalid-transition, and reconcile-backlog coverage now live in focused
    modules.
47. Core base module split: shared errors, typed ids, decimal validation, and
    canonical JSON hashing/serialization helpers now live in focused modules.
48. In-memory order-lifecycle implementation split: write, event-query, and
    reconcile-backlog helpers now live in focused modules.
49. In-memory lifecycle implementation split: execution-lifecycle and
    sign-only lifecycle helpers now live in focused modules.

## Still blocked

Live submit, live cancel, and production deployment remain blocked in v0.25.0 until a later release has canary/production evidence and an explicit release decision.
