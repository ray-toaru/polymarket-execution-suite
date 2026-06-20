# Polymarket execution suite v0.28.0

v0.28.0 is a **production-live-candidate**, not a production-ready or live-trading release. It preserves the historical closed v0.26 BUY/GTC post-only canary evidence, records one local v0.28 reviewed-go single-attempt canary as consumed and closed, and adds executor-side safety and release-governance hardening. The source artifact remains non-live; any future live execution still requires current gates plus a fresh reviewed `go` decision and operator approval.

This repository is the integration repository. It pins two independent implementation repositories as
submodules:

- `hermes-polymarket-executor-adapter`: Python Hermes-compatible executor adapter for typed executor API calls, schema models, tool/report wrappers, and service/admin token separation. It must not hold private keys, CLOB secrets, raw signed payloads, or live-submit authority.
- `polymarket-execution-engine`: Rust execution plane for deterministic validation, lifecycle persistence, runtime state, authorization, signing-boundary isolation, and non-live SDK integration scaffolding.

## Checkout

Clone or refresh with submodules:

```bash
git clone --recurse-submodules https://github.com/ray-toaru/polymarket-execution-suite.git
cd polymarket-execution-suite
git submodule update --init --recursive
```

Private submodules require a GitHub credential that can read both pinned
component repositories. CI uses an explicit submodule token; it is never
written into the release package.

In this local workspace the submodules point at sibling repositories:

```text
../hermes-polymarket-executor-adapter
../polymarket-execution-engine
```

## Canonical documents

Use these current documents first:

- `AGENTS.md` — repository-level agent instructions, safety boundaries, and validation rules.
- `CONTRIBUTING.md` — branch, review, validation, and release-tag policy.
- `SECURITY.md` — private vulnerability reporting policy.
- `PROJECT_ARCHITECTURE.md` — current architecture baseline from the v0.3 design split.
- `COMPONENT_COMPATIBILITY.md` — component ownership, compatibility matrix, and independent versioning policy.
- `DEPENDENCY_POLICY.md` — pinned runtime/toolchain/dependency policy.
- `SECURITY_MODEL.md` — trust boundaries, threats, operator misuse controls, and evidence retention.
- `OFFLINE_INDEPENDENT_REVIEW_MANUAL.md` — detached-signature dual-control procedure when GitHub cannot enforce reviewers.
- `DESIGN_DECISION_RECORD.md` — accepted architectural decisions.
- `IMPLEMENTATION_STATUS.md` — implemented, blocked, and intentionally disabled areas.
- `CONTROLLED_CANARY_CLOSEOUT.md` — tracked summary for the controlled canary closeout boundary and evidence requirements.
- `CURRENT_PROGRESS.md` — current branch-state and governance-freeze summary.
- `ROADMAP.md` — current integration roadmap and remaining scope.
- `TASKS.md` — current task ledger and completed governance/workflow work.
- `VALIDATION_REPORT.md` — what is locally verified versus externally required.
- `REVIEW_AUDIT.md` — known risks and audit judgment.
- `RELEASE_DECISION.md` — current release truth and explicit non-live decision.
- `DEVELOPMENT_HANDOFF.md` — current handoff state and operating assumptions.
- `DOC_STATUS.md` — document/evidence governance map.
- `NO_LOCAL_ACTIONS_REMAINING.md` — local validation limit boundary for the current line.
- `docs/future/CANARY_DECISION_PREP_AUDIT.md`
- `docs/future/CANARY_GO_NO_GO_REVIEW.md`
- `docs/future/CANARY_PRODUCTION_ROADMAP.md`

Historical root documents and previous gate notes have been moved to `docs/archive/` and are excluded from normal release packaging.

## Validation

Recommended local entry points:

```bash
python -m pip install -c constraints-ci.txt -r requirements-ci.txt
make check-local
make check-shell
make check-hermes HERMES_PROFILE=<local-profile>
make check-package
```

`make check-local` is the default no-side-effect developer gate. It checks
version consistency, contracts, the v0.28 release-posture audit, integration
unit tests, Python bytecode, and docs/evidence governance. It does not refresh
release artifacts, run PostgreSQL-backed gates, call external services, or
authorize live submit/cancel.

