# Implementation status — v0.28.0 production-live-candidate

## 2026-06-11 additions

- Added a read-only admin session endpoint with subject, scope, and capability
  reporting.
- Added adapter verification that rejects subject mismatch and missing admin
  capabilities.
- Added non-live release provenance generation and validation with artifact,
  manifest, source, submodule, CI, and dependency-material hashes.
- Regenerated current engine evidence and passed exact-commit CI in all three
  repositories.

External deployment identity proof, independent reviewer signature, GitHub
secret scope, and branch protection remain external requirements. Live submit,
live cancel, production deployment, and real-funds authorization remain blocked.

## 2026-06-10 hardening closeout

- `validate_contracts`: `26` structured, `0` mixed, `0` failed.
- Root CI owns pinned component Rust/PostgreSQL/Python, adapter quality,
  governance, deterministic package, and artifact validation gates.
- Python compatibility is verified on 3.11 and 3.13 across Ubuntu and macOS.
- Submodule branch metadata and release freeze-tag consistency are guarded.
- Candidate-market preparation uses bounded read-only requests, content-type
  validation, retry/backoff, dynamic book rules, reviewed external references,
  and hash-bound snapshots.
- Approval and runtime evidence bind commit/run references, artifact and
  manifest hashes, operator/reviewer identity references, and runtime truth
  without storing raw secrets or signatures.
- `SECURITY_MODEL.md` records threat, misuse, and evidence-retention controls.

Release posture remains `non_live_hardened`; production deployment and live
submit/cancel remain blocked by the formal release decision.

## Phase 5 non-live foundation

- Added typed non-live execution commands for place, cancel, and replace.
  Commands do not authorize remote side effects.
- Added typed fill, position, open-order, exposure, and risk-limit projections
  with fail-closed kill-switch and exposure decisions.
- Added market/book snapshots with stale and future-dated fail-closed checks.
- Added a read-only market-data gateway port whose default implementation is
  disabled.
- Added in-memory and PostgreSQL portfolio projection persistence with
  account-scoped readback, first-write-wins timestamp semantics, and migration
  coverage.
- Added explicit replace preparation/cancel-pending/unknown/rejected lifecycle
  states. Non-live replace preparation persists only opaque hash references and
  replays idempotently by correlation ID.
- Added secret-provider, alerting, and deployment-readiness ports with a
  fail-closed disabled adapter.
- Added normalized live-read event records, in-memory and PostgreSQL
  persistence, a read-only admin query endpoint, and Hermes admin read-only
  tooling. The event model stores only allowlisted readback fields and redacted
  error summaries.
- No live endpoint, production gateway wiring, raw secret material, or live
  submit/cancel authorization was added.

## Implemented source-level items

- Two-plane pre-live boundary: Python executor adapter + Rust execution plane.
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
- v0.28 production-live-candidate gate runner, static guards, version guard, and docs/evidence governance guard.
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
- Explicit live-gateway service tests now re-check runtime truth after remote
  post acknowledgment; if runtime degrades at that point, the order remains
  recorded as posted but the submit receipt is `PARTIAL_REMOTE_UNKNOWN` and
  operator review is required.
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
- Core domain tests now live in focused modules for intent normalization,
  lifecycle transitions, and divergence classification; the parent domain test
  file now only keeps shared helpers and module declarations.
- Gateway tests now live in focused modules for post/cancel flows, signer
  provider boundaries, and read-only reconcile-reader behavior; the parent test
  file now only keeps shared helpers and module declarations.
- Service specialized runtime-worker tests now live in focused modules for
  resource/reconcile, websocket/geoblock, and crash-recovery behavior.
- Service runtime-worker basic tests now live in finer-grained modules for
  provider-backed state, runtime signal/tick fail-closed behavior, and
  runtime-worker status query coverage.
- Service runtime-worker lease tests now live in finer-grained modules for
  continuous provider snapshots, fail-closed lease election, and
  persisted/PostgreSQL lease-owner parity behavior.
- Service non-live order lifecycle tests now live in focused modules for
  cancel/reconcile recording and divergence escalation behavior.
- Service sign-only tests now live in finer-grained modules for lifecycle
  sequencing and standard sign-only construction/redaction behavior.
- Service specialized runtime-worker tests now also separate dedicated
  resource-refresh and reconcile-backlog modules instead of sharing a mixed
  resource/reconcile parent file.
