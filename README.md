# Polymarket execution suite v0.28.0

v0.28.0 is a **production-live-candidate**, not a production-ready or live-trading release. It preserves the closed v0.26 BUY/GTC post-only canary evidence and adds executor-side safety and release-governance hardening. Further live execution still requires current gates plus a fresh reviewed `go` decision, durable runtime truth, dual-control review, operator approval, and an explicit wrapper invocation.

This repository is the integration repository. It pins two independent implementation repositories as submodules:

- `hermes-polymarket-executor-adapter`: Python Hermes-compatible executor adapter for typed executor API calls, schema models, tool/report wrappers, and service/admin token separation. It must not hold private keys, CLOB secrets, raw signed payloads, or live-submit authority.
- `polymarket-execution-engine`: Rust execution plane for deterministic validation, lifecycle persistence, runtime state, authorization, signing-boundary isolation, and non-live SDK integration scaffolding.

## Checkout

Clone or refresh with submodules:

```bash
git submodule update --init --recursive
```

If submodules are not initialized, `scripts/check_version_consistency.py` fails with an explicit remediation message instead of a low-level missing-file error.

## Canonical documents

Use these current documents first:

- `AGENTS.md` — repository-level agent instructions, safety boundaries, and validation rules.
- `PROJECT_ARCHITECTURE.md` — current architecture baseline from the v0.3 design split.
- `COMPONENT_COMPATIBILITY.md` — component ownership, compatibility matrix, and independent versioning policy.
- `DEPENDENCY_POLICY.md` — pinned runtime/toolchain/dependency policy.
- `DESIGN_DECISION_RECORD.md` — accepted architectural decisions.
- `IMPLEMENTATION_STATUS.md` — implemented, blocked, and intentionally disabled areas.
- `CONTROLLED_CANARY_CLOSEOUT.md` — tracked summary for the completed one-time v0.26 controlled canary.
- `VALIDATION_REPORT.md` — what is locally verified versus externally required.
- `REVIEW_AUDIT.md` — known risks and audit judgment.
- `DOC_STATUS.md` — document/evidence governance map.

Historical root documents and previous gate notes have been moved to `docs/archive/` and are excluded from normal release packaging.

## Validation

Integration-level local/static validation entry points:

```bash
python -m pip install -c constraints-ci.txt -r requirements-ci.txt
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
python scripts/check_v28_production_live_candidate.py
python -m unittest discover -s tests -p "test_*.py"
HERMES_PROFILE=<local-profile> PYTHONPATH=hermes-polymarket-executor-adapter/src python -m pytest -q hermes-polymarket-executor-adapter/tests
HERMES_PROFILE=<local-profile> python -m compileall -q hermes-polymarket-executor-adapter/src scripts tests polymarket-execution-engine/validation
python scripts/check_hermes_profile_plugin.py --profile-cmd <local-profile-command>
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

`scripts/check_v28_production_live_candidate.py` is audit-only by default. It reports remaining blockers before a v0.28 release. Use `--require-ready --target-version "$(cat VERSION)"` only for the final release/tag gate after version files, manifests, reports, sidecars, and full gates have been refreshed together.

Full Rust/SDK/PostgreSQL validation requires an external Rust 1.88 + PostgreSQL environment:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Controlled canary candidate and no-go path

Controlled canary review packages require an operator-reviewed market candidate file. The root helper below reads only public market/book/spread APIs and writes the execution-engine input shape; it does not authorize live trading.

```bash
python scripts/prepare_canary_candidate_market.py \
  --market-url <polymarket-event-or-market-url> \
  --outcome Yes \
  --output candidate-market.json \
  --audit-output candidate-market.audit.json \
  --human-review-ref change-ticket://reviewed-canary-market
