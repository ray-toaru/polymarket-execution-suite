# Canary and Production Roadmap

Current source phase: `v0.28.0` is a production-live-candidate. Live submit,
live cancel, and production deployment remain blocked until a later reviewed
release decision changes that boundary with current evidence.

## P0: Preserve the v0.25 baseline while advancing v0.26

Status: current baseline.

Scope:

- Keep release metadata, package output, and `evidence/current/manifest.json`
  aligned after material changes.
- Preserve SDK sign-only behavior as the default construction path.
- Keep Hermes outside the signing boundary and outside direct CLOB access.
- Keep live submit and live cancel disabled by default.

Pause conditions:

- Required current gates fail.
- Evidence cannot be bound to the packaged artifact.
- Any path exposes private keys, CLOB secrets, raw signed payloads, raw
  signatures, or signed order envelopes.

## P1: canary-prep evidence

Status: satisfied by the `v0.25.0` shadow-ready SDK sign-only baseline.

Goal: make the future live canary sequence auditable without enabling live side
effects.

Required deliverables:

- Current gate entrypoint remains `polymarket-execution-engine/validation/run_current_gates.sh`.
- Canary readiness, blocked, and rehearsal drills are included in current
  evidence.
- Canary preflight is included as its own current evidence section with
  structured local-ready and negative fail-closed scenarios.
- Canary prep state records whitelist checks, caps, operator approval,
  reservation/idempotency readiness, reconcile readiness, cancel-only fallback,
  and remote-unknown freeze.
- Remote unknown freezes further submit attempts.
- Cancel-only fallback is modelled and validated before any future canary.
- Validation output proves no live submit and no live cancel occurred.

Not allowed in P1:

- Calling `post_order` or equivalent live submit endpoints.
- Calling live cancel endpoints.
- Treating a blocked rehearsal as canary success.
- Claiming production-ready status.

Exit criteria:

- Required current gates pass.
- Canary drill logs are present in `evidence/current/logs/`.
- Manifest records the canary drill and preflight statuses and log hashes.
- Release decision remains explicit that live side effects are blocked.

## P2: Controlled live canary

Status: next governed phase is canary decision-prep. The real-funds canary
preflight scaffold is implemented and validated; actual remote canary fill
remains blocked until a reviewed release decision and local approval file
authorize the attempt.

`v0.26` should prepare and verify the decision package for a possible future
controlled canary. It should not treat the released `v0.25.0` credentialed
non-trading/sign-only evidence as approval to place a real order.

Current v0.26 audit status is recorded in `CANARY_DECISION_PREP_AUDIT.md`.
The existing `dist/pmx-canary-review-reviewed/` package remains no-go review
material and proves blocked rehearsal behavior, but it is not bound to the
latest supplemental artifact and evidence manifest hashes. A regenerated
decision package is required before any future canary review can proceed.

Goal: validate a tiny real side-effect path under hard runtime, account, market,
amount, approval, kill-switch, and reconciliation controls.

Minimum gates before any live attempt:

- Compile feature, environment, and config live-submit gates all enabled for the
  canary build only.
- `PMX_ALLOW_REAL_FUNDS_CANARY=1` and `allow_real_funds_canary=true` enabled
  only for the canary process.
- Local approval file binds scope `REAL_FUNDS_CANARY`, `GTC_LIMIT_POST_ONLY_CANCEL`, the
  release artifact SHA-256, and the current evidence manifest SHA-256.
- Per-order cap is `1` USD and per-day cap is `5` USD for the first canary.
- Kill switch open and reversible.
- Runtime worker, geoblock, resource, and reconcile state healthy.
- Repository reservation and idempotency key already persisted.
- Account and market whitelists match the operator-approved plan.
- Per-order and per-day caps are enforced.
- Cancel-only fallback and post-submit reconcile path are ready.

Current validated preflight:

- `real_funds_canary_preflight_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `65-real-funds-canary-preflight.log` proves normal gates keep
  `live_submit_allowed=false`, `live_cancel_allowed=false`,
  `real_funds_canary_allowed=false`, `posted=false`, and
  `remote_side_effects=false`.
- The only adapter `post_order` call site is the guarded real-funds canary FOK
  limit-fill path behind the `live-submit` feature and explicit preconditions.

Pause conditions:

- Remote unknown.
- Reconcile worker unhealthy.
- Cancel failure without a clear operator-required path.
- Any evidence gap in the canary chain.

## P3: v0.27 productionization

Status: operations-control evidence scaffold active; promotion remains blocked
until P2 canary evidence is reviewed.

Goal: move from controlled canary to limited production with operational
controls, not broad default live trading.

Required deliverables:

- Secret manager or equivalent production-grade secret handling.
- Production config profile with conservative defaults.
- Deployment, rollback, and incident runbooks.
- Alerting, dashboards, SLOs, and error-budget policy.
- Audit export and retention policy.
- Account, market, and strategy risk limits.
- Dependency update and SDK upstream breakage playbooks.
- Automatic downgrade paths to sign-only, cancel-only, or read-only modes.

Current evidence coverage:

- `production_operations_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `46-production-operations-drill.log` records no live submit, no live cancel,
  no remote side effects, and no production-ready claim.
