# Design decision record

Status: current through v0.28.0 production-live-candidate development.

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

## DDR-009: External independent review may compensate for missing platform enforcement

Accepted for the current private-repository constraint. When GitHub branch
protection or required-review enforcement is unavailable, the repository may
use a direct-main-push exception only when all of the following are true:

- the pushed state is bound to exact parent and submodule commits;
- CI passes for those exact commits;
- external independent review material is archived outside the repository under
  `external_reviews/`;
- the independent reviewer signs the reviewed final state on a separate trust
  path;
- the review result, signature hash, CI run IDs, and reviewed commits are
  recorded in current governance documentation.

This exception is a governance workaround, not a live-release path. External
posthoc review can confirm a final main state after the fact, but it does not
grant live submit, live cancel, production deployment, or repeat-canary
authorization. Any subsequent code, document, evidence, release, or submodule
change requires fresh CI and fresh independent review for the changed final
state.

## DDR-010: Real gateway requires a separate production safety design

Accepted. Future real Polymarket gateway wiring, production submit/cancel, and
generic live readback must follow
`polymarket-execution-engine/docs/PRODUCTION_LIVE_GATEWAY_SECURITY_DESIGN.md`
or a reviewed successor. The design requires disabled defaults, compile-time
and runtime live gates, external secret custody, server-authoritative
PostgreSQL truth, no raw signed-material exposure, remote-unknown freeze,
cancel-only/read-only recovery modes, production alerting, incident drills, and
fresh independent review for the exact artifact and configuration.

This decision records a future implementation constraint only. It does not
enable live submit, live cancel, production deployment, or another real-funds
canary attempt in the current release state.
