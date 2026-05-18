# Roadmap — v0.25.0 shadow-ready SDK sign-only baseline

## Immediate next validation

1. Run local/static checks.
2. Generate a clean package.
3. Run full Rust/SDK/PostgreSQL gates externally against the final package.
4. Bind current evidence to `evidence/current/manifest.json` and the final artifact SHA-256.

## Next source-hardening items

1. Sign-only lifecycle concurrency and replay stress tests.
2. Runtime worker heartbeat leases and real worker persistence.
3. Persistent cancel/reconcile lifecycle beyond non-live placeholders.
4. Audit query pagination and typed per-event payload bodies.
5. Shadow dry-run and rollback drills.

## Still blocked

Live submit, live cancel, and production deployment remain blocked in v0.25.0 until a later release has canary/production evidence and an explicit release decision.
