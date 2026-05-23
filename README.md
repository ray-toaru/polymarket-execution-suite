# Polymarket execution suite v0.26.0

v0.26.0 is a **controlled real-funds canary source-candidate**, not a production-ready or live-trading release. It has one closed BUY/GTC post-only canary exercise with cancel, order, trade, and account-activity readback evidence, but further live execution still requires current gates plus a fresh reviewed `go` decision and operator approval.

This repository is the integration repository. It pins two independent implementation repositories as
submodules:

- `hermes-polymarket-control`: Python control plane for intents, approvals, reporting, and executor API calls. It must not hold private keys, CLOB secrets, raw signed payloads, or live-submit authority.
- `polymarket-execution-engine`: Rust execution plane for deterministic validation, lifecycle persistence, runtime state, authorization, signing-boundary isolation, and non-live SDK integration scaffolding.

## Checkout

Clone or refresh with submodules:

```bash
git submodule update --init --recursive
```

In this local workspace the submodules point at sibling repositories:

```text
../hermes-polymarket-control
../polymarket-execution-engine
```

## Canonical documents

Use these current documents first:

- `AGENTS.md` — repository-level agent instructions, safety boundaries, and validation rules.

- `PROJECT_ARCHITECTURE.md` — v0.26 architecture baseline from the v0.3 design split.
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
HERMES_PROFILE=hm-pdp-test PYTHONPATH=hermes-polymarket-control/src python -m pytest -q hermes-polymarket-control/tests
HERMES_PROFILE=hm-pdp-test python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

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

```bash
python scripts/run_controlled_canary_pipeline.py \
  --output-dir dist/pmx-canary-pipeline-no-go-local \
  --candidate-market-file candidate-market.json
```

Release packaging writes `dist/INDEX.json` and `dist/README.md`. Only the
indexed `polymarket-execution-suite-v0.26.0.zip` plus its detached sidecars are
the current source artifact; any other `dist/pmx-*` directory is local review
material unless explicitly indexed as current.

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
