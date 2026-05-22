# Review audit — v0.26.0 controlled real-funds canary source-candidate

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
- Hermes can report canary readiness references under `hm-pdp-test`, but still
  cannot sign, submit, cancel, hold executor DB credentials, or call CLOB.

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

v0.26.0 controlled canary source is not a production/live-trading release.
