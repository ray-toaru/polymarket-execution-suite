# Canary and Production Roadmap

Current baseline: `v0.25.0` is a shadow-ready SDK sign-only candidate. Live
submit, live cancel, and production deployment remain blocked until a later
reviewed release decision changes that boundary with current evidence.

## P0: Freeze the v0.25 baseline

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

## P1: v0.26 canary-prep

Status: active next source batch.

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

Status: blocked until P1 exits cleanly and a reviewed release decision authorizes
the attempt.

Goal: validate a tiny real side-effect path under hard runtime, account, market,
amount, approval, kill-switch, and reconciliation controls.

Minimum gates before any live attempt:

- Compile feature, environment, and config live-submit gates all enabled for the
  canary build only.
- Kill switch open and reversible.
- Runtime worker, geoblock, resource, and reconcile state healthy.
- Repository reservation and idempotency key already persisted.
- Account and market whitelists match the operator-approved plan.
- Per-order and per-day caps are enforced.
- Cancel-only fallback and post-submit reconcile path are ready.

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

Exit criteria:

- Live capability can be enabled gradually by account, market, amount, and
  strategy.
- Default behavior remains conservative.
- Abnormal runtime, SDK, PostgreSQL, or remote states force a safe downgrade.
