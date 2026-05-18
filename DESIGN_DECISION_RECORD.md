# Design decision record — v0.24.0

## DDR-001: Two independent projects

Accepted. `hermes-polymarket-control` remains the Python control plane. `polymarket-execution-engine` remains the standalone Rust execution plane.

## DDR-002: Execution plane owns funds-moving authority

Accepted. The control plane must not sign, post, cancel, hold execution truth, or receive raw signed order material.

## DDR-003: Server-authoritative execution API

Accepted. The API should prefer executor-owned IDs and stored object graph validation over trusting full client-supplied execution objects.

## DDR-004: Official SDK-first adapter strategy

Accepted. Future live CLOB interaction should use the official Polymarket Rust SDK through isolated adapter crates. REST self-signing is not the primary route.

## DDR-005: Live submit and live cancel remain disabled

Accepted. Live submit/cancel require compile-time feature gates, explicit runtime opt-in, kill-switch policy, healthy runtime workers, PostgreSQL lifecycle evidence, audit redaction, reconciliation drills, and rollback evidence.

## DDR-006: Evidence must be canonical and artifact-bound

Accepted. Current release evidence must live under `polymarket-execution-engine/evidence/current/` with a manifest that records gate status, log paths, log hashes, provenance, and artifact hash when available. Historical evidence must be archived and excluded from normal release packaging.
