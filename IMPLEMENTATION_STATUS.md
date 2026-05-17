# Implementation status — v0.23.1 validation-promotion

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
- Runtime worker loop/tick models for heartbeat lease, resource refresh,
  reconcile backlog, WebSocket liveness, geoblock, and worker crash recovery.
- Order lifecycle event query API and per-order correlation trace field.
- PostgreSQL migration ledger with checksum-bound forward migrations through
  `0003_order_event_trace`.

## Intentionally blocked

- Live submit.
- Live cancel.
- Production deployment.
- Python-side access to signing or CLOB secrets.
- Public exposure of raw signed payloads or signed order envelopes.

## Current validation evidence

The current canonical evidence manifest records passing full gates for Rust,
PostgreSQL, SDK, credentialed non-trading smoke, sign-only dry-run, release
artifact, and governance checks:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Current release status remains `shadow-ready candidate`; live submit/cancel and
production deployment are still intentionally blocked.
