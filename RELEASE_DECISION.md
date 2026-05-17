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
hermes-polymarket-control: 0c9e3011252c5ffa2be41cdad6ae4cf6af54bf36
polymarket-execution-engine: cf37e89c54f69c6792ce4ee867467518d12061a5
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
  live canary readiness, blocked live canary, and productionization guard gates
  passed.
- Runtime worker loop closure, order lifecycle divergence classification, SDK
  standard sign-only plan, live canary prep, and production hardening spec are
  included in the pinned execution-engine source.
- Credentialed gates used explicit opt-in flags and existing `.env` credentials; no credential values are recorded in evidence.
- PostgreSQL gates used an isolated local PostgreSQL 16 instance on
  `localhost:55432`; the `.env` `PMX_DATABASE_URL` target on `localhost:5432`
  was not listening during validation.
- Current source state remains pre-live and fail-closed for live submit/cancel.
- `PMX_ALLOW_LIVE_SUBMIT=0` and `PMX_ALLOW_LIVE_CANCEL=0` during validation;
  blocked canary evidence records `posted=false`, `cancelled=false`, and
  `remote_side_effects=false`.

## Evidence references

Current evidence:

- Environment: `polymarket-execution-engine/evidence/current/environment.json`
- Manifest: `polymarket-execution-engine/evidence/current/manifest.json`
- Logs: `polymarket-execution-engine/evidence/current/logs/`
- Artifact SHA-256: recorded outside the zip in
  `polymarket-dual-project-v0.23.0.zip.sha256` and
  `polymarket-dual-project-v0.23.0.zip.evidence.json`
- Current artifact SHA-256:
  `e594e8bb63e0ce6cd7c717aac3b649172c86b1e494b8ed0ccb3d21e3acbd9d53`

## Explicit non-claims

This is not production-ready and not live-canary-approved. Production promotion
still requires reviewed secret-manager/KMS/HSM controls, deployment and rollback
runbooks, observability, retention, account and market risk limits, real live
canary evidence, and an explicit future release decision.
