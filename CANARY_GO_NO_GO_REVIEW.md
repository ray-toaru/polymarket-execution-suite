# Controlled canary go/no-go review

## Review scope

This review covers the current `v0.26` controlled-canary decision-prep state.
It does not modify the `v0.25.0` release decision and does not approve live
submit, live cancel, production deployment, or a real-funds canary fill.

Current source and evidence references:

```text
source-refresh commit: 5f58885 docs: refresh v0.26 canary decision audit
previous pushed root commit: c0464b35614a0cbd11d0e0967ad9f8aa4effe424
hermes-polymarket-control: bb16582e299f9e6f8da6044226e33900c4e2459d
polymarket-execution-engine: d7e135667f95985e3a6e0ffdd8c1bda614b75aa5
root CI: 26210922346, success
execution-engine CI: 26210917113, success
credentialed SDK evidence: local-current-gates-20260521
artifact sha256: c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6
evidence manifest sha256: 4c53dd9b7abf14184df37932ba5eb645c942f75f075d31f40b587c8b612c7ffa
```

## Decision

Decision: `no_go`

Confidence: high for the no-go decision, because the current release decision,
canonical evidence, regenerated review package, and blocked rehearsal all keep
live side effects disabled.

This is not a finding that the implementation is unsuitable for a future
controlled canary. It is a finding that the current reviewed state is still
decision-prep only and lacks the external approval package required to authorize
real funds.

## Confirmed ready

- The current baseline remains `shadow-ready SDK sign-only candidate`.
- The latest local v0.26 review package was regenerated under
  `dist/pmx-canary-review-v0.26-current/`.
- The package binds the current artifact SHA-256, evidence manifest SHA-256,
  root CI run, execution-engine CI run, and credentialed local evidence id.
- The blocked armed rehearsal requested armed mode and local allow-config flags
  but failed at the release-decision gate before posting.
- The rehearsal report records `posted=false`, `cancelled=false`,
  `remote_side_effects=false`, and `raw_signed_order_exposed=false`.
- Local package validation passed and the release artifact checker confirmed
  `.env`, `.venv`, ignored review bundles, and local build/cache outputs are not
  included in the zip.

## Blockers

- No reviewed `go` release decision is present.
- No externally reviewed operator approval is present for the current artifact
  and evidence manifest hash pair.
- Secret custody is represented by reference material only; no reviewed
  production-grade custody decision is recorded.
- Alert route, dashboard, pager acknowledgement, rollback, and incident-runbook
  review remain review inputs, not approvals.
- Runtime health, reconcile readiness, account whitelist, market whitelist, and
  cap review still require explicit operator signoff before any live attempt.

## Required evidence before changing to go

- A reviewed release-decision JSON with `decision=go`, bound to the exact
  artifact SHA-256 and evidence manifest SHA-256 under review.
- Operator approval for `REAL_FUNDS_CANARY` and `FOK_LIMIT_FILL`, with 1 USD
  per-order and 5 USD per-day caps for the first canary.
- Secret-custody reference reviewed without storing secret values in the
  repository, logs, review package, or release artifact.
- Alert routing, dashboard, pager acknowledgement, rollback, incident runbook,
  cancel-only fallback, runtime health, reconcile health, account whitelist,
  market whitelist, and caps reviewed as current.
- A fresh blocked rehearsal or current-gate rerun after any material source,
  evidence, package, or approval change.

## Next action

Keep the current decision as `no_go`. The next safe action is external human
review of the regenerated no-go package. Do not run a live canary unless a later
reviewed release decision explicitly changes the boundary and the required
external approval evidence is present.
