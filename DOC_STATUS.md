# Documentation and evidence status — v0.26.0 controlled real-funds canary source-candidate

## Current canonical documents

- `AGENTS.md` — repository-level AI agent working rules and safety guardrails.
- `README.md`
- `PROJECT_ARCHITECTURE.md`
- `DEPENDENCY_POLICY.md`
- `DESIGN_DECISION_RECORD.md`
- `IMPLEMENTATION_STATUS.md`
- `CURRENT_PROGRESS.md`
- `ROADMAP.md`
- `TASKS.md`
- `docs/future/CANARY_DECISION_PREP_AUDIT.md`
- `docs/future/CANARY_GO_NO_GO_REVIEW.md`
- `VALIDATION_REPORT.md`
- `REVIEW_AUDIT.md`
- `DEVELOPMENT_HANDOFF.md`
- `NO_LOCAL_ACTIONS_REMAINING.md`

Canary decision-prep documents are active v0.26 governance material. They must
continue to state `no_go` unless a future reviewed release decision explicitly
changes the live/production boundary.

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
polymarket-execution-suite-v0.26.0.zip
sha256=recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

Hermes validation for the control-plane side uses the externally created
`hm-pdp-test` profile.

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
