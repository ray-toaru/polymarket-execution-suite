# AGENTS.md — repository instructions

## Scope and precedence

This file applies to the whole repository. More specific `AGENTS.md` files under subprojects add directory-specific rules; they may refine commands and style, but must not weaken the safety, evidence, or release-truthfulness rules below. For execution-engine work, also read the nearest module-level `AGENTS.md` under `polymarket-execution-engine/crates/`, `adapters/`, `openapi/`, `migrations/`, or `validation/` when present.

## Project shape

This integration repository pins two independent implementation planes as submodules:

- `hermes-polymarket-control/`: Python control plane for intents, approvals, reporting, and executor API calls.
- `polymarket-execution-engine/`: Rust execution plane for validation, lifecycle persistence, runtime state, authorization, signing-boundary isolation, and non-live SDK scaffolding.

When editing implementation code, commit the relevant submodule repository first, then update the
submodule pointer in this integration repository.

Version numbers, release status, and promotion decisions belong in `VERSION`, release manifests, validation reports, and release-decision documents. Do not encode the current version or current promotion state in AGENTS.md; these files should remain durable across releases.

## Working rules

- Stay independent, cautious, evidence-based, and concise.
- Separate confirmed facts, hypotheses, missing evidence, validation method, and next action when handling bugs or design claims.
- Do not claim a root cause, validated release, production readiness, or live readiness without direct evidence from the relevant gate.
- Prefer the minimum sufficient change. For complex or high-risk changes, compare at least two viable options before choosing.
- Keep documentation and code aligned. If behavior changes, update the relevant docs, OpenAPI schema, clients, tests, and guards.

## Safety boundaries

- Do not add, store, log, expose, or test with real private keys, CLOB secrets, raw signed payloads, raw signatures, or signed order envelopes.
- `hermes-polymarket-control` must not sign, submit live orders, cancel live orders, hold executor DB credentials, or call Polymarket CLOB directly.
- `polymarket-execution-engine` must keep live submit, live cancel, and production deployment blocked unless a formally reviewed release decision changes that after full gates pass.
- Sign-only and SDK-related work must remain no-remote-side-effect by default and must be guarded by explicit feature/env gates.

## Canonical documents

Use current documents first:

- `README.md`
- `PROJECT_ARCHITECTURE.md`
- `DEPENDENCY_POLICY.md`
- `DESIGN_DECISION_RECORD.md`
- `IMPLEMENTATION_STATUS.md`
- `VALIDATION_REPORT.md`
- `REVIEW_AUDIT.md`
- `DOC_STATUS.md`

Historical material belongs under archive directories and is excluded from normal release packages. Do not treat archived notes or old logs as current evidence.

## Evidence and release rules

- Canonical current evidence lives only under `polymarket-execution-engine/evidence/current/`.
- The canonical evidence manifest is `polymarket-execution-engine/evidence/current/manifest.json`.
- Regenerate evidence logs and the manifest after changing validation scripts, docs governance, contract schemas, or release packaging.
- Promotion claims require passing evidence for all required Rust, PostgreSQL, SDK, credential, and local static gates relevant to that claim.

## Local validation from repository root

Run the relevant subset for the files changed:

```bash
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
python -m unittest tests.test_controlled_canary_pipeline
PYTHONPATH=hermes-polymarket-control/src python -m pytest -q hermes-polymarket-control/tests
python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python scripts/clean_local_artifacts.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

Full external validation, when Rust/PostgreSQL/SDK prerequisites exist:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Packaging

Run `python scripts/clean_local_artifacts.py` before release hygiene checks on a developer worktree. Use `scripts/package_release.py` and then validate the artifact with `scripts/check_release_artifact.py`. Release packages must not contain archive directories, caches, targets, local env files, or non-canonical evidence directories.
