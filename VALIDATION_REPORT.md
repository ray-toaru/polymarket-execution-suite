# Validation report — v0.24.0 shadow-ready baseline

## Current conclusion

`polymarket-execution-engine/evidence/current/manifest.json` records a passing
full gate run for the pinned source package. Current release decision remains
`shadow-ready candidate`, not production-ready and not live-trading-ready.

Bound artifact:

```text
polymarket-dual-project-v0.24.0.zip
sha256=fd476e36af78099ba542cd6f030ccdd01f325565e8a5667d0d791c2479eaf0be
```

## Local/static checks

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

## Full gate evidence

The latest full gate included:

- Rust fmt/check/clippy/tests;
- PostgreSQL migration, repository tests, and API E2E;
- SDK spike and adapter checks/tests/typecheck;
- credentialed non-trading smoke;
- sign-only dry-run;
- shadow execution would-submit drill;
- observability evidence guard;
- migration drift dry-run;
- release hygiene, release artifact check, contract validation, and docs/evidence governance.

Re-run command:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Evidence rule

Only `polymarket-execution-engine/evidence/current/manifest.json` is canonical for current release decisions. Archived or imported logs are audit context only and must not be cited as proof of this final source package unless their artifact hash matches.
