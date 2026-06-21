# Review audit — v0.28 production-live-candidate

## 2026-06-18 local live-read event continuation

Current local source has advanced after the Phase 5 live-read event
persistence/API continuation. Current component pins are:

- Hermes adapter submodule commit:
  `49fb4b6c209e744f57b87b255bbf92003eacb557`.
- Execution-engine submodule commit:
  `eec14d8e5b126c81150e3d6cdd6147e6be43dab6`.
- Integration root commit before this documentation sync:
  `3fbf823ea1dd4e08a155d754ba04f89cd3a9d823`.

This local state is not pushed and has no GitHub CI result. Local validation
passed for the live-read store/gateway tests, Rust workspace check, API scaffold
test, Hermes adapter tests, OpenAPI parity, contract validation, docs/evidence
governance, release artifact validation after the secret-fixture repair, and
root unit tests after the current documentation sync.

The earlier external review and merge authorization remain scope-bound. They
do not authorize live submit, live cancel, production deployment, or another
canary attempt. Any rebuilt package, sidecar, provenance, reviewed-go package,
or canary packet requires fresh review.

## 2026-06-16 Phase 5 merged non-live evidence refresh

Current `main` has advanced after the Phase 5 non-live foundation merge and
the reviewer fail-closed regression expansion. Current component pins:

- Hermes adapter submodule commit:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`.
- Execution-engine submodule commit:
  `9b383a049c9309b58c9fde2dacf8a3cf6feb5515`.

Local evidence and artifact checks were refreshed for the new source state, but
the pushed source state still requires fresh CI and fresh review before it can
be treated as a reviewed final package. The refreshed local artifact hash is
recorded in detached `dist/` sidecars, not as a live or production approval.

The earlier external review and merge authorization remain scope-bound. They
do not authorize live submit, live cancel, production deployment, or another
canary attempt. Any rebuilt package, sidecar, provenance, reviewed-go package,
or canary packet requires fresh review.

## 2026-06-13 final main governance closeout

Current `main` is closed as a non-live governance baseline after direct main
push, CI, and an external posthoc independent review by `reviewer://lei`.
Exact root commit and artifact hashes are intentionally kept in detached
sidecars and external review JSON instead of self-embedded here.

Current component pins:

- Hermes adapter submodule commit:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`.
- Execution-engine submodule commit:
  `9584348fa8e368e088c92a3d72f44569581a7e13`.

Latest completed remote CI before this documentation refresh:

- Integration suite CI run `27474066294` completed with `success` after the
  parent governance-test alignment.
- Adapter CI run `27473948617` completed with `success` after switching adapter
  CI to the committed executor OpenAPI snapshot.
- Execution-engine CI run `27473806418` completed with `success` before the
  local evidence-refresh commit. The refreshed evidence commit still needs
  fresh remote CI if it is to become reviewed final-state evidence.

External review archive evidence:

- Final approved package-hash review:
  `external_reviews/lei/final-commit-package-hash-review.approved.canonical.json`.
- Signature verification record:
  `external_reviews/lei/final-commit-package-hash-review.signature-verification.txt`.
- Verification result: SSH signature passed for `lei@beyin.tech` in namespace
  `pmx-canary-review` with fingerprint
  `SHA256:D8ZJbmZfyME4gYjZSZ117E7SU/VWIwhAcIjwXLdHS8w`.
- All nine final package-hash review evidence files were present and their SHA-256
  digests matched the approved review JSON.

That completed review confirms only the exact state named in its JSON. It does
not authorize live submit, live cancel, production deployment, or another
canary attempt. This documentation/evidence refresh advances the source state,
so the next package hash and final source commit require fresh CI as needed,
rebuilt sidecars, and fresh independent review before they can be treated as a
reviewed final state. Any changed final state requires a fresh review of that
changed state.

## 2026-06-11 follow-up

The source-level admin-token gap is closed by `GET /v1/admin/session` and the
adapter's fail-closed subject/capability verification. A real deployed executor
probe remains external because no deployment URL or token was configured.

Dependency provenance and exact CI binding are now implemented. A single GPG
operator signature can bind the non-live release statement, but it does not
satisfy independent dual control; `B-009` and `F-100` remain open until a
distinct reviewer identity signs or an equivalent external identity provider
attests the review.

The existing `v0.28.0` tag points to an earlier commit and will not be moved.
The current non-live artifact uses a separate governance tag. Cryptographic
signing remains pending because the available local GPG key requires an
operator-unlocked passphrase and no SSH signing agent is configured.

## 2026-06-10 disposition

All ledger entries have been reclassified against current source and tests:
locally closed items carry direct code/test evidence, non-live controls remain
intentionally blocked, and external identity/platform requirements are not
represented as local passes. The current release posture is
`non_live_hardened`, not production or live-ready.

The remaining external boundary includes independent reviewer identity and
signature evidence, an executor admin-token capability probe, CI token scope,
branch protection unavailable on the current private-repository plan, and a
future formal live release decision. None of these is required to claim this
non-live hardening result.

## Confirmed source-level improvements

- Current docs now have a documented canonical set and archive boundary.
- Evidence now has a canonical current manifest path and archive boundary.
- Release packaging excludes archived docs/evidence and imported historical logs.
- Public lifecycle payload schema is a redacted envelope rather than an unconstrained object.
- Pre-live degraded worker status is treated fail-closed by policy.
- Live submit/cancel remain blocked.
- Runtime worker and order lifecycle governance now have full gate evidence.
- The current final manifest records credentialed non-trading smoke, sign-only
  dry-run, PostgreSQL, and PostgreSQL-backed store-truth CLI sections as pass
  for the local refresh. This is evidence for the non-live candidate only and
  does not authorize production, live submit/cancel, or another canary attempt.
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
