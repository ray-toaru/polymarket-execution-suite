# Tasks — post-v0.25.0

## v0.26 controlled canary decision-prep

- [x] Audit the current v0.26 canary decision-prep state against the latest
  `v0.25.0-evidence.20260521` baseline.
- [x] Identify that the existing `dist/pmx-canary-review-reviewed/` package is
  no-go review material but is not bound to the latest artifact and evidence
  manifest hashes.
- [x] Regenerate a v0.26 decision package bound to the current supplemental
  artifact SHA-256 and evidence manifest SHA-256.
- [x] Re-run the blocked armed rehearsal against the regenerated no-go package.
- [x] Automate v0.26 review-package generation with explicit artifact/evidence
  hash overrides and persistent blocked-rehearsal output.
- [x] Produce a reviewed release-decision JSON template for a future controlled
  canary attempt; default outcome must be no-go.
- [x] Bind any future canary review package to the released `v0.25.0` artifact
  SHA-256, evidence manifest SHA-256, and GitHub evidence run IDs.
- [x] Collect local review-package references for secret custody, no-go
  operator approval, manual alert routing, dashboard, rollback, and
  incident-runbook evidence without storing secret values in the repository.
  These references are review material only and do not claim production pager,
  production dashboard, or live readiness.
- [x] Add reference-only external-reference templates and validators for
  secret-custody/KMS, operator approval, alert routing, dashboard, rollback,
  incident runbook, and retry-policy references.
- [x] Add candidate-file validation and review-package wiring for externally
  collected references; unresolved placeholders are rejected unless explicitly
  running a local placeholder review.
- [x] Add or refresh validation that rejects stale, expired, mismatched, or
  partial canary approval references before any live-submit feature path can be
  armed.
- [x] Automate the blocked real-funds canary rehearsal package: a complete
  review package plus `--armed` CLI invocation remains blocked by a `no_go`
  adapter release decision before posting or remote side effects.
- [x] Re-run the execution-engine full current gates and root integration CI
  after decision-package, preflight, and review-package changes. Local
  `validation/run_current_gates.sh` passed with PostgreSQL enabled, execution
  engine CI `26216163754` passed, and root integration CI `26216163302` passed.
- [x] Keep the release decision explicit that live submit, live cancel,
  production deployment, and actual real-funds canary fill remain blocked unless
  a later reviewed release decision changes that boundary.
- [x] Record the current v0.26 controlled-canary go/no-go review as `no_go`,
  with required external approval evidence listed before any future transition
  to `go`.

## Completed in governance cleanup

- [x] Move stale root gate/validation notes to `docs/archive/`.
- [x] Move historical evidence and validation logs to archive directories.
- [x] Add canonical current evidence manifest path.
- [x] Add docs/evidence governance guard.
- [x] Add release package exclusions for historical docs/evidence.
- [x] Tighten public lifecycle payload schema to a redacted envelope.
- [x] Make pre-live degraded worker status fail closed in policy.

## Required current gates

Latest local full-gate run: passed via
`polymarket-execution-engine/validation/run_current_gates.sh`; current evidence
is under `polymarket-execution-engine/evidence/current/`.

- [x] `cargo fmt --check`
- [x] `cargo check --workspace --locked`
- [x] `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`
- [x] Rust tests
- [x] PostgreSQL migration/store/API E2E with `PMX_TEST_DATABASE_URL`
- [x] SDK adapter/spike checks and tests
- [x] Credentialed non-trading smoke refreshed in current canonical evidence
- [x] Sign-only dry-run refreshed in current canonical evidence

## Still intentionally blocked

- [ ] Live submit
- [ ] Live cancel
- [ ] Production deployment
- [ ] Actual real-funds canary fill

## Real-funds canary program readiness

- [x] Local CLI defaults to dry-run and is available only with the `live-submit` feature
- [x] Automatic market selection uses official SDK read-only data and fails closed on missing/unsafe data
- [x] Armed mode requires explicit env/config/approval/artifact/evidence gates
- [x] Current evidence records program readiness without actual posting
- [x] Dry-run market discovery reports aggregate safe-market diagnostics without
  exposing token identifiers or signing material
- [x] Armed mode requires a reviewed release-decision JSON bound to the same
  artifact and evidence hashes as the approval
- [x] Local review package generation produces review-only material, not an
  armed approval
- [x] Hermes can build blocked canary readiness reports from references under
  the `hm-pdp-test` profile without signing or CLOB access

## P1 canary-prep evidence

- [x] Canary readiness drill
- [x] Canary blocked drill
- [x] Canary rehearsal drill
- [x] Canary preflight structured evidence
- [x] Negative preflight scenarios fail closed

## P3 productionization evidence scaffold

- [x] Production operations drill included in current gates
- [x] Manifest section `production_operations_validation`
- [x] Secret custody, deployment, rollback, incident, alerting/SLO, retention,
  risk-limit, and SDK breakage controls represented as local evidence
- [x] Drill asserts no live submit, no live cancel, no remote side effects, and
  no production-ready claim
