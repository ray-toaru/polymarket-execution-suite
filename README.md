# Polymarket execution suite v0.27.3

v0.27.3 is a **controlled real-funds canary source-candidate**, not a production-ready or live-trading release. It preserves the closed v0.26 BUY/GTC post-only canary evidence and adds executor-side safety and release-governance hardening. Further live execution still requires current gates plus a fresh reviewed `go` decision and operator approval.

This repository is the integration repository. It pins two independent implementation repositories as
submodules:

- `hermes-polymarket-executor-adapter`: Python Hermes-compatible executor adapter for typed executor API calls, schema models, tool/report wrappers, and service/admin token separation. It must not hold private keys, CLOB secrets, raw signed payloads, or live-submit authority.
- `polymarket-execution-engine`: Rust execution plane for deterministic validation, lifecycle persistence, runtime state, authorization, signing-boundary isolation, and non-live SDK integration scaffolding.

## Checkout

Clone or refresh with submodules:

```bash
git submodule update --init --recursive
```

In this local workspace the submodules point at sibling repositories:

```text
../hermes-polymarket-executor-adapter
../polymarket-execution-engine
```

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
python -m pip install -r requirements-ci.txt
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
python scripts/check_v27_release_readiness.py
python -m unittest discover -s tests -p "test_*.py"
HERMES_PROFILE=<local-profile> PYTHONPATH=hermes-polymarket-executor-adapter/src python -m pytest -q hermes-polymarket-executor-adapter/tests
HERMES_PROFILE=<local-profile> python -m compileall -q hermes-polymarket-executor-adapter/src scripts tests polymarket-execution-engine/validation
python scripts/check_hermes_profile_plugin.py --profile-cmd <local-profile-command>
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

`scripts/check_v27_release_readiness.py` is audit-only by default. It reports
the remaining blockers before a v0.27 release; use `--require-ready` only for
the final release gate after version files, manifests, reports, sidecars, and
full gates have been refreshed together.

Controlled canary review packages require an operator-reviewed market candidate
file. The root helper below reads only public market/book/spread APIs and writes
the execution-engine input shape; it does not authorize live trading.

```bash
python scripts/prepare_canary_candidate_market.py \
  --market-url <polymarket-event-or-market-url> \
  --outcome Yes \
  --output candidate-market.json \
  --audit-output candidate-market.audit.json \
  --human-review-ref change-ticket://reviewed-canary-market
```

The reviewed candidate carries a share `target_size`. The canary order uses
`size = target_size`; `notional_usd` is derived as `limit_price * target_size`
for risk caps. It must also bind an `exchange_rule_snapshot` with fresh
evidence for the effective order mode. For the current `BUY/GTC` post-only
path, the local gate checks `post_only=true` and a non-crossing limit price
before any armed command can post. An armed canary must cancel the posted order
and fail if cancel confirmation is missing. Future armed runs must also pass a
`--report-file` path so the post/cancel receipt is persisted as package evidence.

The fail-closed preparation pipeline below is safe to run locally. It can use a
fresh candidate or an existing candidate file, then generates a no-go review
package and proves the armed adapter command is blocked by release decision
before any remote side effect. It does not create a reviewed-go decision and
does not submit or cancel live orders.

For a supplied candidate, the pipeline performs a local dynamic-rule check
before invoking the engine rehearsal. The candidate must bind a fresh
`exchange_rule_snapshot` for `BUY/GTC` post-only behavior, including
`min_share_size`, `min_tick_size`, `target_size_semantics=outcome_shares`, and
an external evidence reference. The pipeline report also emits a stage plan for
candidate, no-go review, blocked rehearsal, reviewed-go, armed post/cancel,
readback, and closeout, plus runtime-truth dependencies that must be promoted
from local evidence before any future live run.

