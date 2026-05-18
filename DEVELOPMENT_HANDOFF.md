# Development handoff — v0.24.0 shadow-ready baseline source candidate

## Start here

1. Read `README.md`, `PROJECT_ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, and `VALIDATION_REPORT.md`.
2. Treat `docs/archive/`, `validation/archive/`, and `polymarket-execution-engine/evidence/archive/` as historical context only.
3. Use `polymarket-execution-engine/evidence/current/manifest.json` as the only current evidence ledger.

## Current gate

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Important paths

- `scripts/check_version_consistency.py`
- `scripts/validate_contracts.py`
- `scripts/package_release.py`
- `scripts/check_release_artifact.py`
- `polymarket-execution-engine/validation/check_docs_evidence_governance.py`
- `polymarket-execution-engine/openapi/executor.v1.yaml`
- `polymarket-execution-engine/crates/pmx-api/src/lib.rs`
- `polymarket-execution-engine/crates/pmx-policy/src/lib.rs`
- `hermes-polymarket-control/src/hermes_polymarket_control/models.py`

## Do not enable without new evidence

- live submit;
- live cancel;
- production deployment;
- public or Python-side signing material access.