- `production_authorization_block_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `47-production-authorization-block-drill.log` proves partial live/prod gates
  remain fail-closed without a reviewed release decision.
- `production_audit_export_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `48-production-audit-export-drill.log` proves local audit export keeps
  trace/digest/ref metadata while excluding private keys, CLOB secrets, raw
  signed payloads, raw signatures, and signed order envelopes.
- `production_dependency_breakage_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `49-production-dependency-breakage-drill.log` proves the SDK remains exactly
  pinned, lockfiles are present, sign-only regression evidence is bound, and SDK
  breakage downgrades to sign-only/read-only with live submit frozen.
- `production_deployment_preflight_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `50-production-deployment-preflight-drill.log` proves artifact SHA-256,
  artifact sidecar, evidence sidecar, evidence manifest hash, and migration
  evidence can be verified while deployment remains blocked.
- `single_host_deployment_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `69-single-host-deployment-drill.log` proves the single-host deployment
  templates for `pmx-api` and the canary runner remain fail-closed, dry-run
  only, reference-only for local custody, and do not authorize production or
  live side effects.
- `single_host_canary_candidate_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `70-single-host-canary-candidate-drill.log` proves the single-host canary
  candidate package can be generated and preflighted against the dry-run runner
  while the release decision remains `no_go` and no live side effects are
  authorized.
- `single_host_go_candidate_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `71-single-host-go-candidate-drill.log` proves a temporary `go` adapter
  release-decision candidate can be generated for operator review without
  committing a `go` file, and that missing reviewed release-decision input still
  blocks armed execution.
- `50-production-deployment-preflight-drill.log` also verifies
  `production_preflight_config_diff_review_validation` and the
  `64-production-preflight-config-diff-review.log` SHA-256 before deployment
  remains blocked.
- `production_secret_custody_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `51-production-secret-custody-drill.log` proves sensitive environment values
  observed by validation are absent from logs, manifest, and package artifact,
  with `.env` excluded from the release zip.
- `production_monitoring_slo_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `52-production-monitoring-slo-drill.log` proves required alert/SLO signals are
  represented and safety SLO or error budget states cannot auto-enable live
  submit.
- `production_incident_response_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `53-production-incident-response-drill.log` proves remote-unknown,
  cancel-failure, SDK-failure, PostgreSQL, geoblock, low-resource, and
  degraded-worker incidents fail closed with evidence preserved and no remote
  side effects.
- `production_rollback_downgrade_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `54-production-rollback-downgrade-drill.log` proves SDK, remote-unknown,
  PostgreSQL, geoblock, kill-switch, and recovery states downgrade safely
  without auto re-enabling live submit.
- `production_risk_limits_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `55-production-risk-limits-drill.log` proves account/market whitelists,
  per-order/per-day/exposure caps, operator threshold, remote-unknown freeze,
  stale-market-data, and geoblock controls remain fail-closed.
- `production_config_profile_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `56-production-config-profile-drill.log` proves conservative production
  defaults keep live submit/cancel disabled, require explicit enablement,
  require caps and operator approval, and isolate canary profile behavior.
- `production_release_decision_guard_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `57-production-release-decision-guard.log` proves the release decision still
  does not claim production-ready, live-ready, or validated-release status.
- `live_canary_controlled_prep_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `58-live-canary-controlled-prep-drill.log` proves controlled canary prep
  gates can be represented locally while live submit, live cancel, posting,
  cancelling, and remote side effects remain blocked without a reviewed release
  decision.
- `external_secret_provider_preflight_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `59-external-secret-provider-preflight.log` proves the KMS/secret-provider,
  rotation, and break-glass contract is represented while missing external
  references keep secret custody not ready and live submit/cancel blocked.
- `external_operator_approval_preflight_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `60-external-operator-approval-preflight.log` proves approval id/hash/ticket,
  approver, expiry, scope, dual-control, replay-block, and expiry-enforcement
  signals are required while missing references keep approval not ready and live
  submit/cancel blocked.
- `external_alert_routing_preflight_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `61-external-alert-routing-preflight.log` proves alert provider, route, pager,
  dashboard, alert-test, runtime, reconcile, remote-unknown, SDK, audit, and
  pager-ack signals are required while missing references keep alerting not
  ready and live submit/cancel blocked.
- `production_preflight_config_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `62-production-preflight-config-guard.log` proves
  `config/production-preflight.example.json` is schema-versioned,
  reference-only, free of forbidden sensitive keys/values, and usable by the
  external preflight checks without enabling live submit/cancel.
- `production_preflight_config_fixture_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `63-production-preflight-config-fixture-drill.log` proves a positive fixture
  can drive external preflight readiness to true while live submit/cancel remain
  blocked, and a negative sensitive-key fixture is rejected without logging the
  fixture secret value.
- `production_preflight_config_diff_review_validation` is present in
  `polymarket-execution-engine/evidence/current/manifest.json`.
- `64-production-preflight-config-diff-review.log` proves baseline/candidate
  config changes are summarized by field paths and SHA-256 hashes only, valid
  reference-only changes pass, and a sensitive-key candidate is rejected without
  logging the fixture secret value.

Exit criteria:

- Live capability can be enabled gradually by account, market, amount, and
  strategy.
- Default behavior remains conservative.
- Abnormal runtime, SDK, PostgreSQL, or remote states force a safe downgrade.
