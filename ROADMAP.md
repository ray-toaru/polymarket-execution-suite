# Roadmap — v0.23.0 pre-live

## Immediate next validation

1. Run local/static checks.
2. Generate a clean package.
3. Run full Rust/SDK/PostgreSQL gates externally against the final package.
4. Bind external evidence to `evidence/current/manifest.json` and the final artifact SHA-256.

## Next source-hardening items

1. Sign-only lifecycle concurrency and replay stress tests.
2. Runtime worker heartbeat leases and real worker persistence.
3. Persistent cancel/reconcile lifecycle beyond non-live placeholders.
4. Audit query pagination and typed per-event payload bodies.
5. Shadow dry-run and rollback drills.

## Still blocked

Live submit, live cancel, and production deployment remain blocked until the evidence above exists and passes.
