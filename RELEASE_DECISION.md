# Release Decision — v0.25.0 shadow-ready SDK sign-only baseline

## Decision

Status: `shadow-ready SDK sign-only candidate`

Allowed final statuses for this batch:

- `validated source candidate`
- `shadow-ready SDK sign-only candidate`
- `not promotable`

Current decision: `shadow-ready SDK sign-only candidate`

## Scope

This decision applies to the integration repository at the pinned submodule
revisions:

```text
hermes-polymarket-control: bb16582e299f9e6f8da6044226e33900c4e2459d
polymarket-execution-engine: 69528924a9228ccc5262322ca64468e97a625648
```

The integration repository commit containing this decision pins those submodule
revisions. The root commit is intentionally not embedded here because editing
this file changes that commit hash.

This source includes Hermes canary readiness reference reporting under the
`hm-pdp-test` profile, aggregate-only real-funds canary dry-run diagnostics,
review-package generation, and a reviewed release-decision JSON gate for any
future armed canary. The refreshed current evidence passed PostgreSQL under
explicit local prerequisites and passed credentialed non-trading/sign-only
dry-run sections under explicit local env gates; it still does not authorize
production, live submit, live cancel, or real-funds order placement.

The target is promotion of the v0.25.0 shadow-ready SDK sign-only baseline. This batch does not introduce
live trading capability.

## GitHub CI boundary

The GitHub CI boundary now follows the repository ownership model:

- `polymarket-execution-suite` owns integration, release hygiene, packaging, and
  artifact validation only.
- `hermes-polymarket-control` owns Python control-plane tests and the no-secret
  boundary.
- `polymarket-execution-engine` owns Rust locked checks, PostgreSQL gates,
  current gates, SDK adapter checks, and the manual `credentialed-sdk`
  workflow.

Latest verified GitHub Actions runs for this decision:

```text
polymarket-execution-suite ci: 26206286587, success
polymarket-execution-engine ci: 26206281885, success
```

The `credentialed-sdk` environment exists in `polymarket-execution-engine`; the
integration repository has no Polymarket credential environment. Current local
canonical evidence refreshed authenticated non-trading smoke and sign-only
dry-run with explicit env gates. Secret values are not recorded in this
decision.

## Required evidence

- Rust fmt/check/clippy/tests pass.
- PostgreSQL migration, repository tests, and API E2E pass.
- SDK adapter tests pass.
- Sign-only dry-run is either passed in a credentialed safe environment or explicitly skipped with reason.
- Credentialed non-trading smoke is either passed in a safe environment or explicitly skipped with reason.
- Audit redaction, runtime degraded policy, and PG sign-only lifecycle concurrency risks have direct evidence.
- Release artifact hash is bound to `polymarket-execution-engine/evidence/current/manifest.json`.

## Prohibited promotion claims

- Do not claim production readiness.
- Do not claim live-trading readiness.
- Do not claim live submit or live cancel availability.
- Do not cite archived evidence as current evidence.

## Promotion outcome

Final status: `shadow-ready SDK sign-only candidate`

Rationale:

- Rust workspace, PostgreSQL migration/store/API E2E, SDK adapter/spike, SDK
  regression, credentialed non-trading smoke, sign-only dry-run, local static,
  contract, release artifact, and governance gates passed in this environment.
- The current local refresh at
  `polymarket-execution-engine: 69528924a9228ccc5262322ca64468e97a625648`
  passed the current no-live gate chain, including PostgreSQL and credentialed
  SDK sections under explicit local env gates.
- Shadow execution, reconciliation drift, rollback/kill-switch, migration drift,
  live canary readiness, blocked live canary, and productionization guard gates
  passed.
- Runtime worker loop closure, order lifecycle divergence classification, SDK
  standard sign-only plan, live canary prep, and production hardening spec are
  included in the pinned execution-engine source.
- Runtime heartbeat worker scaffolding now uses a non-trading heartbeat loop
  with an injected persistence sink instead of a discard-only placeholder.
- Read-only remote reconcile reader, continuous runtime worker tick entry,
  explicit SDK sign-only default path, fail-closed live canary defaults, and
  production evidence controls are included in the pinned execution-engine
  source.
- Canary drill validation now binds the public release gate entrypoint
  `validation/run_current_gates.sh` to the current implementation gate chain.
