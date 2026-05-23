# Release Decision — v0.27.3 controlled real-funds canary source-candidate

## Decision

Current decision: `controlled real-funds canary source-candidate`

This is a source-candidate and review-material release. It is not a validated
production release, not live-trading-ready, and not an approval to submit or
cancel live orders.

Current explicit non-claims:

- `validated_release=false`
- `production_ready=false`
- `live_trading_ready=false`
- `live_submit_allowed=false`
- `live_cancel_allowed=false`
- `real_funds_canary_authorized=false`

Do not claim production readiness. Do not claim live-trading readiness. The
first controlled canary was authorized through a separate reviewed-go package,
then consumed and closed; this release decision remains the durable non-live
source-candidate decision and does not authorize a second attempt.

## Scope

This decision applies to v0.27.3 source at the integration repository commit
that contains this file. The release package is the source archive
`polymarket-execution-suite-v0.27.3.zip` plus its detached `.sha256` and
`.zip.evidence.json` sidecars.

The package advances controlled canary preparation, v0.27 release-governance
hardening, and records one completed controlled canary closeout:

- reviewed candidate-market binding;
- BUY/GTC post-only canary size semantics where `target_size` is a reviewed share
  quantity and `notional_usd = limit_price * target_size`;
- explicit service-layer SDK gateway wiring behind injected signer/gateway
  dependencies, with the default service/API path still fail-closed;
- cancel-only fallback semantics at the service layer for remote-posted orders,
  with remote-unknown cancel outcomes requiring operator review;
- release-review package generation and explicit independent component version
  governance;
- no-go and blocked rehearsal material;
- tracked closeout summary for one consumed BUY/GTC post-only canary attempt,
  with stage-history and operator-recovery evidence required for non-clean
  remote-side-effect outcomes;
- PostgreSQL, SDK, credentialed smoke, sign-only dry-run, local static,
  governance, and deployment-template evidence.

It does not implement a production live execution stack. Any future live canary
requires a separate reviewed `go` release-decision JSON bound to the exact
artifact SHA-256, evidence manifest SHA-256, approval hash, and reviewed market
candidate SHA-256.

## Current Evidence

Canonical current evidence lives only at:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

The manifest currently records:

- local/current gates: pass;
- 2026-05-23 local refresh: Rust workspace, SDK adapter, PostgreSQL migration,
  PostgreSQL store tests, HTTP PostgreSQL E2E, PostgreSQL-backed store-truth
  CLI preflight, static guards, governance drills, release packaging, and
  review-package drills passed;
- PostgreSQL validation: pass, backed by `13-pg-migration.log`,
  `14-pg-store-tests.log`, and `15-http-postgres-e2e.log`;
- store-truth CLI preflight: pass, backed by
  `72-real-funds-canary-store-truth-cli-preflight.log`, with
  `--runtime-truth-store postgres`, no post/cancel, no remote side effects, and
  no raw signed order exposure;
- credentialed non-trading and sign-only dry-run sections: pass, backed by
  `16-authenticated-smoke.log` and `17-sign-only-dry-run.log` under explicit
  env gates;
- release decision: not validated, not production-ready, not live-ready.

Current detached artifact binding:

- artifact SHA-256: recorded in the detached `.zip.sha256` sidecar;
- evidence manifest SHA-256: recorded in the detached `.zip.evidence.json`
  sidecar and the current review package;
- current user-selected review package: the latest
  `dist/pmx-canary-review-v0.26-*-gtc-post-only-current-no-go` directory;
- review package decision: `no_go`, `real_funds_canary_authorized=false`.
- consumed reviewed-go package: one local v0.26 package produced a posted,
  cancelled, zero-fill closeout summarized in `CONTROLLED_CANARY_CLOSEOUT.md`.

Detached release sidecars bind the final containing zip hash. The manifest
inside the source zip intentionally does not self-bind the containing archive.

`dist/INDEX.json` is validated by `scripts/check_dist_index.py` and by
`scripts/check_release_artifact.py`. The index must name exactly one current
source artifact, keep `validated_release=false`, `production_ready=false`, and
`live_trading_ready=false`, and classify no-go, consumed, or closed local
review material as non-reusable for approval.

Final local package audit for this decision requires:

- no `.env`, cache, target, archive, or local `dist/` members inside the source
  zip;
- executable archive permissions for every shebang script;
- `.sha256`, `.zip.evidence.json`, `dist/INDEX.json`, and archived manifest
  SHA-256 values agreeing with the generated artifact.

## GitHub CI Boundary

Repository ownership is split:

- root integration repository: version consistency, contract parity, release
  hygiene, packaging, artifact validation;
- `hermes-polymarket-executor-adapter`: Python Hermes-compatible executor adapter, model/client contract,
  no-secret boundary;
- `polymarket-execution-engine`: Rust locked checks, PostgreSQL gates, SDK
  adapter checks, current gates, manual credentialed SDK workflow.

Historical v0.25 CI runs and review packages are audit context only. They are
not current v0.26 artifact proof unless a report explicitly binds the exact
v0.26 artifact SHA-256 and evidence manifest SHA-256.

## Required Before Any `go`

A future armed canary attempt must have all of the following:

- current full gates regenerated from the exact source commit;
- artifact `.sha256` and `.zip.evidence.json` sidecars regenerated after the
  final root commit;
- reviewed external references with no placeholders and no secret values;
- reviewed release-decision JSON with `real_funds_canary_authorized=true`;
- reviewed candidate-market JSON with a bound SHA-256;
- explicit account, market, size, notional, and daily caps;
- operator approval with expiry and object binding;
- runtime state healthy, kill switch open, no geoblock, no remote-unknown
  freeze, and idempotency reservation path verified;
- rollback, cancel-only, incident, alert, audit, and custody runbooks reviewed.

Until those conditions are met, v0.27.3 remains a non-live controlled canary
source-candidate.
