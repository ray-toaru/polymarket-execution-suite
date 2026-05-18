# Documentation and evidence status — v0.24.0 shadow-ready baseline

## Current canonical root documents

- `AGENTS.md` — repository-level AI agent working rules and safety guardrails.
- `README.md`
- `PROJECT_ARCHITECTURE.md`
- `DEPENDENCY_POLICY.md`
- `DESIGN_DECISION_RECORD.md`
- `IMPLEMENTATION_STATUS.md`
- `CURRENT_PROGRESS.md`
- `ROADMAP.md`
- `TASKS.md`
- `VALIDATION_REPORT.md`
- `REVIEW_AUDIT.md`
- `DEVELOPMENT_HANDOFF.md`
- `NO_LOCAL_ACTIONS_REMAINING.md`

## Historical documents

Historical root notes, old validation confirmations, and previous-version review material live under:

```text
docs/archive/
```

They may mention old versions and must not be used as current release evidence.

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
polymarket-dual-project-v0.24.0.zip
sha256=fd476e36af78099ba542cd6f030ccdd01f325565e8a5667d0d791c2479eaf0be
```

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
