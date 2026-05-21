# Validation report — v0.25.0 shadow-ready SDK sign-only baseline

## Current conclusion

`polymarket-execution-engine/evidence/current/manifest.json` records a passing
source-candidate gate run for the pinned source package, including credentialed
non-trading smoke and sign-only dry-run under explicit local env gates. Current
release decision remains `shadow-ready SDK sign-only candidate`, not
production-ready and not live-trading-ready.

Bound artifact:

```text
polymarket-execution-suite-v0.25.0.zip
sha256=recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

Latest pushed CI/evidence checkpoint:

```text
root_ci_run_id=26254755001
execution_engine_ci_run_id=26254745573
hermes_ci_run_id=26198048337
current_local_hermes_commit=cd6491df9a3a07028996159788e0b1366a44c0d9
current_local_execution_engine_commit=399996403fa2bd4d5af4490fcd1c31dfc7a9814b
evidence_manifest_sha256=b8a9cf6a92c54363333c703ec7ee3754db1d4c1b8ae78f7136b61aafe7bc56b4
release_zip_sha256=recorded in external .zip.sha256 and .zip.evidence.json sidecars
```

This checkpoint plus the local checks below records validation status only. It
does not promote the release decision and does not authorize production
deployment, live submit, live cancel, or real-funds canary execution.

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

Use local/static checks as the default validation path for routine edits. Do
not push solely to trigger GitHub CI for every small change. Remote CI is the
confirmation layer for release candidates, submodule pointer updates, GitHub
Environment or secret wiring, runner-specific behavior, and changes that cannot
be reproduced locally.

Latest local targeted review-package checks passed with no new CI run:

```bash
.venv/bin/python scripts/check_version_consistency.py
.venv/bin/python scripts/validate_contracts.py
HERMES_PROFILE=hm-pdp-test PYTHONPATH=hermes-polymarket-control/src .venv/bin/python -m pytest -q hermes-polymarket-control/tests
HERMES_PROFILE=hm-pdp-test .venv/bin/python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
.venv/bin/python polymarket-execution-engine/validation/run_single_host_deployment_drill.py
.venv/bin/python polymarket-execution-engine/validation/run_single_host_canary_candidate_drill.py
.venv/bin/python polymarket-execution-engine/validation/run_single_host_go_candidate_drill.py
.venv/bin/python polymarket-execution-engine/validation/run_real_funds_canary_blocked_rehearsal_package.py
.venv/bin/python polymarket-execution-engine/validation/run_real_funds_canary_review_package_drill.py
.venv/bin/python polymarket-execution-engine/validation/validate_controlled_canary_external_references.py --file dist/pmx-canary-review-reviewed/external-references.json
.venv/bin/python scripts/package_release.py
.venv/bin/python scripts/check_release_artifact.py dist/polymarket-execution-suite-v0.25.0.zip 0.25.0
.venv/bin/python polymarket-execution-engine/validation/prepare_real_funds_canary_review.py --external-references-file dist/pmx-canary-review-reviewed/external-references.json --artifact-sha256 <release-zip-sha256-from-sidecar> --evidence-manifest-sha256 <current-evidence-manifest-sha256> --output-dir /tmp/pmx-canary-review-final-release-check
.venv/bin/python scripts/prepare_canary_candidate_market.py --output /tmp/pmx-canary-review-final-release-check/candidate-market.json --audit-output /tmp/pmx-canary-review-final-release-check/candidate-market.audit.json --max-markets 5 --timeout-seconds 8
cd polymarket-execution-engine && cargo run --manifest-path adapters/pmx-official-sdk-adapter/Cargo.toml --features live-submit --bin pmx-real-funds-canary -- --dry-run --approval-file /tmp/pmx-canary-review-final-release-check/approval.json --artifact-sha256 <release-zip-sha256-from-sidecar> --evidence-manifest-sha256 <current-evidence-manifest-sha256> --idempotency-key dry-run-final-release-check-20260521 --account-id acct-canary --execution-id exec-canary-dry-run-final-release-check-20260521 --plan-hash plan-canary-dry-run-final-release-check-20260521 --market-file /tmp/pmx-canary-review-final-release-check/candidate-market.json
.venv/bin/python scripts/check_hermes_no_secrets.py
.venv/bin/python polymarket-execution-engine/validation/check_docs_evidence_governance.py
.venv/bin/python polymarket-execution-engine/validation/check_current_evidence_manifest.py
.venv/bin/python scripts/clean_local_artifacts.py
.venv/bin/python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

The local reviewed package uses reference-only local custody via `pass`/GPG, a
`no_go` operator approval hash, and a manual GitHub-issue alert route. This is
review material only: live submit, live cancel, production deployment,
real-funds canary execution, and remote side effects remain blocked.
The blocked rehearsal script also invokes the real-funds canary CLI with
`--armed` and local allow-config flags, then verifies the `no_go` adapter
release decision blocks at the release-decision gate before posting,
cancelling, raw signed order exposure, or remote side effects.

## Full gate evidence

The latest pushed GitHub Actions baseline runs for this source/evidence refresh
are:

```text
polymarket-execution-suite ci: 26254755001, success
polymarket-execution-engine ci: 26254745573, success
```

Repository ownership is intentionally split:

- the integration repository validates version consistency, contracts, release
  hygiene, packaging, and artifact validation;
- `hermes-polymarket-control` validates the Python control plane in its own CI;
- `polymarket-execution-engine` validates Rust locked checks, PostgreSQL gates,
  current gates, SDK adapter checks, and owns the manual `credentialed-sdk`
  workflow.

The latest execution-engine CI completed:

- Rust fmt/check/clippy/tests;
- PostgreSQL migration, repository tests, and API E2E;
- SDK spike and adapter checks/tests/typecheck;
- static release and safety guards;
- current gates.

The latest canonical evidence refresh was generated at
`2026-05-21T23:22:48.922574+00:00`. It records:

- PostgreSQL validation: `pass`;
- credentialed non-trading smoke: `pass`;
- sign-only dry-run: `pass`;
- shadow execution would-submit drill;
- observability evidence guard;
- migration drift dry-run;
- release hygiene, release artifact check, contract validation, and docs/evidence governance.
- single-host limited deployment validation: `pass`; deployment templates are
  dry-run/fail-closed and do not authorize live submit, live cancel, production
  deployment, or real-funds canary execution.
- single-host canary candidate validation: `pass`; reviewed package material
  binds the release artifact and evidence manifest, but remains `no_go`,
  dry-run only, and no-remote-side-effect.
- single-host temporary `go` candidate validation: `pass`; no `go` file is
  committed and missing reviewed release-decision input still blocks armed
  execution.

The latest local refresh completed the current gate chain with live
submit/cancel blocked. PostgreSQL passed under explicit
`PMX_TEST_DATABASE_URL`; credentialed SDK sections passed under explicit
`PMX_RUN_AUTHENTICATED_NON_TRADING_SMOKE=1`,
`PMX_RUN_SIGN_ONLY_DRY_RUN=1`, and `PMX_ALLOW_SIGN_ONLY_DRY_RUN=1`.
Hermes validation is run with the `hm-pdp-test` profile.

The credentialed checks validate authenticated non-trading smoke and sign-only
dry-run only. They do not authorize live submit, live cancel, or real-funds
canary execution.

Re-run command:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Evidence rule

Only `polymarket-execution-engine/evidence/current/manifest.json` is canonical for current release decisions. Archived or imported logs are audit context only and must not be cited as proof of this final source package unless their artifact hash matches.
