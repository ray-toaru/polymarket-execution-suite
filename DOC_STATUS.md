# Documentation and evidence status — v0.28.0 production-live-candidate

## 2026-06-13 status

Current `main` is a non-live governance baseline with external posthoc
independent review by `reviewer://lei`. The reviewed source state is
integration suite commit
`42505d90a20a7cfb11e00a7161690e50a7d64d2a` with execution-engine submodule
commit `8006d7de0edf4a87371f2fb70751fa804da3f636`.

The binding CI evidence is integration suite run `27459730580` and
execution-engine run `27459730710`, both successful for the exact reviewed
commits. The external posthoc review archive remains outside the repository
under `external_reviews/lei/`; the approved/canonical review SHA-256 is
`81797dfae7a58f4c6f5a928244940657e69d7935bf8c47602814223f5da0fe47`, and the
signature SHA-256 is
`304b7b3db5dd4eec7d6c1c7cf53fb1f9a14a7e377edb802d631eb354d0478887`.

This status does not authorize live submit, live cancel, production deployment,
or another canary attempt. Later code, document, evidence, release, or
submodule changes require fresh CI and fresh independent review for the changed
final state.

## 2026-06-11 status

Canonical evidence was regenerated after the admin-session and provenance
changes. Current release material must include the zip, SHA-256 sidecar,
evidence sidecar, and provenance sidecar. External signature material belongs
in the GitHub release, not in the repository.

The governance tag for this source line is
`v0.28.0-non-live-hardened.1`. It does not replace or move the historical
`v0.28.0` tag and does not authorize live trading.

## 2026-06-10 status

Current documents describe a `non_live_hardened` source candidate. Historical
canary material remains audit context only; current CI, artifact, and evidence
references must bind exact commits and hashes. `SECURITY_MODEL.md` is the
canonical trust-boundary, misuse, threat, and evidence-retention summary.

## Current canonical documents

- `AGENTS.md` — repository-level AI agent working rules and safety guardrails.
- `README.md`
- `PROJECT_ARCHITECTURE.md`
- `COMPONENT_COMPATIBILITY.md`
- `DEPENDENCY_POLICY.md`
- `SECURITY_MODEL.md`
- `OFFLINE_INDEPENDENT_REVIEW_MANUAL.md`
- `DESIGN_DECISION_RECORD.md`
- `IMPLEMENTATION_STATUS.md`
- `CONTROLLED_CANARY_CLOSEOUT.md`
- `CURRENT_PROGRESS.md`
- `ROADMAP.md`
- `TASKS.md`
- `RELEASE_DECISION.md`
- `docs/future/CANARY_DECISION_PREP_AUDIT.md`
- `docs/future/CANARY_GO_NO_GO_REVIEW.md`
- `docs/future/CANARY_PRODUCTION_ROADMAP.md`
- `VALIDATION_REPORT.md`
- `REVIEW_AUDIT.md`
- `DEVELOPMENT_HANDOFF.md`
- `NO_LOCAL_ACTIONS_REMAINING.md`

Canary decision-prep documents are active v0.28 governance material. The
historical v0.26 controlled canary is closed, and one local v0.28 reviewed-go
single-attempt canary package is also consumed and closed. Future canary
decision-prep material must continue to state `no_go` unless a fresh reviewed
release decision explicitly changes the live/production boundary for that
single attempt.

## Historical documents

Historical root notes, old validation confirmations, and previous-version review material live under:

```text
docs/archive/
```

They may mention old versions and must not be used as current release evidence.
`docs/archive/VALIDATION_PROMOTION.md` is the archived historical v0.23.1
validation-promotion plan.

## Current evidence rule

Canonical current evidence lives only under:

```text
polymarket-execution-engine/evidence/current/
```

The required manifest is:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

The current manifest binds the release artifact:

```text
polymarket-execution-suite-v0.28.0.zip
sha256=recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

Hermes runtime validation for the adapter side requires an externally created
local profile command supplied as `HERMES_PROFILE_CMD` or `--profile-cmd`; no
specific workstation profile name is part of the project contract.

Historical or imported logs live under:

```text
polymarket-execution-engine/evidence/archive/
validation/archive/
```

Historical evidence is retained for audit context but is excluded from normal release packages by `scripts/package_release.py`.

## Current governance guard

Run:

```bash
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
```

This guard rejects stale root document names, non-canonical evidence logs outside archive/current, missing current evidence manifest, bad log hashes, and missing release-manifest evidence binding.
