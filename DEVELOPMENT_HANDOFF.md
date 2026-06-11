# Development handoff — v0.28.0 production-live-candidate

## Start here

1. Read `README.md`, `PROJECT_ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, and `VALIDATION_REPORT.md`.
2. Treat `docs/archive/`, `validation/archive/`, and `polymarket-execution-engine/evidence/archive/` as historical context only.
3. Use `polymarket-execution-engine/evidence/current/manifest.json` as the only current evidence ledger.

## Current gate

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Branch governance

`main` is the permanent integration branch in this repository and both
component repositories. Version-named candidate branches and release tags are
retained for audit history; they are not permanent default branches.

The integration repository pins exact component commits. Commit component
changes in the relevant submodule first, then update the pinned submodule
commit here as one reviewed integration change. A commit being reachable from
`main` does not change the documented non-live release posture.

## Current canary decision-prep state

The current next phase is still decision preparation, not live execution. Read
`docs/future/CANARY_DECISION_PREP_AUDIT.md` and `docs/future/CANARY_GO_NO_GO_REVIEW.md` before any
canary-related work.

Current review decision: `no_go`.

Local review packages under `dist/pmx-*` are ignored by Git and must be
classified by `dist/INDEX.json` before use. No-go material is not armed
approval. Consumed or closed reviewed-go packages are historical evidence only.
A later reviewed release decision must explicitly change the boundary for one
bounded canary attempt before any live canary work resumes.

## Important paths

- `scripts/check_version_consistency.py`
- `scripts/validate_contracts.py`
- `scripts/package_release.py`
- `scripts/check_release_artifact.py`
- `polymarket-execution-engine/validation/check_docs_evidence_governance.py`
- `polymarket-execution-engine/openapi/executor.v1.yaml`
- `polymarket-execution-engine/crates/pmx-api/src/lib.rs`
- `polymarket-execution-engine/crates/pmx-policy/src/lib.rs`
- `hermes-polymarket-executor-adapter/src/hermes_polymarket_executor_adapter/models.py`

## Do not enable without new evidence

- live submit;
- live cancel;
- production deployment;
- real-funds canary fill;
- public or Python-side signing material access.