- Current gate-chain validation is centralized for lifecycle, migration, SDK,
  observability, canary, and production guard checks.
- The active gate implementation is version-neutral
  `validation/run_current_gates_impl.sh`; `validation/run_current_gates.sh`
  remains the public entrypoint.
- Standard sign-only mapping now has explicit non-posting MARKET-order coverage
  in the SDK adapter regression evidence.
- Live canary preflight now has an independent manifest section with structured
  local-ready and negative fail-closed scenarios; it still records no live
  submit, no live cancel, and no remote trading side effects.
- Production operations drill evidence is included as an independent manifest
  section for secret custody, deployment preflight, rollback, incident,
  alerting/SLO, audit retention, risk-limit, and SDK breakage controls; it
  still records no live submit, no live cancel, and no production-ready claim.
- Production authorization block evidence is included as an independent
  manifest section proving partial live/prod gates remain fail-closed without a
  reviewed release decision.
- Production audit export evidence is included as an independent manifest
  section proving exported local audit records keep trace/digest/ref metadata
  and exclude private keys, CLOB secrets, raw signed payloads, raw signatures,
  and signed order envelopes.
- Production dependency breakage evidence is included as an independent
  manifest section proving the SDK remains exactly pinned, adapter/spike
  lockfiles are present, sign-only regression evidence is bound, and SDK
  breakage downgrades to sign-only/read-only with live submit frozen.
- Production deployment preflight evidence is included as an independent
  manifest section proving the release artifact SHA-256 sidecar, evidence
  sidecar, evidence manifest hash, and migration evidence can be verified while
  deployment remains blocked.
- Production deployment preflight evidence now also verifies the current
  production config diff-review manifest section and the `64` diff-review log
  SHA-256 before deployment remains blocked.
- Production secret custody evidence is included as an independent manifest
  section proving sensitive environment values observed by validation are absent
  from logs, manifest, and release artifact, with `.env` excluded from the
  package.
- Production monitoring/SLO evidence is included as an independent manifest
  section proving required alert signals are represented and safety SLO or error
  budget states cannot auto-enable live submit.
- Production incident response evidence is included as an independent manifest
  section proving remote-unknown, cancel-failure, SDK-failure, PostgreSQL,
  geoblock, low-resource, and degraded-worker incidents fail closed with
  evidence preserved and no remote side effects.
- Production rollback/downgrade evidence is included as an independent manifest
  section proving SDK, remote-unknown, PostgreSQL, geoblock, kill-switch, and
  recovery states downgrade to sign-only, cancel-only, or read-only modes
  without auto re-enabling live submit.
- Production risk-limit evidence is included as an independent manifest section
  proving account whitelist, market whitelist, per-order cap, per-day cap,
  exposure cap, operator threshold, remote-unknown freeze, stale-market-data,
  and geoblock controls remain fail-closed.
- Production config-profile evidence is included as an independent manifest
  section proving conservative defaults keep live submit/cancel disabled,
  production-ready false, kill switch closed, per-account/per-market enablement
  required, caps required, operator approval required, and canary profile
  isolated.
- Production release-decision guard evidence is included as an independent
  manifest section proving the current release decision does not claim
  production-ready, live-ready, or validated-release status.
- Controlled live canary prep evidence is included as an independent manifest
  section proving compile/env/config/operator/whitelist/cap/idempotency/
  reservation/reconcile/fallback gates can be represented while live submit,
  live cancel, posting, cancelling, and remote side effects remain blocked
  without a reviewed release decision.
- External secret-provider preflight evidence is included as an independent
  manifest section proving KMS/secret-provider, rotation, and break-glass
  references are represented as a contract while missing external references
  keep `external_secret_custody_ready=false` and live submit/cancel blocked.
- External operator-approval preflight evidence is included as an independent
  manifest section proving approval id/hash/ticket/approver/expiry/scope,
  dual-control, replay-block, and expiry-enforcement signals are required while
  missing references keep `operator_approval_ready=false` and live submit/cancel
  blocked.
- External alert-routing preflight evidence is included as an independent
  manifest section proving alert provider, route, pager policy, dashboard, alert
  test evidence, runtime/reconcile/remote-unknown/SDK/audit alert signals, and
  pager acknowledgement are required while missing references keep
  `alerting_ready=false` and live submit/cancel blocked.