Optional `--reviewed-go-decision-file`, `--runtime-truth-file`, and
`--closeout-package-dir` inputs are local validation hooks. A reviewed-go file
must be single-attempt scoped (`max_order_count=1`, post/cancel and
readback/closeout required). A runtime-truth file must prove durable
`kill_switch`, `live_submit_gate`, `idempotency_lease`, and
`order_cancel_reconciliation` dependencies before the report marks the armed
stage as operator-runnable. Use
`polymarket-execution-engine/config/controlled-canary.runtime-truth.template.json`
as the input shape; it is references-only and does not authorize live submit by
itself. A closeout package runs the read-only closeout
script and records the resulting local evidence hash plus
`post-canary-report.json.stages.jsonl` summary/hash; it does not query remote
APIs or place/cancel orders. v0.27 closeout refuses to claim clean closure if
the ordered stage history is missing, exposes raw signed material, references a
different remote order id, or contains an unresolved `operator_required` stage.
If an `operator_required` stage occurred, the package must also include
`operator-recovery.json` bound to the stage-history hash, the same remote order
id, no-retry/no-second-order assertions, and the readback evidence files.
For `post_unknown` without a remote order id, ordinary order closeout is not
valid; the package must instead include `operator-incident-recovery.json` with
`operator_reviewed_no_remote_order_found_no_retry`, a bound investigation
window, and account-level open-order/trade/activity readback proving no matching
remote order or fill was found.

Validate runtime truth before passing it to the pipeline:

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

The pipeline also emits an `operator_runbook` block. It is blocked by default;
even with a future fresh reviewed-go decision and durable runtime-truth input,
the runbook is marked operator-runnable, not auto-executed. Already consumed or
closed reviewed-go package directories are rejected before rehearsal.

```bash
python scripts/run_controlled_canary_pipeline.py \
  --output-dir dist/pmx-canary-pipeline-no-go-local \
  --candidate-market-file candidate-market.json
```

When an independent reviewer has produced an approved dual-control review JSON,
the highest-level promotion helper can turn the review packet into a
self-contained reviewed-go package:

```bash
python scripts/prepare_canary_reviewed_go_bundle.py \
  --review-packet-dir <review-packet-dir> \
  --approved-dual-control-review-file <approved-dual-control-review.json> \
  --external-references-file <external-references.json> \
  --output-dir dist/pmx-canary-reviewed-go-<timestamp> \
  --decision-reason "approved by independent reviewer"
```

This promotion step remains local and authorization-bearing, but still does not
run an armed canary. It packages the reviewed decision and canonical CLI
approval for a later explicit armed invocation.

If you need the lower-level file-by-file entry, it remains available:

```bash
python scripts/prepare_reviewed_go_package.py \
  --output-dir dist/pmx-canary-reviewed-go-<timestamp> \
  --release-zip dist/polymarket-execution-suite-v0.27.3.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --approval-request-file <operator-approval-request.json> \
  --dual-control-review-file <approved-dual-control-review.json> \
  --external-references-file <external-references.json> \
  --decision-id reviewed-go-<timestamp> \
  --decision-reason "approved by independent reviewer"
```

This package is authorization-bearing local material. It must stay single-use,
must be marked consumed after any armed attempt, and must then be closed with
the tracked closeout flow before any later review.

The reviewed-go package now contains two distinct approval artifacts:

- `approval-request.json`: the governance request and dual-control binding record
- `approval.json`: the canonical CLI approval consumed by `pmx-real-funds-canary`

For multi-account local operation, keep profile-specific secrets in a private
source inventory and activate exactly one account profile into generic runtime
variables before any preflight or armed command:

```bash
python scripts/activate_pmx_profile.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --output polymarket-execution-engine/.env.runtime

python polymarket-execution-engine/validation/check_active_profile_consistency.py \
  --env-file polymarket-execution-engine/.env.runtime \
  --expected-account-id <approved-account-id>
```

The runtime-facing env file must expose only generic variables such as
`POLYMARKET_PRIVATE_KEY`, `POLY_API_*`, `PMX_CLOB_FUNDER`,
`PMX_CLOB_SIGNATURE_TYPE`, and active-profile metadata. Runtime commands must
not consume `PMX_PROFILE_*` or `PMX_ACCT_*` source inventory directly.

For the full local pre-review path, you can now prepare the fresh public
candidate, PostgreSQL-backed runtime-truth, activated runtime env, approval
request, dual-control template, and non-authorizing review packet in one step:

