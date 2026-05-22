# Controlled canary go/no-go review

## Review scope

This review covers the current `v0.26` controlled-canary decision-prep state.
It does not approve live submit, live cancel, production deployment, or a
real-funds canary fill. v0.26.0 remains `no_go` until the current gates and a
reviewed `go` release decision are regenerated for the final artifact.

Current source and evidence references:

```text
source-refresh root commit: final root commit recorded in .zip.evidence.json sidecar
hermes-polymarket-control: bb16582e299f9e6f8da6044226e33900c4e2459d
polymarket-execution-engine: 76fdb3ee136b0350e4718fff60a1edcee1f67d03
latest pushed root CI baseline: 26254755001, success
latest pushed execution-engine CI baseline: 26254745573, success
targeted local post-CI checks: pass, 2026-05-21, no new CI run
local full current gates: pass, 2026-05-21
credentialed SDK evidence: local-current-gates-20260521
artifact sha256: recorded in the external .zip.sha256 sidecar for the generated release zip
evidence manifest sha256: 80b4b7fa8ef325ffb3cff6d839176a9af1ce28ce226c4d3ebef826c6c2b981d1
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
