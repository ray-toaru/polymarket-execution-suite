# Tasks — v0.25.0

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
- [x] Credentialed non-trading smoke, explicitly enabled
- [x] Sign-only dry-run, explicitly enabled

## Still intentionally blocked

- [ ] Live submit
- [ ] Live cancel
- [ ] Production deployment

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
- [x] Production secret custody drill included in current gates
- [x] Sensitive environment values are checked absent from logs, manifest, and
  package artifact without printing the values
- [x] Production monitoring/SLO drill included in current gates
- [x] Required alert signals are represented and safety SLO/error budget states
  cannot auto-enable live submit
