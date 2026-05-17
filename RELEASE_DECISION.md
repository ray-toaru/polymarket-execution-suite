# Release Decision — v0.23.1 validation-promotion

## Decision

Status: `shadow-ready candidate`

Allowed final statuses for this batch:

- `validated source candidate`
- `shadow-ready candidate`
- `not promotable`

Current decision: `shadow-ready candidate`

## Scope

This decision applies to the integration repository at the pinned submodule revisions:

```text
hermes-polymarket-control: f668365fa9246ed150713d19734b04fd5453ce9f
polymarket-execution-engine: f1a4fd9221ad5b008c656a82bc47f742c6eff9b4
```

The target is validation promotion of v0.23.x. This batch does not introduce
live trading capability.

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

Final status: `shadow-ready candidate`

Rationale:

- Rust workspace, PostgreSQL migration/store/API E2E, SDK adapter/spike, SDK
  regression, credentialed non-trading smoke, sign-only dry-run, local static,
  contract, release artifact, and governance gates passed in this environment.
- Shadow execution, reconciliation drift, rollback/kill-switch, migration drift,
  live canary readiness, and productionization guard gates passed.
- Credentialed gates used explicit opt-in flags and existing `.env` credentials; no credential values are recorded in evidence.
- Current source state remains pre-live and fail-closed for live submit/cancel.
- `PMX_ALLOW_LIVE_SUBMIT=0` and `PMX_ALLOW_LIVE_CANCEL=0` during validation;
  no live submit or live cancel evidence exists, and none is claimed.

## Evidence references

Current evidence:

- Environment: `polymarket-execution-engine/evidence/current/environment.json`
- Manifest: `polymarket-execution-engine/evidence/current/manifest.json`
- Logs: `polymarket-execution-engine/evidence/current/logs/`
- Artifact SHA-256: recorded outside the zip in
  `polymarket-dual-project-v0.23.0.zip.sha256` and
  `polymarket-dual-project-v0.23.0.zip.evidence.json`

## Explicit non-claims

This is not production-ready. Production promotion still requires reviewed
secret-manager/KMS/HSM controls, deployment and rollback runbooks, observability,
retention, account and market risk limits, live canary evidence, and an explicit
future release decision.
