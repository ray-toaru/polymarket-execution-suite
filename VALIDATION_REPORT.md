# Validation Report — v0.28.0 production-live-candidate

## 2026-06-18 local live-read event validation

Current tracked component pins after the Phase 5 live-read event
persistence/API continuation:

- Hermes adapter submodule commit:
  `49fb4b6c209e744f57b87b255bbf92003eacb557`.
- Execution-engine submodule commit:
  `eec14d8e5b126c81150e3d6cdd6147e6be43dab6`.
- Integration root commit before this documentation sync:
  `3fbf823ea1dd4e08a155d754ba04f89cd3a9d823`.

Local validation passed:

- `cargo fmt --check`;
- `cargo check --workspace --locked`;
- `cargo test -p pmx-store live_read --locked`;
- `cargo test -p pmx-gateway live_read --locked`;
- `cargo test -p pmx-api full_scaffold_path_compile_submit_cancel_and_reconcile --locked -- --test-threads=1`;
- `PYTHONPATH=hermes-polymarket-executor-adapter/src .venv/bin/python -m pytest -q hermes-polymarket-executor-adapter/tests`;
- `PYTHONPATH=hermes-polymarket-executor-adapter/src .venv/bin/python hermes-polymarket-executor-adapter/scripts/check_openapi_parity.py polymarket-execution-engine/openapi/executor.v1.yaml`;
- `.venv/bin/python polymarket-execution-engine/validation/check_docs_evidence_governance.py`;
- `.venv/bin/python scripts/validate_contracts.py --report-file /tmp/pmx-contracts-doc-sync-report.json`;
- `.venv/bin/python scripts/check_release_artifact.py dist/polymarket-execution-suite-v0.28.0.zip 0.28.0`;
- `.venv/bin/python scripts/check_dist_index.py dist 0.28.0`;
- `.venv/bin/python polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree`;
- `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`.

This validation is local only. No push, GitHub CI, tag, release, package
refresh, production deployment, live submit/cancel enablement, or real-funds
authorization is included.

## 2026-06-18 Phase 5 evidence refresh

Current tracked component pins after the completed Phase 5 non-live foundation
merge:

- Hermes adapter submodule commit:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`.
- Execution-engine submodule commit:
  `85f0641db4c02262829a2e94134193d8842db7de`.

Local validation refreshed the current gates, artifact, detached sidecars,
workspace manifest snapshot, dist index, current evidence manifest, docs
governance, and release hygiene for this changed state. PostgreSQL,
credentialed non-trading smoke, sign-only dry-run, and PostgreSQL-backed
store-truth remain skipped unless their explicit environment prerequisites are
provided.

Latest Phase 5 code-state evidence before this evidence/document refresh:

- root commit: `864bf9ee710f24f5b38eb0299557280cc6a40960`;
- root CI run: `https://github.com/ray-toaru/polymarket-execution-suite/actions/runs/27751360977`, success;
- engine CI run: `https://github.com/ray-toaru/polymarket-execution-engine/actions/runs/27751351091`, success;
- final artifact, evidence sidecar, provenance sidecar, and manifest hashes:
  recorded outside the source archive in `dist/` sidecars and the external
  progress tracker.

This evidence/document refresh still requires fresh CI and fresh independent
package review before it can be treated as reviewed final package material. It
does not authorize live submit, live cancel, production deployment, or another
canary attempt.

## 2026-06-13 final package-hash review state

Exact root commit, artifact hash, manifest hash, sidecar hash, and review hash
belong in detached sidecars and external review JSON rather than this source
document. Current tracked component pins at this documentation refresh are:

- Hermes adapter submodule commit:
  `7477c028d5c4f0f2215e7ee6c3ee4ea750331553`.
- Execution-engine submodule commit:
  `9584348fa8e368e088c92a3d72f44569581a7e13`.

Integration suite CI run `27474066294`, adapter CI run `27473948617`, and
execution-engine CI run `27473806418` passed before this documentation refresh.
- Lei's final package-hash review approved only this exact commit and package
  hash named in
  `external_reviews/lei/final-commit-package-hash-review.approved.canonical.json`,
  with non-live limits. This documentation/evidence refresh changes the source
  state after that review and therefore requires a fresh package rebuild and
  fresh review before it can be treated as a reviewed final state.

The posture remains `production-live-candidate`, non-live by default. The
current final manifest explicitly records `postgres_validation`,
`credentialed_non_trading_validation`, and
`real_funds_canary_store_truth_cli_validation` as skipped in this local
environment. Those skipped sections are blockers for any production, live, or
reviewed-go execution claim until refreshed for the exact source/artifact under
review.

## 2026-06-11 evidence refresh

