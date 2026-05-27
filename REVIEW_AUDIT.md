# Review audit — v0.28 production-live-candidate

## Confirmed source-level improvements

- Current docs now have a documented canonical set and archive boundary.
- Evidence now has a canonical current manifest path and archive boundary.
- Release packaging excludes archived docs/evidence and imported historical logs.
- Public lifecycle payload schema is a redacted envelope rather than an unconstrained object.
- Pre-live degraded worker status is treated fail-closed by policy.
- Live submit/cancel remain blocked.
- Runtime worker and order lifecycle governance now have full gate evidence.
- Credentialed non-trading smoke and sign-only dry-run passed under explicit
  opt-in gates without enabling live submit/cancel.
- Real-funds canary dry-run diagnostics are aggregate-only and do not expose
  token identifiers, raw signed material, or secrets.
- Armed real-funds canary requires a reviewed release-decision JSON in addition
  to approval, artifact, evidence, env, config, market, and balance gates.
- v0.26.0 additionally binds the candidate market file SHA-256 into both
  approval and release decision, requires BUY/GTC post-only plus a human review reference,
  and consumes a one-time approval marker before any armed post attempt.
- The historical v0.26.0 real-funds canary completed as a GTC post-only order
  that was cancelled with `size_matched=0`; a subsequent read-only trades query
  found zero matching fills for the remote order id.
- A separate local v0.28 reviewed-go single-attempt canary has now also been
  posted, cancelled, and closed with `remote_status=CANCELED`,
  `size_matched=0`, zero matching trades, zero matching activity, zero matching
  open/closed positions, and value `0`.
- New canary tooling requires future armed runs to provide `--report-file`, so
  the post/cancel receipt is persisted instead of relying on terminal output.
- Hermes can report canary readiness references under an operator-provided
  local Hermes profile, but still cannot sign, submit, cancel, hold executor DB
  credentials, or call CLOB.

## Current evidence

Current canonical evidence:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Bound artifact SHA-256:

```text
recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

## Current conclusion

v0.28.0 now records one closed local reviewed-go canary exercise in addition to
the historical v0.26 audit trail, but it is still not a production/live-trading
release.