- Runtime breakdown/evaluation tests now live in finer-grained focused modules
  for capability grouping, worker-loop behavior, provider-fed loop behavior,
  lease/resource evaluation, reconcile/websocket/geoblock evaluation, and
  crash-recovery evaluation.
- Core lifecycle domain models now live in focused modules for sign-only
  lifecycle, order-lifecycle transitions, and divergence/reconcile
  classification.
- Core plan/adapter-facing models now live in focused modules for decision
  results, execution summaries/submit receipts, redaction envelopes, and
  adapter request/receipt models.
- Core base domain primitives now live in focused modules for shared errors,
  typed ids, decimal validation, and canonical JSON hashing/serialization
  helpers.
- In-memory store admin/sign-only tests now live in focused modules for
  admin-audit behavior and sign-only lifecycle behavior.
- In-memory store sign-only tests now also separate happy-path, idempotency,
  and reject-path coverage into focused modules.
- Runtime breakdown capability tests now also separate blocking, capability
  grouping, and store-write fail-closed coverage into focused modules.
- PostgreSQL order-lifecycle tests now also separate persistence, replay, and
  reconcile-backlog coverage into focused modules.
- PostgreSQL sign-only tests now also separate persistence and concurrent
  idempotency coverage into focused modules.
- PostgreSQL runtime-state tests now also separate state-loading/degradation
  and observation-write coverage into focused modules.
- Service standard sign-only implementation now separates request validation,
  digest/ref derivation, and lifecycle persistence/replay helpers.
- Service heartbeat lease tick implementation now separates lease-election
  recording and store-backed heartbeat/status persistence helpers while
  preserving the same public runtime-worker API and fail-closed behavior.
- PostgreSQL order-lifecycle write implementation now separates upsert,
  replay lookup/conflict handling, and event-apply SQL paths.
- In-memory order-lifecycle store implementation now separates write,
  event-query, and reconcile-backlog helpers while preserving the same public
  store traits.
- In-memory lifecycle store implementation now separates execution-lifecycle
  and sign-only lifecycle helpers while preserving the same public store
  traits.
- In-memory execution store implementation now separates normalized-intent/
  snapshot, decision, plan-summary, and reservation/receipt helpers while
  preserving the same public store traits.
- Service binding helpers now separate hash-input DTOs, sign-only lifecycle
  append validation, and snapshot/decision binding verification while
  preserving the same public service exports.
- Runtime helper logic now separates freshness horizon checks, worker-status
  aggregation, and observation-application helpers while preserving the same
  store helper exports.
- PostgreSQL runtime-state loading now separates account/collateral lookup,
  worker-heartbeat row collection, and runtime-worker observation loading while
  preserving the same `RuntimeStateStore` behavior.
- API backend lifecycle delegation now separates execution-event,
  order-lifecycle, and sign-only/receipt helpers while preserving the same
  backend method surface.
- API route assembly now separates bootstrap/router construction and health
  endpoint helpers while preserving the same exported app builders.
- PostgreSQL support helpers now separate database-error normalization,
  JSON-payload loading, and runtime-state enum/status conversion while
  preserving the same public store helper behavior.
- PostgreSQL migration helpers now separate manifest/checksum, apply flow, and
  applied-migration recording while preserving the same `PostgresStore`
  schema-apply behavior.
- API admin reconcile support now separates shared auth/correlation context,
  non-live request validation, and local reconcile validation while preserving
  the same route behavior.
- API fake/PostgreSQL E2E tests now serialize process-env token mutation so
  crate-level tests remain deterministic under parallel scheduling.
- API read routes now separate submit-receipt reads, lifecycle-event queries,
  and runtime-worker status queries while preserving the same public API
  behavior.
- API flow routes now separate intent/snapshot/decision, plan compile/submit,
  and sign-only lifecycle handlers while preserving the same public API
  behavior.
- Service submit implementation now separates request/response fingerprinting,
  blocked-before-remote receipt construction, and replay decoding while
  preserving the same submit/idempotency behavior.
- Service runtime-state providers now separate fail-closed fallback, static
  provider, and store-backed provider implementations while preserving the
  same public provider behavior.
- In-memory order-lifecycle tests now also separate cancel-requested,
  replay/conflict, invalid-transition, and reconcile-backlog coverage into
  focused modules.
- The HTTP fake scaffold E2E test now uses local helper functions to preserve
  the same route assertions with lower single-function complexity.
- The HTTP fake scaffold E2E test now also keeps compile, submit/sign-only,
  admin, and public-query phases in focused helper modules while preserving the
  same single test flow.