`make check-shell` runs shellcheck over local shell gate scripts when
`shellcheck` is installed. If it is not installed, the target prints a skip
message and exits successfully. This target is local lint only; it does not run
current gates, refresh packages, call GitHub, or authorize live actions.

`make check-package` runs local cleanup and release hygiene only; it also does
not rebuild the final release package. Use `scripts/package_release.py` only
during a deliberate package refresh/review cycle.

`make check-current-gates` runs the execution-engine full current gate wrapper:

```bash
make check-current-gates
```

That wrapper requires the Rust/PostgreSQL/SDK prerequisites for the engine
suite and may consume local database resources. Credentialed smoke, sign-only
checks, push, tag, release, production deployment, and real-funds actions remain
separate authorization gates.

`scripts/check_v28_production_live_candidate.py` is audit-only by default. It reports
the remaining blockers before a v0.28 release; use `--require-ready` only for
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
APIs or place/cancel orders. v0.28 closeout refuses to claim clean closure if
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
  --output-dir dist/pmx-v028-reviewed-go-<timestamp> \
  --decision-reason "approved by independent reviewer"
```

This promotion step remains local and authorization-bearing, but still does not
run an armed canary. It packages the reviewed decision and canonical CLI
approval for a later explicit armed invocation.

If you need the lower-level file-by-file entry, it remains available:

```bash
python scripts/prepare_reviewed_go_package.py \
  --output-dir dist/pmx-v028-reviewed-go-<timestamp> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
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

Use `polymarket-execution-engine/.env.profiles.example` for the private source
inventory shape and `polymarket-execution-engine/.env.runtime.example` for the
runtime-facing output shape.

`activate_pmx_profile.py` writes only active identity fields. Supply
secret-bearing values separately through an explicit external secrets env file;
local secret file generation is rejected.

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
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
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

To keep the full governance chain on one root entry point, the wrapper below
plans or runs the two-stage reviewed-go decision workflow:

```bash
python scripts/run_reviewed_go_decision_workflow.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --runtime-env-output polymarket-execution-engine/.env.runtime \
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
  --operator-identity-ref <operator-ref> \
  --approval-ticket-ref <ticket-ref>
```

Without `--run`, it prints the plan only. With `--run`, it executes the
prereview stage and stops at
`review_packet_ready_requires_independent_review` unless all three promotion
inputs are also supplied:

- `--approved-dual-control-review-file`
- `--external-references-file`
- `--reviewed-go-output-dir`

Only when those inputs are present does the same wrapper continue into
reviewed-go package promotion. It does not synthesize reviewer approval or
weaken dual-control boundaries.

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
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
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

Identity contract for these helpers:

- `--profile` is only the local selector used to choose one `PMX_PROFILE_<...>_*`
  source inventory block.
- `PMX_ACTIVE_ACCOUNT_ID` is an opaque runtime identity string copied from that
  source inventory. It does not need to match the profile label spelling.
- `PMX_ACTIVE_PROFILE_REF` is an opaque reference string copied from that source
  inventory. It is compared for exact equality only.

In other words, `acct_b`, `acct-b`, and `local-profile://acct_b` are different
fields with different roles. The tooling does not normalize them into one
canonical spelling; it only enforces that later steps use the same reviewed
runtime identity that was activated into `.env.runtime`.

If you only need the runtime env plus approval request, the narrower bundle
script remains available:

```bash
python scripts/prepare_canary_runtime_bundle.py \
  --profile <profile> \
  --source-env-file polymarket-execution-engine/.env.profiles \
  --runtime-env-output polymarket-execution-engine/.env.runtime \
  --approval-request-output <operator-approval-request.json> \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
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
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip \
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
  --features live-submit --bin pmx-real-funds-canary-armed -- \
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

For the full reviewed-go single-attempt path, including local readback capture
and `closeout.json` / `CLOSEOUT.md` generation, use the workflow wrapper below.
It still fails closed by default and only executes with `--run`. Use this full
workflow only before the one authorized canary attempt has been consumed:

```bash
python scripts/run_reviewed_go_canary_closeout.py \
  --package-dir <reviewed-go-package-dir> \
  --env-file polymarket-execution-engine/.env.runtime
