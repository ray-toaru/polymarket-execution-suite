# Component compatibility and ownership

## Current v0.28.0 composition

| Component | Current repository name | Current version | Pinned commit | Role |
|---|---|---:|---|---|
| Integration suite | `polymarket-execution-suite` | `0.28.0` | root tag `v0.28.0` after release | Pins component commits, release evidence, contract parity, canary packages, and artifact sidecars. |
| Execution engine | `polymarket-execution-engine` | `0.28.0` | recorded in `.zip.evidence.json` | Rust executor: normalization, policy gates, runtime truth, lifecycle persistence, idempotency, audit, sign-only, and future live boundary. |
| Hermes adapter | `hermes-polymarket-executor-adapter` | `0.28.0` | recorded in `.zip.evidence.json` | Python Hermes-compatible executor adapter: typed executor client, public schema models, safe reports, native Hermes plugin tools, and service/admin token split. |

## Ownership boundaries

`polymarket-execution-engine` owns executor truth and any future
funds-moving boundary:

- intent normalization;
- risk and policy gates;
- feasibility snapshots;
- execution plan compilation;
- idempotency and reservations;
- audit and lifecycle persistence;
- runtime truth and worker health;
- signer/gateway isolation, sign-only, and future live-submit/cancel gates.

It must not own Hermes plugin behavior, prompt/agent logic, market research, or
operator UI.

`hermes-polymarket-executor-adapter` acts as the executor adapter. It may own:

- typed executor API client calls;
- Pydantic models aligned to the executor OpenAPI contract;
- Hermes-compatible tool/report wrappers;
- safe report rendering;
- service/admin permission split;
- no-secret static checks.

It must not own trading strategy, execution-engine risk policy, private keys,
CLOB secrets, raw signed payloads, direct CLOB calls, executor database
credentials, release/canary governance, or production/live authorization.

`polymarket-execution-suite` owns composition and evidence:

- submodule pinning;
- cross-repository contract parity;
- version and release-status documents;
- canonical evidence manifests and detached artifact sidecars;
- canary review package generation and no-go/consumed indexing;
- release hygiene and package validation.

It is not a runtime service and should not be imported by either component.

## Versioning policy

The three repositories may evolve independently after v0.26.1. The v0.28.0
suite line pins execution-engine `0.28.0` with Hermes adapter `0.28.0` because
this line includes both executor-side canary-closeout hardening and a
Hermes-facing native plugin surface.

- The execution engine follows its own semver based on executor API, state
  machine, database schema, SDK/gateway behavior, and live-boundary changes.
- The Hermes adapter follows its own semver based on Python client/tool schema
  compatibility. It must declare which executor API contract versions it
  supports.
- The integration suite follows composition semver. A suite release pins exact
  component commits and records the compatibility matrix for that combination.

Lockstep version numbers are allowed for a coordinated release, but they are
not required for normal development. A future suite release may pin, for
example, engine `0.27.x` with adapter `0.26.y` only if contract parity checks
and compatibility notes explicitly support that combination.
