# Review audit — v0.28 production-live-candidate

## 2026-06-13 final main governance closeout

Current `main` is closed as a non-live governance baseline after direct main
push, CI, and an external posthoc independent review by `reviewer://lei`.

Reviewed source state:

- Integration suite commit:
  `42505d90a20a7cfb11e00a7161690e50a7d64d2a`.
- Execution-engine submodule commit:
  `8006d7de0edf4a87371f2fb70751fa804da3f636`.

CI evidence:

- Integration suite CI run `27459730580` completed with `success` for
  `42505d90a20a7cfb11e00a7161690e50a7d64d2a`.
- Execution-engine CI run `27459730710` completed with `success` for
  `8006d7de0edf4a87371f2fb70751fa804da3f636`.

External review archive evidence:

- Approved posthoc review:
  `external_reviews/lei/final-main-posthoc-review.approved.json`.
- Approved/canonical review SHA-256:
  `81797dfae7a58f4c6f5a928244940657e69d7935bf8c47602814223f5da0fe47`.
- Signature SHA-256:
  `304b7b3db5dd4eec7d6c1c7cf53fb1f9a14a7e377edb802d631eb354d0478887`.
- Signature verification record:
  `external_reviews/lei/final-main-posthoc-review.signature-verification.txt`.
- Verification result: SSH signature passed for `lei@beyin.tech` in namespace
  `pmx-canary-review` with fingerprint
  `SHA256:D8ZJbmZfyME4gYjZSZ117E7SU/VWIwhAcIjwXLdHS8w`.
- All nine posthoc review evidence files were present and their SHA-256
  digests matched the approved review JSON.

This closeout confirms the final main branch state only. It does not authorize
live submit, live cancel, production deployment, or another canary attempt. Any
later code, document, evidence, release, or submodule change invalidates this
posthoc confirmation for the changed final state and requires a fresh review of
that changed state.

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
