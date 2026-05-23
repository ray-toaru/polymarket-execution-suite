# Development handoff — v0.26.0 controlled real-funds canary source-candidate

## Start here

1. Read `README.md`, `PROJECT_ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, and `VALIDATION_REPORT.md`.
2. Treat `docs/archive/`, `validation/archive/`, and `polymarket-execution-engine/evidence/archive/` as historical context only.
3. Use `polymarket-execution-engine/evidence/current/manifest.json` as the only current evidence ledger.

## Current gate

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Current v0.26 canary decision-prep state

The current next phase is still decision preparation, not live execution. Read
`docs/future/CANARY_DECISION_PREP_AUDIT.md` and `docs/future/CANARY_GO_NO_GO_REVIEW.md` before any
canary-related work.

Current review decision: `no_go`.

The regenerated local review package under
`dist/pmx-canary-review-v0.26-current/` is no-go review material only. It is
ignored by Git, must not be treated as armed approval, and must not be used to
run a live canary unless a later reviewed release decision explicitly changes
the boundary.

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
