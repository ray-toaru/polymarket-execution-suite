# Validation report — v0.25.0 shadow-ready SDK sign-only baseline

## Current conclusion

`polymarket-execution-engine/evidence/current/manifest.json` records a passing
full gate run for the pinned source package. Current release decision remains
`shadow-ready SDK sign-only candidate`, not production-ready and not live-trading-ready.

Bound artifact:

```text
polymarket-execution-suite-v0.25.0.zip
sha256=recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

## Local/static checks

```bash
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
HERMES_PROFILE=hm-pdp-test PYTHONPATH=hermes-polymarket-control/src python -m pytest -q hermes-polymarket-control/tests
HERMES_PROFILE=hm-pdp-test python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
python polymarket-execution-engine/validation/check_plan_storage.py
python polymarket-execution-engine/validation/check_live_submit_guard.py
python polymarket-execution-engine/validation/check_sign_only_lifecycle.py
python polymarket-execution-engine/validation/check_runtime_worker_models.py
python polymarket-execution-engine/validation/check_current_lifecycle_api.py
python polymarket-execution-engine/validation/check_current_evidence_manifest.py
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
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

The latest local refresh completed the current gate chain with live
submit/cancel blocked. In this workspace refresh, PostgreSQL and credentialed
SDK sections passed under explicit `PMX_TEST_DATABASE_URL`,
`PMX_RUN_AUTHENTICATED_NON_TRADING_SMOKE`, `PMX_RUN_SIGN_ONLY_DRY_RUN`, and
`PMX_ALLOW_SIGN_ONLY_DRY_RUN` prerequisites. Hermes validation is run with the
`hm-pdp-test` profile.

Re-run command:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Evidence rule

Only `polymarket-execution-engine/evidence/current/manifest.json` is canonical for current release decisions. Archived or imported logs are audit context only and must not be cited as proof of this final source package unless their artifact hash matches.