```

The reviewed candidate carries a share `target_size`. The canary order uses `size = target_size`; `notional_usd` is derived as `limit_price * target_size` for risk caps. It must also bind an `exchange_rule_snapshot` with fresh evidence for the effective order mode. For the current `BUY/GTC` post-only path, local gates check `post_only=true`, live/accepting market state, non-crossing limit price, tick alignment, and risk-cap coverage before any armed wrapper plan can be built.

The fail-closed preparation pipeline below is safe to run locally. It can use a fresh candidate or an existing candidate file, then generates a no-go review package and proves the armed adapter command is blocked by release decision before any remote side effect. It does not create a reviewed-go decision and does not submit or cancel live orders.

```bash
python scripts/run_controlled_canary_pipeline.py \
  --output-dir dist/pmx-canary-pipeline-no-go-local \
  --candidate-market-file candidate-market.json
```

## Runtime truth and approval request

Runtime truth must be validated before it can be bound into any operator approval request:

```bash
cd polymarket-execution-engine
python validation/run_real_funds_canary_store_truth_cli_preflight.py \
  --artifact-sha256 <release_zip_sha256> \
  --workspace-manifest-sha256 <workspace_manifest_sha256> \
  --archived-manifest-sha256 <archived_manifest_sha256> \
  --runtime-truth-output /path/to/reviewed-runtime-truth.json
python validation/validate_controlled_canary_runtime_truth.py \
  --file /path/to/reviewed-runtime-truth.json
```

The root approval tooling now requires current CI evidence, including an explicit `--credentialed-sdk-run-id`. There is no safe default for credentialed SDK evidence.

For multi-account local operation, keep profile-specific secrets in a private source inventory and activate exactly one account profile into generic runtime variables before any preflight or armed command. Runtime secret output is allowed only with an explicit secret-writing path policy.

```bash
python scripts/activate_pmx_profile.py \
  --profile <profile> \
  --source-env-file <private-profile-inventory.env> \
  --output <private-runtime-env-path>

python polymarket-execution-engine/validation/check_active_profile_consistency.py \
  --env-file <private-runtime-env-path> \
  --expected-account-id <approved-account-id>
```

Runtime commands must consume only generic runtime variables such as `POLYMARKET_PRIVATE_KEY`, `POLY_API_*`, `PMX_CLOB_FUNDER`, `PMX_CLOB_SIGNATURE_TYPE`, and active-profile metadata. They must not consume `PMX_PROFILE_*` or `PMX_ACCT_*` source inventory directly.

## Non-authorizing review bundle flow

For the full local pre-review path, prepare the fresh public candidate, PostgreSQL-backed runtime truth, activated runtime env, approval request, dual-control template, and non-authorizing review packet in one step:

```bash
python scripts/prepare_canary_prereview_bundle.py \
  --profile <profile> \
  --source-env-file <private-profile-inventory.env> \
  --runtime-env-output <private-runtime-env-path> \
  --candidate-market-output <candidate-market.json> \
  --candidate-audit-output <candidate-market.audit.json> \
  --runtime-truth-output <runtime-truth.json> \
  --approval-request-output <operator-approval-request.json> \
  --dual-control-template-output <dual-control-review.template.json> \
  --review-packet-output-dir <review-packet-dir> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
  --market-url <polymarket-event-or-market-url> \
  --outcome Yes \
  --human-review-ref <market-review-ref> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --credentialed-sdk-run-id <credentialed-sdk-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

If you already have a fresh candidate and runtime truth, the narrower review bundle helper remains available. It binds the same runtime env so `account_id` and `active_profile_ref` are derived from the activated profile instead of being retyped by hand:

```bash
python scripts/prepare_canary_review_bundle.py \
  --profile <profile> \
  --source-env-file <private-profile-inventory.env> \
  --runtime-env-output <private-runtime-env-path> \
  --approval-request-output <operator-approval-request.json> \
  --dual-control-template-output <dual-control-review.template.json> \
  --review-packet-output-dir <review-packet-dir> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --credentialed-sdk-run-id <credentialed-sdk-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

If you only need the runtime env plus approval request, the narrower bundle script remains available:

```bash
python scripts/prepare_canary_runtime_bundle.py \
  --profile <profile> \
  --source-env-file <private-profile-inventory.env> \
  --runtime-env-output <private-runtime-env-path> \
  --approval-request-output <operator-approval-request.json> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --credentialed-sdk-run-id <credentialed-sdk-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

The lower-level command remains available when you already have a prepared runtime env and only want to regenerate the approval request:

