# v0.23.1 validation-promotion plan

## Objective

Turn the current v0.23 source candidate into an auditable, repeatable promotion candidate. This batch is validation-only by default; it must not add live trading capability.

## P0: external validation closure

Run from the integration repository:

```bash
git submodule update --init --recursive
python scripts/collect_validation_environment.py > polymarket-execution-engine/evidence/current/environment.json
cd polymarket-execution-engine
PMX_INTEGRATION_ROOT="$(pwd)/.." ./validation/run_current_gates.sh
```

Required environment facts:

- OS and kernel.
- Python version.
- Rust version.
- Cargo version.
- PostgreSQL client/server version when available.
- Git commit and submodule revisions.
- SDK dependency lock hashes.

Completion criteria:

- All required gates pass.
- Every skipped gate has an explicit reason.
- Every log has a SHA-256 in the evidence manifest.
- The release artifact SHA-256 is bound in the evidence manifest.
- Live submit and live cancel remain blocked.

## P1: current design risks

Address only after P0 has produced real evidence.

- Audit payload redaction E2E: prove API, DB, and query paths do not expose private keys, CLOB secrets, raw signed payloads, raw signatures, or signed order envelopes.
- Runtime degraded policy: prove degraded, stale, unknown, and missing heartbeat/reconcile/resource-refresh states fail closed under the active policy.
- PG sign-only lifecycle concurrency: prove `client_event_id` idempotency, advisory locks, partial unique indexes, duplicate replay/conflict behavior, terminal state constraints, and `SIGNED_DRY_RUN` signed-ref limits.

## P2: release decision

Update `RELEASE_DECISION.md` after evidence is complete. The only allowed outcomes are:

- `validated source candidate`
- `shadow-ready candidate`
- `not promotable`

Do not use `production-ready` or `live-ready` for this batch.

## P3: Rust structure governance

Only start after P0/P1 pass or are explicitly closed as non-blocking.

Refactor order:

- Pure types, DTOs, and errors.
- Repository traits and PostgreSQL implementation.
- SDK adapter config, signer, transport, dry-run, and error mapping.

Each refactor must be behavior-preserving and followed by Rust gates.

## P4: future v0.24 direction

Do not start v0.24 until this batch is closed. Candidate v0.24 themes are shadow execution, reconciliation drills, rollback/kill-switch drills, and observability.

## Pause conditions

Pause feature work and fix validation if any of these occur:

- Rust gates fail.
- PG lifecycle concurrency tests fail.
- SDK adapter shows remote side-effect risk.
- Audit redaction E2E fails.
- Runtime degraded policy conflicts with docs or tests.
- Evidence manifest cannot bind the artifact hash.