- The HTTP PostgreSQL smoke E2E test now keeps compile/submit, sign-only,
  admin lifecycle, and public-query phases in focused helper modules while
  preserving the same single test flow.
- The HTTP PostgreSQL runtime E2E test now keeps runtime-state/degraded checks
  and ready-plan/blocked-submit verification in focused helper modules while
  preserving the same single test flow.
- Observability evidence guard binds correlation id, redacted payload, order
  event trace, admin audit query, shadow trace, reconcile trace, and rollback
  fallback evidence.
- Live canary rehearsal has an expanded blocked dry-run stage model covering
  whitelist, caps, operator approval, reservation, idempotency, reconcile,
  remote-unknown freeze, post-submit reconcile, cancel-unknown escalation, and
  cancel-only fallback checks.
- Runtime heartbeat worker scaffolding now exposes a non-trading heartbeat
  loop with an injected persistence sink; the old discard-only placeholder
  compatibility entry point has been removed on the v0.28 development branch.
- Guarded real-funds canary preflight is implemented behind explicit
  `live-submit`, `PMX_ALLOW_LIVE_SUBMIT`, `PMX_ALLOW_REAL_FUNDS_CANARY`,
  config, approval, artifact-hash, evidence-manifest-hash, balance/allowance,
  market-safety, and cap preconditions.
- The real-funds canary SDK path constructs a GTC post-only BUY limit order,
  immediately cancels it after accepted posting, and contains the only permitted
  adapter `post_order` call site; normal gates validate this without posting or
  cancelling.
- The first authorized v0.26 controlled real-funds canary completed as
  `BUY/GTC/post_only=true`, `size=5`, `limit_price=0.02`; order readback
  returned `CANCELED` and `size_matched=0`, trade readback returned zero
  matching fills, and account readback returned zero matching activity,
  positions, and value impact. The tracked summary is
  `CONTROLLED_CANARY_CLOSEOUT.md`.
- PostgreSQL migration `0004_real_funds_canary` adds idempotent, hash-bound,
  redaction-preserving local canary run storage without raw signed order
  exposure.
- Real-funds canary lifecycle closure now has in-memory and PostgreSQL-backed
  local run persistence, `(account_id, idempotency_key)` replay/conflict
  handling, remote-unknown freeze escalation, simulated reconcile state, and
  service helpers that reject remote side effects and raw signed order exposure.
- Real-funds canary program readiness now includes a local-only
  `pmx-real-funds-canary` CLI behind the `live-submit` feature, SDK read-only
  validation of an externally supplied candidate market, default dry-run
  behavior, and readiness evidence that records no posting and no remote side
  effects.
- Real-funds canary dry-run candidate validation emits aggregate safety
  diagnostics without token identifiers, signed material, secrets, or raw order
  payloads. Active market discovery is intentionally outside the execution
  engine boundary.
- Real-funds canary armed mode now requires a reviewed release-decision JSON
  bound to the same artifact SHA-256 and evidence-manifest SHA-256 as the
  approval file.
- Real-funds canary armed stage reporting now keeps the latest handoff report
  in `--report-file` and appends every post/cancel stage to
  `<report-file>.stages.jsonl` for ordered recovery review.
- Reviewed-go armed invocation planning now reports the required explicit
  operator env gates `PMX_ALLOW_LIVE_SUBMIT=1` and
  `PMX_ALLOW_REAL_FUNDS_CANARY=1` instead of implying config flags alone are
  sufficient.
- Controlled canary closeout now consumes that append-only stage history,
  records its SHA-256 and stage summary, and fails closed on missing history,
  mismatched remote order id, raw signed material exposure, or unresolved
  `operator_required` stages.
- Reviewed-go closeout orchestration now has a `--readback-closeout-only` mode
  for already consumed canary packages and refuses the full preflight/armed
  workflow when post-canary evidence already exists. Its Data API readback
  account resolution can use `PMX_CLOB_FUNDER` from either the runtime env or a
  local `--secrets-env-file` without logging secret values.
- If an `operator_required` stage exists, closeout now requires a bound
  `operator-recovery.json` with an operator review reference, exact stage
  history SHA-256, same remote order id, no-retry/no-second-order assertions,
  and order/trade/account readback evidence references before it can close.
- `post_unknown` without a remote order id now uses a separate
  `operator-incident-recovery.json` path. It can only close as
  `controlled_real_funds_canary_incident_closed_no_remote_order_found` after a
  bound investigation window plus account-level open-order, trade, and activity
  readback prove no matching remote order or fill was found.
