# Validation Report — v0.26.0 controlled real-funds canary source-candidate

## Current Conclusion

v0.26.0 is locally validated as a controlled real-funds canary
source-candidate. It is not production-ready and not live-trading-ready.

On 2026-05-22, one explicitly authorized BUY/GTC post-only controlled canary
was posted and immediately cancelled against the reviewed market candidate. The
saved readback evidence records `remote_status=CANCELED`, `size_matched=0`, and
zero matching trades for the submitted order id. A broader public Data API
readback for the same account/market/token also records zero activity, zero
trades, zero open positions, zero closed positions, and value `0`. This
validates the one-time canary exercise only; it is not evidence for general
production/live readiness.

The current package is valid only when the following detached sidecars are
present next to the source archive:

```text
dist/polymarket-execution-suite-v0.26.0.zip
dist/polymarket-execution-suite-v0.26.0.zip.sha256
dist/polymarket-execution-suite-v0.26.0.zip.evidence.json
```

The source archive does not self-bind its containing zip hash. The detached
evidence sidecar binds the artifact SHA-256 and the canonical evidence manifest
SHA-256.

## Local Evidence Status

Canonical manifest:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Current evidence policy:

- `postgres_validation=pass` only when the PostgreSQL logs are present and the
  dedicated store log runs non-zero `postgres::postgres_tests`;
- credentialed non-trading smoke is `pass` only when
  `16-authenticated-smoke.log` exists and satisfies the manifest test-count
  rule; otherwise it is skipped, not promotion evidence;
- sign-only dry-run is `pass` only when `17-sign-only-dry-run.log` exists and
  satisfies the manifest test-count rule; otherwise it is skipped, not
  promotion evidence;
- local static, Rust, SDK, package, governance, and deployment-template gates
  are evidence only for the source-candidate boundary.

## Local Validation Commands

Use local checks before CI:

```bash
.venv/bin/python scripts/check_version_consistency.py
.venv/bin/python scripts/validate_contracts.py
HERMES_PROFILE=hm-pdp-test PYTHONPATH=hermes-polymarket-control/src .venv/bin/python -m pytest -q hermes-polymarket-control/tests
HERMES_PROFILE=hm-pdp-test .venv/bin/python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
cd polymarket-execution-engine && ./validation/run_current_gates.sh
```

Routine edits should use the relevant local subset first. Remote CI is a release
confirmation layer, not the default way to validate every small local change.

## Canary Review Boundary

Review packages under `dist/pmx-*` are local review material unless the
machine-readable `dist/INDEX.json` names them as the current release artifact.
Multiple local review directories may exist; they are not interchangeable
approval sources.

The user-selected canary market review package must bind:

- artifact SHA-256;
- evidence manifest SHA-256;
- candidate-market SHA-256;
- external references with no placeholders;
- a release-decision JSON that remains no-go unless explicitly reviewed as go.

The controlled canary dry-run may report `dry_run_ready`, but that status still
means no live submit, no live cancel, no posted order, and no remote side
effects.

## Non-Claims

This validation report does not claim:

- production deployment readiness;
- live submit or live cancel availability;
- a successful real-funds canary fill;
- readiness for a second real-funds canary without a fresh reviewed decision;
- equivalence between historical v0.25 evidence and the current v0.26 package.

Any future live attempt needs a new reviewed release decision and fresh evidence
bound to the exact artifact under review.