```bash
python scripts/prepare_operator_approval_request.py \
  --output <operator-approval-request.json> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --runtime-env-file <private-runtime-env-path> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --credentialed-sdk-run-id <credentialed-sdk-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

`approval-request.json` is not an authorization. It is the governance request and dual-control binding record. `dual-control-review.template.json` is also not an authorization. A later approved dual-control review and reviewed-go package are required before any armed path can be planned.

## Reviewed-go package and explicit wrapper path

When an independent reviewer has produced an approved dual-control review JSON, the highest-level promotion helper can turn the review packet into a self-contained reviewed-go package:

```bash
python scripts/prepare_canary_reviewed_go_bundle.py \
  --review-packet-dir <review-packet-dir> \
  --approved-dual-control-review-file <approved-dual-control-review.json> \
  --external-references-file <external-references.json> \
  --output-dir dist/pmx-canary-reviewed-go-<timestamp> \
  --decision-reason "approved by independent reviewer"
```

The reviewed-go package is authorization-bearing local material. Do not commit, upload, email, or re-package it unless it is encrypted and separately approved. It must stay single-use, must be marked consumed after any armed attempt, and must then be closed with the tracked closeout flow before any later review.

The reviewed-go package contains two distinct approval artifacts:

- `approval-request.json`: the governance request and dual-control binding record.
- `approval.json`: the canonical CLI approval consumed by `pmx-real-funds-canary`.

Operators should use `scripts/run_reviewed_go_canary.py` rather than hand-building the lower-level cargo command. The wrapper resolves package files, validates that the reviewed-go package is still fresh, checks active runtime profile binding, verifies approval/runtime/review hashes, prints the exact invocation plan, and does not execute unless `--run` is supplied.

Dry-run planning path:

```bash
python scripts/run_reviewed_go_canary.py \
  --package-dir <reviewed-go-package-dir> \
  --env-file <private-runtime-env-path> \
  --mode preflight
```

Armed execution remains an explicit operator action. The wrapper deliberately does not auto-set gate env vars; it reports any missing gate variables in its invocation plan. For a real invocation, set the required gate env vars in the shell and opt into execution:

```bash
PMX_ALLOW_LIVE_SUBMIT=1 \
PMX_ALLOW_REAL_FUNDS_CANARY=1 \
PMX_KILL_SWITCH_OPEN=1 \
PMX_RUNTIME_WORKER_HEALTHY=1 \
PMX_GEOBLOCK_ALLOWED=1 \
PMX_REPOSITORY_RESERVATION_EXISTS=1 \
PMX_IDEMPOTENCY_KEY_WRITTEN=1 \
PMX_RECONCILE_WORKER_HEALTHY=1 \
PMX_CANCEL_ONLY_FALLBACK_READY=1 \
PMX_BALANCE_ALLOWANCE_CHECKED=1 \
python scripts/run_reviewed_go_canary.py \
  --package-dir <reviewed-go-package-dir> \
  --env-file <private-runtime-env-path> \
  --mode armed \
  --run
```

## Release packaging

Release packaging writes `dist/INDEX.json` and `dist/README.md`. Only the indexed `polymarket-execution-suite-v0.28.0.zip` plus its detached sidecars are the current source artifact after v0.28 packaging; any other `dist/pmx-*` directory is local review material unless explicitly indexed as current. The index classifies no-go, consumed, and closed canary material and marks it non-reusable for approval.

```bash
artifact="$(python scripts/package_release.py | tail -n 1)"
python scripts/check_release_artifact.py "$artifact" "$(cat VERSION)"
```

## Safety boundary

Still intentionally blocked by default:

- live `post_order` / `post_orders`;
- live cancel;
- production deployment;
- Python-side signing or direct CLOB trading;
- public exposure of private keys, CLOB secrets, raw signed payloads, signed order envelopes, reviewed-go packages, or runtime env files.

The project-level term `production-live-candidate` means: source, governance, and operator tooling are moving toward a controlled production live canary, but the release remains non-live by default and is not production-ready or live-trading-ready until all current gates and reviewed-go/closeout requirements are freshly satisfied.