- Local real-funds canary review package generation now binds artifact/evidence
  hashes and produces review-only material that is not an armed approval.
- Single-host limited deployment templates now cover `pmx-api`, a dry-run
  canary runner, preflight, rollback, and reference-only local custody defaults
  while keeping live submit, live cancel, production deployment, and real-funds
  canary execution disabled.
- Single-host canary candidate preflight now verifies generated review-package
  material remains `no_go`, reference-only, dry-run only, and bound to artifact
  and evidence hashes before any future operator review.
- Single-host `go` candidate drill now creates only a temporary operator-review
  candidate, keeps `go_candidate_committed=false`, and verifies the armed CLI
  still requires an explicit reviewed release-decision file.
- Hermes executor adapter can build a blocked canary readiness report from
  approval/evidence references under an operator-provided local Hermes profile
  without signing, direct CLOB access, or remote side effects.

## Intentionally blocked

- Live submit.
- Live cancel.
- Production deployment.
- Actual real-funds canary fill until a reviewed release decision and local
  approval file explicitly authorize it.
- Any second real-funds canary attempt until fresh market discovery, a new
  reviewed release decision, current gates, and a new closeout plan are bound to
  that exact attempt.
- Python-side access to signing or CLOB secrets.
- Public exposure of raw signed payloads or signed order envelopes.

## Current validation evidence

The current canonical evidence manifest records a mix of passing local gates
and explicitly skipped environment-gated checks. Current manifest gate
statuses are:

- `postgres_validation=pass`
- `credentialed_non_trading_validation=skipped`
- `sdk_standard_sign_only_validation=pass`
- `real_funds_canary_store_truth_cli_validation=pass`

PostgreSQL-backed gates and store-truth CLI preflight were executed locally on
2026-06-20 against an isolated PostgreSQL 16 test cluster. Credentialed
non-trading smoke remains skipped because explicit credentialed opt-in was not
enabled for this run. Skipped credentialed checks must not be inferred as
current pass results from older evidence.

- Current execution-engine commit:
  `eacd6dbb94802e0402d213361c06649caaaf6386`.
- Latest pushed Phase 5 code-state integration GitHub CI:
  `ray-toaru/polymarket-execution-suite/actions/runs/27751360977`, success.
- Latest pushed Phase 5 code-state execution-engine GitHub CI:
  `ray-toaru/polymarket-execution-engine/actions/runs/27751351091`, success.
- Current local Phase 5 live-read event persistence/API commits are not pushed
  and have no GitHub CI result:
  integration root before this status sync
  `aabdbda65a90262d01317b13aef0f08224133bae`;
  execution-engine `eec14d8e5b126c81150e3d6cdd6147e6be43dab6`;
  adapter `49fb4b6c209e744f57b87b255bbf92003eacb557`.
  Local validation passed for Rust workspace check, targeted live-read store
  and gateway tests, API scaffold test, Hermes adapter tests, OpenAPI parity,
  contract validation, and root unit tests.
- Historical credentialed SDK GitHub gate:
  `ray-toaru/polymarket-execution-engine/actions/runs/26175786984`, success.
- GitHub CI ownership is split by repository: the integration repository owns
  version/contract/release-artifact checks; execution-engine owns Rust,
  PostgreSQL, current gates, SDK adapter checks, and the manual
  `credentialed-sdk` workflow.
- The `credentialed-sdk` environment is configured only in
  `polymarket-execution-engine`; the integration repository does not own those
  secrets.
- `real_funds_canary_preflight_validation`: pass.
- `real_funds_canary_lifecycle_validation`: pass.
- `real_funds_canary_ready_validation`: pass.
- `real_funds_canary_review_package_validation`: pass.
- `single_host_deployment_validation`: pass.
- `single_host_canary_candidate_validation`: pass.
- `single_host_go_candidate_validation`: pass.
- `65-real-funds-canary-preflight.log`: pass, no post, no cancel, no remote side
  effect.
- `67-real-funds-canary-ready-drill.log`: pass, program ready, no actual
  execution, no post, no remote side effect.

Historical evidence, not current exact-commit evidence:

- 2026-05-23 PostgreSQL repository/API and store-truth checks passed.
- The historical credentialed SDK GitHub gate
  `ray-toaru/polymarket-execution-engine/actions/runs/26175786984` passed.

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Current release status remains `production-live-candidate`;
live submit/cancel and production deployment are still intentionally blocked.
