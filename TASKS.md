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
