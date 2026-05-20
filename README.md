# Polymarket dual project v0.25.0

v0.25.0 is a **shadow-ready SDK sign-only candidate**, not a production-ready or live-trading release.

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

- `PROJECT_ARCHITECTURE.md` — v0.25 architecture baseline from the v0.3 design split.
- `DEPENDENCY_POLICY.md` — pinned runtime/toolchain/dependency policy.
- `DESIGN_DECISION_RECORD.md` — accepted architectural decisions.
- `IMPLEMENTATION_STATUS.md` — implemented, blocked, and intentionally disabled areas.
- `VALIDATION_REPORT.md` — what is locally verified versus externally required.
- `REVIEW_AUDIT.md` — known risks and audit judgment.
- `DOC_STATUS.md` — document/evidence governance map.

Historical root documents and previous gate notes have been moved to `docs/archive/` and are excluded from normal release packaging.

## Validation

Integration-level local/static validation entry points:

```bash
python scripts/check_version_consistency.py
python scripts/validate_contracts.py
HERMES_PROFILE=hm-pdp-test PYTHONPATH=hermes-polymarket-control/src python -m pytest -q hermes-polymarket-control/tests
HERMES_PROFILE=hm-pdp-test python -m compileall -q hermes-polymarket-control/src scripts polymarket-execution-engine/validation
python polymarket-execution-engine/validation/check_docs_evidence_governance.py
python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree
```

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