- Production preflight config evidence is included as an independent manifest
  section proving `config/production-preflight.example.json` is schema-versioned,
  reference-only, free of forbidden sensitive keys/values, and usable by the
  external secret-provider, operator-approval, and alert-routing preflight
  checks without enabling live submit or live cancel.
- Production preflight config fixture evidence is included as an independent
  manifest section proving a positive fixture can drive external
  secret-provider, operator-approval, and alert-routing readiness to `true`
  while live submit/cancel remain blocked, and a negative fixture containing a
  forbidden sensitive key is rejected by field path without logging the fixture
  secret value.
- Production preflight config diff-review evidence is included as an
  independent manifest section proving baseline/candidate config changes are
  summarized by field paths and SHA-256 hashes only, valid reference-only
  changes pass, and a candidate containing a forbidden sensitive key is rejected
  without logging the fixture secret value.
- Shadow execution evidence now runs by default in the current gate, and
  observability evidence is bound as an explicit manifest section.
- Credentialed gates used explicit opt-in flags and existing local `.env`
  credentials; no credential values are recorded in evidence.
- Authenticated non-trading smoke and sign-only dry-run passed in current local
  canonical evidence. They do not authorize live submit, live cancel, or
  real-funds canary execution.
- PostgreSQL gates used a local PostgreSQL 16 instance with
  `PMX_TEST_DATABASE_URL`.
- Current source state remains pre-live and fail-closed for live submit/cancel.
- `PMX_ALLOW_LIVE_SUBMIT=0` and `PMX_ALLOW_LIVE_CANCEL=0` during validation;
  blocked canary evidence records `posted=false`, `cancelled=false`, and
  `remote_side_effects=false`.
- Real-funds canary preflight is implemented and validated, but no real-funds
  order was submitted in this batch. Evidence records
  `real_funds_canary_allowed=false`, `posted=false`, and
  `remote_side_effects=false` during normal gates.
- Real-funds canary lifecycle closure is implemented locally with persisted run
  records, idempotency replay/conflict handling, remote-unknown freeze
  escalation, and simulated reconcile. It does not authorize live submit,
  live cancel, or real-funds order placement.
- Real-funds canary dry-run market discovery now reports aggregate-only
  diagnostics, armed mode requires a reviewed release-decision JSON bound to the
  same artifact/evidence hashes as the approval, and local review-package
  generation is included in current evidence without creating armed approval.
- Hermes can produce blocked canary readiness reference reports under
  `hm-pdp-test`; it still cannot sign, submit, cancel, hold executor database
  credentials, or call Polymarket CLOB.

## Evidence references

Current evidence:

- GitHub integration CI:
  `ray-toaru/polymarket-execution-suite/actions/runs/26206286587`
- GitHub execution-engine CI:
  `ray-toaru/polymarket-execution-engine/actions/runs/26206281885`
- Historical GitHub credentialed SDK audit context:
  `ray-toaru/polymarket-execution-engine/actions/runs/26175786984`
- Environment: `polymarket-execution-engine/evidence/current/environment.json`
- Manifest: `polymarket-execution-engine/evidence/current/manifest.json`
- Manifest SHA-256:
  `4c53dd9b7abf14184df37932ba5eb645c942f75f075d31f40b587c8b612c7ffa`
- Logs: `polymarket-execution-engine/evidence/current/logs/`
- Real-funds canary preflight log:
  `polymarket-execution-engine/evidence/current/logs/65-real-funds-canary-preflight.log`
- Real-funds canary lifecycle log:
  `polymarket-execution-engine/evidence/current/logs/66-real-funds-canary-lifecycle-drill.log`
- Artifact SHA-256: recorded outside the zip in
  `polymarket-execution-suite-v0.25.0.zip.sha256` and
  `polymarket-execution-suite-v0.25.0.zip.evidence.json`
- The release artifact sidecars must be regenerated after this document update
  during the pre-publish check; the external sidecars are the artifact hash
  source of truth because the in-archive files cannot self-bind the containing
  zip hash.

## Explicit non-claims

This is not production-ready and not live-canary-approved. Production promotion
still requires reviewed secret-manager/KMS/HSM controls, deployment and rollback
runbooks, observability, retention, account and market risk limits, actual
real-funds canary execution evidence, and an explicit future release decision.
