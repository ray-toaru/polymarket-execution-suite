# Release Decision — v0.28.0 production-live-candidate

```json release-decision
{
  "live_cancel_allowed": false,
  "live_submit_allowed": false,
  "live_trading_ready": false,
  "production_ready": false,
  "real_funds_canary_authorized": false,
  "release_posture": "production-live-candidate",
  "schema_version": 1,
  "validated_release": false,
  "version": "0.28.0"
}
```

## 2026-06-11 non-live freeze

The historical `v0.28.0` tag points to an earlier commit and is not moved.
Current evidence is published under the governance tag
`v0.28.0-non-live-hardened.1`.

That tag binds a `non_live_hardened` source and artifact. It is not an
independent dual-control approval, production approval, live-trading approval,
or real-funds authorization. Cryptographic approval remains external.

## Decision

Current decision: `production-live-candidate`

This is a production-live candidate and review-material release. It is not a
validated production release, not live-trading-ready, and not an approval to
submit or cancel live orders.

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
production-live-candidate decision and does not authorize a second attempt.

## Scope

This decision applies to v0.28.0 source at the integration repository commit
that contains this file. The release package is the source archive
`polymarket-execution-suite-v0.28.0.zip` plus its detached `.sha256` and
`.zip.evidence.json` sidecars.

The historical governance freeze point is git tag `v0.28.0`. Current non-live
hardening evidence uses `v0.28.0-non-live-hardened.1`; neither tag authorizes
live execution.

The package advances controlled canary preparation, v0.28 release-governance
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

Current source/artifact binding for this document state is detached rather than
self-embedded. Exact commits, artifact hashes, manifest hashes, and CI run
bindings belong in the generated `dist/` sidecars, release provenance, and the
external progress tracker.

Final artifact and sidecar hashes are detached binding material. They are
recorded next to the generated archive in `dist/` and in the external progress
tracker, not self-embedded in this source document.

The manifest currently records:

- `postgres_validation=pass`
- `credentialed_non_trading_validation=pass`
- `sdk_standard_sign_only_validation=pass`
- `real_funds_canary_store_truth_cli_validation=pass`
- other local/static source-candidate gates: pass;
- release decision: not validated, not production-ready, not live-ready.

PostgreSQL-backed gates and store-truth CLI preflight were run locally on
2026-06-20 against an isolated PostgreSQL 16 test cluster. Credentialed
non-trading smoke and sign-only dry-run were run locally on 2026-06-21 with
operator-provided execution-engine credentials, redacted logs, and live
submit/cancel env gates unarmed. Historical 2026-05-23 credentialed
non-trading evidence remains prior context only.

Current detached artifact binding:

- artifact SHA-256: recorded in the detached `.zip.sha256` sidecar;
- evidence manifest SHA-256: recorded in the detached `.zip.evidence.json`
  sidecar and the current review package;
- current user-selected review package: any future package must be freshly
  generated, classified in `dist/INDEX.json`, and default to `no_go`;
- review package decision: `no_go`, `real_funds_canary_authorized=false`;
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

Historical v0.25 and v0.26 CI runs and review packages are audit context only.
They are not current v0.28 artifact proof unless a report explicitly binds the
exact v0.28 artifact SHA-256 and evidence manifest SHA-256.

## Production-Live Candidate Closure Criteria

v0.28 moves the project toward production/live operation only when all eight
candidate criteria below have fresh evidence bound to the exact artifact under
review:

1. Release decision: a fresh reviewed release decision must bind the final
   artifact SHA-256, evidence manifest SHA-256, candidate-market SHA-256, and
   approval hash.
2. Canary approval: operator approval must be dual-control reviewed, scoped to
   one bounded attempt, expired after use, and marked consumed before closeout.
3. Runtime truth: runtime state healthy, kill switch open, no geoblock, market
   live, account allowlisted, balance/allowance checked, idempotency reservation
   ready, and reconciliation worker healthy must all be durable facts.
4. Execution boundary: live submit and live cancel remain disabled by default;
   any enabled path must prove post/cancel/readback/closeout stage persistence
   and operator-required handling for remote-unknown outcomes.
5. Deployment: production deployment evidence must include service topology,
   database migration plan, health probes, rollback command, and recovery path.
6. Operations: alert routing, incident runbook, monitoring/SLO, audit export,
   and rollback drills must be reviewed and attached as external references.
7. Custody and permissions: secret custody, key management, service/admin token
   split, no raw signed payload exposure, and Hermes no-secret/no-signing
   boundaries must remain enforced.
8. Risk limits: explicit account, market, size, notional, daily caps, price
   tick, post-only/GTC semantics, and no-fill/zero-impact closeout checks must
   be bound to the reviewed attempt.

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

Until those conditions are met, v0.28.0 remains a non-live
production-live-candidate.