```bash
python scripts/prepare_canary_prereview_bundle.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --runtime-env-output polymarket-execution-engine/.env.runtime \
  --candidate-market-output <candidate-market.json> \
  --candidate-audit-output <candidate-market.audit.json> \
  --runtime-truth-output <runtime-truth.json> \
  --approval-request-output <operator-approval-request.json> \
  --dual-control-template-output <dual-control-review.template.json> \
  --review-packet-output-dir <review-packet-dir> \
  --release-zip dist/polymarket-execution-suite-v0.27.3.zip \
  --market-url <polymarket-event-or-market-url> \
  --outcome Yes \
  --human-review-ref <market-review-ref> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

This highest-level helper prepares:

- `candidate-market.json`
- `candidate-market.audit.json`
- `runtime-truth.json`
- `.env.runtime`
- `operator-approval-request.json`
- `dual-control-review.template.json`
- a non-authorizing dual-control review packet directory

If you already have a fresh candidate and runtime-truth, the narrower review
bundle helper remains available. It still binds the same runtime env so
`account_id` and `active_profile_ref` are derived from the activated profile
instead of being retyped by hand:

```bash
python scripts/prepare_canary_review_bundle.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --runtime-env-output polymarket-execution-engine/.env.runtime \
  --approval-request-output <operator-approval-request.json> \
  --dual-control-template-output <dual-control-review.template.json> \
  --review-packet-output-dir <review-packet-dir> \
  --release-zip dist/polymarket-execution-suite-v0.27.3.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

This high-level helper prepares:

- `.env.runtime`
- `operator-approval-request.json`
- `dual-control-review.template.json`
- a non-authorizing dual-control review packet directory

If you only need the runtime env plus approval request, the narrower bundle
script remains available:

```bash
python scripts/prepare_canary_runtime_bundle.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --runtime-env-output polymarket-execution-engine/.env.runtime \
  --approval-request-output <operator-approval-request.json> \
  --release-zip dist/polymarket-execution-suite-v0.27.3.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

The lower-level command remains available when you already have a prepared
`.env.runtime` and only want to regenerate the approval request:

```bash
python scripts/prepare_operator_approval_request.py \
  --output <operator-approval-request.json> \
  --release-zip dist/polymarket-execution-suite-v0.27.3.zip \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --runtime-env-file polymarket-execution-engine/.env.runtime \
  --root-ci-run-id <root-ci-run-id> \
  --hermes-ci-run-id <hermes-ci-run-id> \
  --execution-engine-ci-run-id <execution-engine-ci-run-id> \
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

For armed execution, pass the canonical approval file plus an explicit env file:

```bash
cargo run --manifest-path polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.toml \
  --features live-submit --bin pmx-real-funds-canary -- \
  --armed \
  --env-file polymarket-execution-engine/.env.runtime \
  --approval-file <reviewed-go-package>/approval.json \
  --release-decision-file <reviewed-go-package>/release-decision.json \
  --runtime-truth-file <runtime-truth.json> \
  ...
```

To avoid rebuilding that command by hand every time, the wrapper below resolves
the package files, validates that the reviewed-go package is still fresh, checks
the active runtime profile env, and prints the exact invocation plan. It does
not execute unless `--run` is supplied:

```bash
python scripts/run_reviewed_go_canary.py \
  --package-dir <reviewed-go-package-dir> \
  --env-file polymarket-execution-engine/.env.runtime \
  --mode preflight
```

For a real invocation, keep the required gate env vars explicit in the shell
and opt into execution:

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
  --env-file polymarket-execution-engine/.env.runtime \
  --mode armed \
  --run
```

This wrapper deliberately does not auto-set those gate env vars. They remain
explicit operator assertions, and the script will report any that are missing in
its invocation plan output.

Release packaging writes `dist/INDEX.json` and `dist/README.md`. Only the
indexed `polymarket-execution-suite-v0.27.3.zip` plus its detached sidecars are
the current source artifact after v0.27 packaging; any other `dist/pmx-*`
directory is local review material unless explicitly indexed as current. The
index classifies no-go, consumed, and closed canary material and marks it
non-reusable for approval.

Full Rust/SDK/PostgreSQL validation requires an external Rust 1.88 + PostgreSQL environment:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

## Safety boundary

Still intentionally blocked:

- live `post_order` / `post_orders`;
- live cancel;
- production deployment;
- Python-side signing or direct CLOB trading;
- public exposure of private keys, CLOB secrets, raw signed payloads, or signed order envelopes.