- Root CI run `27326801031` passed for commit `5d7eaced32e7f24048435f52d0a9fa96415b2f63`.
- Adapter CI run `27326769709` passed for commit `0286fa59864b6f9860835f3a29da1c395be8ea93`.
- Engine CI run `27326785130` passed after rerunning a PostgreSQL job whose first attempt failed before checkout during a Docker image pull.
- Engine current evidence was regenerated at commit `04114a32b5d16306a5f2c29048f2f62c949ecfde`.
- The admin session probe verifies the authenticated subject and required admin capabilities without remote side effects.
- Release provenance now binds the artifact, evidence manifest, source commits, dependency materials, and exact CI runs.

The posture remains `non_live_hardened`. PostgreSQL and credentialed runtime
proof omitted from the local refresh remains explicitly skipped where external
configuration was absent; GitHub branch protection is unavailable for this
private repository under the current plan.

## 2026-06-10 non-live hardening result

The validated posture is `non_live_hardened`. It is not `production_ready`,
`live_ready`, or `real_funds_authorized`.

- Contract validation passes with `26` structured checks and `0` mixed checks.
- Root tests pass on Python 3.11 and 3.13 on Ubuntu and macOS.
- Adapter tests, Ruff, mypy, Bandit, Rust locked checks, PostgreSQL integration,
  docs governance, release hygiene, deterministic packaging, and artifact
  validation are mandatory CI jobs.
- Release candidate hashes are checked against the zip bytes, detached SHA-256
  sidecar, evidence sidecar, and `dist/INDEX.json`.
- Runtime secret generation is disabled; only explicit external secret inputs
  are accepted.

External reviewer identity, operator approval, signature evidence, token scope,
branch protection, and any future live decision remain external blockers.

## Current Conclusion

v0.28.0 is being prepared as a production-live-candidate.
It is not production-ready and not live-trading-ready until the v0.28 full
current gates, package, detached sidecars, and release readiness audit are
refreshed together.

Two local controlled-canary closeout records now exist:

- historical v0.26 controlled canary evidence retained for audit context;
- one v0.28 reviewed-go single-attempt BUY/GTC post-only canary closed on
  2026-06-20 UTC.

For the v0.28 local attempt, the saved readback evidence records
`remote_status=CANCELED`, `size_matched=0`, zero matching trades for the
submitted order id, and a broader public Data API readback with zero activity,
zero trades, zero open positions, zero closed positions, and value `0`. This
validates that one-time canary exercise only; it is not evidence for general
production/live readiness.

Tracked closeout summary:

```text
CONTROLLED_CANARY_CLOSEOUT.md
```

The current package is valid only when the following detached sidecars are
present next to the source archive:

```text
dist/polymarket-execution-suite-v0.28.0.zip
dist/polymarket-execution-suite-v0.28.0.zip.sha256
dist/polymarket-execution-suite-v0.28.0.zip.evidence.json
```

The source archive does not self-bind its containing zip hash. The detached
evidence sidecar binds the artifact SHA-256 and the canonical evidence manifest
SHA-256.

`dist/INDEX.json` is part of the local release boundary. It is not embedded in
the source archive; it indexes the generated artifact and local review
directories in the developer `dist/` workspace. The index is valid only when
`scripts/check_dist_index.py dist 0.28.0` passes and
`scripts/check_release_artifact.py` confirms the same artifact and sidecar
hashes.

Git governance freeze:

- git tag `v0.28.1` marks the first post-closeout freeze point for the current
  v0.28 branch state;
- the source artifact version string remains `v0.28.0`, so `v0.28.1` is a
  repository governance tag, not a renamed zip artifact.

## Local Evidence Status

Canonical manifest:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

Latest local refresh:

- date: 2026-06-20 UTC for the local reviewed-go package and closeout refresh;
  canonical current evidence manifest freshness remains whatever is bound in the
  detached `.zip.evidence.json` sidecar after packaging;
- gate source root commit: recorded in the detached `.zip.evidence.json`
  sidecar generated after the final root commit;
- gate source execution-engine commit: recorded in the detached
  `.zip.evidence.json` sidecar submodule records;
- release artifact SHA-256: recorded in the detached `.zip.sha256` sidecar;
- evidence manifest SHA-256: recorded in the detached `.zip.evidence.json`
  sidecar;
- completed canary closeout packages:
  `dist/pmx-canary-reviewed-go-v0.26-20260523T022339Z-gtc-post-only-size5` and
  `dist/pmx-v028-reviewed-go-20260527T035142Z`;
- next canary review package: must start from a fresh no-go review package and
  cannot reuse the consumed reviewed-go package;
- next-phase local no-go pipeline evidence:
  `dist/pmx-canary-pipeline-next-phase-no-go-local/pipeline-report.json`
  records `status=pass`, `remote_side_effects=false`,
  `armed_live_attempted=false`, and `operator_runbook.status=blocked`;
