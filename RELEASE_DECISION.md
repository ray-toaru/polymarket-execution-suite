# Release Decision — v0.26.0 controlled real-funds canary source-candidate

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

Do not claim production readiness. Do not claim live-trading readiness.

## Scope

This decision applies to v0.26.0 source at the integration repository commit
that contains this file. The release package is the source archive
`polymarket-execution-suite-v0.26.0.zip` plus its detached `.sha256` and
`.zip.evidence.json` sidecars.

The package advances controlled canary preparation:

- reviewed candidate-market binding;
- BUY/GTC post-only canary size semantics where `target_size` is a reviewed share
  quantity and `notional_usd = limit_price * target_size`;
- explicit service-layer SDK gateway wiring behind injected signer/gateway
  dependencies, with the default service/API path still fail-closed;
- cancel-only fallback semantics at the service layer for remote-posted orders,
  with remote-unknown cancel outcomes requiring operator review;
- release-review package generation;
- no-go and blocked rehearsal material;
- PostgreSQL, SDK, local static, governance, and deployment-template evidence.

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
- 2026-05-23 local refresh: Rust workspace, SDK adapter, static guards,
  governance drills, release packaging, and review-package drills passed;
- PostgreSQL external validation: skipped in the 2026-05-23 refresh because
  `PMX_TEST_DATABASE_URL` was not set; this remains a blocker for promotion
  and must not be treated as current PostgreSQL proof;
- PostgreSQL validation: pass only when `PMX_TEST_DATABASE_URL` is supplied and
  the dedicated migration, store, and HTTP PostgreSQL logs are present;
- credentialed non-trading and sign-only dry-run sections: pass only when their
  explicit env-gated logs are present, otherwise skipped and not promotion
  evidence;
- release decision: not validated, not production-ready, not live-ready.

Detached release sidecars bind the final containing zip hash. The manifest
inside the source zip intentionally does not self-bind the containing archive.

## GitHub CI Boundary

Repository ownership is split:

- root integration repository: version consistency, contract parity, release
  hygiene, packaging, artifact validation;
- `hermes-polymarket-control`: Python control plane, model/client contract,
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

Until those conditions are met, v0.26.0 remains a non-live controlled canary
source-candidate.
