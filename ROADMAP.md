# Roadmap — v0.26 controlled canary

## Current baseline

`v0.25.0` remains the released GitHub prerelease baseline:
`https://github.com/ray-toaru/polymarket-execution-suite/releases/tag/v0.25.0`.

Current source is v0.26.0 controlled canary work. One explicitly authorized
BUY/GTC post-only canary was posted, cancelled, and closed with zero observed
fill/position impact. It is still not production-ready, not live-canary-approved
for a second attempt, and does not authorize live submit, live cancel, or
real-funds canary execution without a fresh reviewed `go` decision.

## Immediate next validation

1. Preserve the released `v0.25.0` package and evidence as the historical baseline.
2. Keep root, Hermes, execution-engine CI, and the manual `credentialed-sdk`
   gate green after any source change.
3. Rebuild and revalidate a package only after material source or release-doc
   changes.
4. Keep `polymarket-execution-engine/evidence/current/manifest.json` as the
   only current evidence manifest.
5. Keep `CONTROLLED_CANARY_CLOSEOUT.md` as the tracked summary for the completed
   v0.26 controlled canary; the source JSON evidence remains local `dist/`
   review material.

## Next-phase target on the v0.26 branch

The next release should not broaden live trading. Its goal is a repeatable,
auditable, fail-closed canary pipeline:

1. Single command or runbook stage for fresh market discovery, reviewed
   candidate generation, release-decision binding, preflight, armed submit,
   immediate cancel, readback, and closeout. The first landed entry point is
   no-go only: `scripts/run_controlled_canary_pipeline.py` prepares or accepts a
   candidate, validates dynamic exchange-rule evidence, emits the blocked
   future live/readback/closeout stages, and proves the armed command is
   blocked before remote side effects.
2. Runtime truth integration for kill switch, live-submit gates, idempotency
   lease/owner recovery, and order/cancel reconciliation. The root pipeline now
   reports these as required dependencies and can validate an external
   runtime-truth evidence file before marking a future reviewed-go armed stage
   as operator-runnable. The execution-engine real-funds canary CLI now accepts
   `--runtime-truth-file`, binds the four durable dependency evidence refs, and
   fails closed when the file is missing or incomplete. The execution-engine
   store/service layer now has `CanaryRuntimeTruthStore`, which derives the
   same four gates from runtime state plus `CanaryRuntimeTruth` worker rows. The
   CLI can now consume that projection from PostgreSQL with explicit account and
   condition scope, and the local DB-backed CLI preflight proves this path
   without post/cancel side effects.
3. Dynamic exchange-rule evidence for minimum size, order type, tick, and
   post-only behavior; no permanent `size=5` release invariant.
4. Tracked closeout summaries plus detached local JSON evidence that remain
   redacted and reproducible without exposing signing material.
5. A release decision that can approve exactly one controlled canary attempt or
   remain no-go; production/live trading stays blocked until separate evidence
   exists.

## Next source-hardening items

1. Treat prior canary-prep evidence as satisfied by the `v0.25.0` baseline.
2. Make `v0.26` a controlled canary source-candidate phase, not an implicit live
   canary attempt.
3. Use `docs/future/CANARY_DECISION_PREP_AUDIT.md` as active next-phase governance material,
   not as part of the v0.25.0 release decision. The
   existing reviewed canary package is no-go rehearsal material, but it is not
   bound to the latest supplemental artifact and evidence manifest hashes.
4. Use the regenerated local `dist/pmx-canary-review-v0.26-current/` package as
   no-go review material only; it is ignored by Git and must not be treated as
   armed approval.
5. Before any future canary attempt, produce a reviewed release-decision JSON,
   operator approval reference, external secret-custody reference, alert-routing
   reference, and rollback/runbook review bound to the released artifact and
   evidence hashes.
6. Continue only:
   - validation replay after material code changes;
   - release/evidence consistency fixes;
   - review-package and decision-package improvements that preserve fail-closed
     live submit/cancel behavior.

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
    receipts, redaction envelopes, and adapter request/receipt models now
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
50. In-memory execution implementation split: normalized-intent/snapshot,
    decision, plan-summary, and reservation/receipt helpers now live in
    focused modules.
51. Service binding split: hash-input DTOs, sign-only lifecycle append
    validation, and snapshot/decision binding verification now live in
    focused modules.
52. Runtime helper split: freshness horizon checks, worker-status aggregation,
    and observation-application helpers now live in focused modules.
53. PostgreSQL runtime-state split: account/collateral lookup, worker-row
    collection, and runtime-worker observation loading now live in focused
    modules.
54. API backend lifecycle split: execution-event, order-lifecycle, and
    sign-only/receipt helpers now live in focused modules.
55. API routes split: bootstrap/router construction and health endpoint
    helpers now live in focused modules.
56. PostgreSQL support-helper split: database-error normalization, JSON-payload
    loading, and runtime-state enum/status conversion now live in focused
    modules.
57. PostgreSQL migration-helper split: manifest/checksum, apply flow, and
    applied-migration recording now live in focused modules.
58. API admin reconcile support split: shared auth/correlation context,
    placeholder reconcile validation, and local reconcile validation now live
    in focused modules.
59. API E2E env-guard hardening: fake and PostgreSQL E2E suites now serialize
    token env mutation so local crate tests remain deterministic.
60. API read-route split: submit receipt, lifecycle queries, and runtime
    worker status handlers now live in focused modules.
61. API flow-route split: intent/snapshot/decision, plan compile/submit, and
    sign-only lifecycle handlers now live in focused modules.
62. Service submit split: request/response fingerprinting, blocked-before-
    remote receipt construction, and replay decoding now live in focused
    modules.
63. Service runtime-state provider split: fail-closed, static, and
    store-backed providers now live in focused modules.
64. First real-funds controlled canary closeout: one BUY/GTC post-only order was
    posted, cancelled, and read back with `size_matched=0`, zero matching
    trades, and zero matching account/position/value impact.

## Still blocked

General live submit, general live cancel, repeated real-funds canary attempts,
and production deployment remain blocked in v0.26.0 until a later release has
fresh canary/production evidence and an explicit release decision for that
scope.
