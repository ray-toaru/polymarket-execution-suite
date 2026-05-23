# Design decision record

Status: current through v0.27 source-candidate development.

## DDR-001: Two independent projects

Accepted. `hermes-polymarket-executor-adapter` is the Python
Hermes-compatible executor adapter. `polymarket-execution-engine` remains the
standalone Rust execution plane.

## DDR-002: Execution plane owns funds-moving authority

Accepted. The Hermes adapter must not sign, post, cancel, hold execution truth,
or receive raw signed order material.

## DDR-003: Server-authoritative execution API

Accepted. The API should prefer executor-owned IDs and stored object graph validation over trusting full client-supplied execution objects.

## DDR-004: Official SDK-first adapter strategy

Accepted. Future live CLOB interaction should use the official Polymarket Rust SDK through isolated adapter crates. REST self-signing is not the primary route.

## DDR-005: Live submit and live cancel remain disabled

Accepted. Live submit/cancel require compile-time feature gates, explicit runtime opt-in, kill-switch policy, healthy runtime workers, PostgreSQL lifecycle evidence, audit redaction, reconciliation drills, and rollback evidence.

## DDR-006: Evidence must be canonical and artifact-bound

Accepted. Current release evidence must live under `polymarket-execution-engine/evidence/current/` with a manifest that records gate status, log paths, log hashes, provenance, and artifact hash when available. Historical evidence must be archived and excluded from normal release packaging.

## DDR-007: Controlled real-funds canary requires bound human-reviewed market input

Accepted for the controlled-canary line. The execution engine may consume an
externally prepared candidate market file only when its SHA-256 is bound into
the approval and reviewed release decision, and the candidate explicitly
declares BUY/GTC post-only plus an external human review reference.

## DDR-008: Components may version independently

Accepted. v0.26.x was kept as a coordinated suite line, so the root suite,
adapter, and execution engine shared the same version. Future development does
not require permanent lockstep versions. The execution engine versions executor
API, state machine, schema, SDK/gateway, and live-boundary changes; the Hermes
adapter versions client/tool compatibility with executor API contracts; the
suite versions pinned component combinations and evidence.
