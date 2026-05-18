# Tasks — v0.24.0

## Completed in governance cleanup

- [x] Move stale root gate/validation notes to `docs/archive/`.
- [x] Move historical evidence and validation logs to archive directories.
- [x] Add canonical current evidence manifest path.
- [x] Add docs/evidence governance guard.
- [x] Add release package exclusions for historical docs/evidence.
- [x] Tighten public lifecycle payload schema to a redacted envelope.
- [x] Make pre-live degraded worker status fail closed in policy.

## Required current gates

- [ ] `cargo fmt --check`
- [ ] `cargo check --workspace --locked`
- [ ] `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`
- [ ] Rust tests
- [ ] PostgreSQL migration/store/API E2E with `PMX_TEST_DATABASE_URL`
- [ ] SDK adapter/spike checks and tests
- [ ] Credentialed non-trading smoke, if explicitly enabled
- [ ] Sign-only dry-run, if explicitly enabled

## Still intentionally blocked

- [ ] Live submit
- [ ] Live cancel
- [ ] Production deployment