```

When `--run` is supplied, the wrapper executes:

1. reviewed-go preflight
2. reviewed-go armed post/cancel
3. order-status readback
4. trade readback
5. account-activity readback
6. local closeout generation

It does not invent account identity. Data API readback uses `--account-address`
if supplied; otherwise it requires `PMX_CLOB_FUNDER` in the runtime env or
`--secrets-env-file` and fails closed when that address is unavailable.

After an armed attempt has already produced `post-canary-report.json` or an
`approval-consumed-*.json` marker, do not run the full workflow again. Use the
readback/closeout-only mode, which never invokes preflight or the armed
post/cancel step:

```bash
python scripts/run_reviewed_go_canary_closeout.py \
  --package-dir <reviewed-go-package-dir> \
  --env-file polymarket-execution-engine/.env.runtime \
  --secrets-env-file <local-runtime-secrets-env> \
  --readback-closeout-only \
  --run
```

Release packaging writes `dist/INDEX.json` and `dist/README.md`. Only the
indexed `polymarket-execution-suite-v0.28.0.zip` plus its detached sidecars are
the current source artifact after v0.28 packaging; any other `dist/pmx-*`
directory is local review material unless explicitly indexed as current. The
index classifies no-go, consumed, and closed canary material and marks it
non-reusable for approval.

Full Rust/SDK/PostgreSQL validation requires an external Rust 1.88 + PostgreSQL environment:

```bash
cd polymarket-execution-engine
./validation/run_current_gates.sh
```

For the production-control evidence subset, the root suite below plans or runs
the local fail-closed drills as one bundle:

```bash
python scripts/run_production_control_suite.py \
  --release-zip dist/polymarket-execution-suite-v0.28.0.zip
```

With `--run`, it executes the current local suite for:

1. production operations inventory
2. authorization block
3. deployment preflight
4. secret custody
5. monitoring and SLO
6. incident response
7. rollback and downgrade
8. risk limits
9. dependency breakage
10. audit export

It never enables live submit, live cancel, or production-ready claims. If
`--output-dir` is supplied, each drill's JSON result is written there for later
review.

For the live-submit / live-cancel promotion-evidence subset, the root suite
below plans or runs the local fail-closed promotion drills as one bundle:

```bash
python scripts/run_live_submit_promotion_suite.py
```

With `--run`, it executes the current local suite for:

1. live-submit static guard
2. live canary readiness drill
3. live canary preflight drill
4. live canary blocked drill
5. live canary rehearsal drill
6. controlled live canary prep drill
7. real-funds canary preflight drill
8. real-funds canary ready drill
9. real-funds canary lifecycle drill
10. real-funds canary review-package drill

This suite still proves fail-closed promotion evidence only. It does not
authorize live submit, live cancel, production deployment, a second canary, or
generalized order posting.

For deployment-oriented validation, the root suite below plans or runs the
current local deployment evidence drills as one bundle:

```bash
python scripts/run_deployment_validation_suite.py
```

With `--run`, it executes:

1. production deployment preflight drill
2. single-host limited deployment drill
3. single-host canary candidate drill
4. single-host temporary go-candidate drill

This suite improves deployability verification because it combines artifact
binding checks, single-host template validation, local API bind smoke, canary
candidate packaging checks, and temporary go-candidate governance checks. It
still does not authorize production deployment, generalized live submit/cancel,
or a second armed canary.

At the highest level, the root orchestrator below combines the current release
phase workflows without flattening their approval boundaries:

```bash
python scripts/run_release_phase_orchestrator.py
```

Without `--run`, it prints the planned stages. With `--run`, it executes the
currently available root workflows:

1. production control evidence
2. deployment validation evidence
3. live-submit promotion evidence
4. reviewed-go decision chain, but only when its prereview inputs are supplied

If the reviewed-go inputs are incomplete, that stage remains explicitly
blocked. If the approved dual-control review and external references are also
missing, the reviewed-go decision chain stops at
`review_packet_ready_requires_independent_review`.

This orchestrator improves release-phase operability, but it is still only a
workflow aggregator. It does not authorize production deployment, live submit,
live cancel, or any new armed canary by itself.

## Safety boundary

Still intentionally blocked:

- live `post_order` / `post_orders`;
- live cancel;
- production deployment;
- Python-side signing or direct CLOB trading;
- public exposure of private keys, CLOB secrets, raw signed payloads, or signed order envelopes.
