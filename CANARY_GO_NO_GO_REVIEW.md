# Controlled canary go/no-go review

## Review scope

This review covers the current `v0.26` controlled-canary decision-prep state.
It does not modify the `v0.25.0` release decision and does not approve live
submit, live cancel, production deployment, or a real-funds canary fill.

Current source and evidence references:

```text
source-refresh commit: 4b571a29481c4a826c90a3b3aa907b74d92dbb39
previous pushed root commit: 1bfda7435503ebcdc1f35c8d267c5e89473b5e48
hermes-polymarket-control: bb16582e299f9e6f8da6044226e33900c4e2459d
polymarket-execution-engine: 4b571a29481c4a826c90a3b3aa907b74d92dbb39
latest pushed root CI before this local refresh: 26212663156, success
latest pushed execution-engine CI before this local refresh: 26210917113, success
local full current gates: pass, 2026-05-21
credentialed SDK evidence: local-current-gates-20260521
artifact sha256: c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6
evidence manifest sha256: 99ce4f47eb8e94fa0373f448180fde33643e0f2e19dcbeae148d8e95bbfaab5e
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
