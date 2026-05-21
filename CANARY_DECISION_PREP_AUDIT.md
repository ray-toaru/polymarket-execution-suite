# Canary decision-prep audit — v0.26

## Current conclusion

The next phase is decision preparation only. The project remains a
`shadow-ready SDK sign-only candidate`; it is not production-ready,
live-trading-ready, or approved for a real-funds canary fill.

Current evidence baseline:

```text
source release: v0.25.0
supplemental evidence tag: v0.25.0-evidence.20260521
root commit: 73024a120cdc14038744b207aef4904ca2789919
hermes-polymarket-control: bb16582e299f9e6f8da6044226e33900c4e2459d
polymarket-execution-engine: 69528924a9228ccc5262322ca64468e97a625648
root CI: 26208090302, success
artifact sha256: c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6
current evidence manifest sha256: 4c53dd9b7abf14184df37932ba5eb645c942f75f075d31f40b587c8b612c7ffa
```

Current canonical evidence records `credentialed_non_trading_validation=pass`,
`postgres_validation=pass`, `real_funds_canary_preflight_validation=pass`,
`real_funds_canary_lifecycle_validation=pass`, and
`real_funds_canary_review_package_validation=pass`. The release decision in the
manifest still records `validated_release=false`, `production_ready=false`, and
`live_trading_ready=false`.

## Decision package audit

The reviewed package currently under `dist/pmx-canary-review-reviewed/` is
review material only, not an armed approval. It remains useful as a no-go
rehearsal sample, but it is not bound to the latest supplemental evidence:

- package `artifact_sha256`: `6bc50ff7ba942d2d001e347d045a6773da09d73a0b242589d14ce3566aca2dd9`
- package `evidence_manifest_sha256`: `11711ef30110d30ffb2556de507b9e1d3e3b181c9eea353cbc626da721f7481a`
- current artifact SHA-256: `c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6`
- current manifest SHA-256: `4c53dd9b7abf14184df37932ba5eb645c942f75f075d31f40b587c8b612c7ffa`

The package correctly preserves the safety boundary:

- `release-decision.json` has `decision=no_go` and
  `status=template_not_reviewed`.
- `adapter-release-decision.no-go.json` has
  `allow_real_funds_canary=false`.
- `external-references.json` has `references_only_no_secret_values=true`,
  `live_submit_allowed=false`, `live_cancel_allowed=false`, and
  `real_funds_canary_authorized=false`.
- `blocked-rehearsal.report.json` records `status=pass`,
  `blocked_at=release_decision_gate`, `posted=false`, `cancelled=false`, and
  `remote_side_effects=false`.

The current local v0.26 decision-prep package has been regenerated under
`dist/pmx-canary-review-v0.26-current/`. The directory is intentionally ignored
by Git because release packages and local review bundles are not source files.
It was generated through
`validation/run_real_funds_canary_blocked_rehearsal_package.py --output-dir`
with explicit `--artifact-sha256` and `--evidence-manifest-sha256` overrides,
so no manual JSON patching is required. Its review metadata is bound to the
current supplemental evidence:

- package `artifact_sha256`: `c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6`
- package `evidence_manifest_sha256`: `4c53dd9b7abf14184df37932ba5eb645c942f75f075d31f40b587c8b612c7ffa`
- `external_references_placeholders_remaining`: `[]`
- `live_submit_allowed=false`
- `live_cancel_allowed=false`
- `real_funds_canary_authorized=false`
- `remote_side_effects=false`

The regenerated blocked armed rehearsal passed. It requested armed mode with
local allow-config flags, exited with code `1`, and blocked at
`release_decision_gate` with reason
`real-funds canary not allowed by release decision`. The report records
`posted=false`, `cancelled=false`, `remote_side_effects=false`, and
`raw_signed_order_exposed=false`.

## Remaining blockers

Before any future controlled canary can be considered, the regenerated no-go
package must be externally reviewed and converted into a new explicit release
decision. That future decision must keep secret values out of repository files,
logs, and release artifacts.

The following items remain blockers, not implementation-ready approvals:

- externally reviewed local keyring or secret-custody record;
- operator approval with current artifact and evidence hash binding;
- alert route, dashboard, pager acknowledgement, and incident-runbook review;
- rollback and cancel-only fallback review;
- runtime, reconcile, account whitelist, market whitelist, and cap review;
- explicit future release decision that changes the no-go boundary.

Actual live submit, live cancel, production deployment, and real-funds canary
fill remain intentionally blocked.

## Next safe action

Review the regenerated package as a no-go decision artifact. Do not convert it
to go/live approval unless a future release decision explicitly changes the
boundary and supplies reviewed secret custody, operator approval, alerting,
rollback, runtime, reconcile, whitelist, and cap evidence.