- [x] Production authorization block drill included in current gates
- [x] Partial live/prod gate combinations fail closed without a reviewed release
  decision
- [x] Production audit export drill included in current gates
- [x] Local audit export evidence preserves trace/digest/ref metadata without
  exporting sensitive signing material
- [x] Production dependency breakage drill included in current gates
- [x] SDK pin, lockfiles, sign-only regression evidence, compatibility review,
  rollback plan, and safe downgrade path are bound in current evidence
- [x] Production deployment preflight drill included in current gates
- [x] Artifact SHA-256, artifact sidecar, evidence sidecar, manifest hash, and
  migration evidence are verified while deployment remains blocked
- [x] Single-host limited deployment templates added for `pmx-api` and dry-run
  canary runner with fail-closed systemd/env defaults; current evidence records
  `single_host_deployment_validation=pass` without enabling live submit, live
  cancel, production deployment, or real-funds canary execution
- [x] Single-host canary candidate package preflight added; current evidence
  records `single_host_canary_candidate_validation=pass` for a `no_go`,
  dry-run-only candidate package bound to the release artifact and evidence
  manifest
- [x] Single-host temporary `go` candidate drill added; current evidence records
  `single_host_go_candidate_validation=pass`, proves no `go` decision file is
  committed, and confirms missing reviewed release decision still blocks armed
  execution
- [x] Production secret custody drill included in current gates
- [x] Sensitive environment values are checked absent from logs, manifest, and
  package artifact without printing the values
- [x] Production monitoring/SLO drill included in current gates
- [x] Required alert signals are represented and safety SLO/error budget states
  cannot auto-enable live submit
- [x] Production incident response drill included in current gates
- [x] Remote-unknown, cancel-failure, SDK-failure, PostgreSQL, geoblock,
  low-resource, and degraded-worker incidents fail closed with evidence
  preserved
- [x] Production rollback/downgrade drill included in current gates
- [x] SDK, remote-unknown, PostgreSQL, geoblock, kill-switch, and recovery
  states downgrade to sign-only, cancel-only, or read-only without auto
  re-enabling live submit
- [x] Production risk-limits drill included in current gates
- [x] Account/market whitelists, per-order/per-day/exposure caps, operator
  threshold, remote-unknown freeze, stale-market-data, and geoblock controls
  remain fail-closed
- [x] Production config-profile drill included in current gates
- [x] Conservative defaults keep live submit/cancel disabled and require explicit
  enablement, caps, operator approval, and isolated canary profile behavior
- [x] Production release-decision guard included in current gates
- [x] Current release decision does not claim production-ready, live-ready, or
  validated-release status
- [x] Controlled live canary prep drill included in current gates
- [x] Canary prep gates are represented locally while live submit, live cancel,
  posting, cancelling, and remote side effects remain blocked
- [x] External secret-provider/KMS preflight included in current gates
- [x] Secret-provider, rotation, and break-glass references are required before
  secret custody can be considered externally ready
- [x] External operator-approval preflight included in current gates
- [x] Approval id/hash/ticket, approver, expiry, scope, dual-control,
  replay-block, and expiry-enforcement signals are required before approval can
  be considered externally ready
- [x] External alert-routing/pager preflight included in current gates
- [x] Alert provider, route, pager policy, dashboard, alert-test, runtime,
  reconcile, remote-unknown, SDK, audit, and pager-ack signals are required
  before alerting can be considered externally ready
- [x] Production preflight example config added and included in release package
- [x] Production preflight config guard included in current gates
- [x] Preflight config is schema-versioned, reference-only, and checked for
  forbidden sensitive keys/values before external preflight checks can mark
  readiness
- [x] Positive production preflight fixture added and validated
- [x] Negative sensitive-key production preflight fixture added and rejected
  without logging the fixture secret value
- [x] Production preflight config fixture drill included in current gates and
  evidence manifest
- [x] Production preflight baseline/candidate config diff review added
- [x] Config diff summary reports changed field paths and config SHA-256 hashes
  only, without full reference values or secret values
- [x] Sensitive-key candidate config is rejected without logging the fixture
  secret value
- [x] Deployment preflight verifies the current config diff-review manifest
  section before deployment remains blocked
- [x] Deployment preflight verifies the `64` diff-review log SHA-256 before
  deployment remains blocked
- [x] Runtime heartbeat worker placeholder replaced with a non-trading
  sink-driven heartbeat loop and compatibility wrapper
- [x] Guarded real-funds canary preflight implemented and included in current
  gates
- [x] Real-funds canary approval fixture binds scope, artifact hash, evidence
  manifest hash, FOK limit-fill style, and 1 USD / 5 USD caps
- [x] Current evidence records `real_funds_canary_preflight_validation=pass`
  while live submit, live cancel, posting, and remote side effects remain
  disabled
- [x] Real-funds canary lifecycle closure implemented for local run
  persistence, idempotency replay/conflict, remote-unknown freeze escalation,
  and simulated reconcile without live submit, live cancel, posting, or remote
  side effects
