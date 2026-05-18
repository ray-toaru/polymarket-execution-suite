# Roadmap — v0.25.0 shadow-ready SDK sign-only baseline

## Immediate next validation

1. Run local/static checks.
2. Generate a clean package.
3. Run full Rust/SDK/PostgreSQL gates externally against the final package.
4. Bind current evidence to `evidence/current/manifest.json` and the final artifact SHA-256.

## Next source-hardening items

1. Persistent cancel/reconcile lifecycle beyond non-live placeholders.
2. Audit query pagination and typed per-event payload bodies.
3. Shadow dry-run and rollback drills.

## Recently landed hardening

1. Sign-only lifecycle PostgreSQL concurrency and replay stress test for `client_event_id`, mismatched replay rejection, and terminal-state rejection.
2. Runtime heartbeat lease persistence proof: local heartbeat is written to `worker_health`, candidates are read back through `RuntimeWorkerStatusStore`, owner election is persisted to runtime observations, and both in-memory plus PostgreSQL-backed service tests cover the path.

## Still blocked

Live submit, live cancel, and production deployment remain blocked in v0.25.0 until a later release has canary/production evidence and an explicit release decision.