- result for the final package-hash reviewed state: local/Rust/SDK/static,
  governance, package, artifact, and dist-index checks passed. PostgreSQL,
  credentialed non-trading/sign-only, and PostgreSQL-backed store-truth CLI
  sections are skipped in the current final manifest because the required
  database URLs and credentialed opt-in variables were not provided.

Current evidence policy:

- `postgres_validation=pass` only when the PostgreSQL logs are present and the
  dedicated store log runs non-zero `postgres::postgres_tests`;
- credentialed non-trading smoke is `pass` only when
  `16-authenticated-smoke.log` exists and satisfies the manifest test-count
  rule; otherwise it is skipped, not promotion evidence;
- sign-only dry-run is `pass` only when `17-sign-only-dry-run.log` exists and
  satisfies the manifest test-count rule; otherwise it is skipped, not
  promotion evidence;
- PostgreSQL-backed store-truth CLI preflight is `pass` only when
  `72-real-funds-canary-store-truth-cli-preflight.log` records
  `status=pass`, `preflight_ready=true`, no post/cancel side effects, no raw
  signed order exposure, and `runtime_truth_source=postgres`;
- local static, Rust, SDK, package, governance, and deployment-template gates
  are evidence only for the production-live-candidate boundary.
- controlled canary closeout evidence is valid only for the single order id
  recorded in `CONTROLLED_CANARY_CLOSEOUT.md`; it is not reusable authorization
  for a later canary.

Full current gates for v0.28 are required before promotion to validated/final
release evidence. Git tag `v0.28.1` freezes the current governance state, but
it does not by itself upgrade this package to validated release, production
readiness, or live-trading readiness. Until
`polymarket-execution-engine/validation/run_current_gates.sh` has refreshed the
canonical evidence manifest for v0.28.0 and the v0.28 artifact sidecars exist,
this report remains a development-state report rather than final release
evidence.

## Local Validation Commands

Use local checks before CI:

```bash
.venv/bin/python scripts/check_version_consistency.py
.venv/bin/python scripts/validate_contracts.py
.venv/bin/python scripts/check_v28_production_live_candidate.py
.venv/bin/python scripts/check_dist_index.py dist 0.28.0
PYTHONPATH=hermes-polymarket-executor-adapter/src .venv/bin/python -m pytest -q hermes-polymarket-executor-adapter/tests
.venv/bin/python -m compileall -q hermes-polymarket-executor-adapter/src scripts polymarket-execution-engine/validation
HERMES_PROFILE_CMD=<local-profile-command> .venv/bin/python scripts/check_hermes_profile_plugin.py
cd polymarket-execution-engine && ./validation/run_current_gates.sh
```

Routine edits should use the relevant local subset first. Remote CI is a release
confirmation layer, not the default way to validate every small local change.

`check_v28_production_live_candidate.py` remains audit-only by default. It becomes a
failing gate only with `--require-ready`, which should be used when the v0.28
version bump, manifests, release decision, validation report, deterministic
artifact, sidecars, and full gates are all refreshed.

## Canary Review Boundary

Review packages under `dist/pmx-*` are local review material unless the
machine-readable `dist/INDEX.json` names them as the current release artifact.
Multiple local review directories may exist; they are not interchangeable
approval sources.

The current `dist/INDEX.json` guard requires:

- the current release artifact SHA-256 to match both detached sidecars;
- no-go review material to set `approval_reuse_allowed=false` and
  `remote_side_effects_authorized=false`;
- consumed or closed reviewed-go material to remain non-reusable and
  non-authorizing for remote side effects.

The user-selected canary market review package must bind:

- artifact SHA-256;
- evidence manifest SHA-256;
- candidate-market SHA-256;
- external references with no placeholders;
- a release-decision JSON that remains no-go unless explicitly reviewed as go.

The controlled canary dry-run may report `dry_run_ready`, but that status still
means no live submit, no live cancel, no posted order, and no remote side
effects.

The current user-selected reviewed-go package has been consumed and closed. Any
future user-selected review package must start as `no_go` and not armed until a
fresh reviewed decision changes only that package:

- market: `will-iran-legalize-gay-marriage`;
- side/outcome: BUY Yes;
- execution style: GTC limit post-only cancel;
- target size: `5` outcome shares;
- limit price: `0.02`;
- maximum order notional: `1.00` USD;
- `real_funds_canary_authorized=false` by default;
- `live_submit_authorized=false` by default;
- `live_cancel_authorized=false` by default.

## Non-Claims

This validation report does not claim:

- production deployment readiness;
- live submit or live cancel availability;
- a successful real-funds canary fill;
- readiness for a second real-funds canary without a fresh reviewed decision;
- equivalence between historical v0.25 evidence and the current v0.28 package.

Any future live attempt needs a new reviewed release decision and fresh evidence
bound to the exact artifact under review.
