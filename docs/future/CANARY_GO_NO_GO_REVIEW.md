# Controlled canary go/no-go review

Status: active v0.28 production-live-candidate governance material. This file
keeps the default decision at `no_go` unless a fresh reviewed v0.28.0 release
decision explicitly authorizes exactly one bounded attempt.

## Review scope

This review covers the current `v0.28.0` production-live-candidate
decision-prep state.
It does not approve live submit, live cancel, production deployment, or a
real-funds canary fill. Historical v0.26 material remains `no_go` audit context
only; any future v0.28 attempt needs current gates and a reviewed `go` release
decision regenerated for the final artifact.

Current source and evidence references:

```text
source-refresh root commit: recorded in .zip.evidence.json sidecar
hermes-polymarket-executor-adapter: 7477c028d5c4f0f2215e7ee6c3ee4ea750331553
polymarket-execution-engine: be6298241d28eecc3eaf3be871c8f5776a8157d0
latest pushed root CI baseline: 27474066294, success
latest pushed adapter CI baseline: 27473948617, success
latest pushed execution-engine CI baseline: 27473806418, success
artifact sha256: recorded in the detached .zip.sha256 and .zip.evidence.json sidecars
evidence manifest sha256: recorded in the detached .zip.evidence.json sidecar
credentialed SDK evidence: skipped in the current final manifest; must be
refreshed before any go/live claim
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
- The final non-live package binds the current artifact SHA-256, evidence
  manifest SHA-256, root CI run, adapter CI run, and execution-engine CI run.
- The latest local historical v0.26 review packages are retained only as audit
  context and are not current approval material.
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
- Operator approval for `REAL_FUNDS_CANARY` and `GTC_LIMIT_POST_ONLY_CANCEL`, with 1 USD
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
