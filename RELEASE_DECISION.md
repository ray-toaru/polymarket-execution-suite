# Release Decision — v0.25.0 shadow-ready SDK sign-only baseline

## Decision

Status: `shadow-ready SDK sign-only candidate`

Allowed final statuses for this batch:

- `validated source candidate`
- `shadow-ready SDK sign-only candidate`
- `not promotable`

Current decision: `shadow-ready SDK sign-only candidate`

## Scope

This decision applies to the integration repository at the pinned submodule revisions:

```text
hermes-polymarket-control: f0680017a37d5647a0abd2e44e0642a4b7b762da
polymarket-execution-engine: d9b8f77a5623336c775f777bf17cc11b584ba235
```

The target is promotion of the v0.25.0 shadow-ready SDK sign-only baseline. This batch does not introduce
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

Final status: `shadow-ready SDK sign-only candidate`

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
- Read-only remote reconcile reader, continuous runtime worker tick entry,
  explicit SDK sign-only default path, fail-closed live canary defaults, and
  production evidence controls are included in the pinned execution-engine
  source.
- Shadow execution evidence now runs by default in the current gate, and
  observability evidence is bound as an explicit manifest section.
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
  `polymarket-dual-project-v0.25.0.zip.sha256` and
  `polymarket-dual-project-v0.25.0.zip.evidence.json`
- Current artifact SHA-256:
  recorded in the external sidecars generated with the artifact

## Explicit non-claims

This is not production-ready and not live-canary-approved. Production promotion
still requires reviewed secret-manager/KMS/HSM controls, deployment and rollback
runbooks, observability, retention, account and market risk limits, real live
canary evidence, and an explicit future release decision.
