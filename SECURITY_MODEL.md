# Security model - v0.28.0 non-live hardening

## Release posture

This source line is `non_live_hardened`. It is not production-ready,
live-ready, or authorized for real-funds trading. Live submit, live cancel, and
production deployment remain blocked unless a separate reviewed decision binds
the exact artifact, evidence manifest, operator approval, and runtime truth.

Future real gateway, production submit/cancel, and generic live readback work
must follow
`polymarket-execution-engine/docs/PRODUCTION_LIVE_GATEWAY_SECURITY_DESIGN.md`.
That document is design input only; it does not change the current non-live
release posture.

## Trust boundaries

- Hermes and the Python adapter may prepare intents, approvals, reports, and
  typed executor API requests. They must not sign orders, call CLOB directly,
  hold executor database credentials, or store trading secrets.
- The Rust execution engine owns authorization, persistence, idempotency,
  lifecycle reconciliation, and the feature-gated signing/SDK boundary.
- Runtime secrets come only from an explicit external secrets file or provider.
  Profile activation writes identity references, never private keys, API
  secrets, raw signatures, or signed order envelopes.
- GitHub CI, reviewer identities, operator approvals, and external signatures
  are external evidence. Local source and tests cannot substitute for them.

## Threat model

| Threat | Required control |
|---|---|
| Accidental live invocation | Default no-go decision, separate armed wrapper, explicit feature gates, single-attempt approval |
| Replayed approval | Artifact, manifest, candidate, runtime-truth, invocation, idempotency, and consumed-marker binding |
| Secret disclosure | External-only secret inputs, redacted errors, package denylist and allowlist, no raw signed material |
| Wrong account or market | Active-profile/account equality checks, reviewed candidate hash, condition and exchange-rule binding |
| Partial post/cancel failure | Durable lifecycle stages, cancel-only fallback, readback, operator recovery, no automatic retry |
| Stale or fabricated evidence | SHA-256 bindings, exact commit CI URLs, canonical current manifest, archived evidence exclusion |
| Dependency or submodule drift | Locked dependencies, pinned actions, pinned submodule commits, version consistency gates |

## Operator misuse matrix

| Misuse | Expected result |
|---|---|
| Run preflight without a reviewed-go decision | Fail closed before remote side effects |
| Reuse a consumed or closed approval package | Reject the package |
| Supply mismatched account, artifact, or runtime truth | Reject before command execution |
| Place secrets in the profile output | Reject generation or post-write verification |
| Pass live flags through the normal adapter path | Reject; adapter supports blocked dry-run only |
| Skip post/cancel readback or recovery evidence | Refuse clean closeout |
| Treat local or historical logs as current CI proof | Reject promotion claim |

## Evidence retention

- Canonical current evidence lives only under
  `polymarket-execution-engine/evidence/current/`.
- Historical evidence moves to archive directories and is excluded from normal
  release packages.
- Current evidence and release sidecars contain references, status, timestamps,
  commit IDs, and hashes. They must not contain raw secrets, raw signatures, or
  signed order payloads.
- Local operational drills currently model a 365-day redacted audit retention
  policy. A production retention system, legal hold, deletion workflow, and
  access review remain external production prerequisites.
