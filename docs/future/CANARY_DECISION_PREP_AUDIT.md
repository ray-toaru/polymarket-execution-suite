# Canary decision-prep audit — v0.28.0

Status: active v0.28.0 production-live-candidate governance material. Older
v0.25/v0.26/v0.27 references are historical evidence pointers only and do not
authorize live submit, live cancel, production deployment, or another
real-funds canary.

## Current conclusion

The current v0.28.0 phase is controlled canary source preparation only. The
project is not production-ready, live-trading-ready, or approved for a
real-funds canary fill.

Reviewed evidence baseline:

```text
hermes-polymarket-executor-adapter: c3c644571ae28067ad7ed2c8ab4dd042a1d54923
polymarket-execution-engine: 847389c1f72c4a7476135031770b73186324ab72
latest reviewed root CI baseline: 27895560086, success
latest reviewed adapter CI baseline: 27895590621, success
latest reviewed execution-engine CI baseline: 27895560093, success
artifact sha256: recorded in the detached .zip.sha256 and .zip.evidence.json sidecars
current evidence manifest sha256: recorded in the detached .zip.evidence.json sidecar
artifact evidence sidecar sha256: external review material, not self-embedded
```

Historical v0.26 decision-prep source refreshes are audit context only. Their
exact commits, CI runs, and credentialed evidence identifiers must not be used
as current v0.28 promotion evidence.

The 2026-06-21 Lei evidence-sufficiency review artifact accepts entry into an
operator production/live decision gate for the exact reviewed packet. That
acceptance does not change the live-trading boundary and does not itself
authorize CI dispatch, credentialed smoke, sign-only dry-run, live submit, live
cancel, production deployment, or real-funds action. This documentation sync is
not part of that exact reviewed packet until a fresh package/review binds it.

Current canonical evidence records `postgres_validation=pass`,
`credentialed_non_trading_validation=pass`,
`sdk_standard_sign_only_validation=pass`, `sdk_adapter_validation=pass`, and
`real_funds_canary_store_truth_cli_validation=pass`. The release decision in the
manifest still records `validated_release=false`, `production_ready=false`, and
`live_trading_ready=false`.

## Decision package audit

The reviewed package currently under `dist/pmx-canary-review-reviewed/` is
review material only, not an armed approval. It remains useful as a no-go
rehearsal sample, but it is not bound to the latest supplemental evidence:

- package `artifact_sha256`: `6bc50ff7ba942d2d001e347d045a6773da09d73a0b242589d14ce3566aca2dd9`
- package `evidence_manifest_sha256`: `11711ef30110d30ffb2556de507b9e1d3e3b181c9eea353cbc626da721f7481a`
- current artifact SHA-256: recorded in the external `.zip.sha256` sidecar
- current manifest SHA-256: recorded in the detached sidecar for the current
  generated package.

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

The current local historical v0.26 decision-prep package has been regenerated under
`dist/pmx-canary-review-v0.26-current/`. The directory is intentionally ignored
by Git because release packages and local review bundles are not source files.
It was generated through
`validation/run_real_funds_canary_blocked_rehearsal_package.py --output-dir`
with explicit `--artifact-sha256` and `--evidence-manifest-sha256` overrides,
so no manual JSON patching is required. Its review metadata is bound to the
current supplemental evidence:

- package `artifact_sha256`: supplied from the external `.zip.sha256` sidecar
- package `evidence_manifest_sha256`: historical value; not current final-state
  promotion evidence.
- historical package root CI baseline after final package generation: `27474066294`
- historical package adapter CI baseline after final package generation: `27473948617`
- historical package execution-engine CI baseline after final package generation:
  `27473806418`
- package `credentialed_sdk_run_id`: historical local-current-gates identifier;
  not current final-state promotion evidence.
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
