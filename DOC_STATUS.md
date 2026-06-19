# Documentation and evidence status — v0.28.0 production-live-candidate

## 2026-06-18 local live-read event status

Current local source includes the Phase 5 live-read event persistence/API
continuation. Current tracked component pins are:

- Hermes adapter submodule:
  `49fb4b6c209e744f57b87b255bbf92003eacb557`;
- execution-engine submodule:
  `eec14d8e5b126c81150e3d6cdd6147e6be43dab6`;
- integration root before this documentation sync:
  `3fbf823ea1dd4e08a155d754ba04f89cd3a9d823`.

This state is local and unpushed. It has local validation but no GitHub CI,
fresh package sidecars, or fresh independent package review. It remains
`production_ready=false`, `live_trading_ready=false`, and
`validated_release=false`.

## 2026-06-18 status

Current `main` has advanced through the completed Phase 5 non-live foundation
merge. Current tracked component pins are:

- Hermes adapter submodule:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`;
- execution-engine submodule:
  `85f0641db4c02262829a2e94134193d8842db7de`.

The current local source package and detached sidecars were rebuilt from this
state with `production_ready=false`, `live_trading_ready=false`, and
`validated_release=false`. Root CI run `27751360977` and engine CI run
`27751351091` passed for the Phase 5 code state before this evidence/document
refresh. Fresh CI for these evidence/document commits and fresh independent
package review are still required before this changed state can be treated as
reviewed final package material. Existing PR-content and merge signatures do
not authorize live submit, live cancel, production deployment, reviewed-go
execution, or another canary attempt.

## 2026-06-13 status

Current `main` is a non-live governance baseline. Exact source commits,
artifact hashes, manifest hashes, and review hashes are recorded in detached
sidecars and external review JSON rather than self-embedded here, because this
document is part of the source package.

Current tracked component pins at this documentation refresh are:

- Hermes adapter submodule:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`;
- execution-engine submodule:
  `9584348fa8e368e088c92a3d72f44569581a7e13`.

Latest completed remote CI before this documentation refresh:

- integration suite run `27474066294`;
- adapter run `27473948617`;
- execution-engine run `27473806418`.

The external posthoc review archive remains outside the repository under
`external_reviews/lei/`. The latest completed approved/canonical review is
`external_reviews/lei/final-commit-package-hash-review.approved.canonical.json`.
It approves only the exact commit and package hash named in that JSON, with
non-live limits. This documentation/evidence refresh changes the source state,
so a fresh review is required after the next package rebuild.

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
- `polymarket-execution-engine/docs/PRODUCTION_LIVE_GATEWAY_SECURITY_DESIGN.md`
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
