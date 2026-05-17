# Implementation status — v0.23.0 source candidate

## Implemented source-level items

- Two-plane pre-live boundary: Python control plane + Rust execution plane.
- Server-authoritative execution service scaffold.
- PostgreSQL-backed store scaffolding for core execution data.
- Sign-only lifecycle API, store path, query path, and idempotency field.
- Runtime worker observation and heartbeat store scaffolding.
- Non-live cancel/reconcile lifecycle event recording.
- Lifecycle and admin audit query APIs.
- Redacted lifecycle payload envelope at public API/model level.
- v0.23 gate runner, static guards, version guard, and docs/evidence governance guard.

## Intentionally blocked

- Live submit.
- Live cancel.
- Production deployment.
- Python-side access to signing or CLOB secrets.
- Public exposure of raw signed payloads or signed order envelopes.

## Not proven in this local environment

- Rust format/check/clippy/tests.
- PostgreSQL migration/store/API E2E.
- SDK adapter/spike checks and tests.
- Credentialed non-trading smoke.
- Sign-only dry-run with real credentials.
