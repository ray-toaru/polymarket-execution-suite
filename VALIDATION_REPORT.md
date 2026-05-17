# Validation report — v0.23.0 source candidate

## Local/static checks expected for this cleanup package

```bash
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
PYTHONPATH=hermes-polymarket-control/src python -m pytest -q hermes-polymarket-control/tests
python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
python polymarket-execution-engine/validation/check_plan_storage.py
python polymarket-execution-engine/validation/check_live_submit_guard.py
python polymarket-execution-engine/validation/check_sign_only_lifecycle.py
python polymarket-execution-engine/validation/check_runtime_worker_models.py
python polymarket-execution-engine/validation/check_v0_23_lifecycle_api.py
python polymarket-execution-engine/validation/check_v0_23_evidence_manifest.py
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py .
```

## External checks still required

The local packaging environment does not prove:

- Rust format/check/clippy/tests;
- PostgreSQL migration/store/API E2E;
- SDK adapter/spike checks and tests;
- credentialed non-trading smoke;
- sign-only dry-run with real credentials.

Run the full gate externally:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Evidence rule

Only `polymarket-execution-engine/evidence/current/manifest.json` is canonical for current release decisions. Archived or imported logs are audit context only and must not be cited as proof of this final source package unless their artifact hash matches.
