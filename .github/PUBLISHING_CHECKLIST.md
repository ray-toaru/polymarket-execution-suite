# GitHub Publishing Checklist

This repository is release-sensitive because it pins independent Hermes and execution-engine submodules. Complete these checks before publishing the private GitHub repository.

## Repository wiring

- Create or select the private GitHub repositories for:
  - `polymarket-execution-suite`;
  - `hermes-polymarket-executor-adapter`;
  - `polymarket-execution-engine`.
- Replace the local `.gitmodules` URLs with GitHub clone URLs that GitHub Actions can reach.
- Commit each submodule first, then commit the updated submodule pointers in this integration repository.
- Add the integration repository remote and push the release branch.

## CI requirements

- Prefer local validation for routine edits. Do not push solely to spend a
  GitHub Actions run after each small documentation, script, or fixture change.
  Use the relevant local command first, then reserve remote CI for release
  candidates, submodule pointer updates, GitHub Environment or secret changes,
  and runner-only behavior that local validation cannot cover.
- Keep `actions/checkout` configured with `submodules: recursive`.
- Because the submodules are private sibling repositories, configure `CI_SUBMODULE_TOKEN` with read access to all three repositories and wire it into checkout before enabling required checks.
- Require the integration repository `ci` workflow before merging release
  branches.
- Require the child repository workflows on the pinned commits before promoting a
  release candidate:
  - `hermes-polymarket-executor-adapter` `ci`;
  - `polymarket-execution-engine` `ci`.
- Do not duplicate child repository Rust, PostgreSQL, SDK, or credentialed gates
  as standalone integration-repository workflows. The integration repository
  records the pinned commit and evidence reference; the child repository owns the
  code gate.
- Keep credentialed SDK validation out of this integration repository. It belongs
  to the `polymarket-execution-engine` repository because that subproject owns
  the SDK adapter, signing boundary, and non-trading credential checks.

## Credentialed SDK gate

Configure the protected `credentialed-sdk` environment in
`polymarket-execution-engine`, not in this integration repository. Add these
secrets only when a reviewed operator is ready to run the non-trading
credentialed checks:

- `POLYMARKET_PRIVATE_KEY`
- `POLY_API_KEY`
- `POLY_API_SECRET`
- `POLY_API_PASSPHRASE`

Do not add live-submit or live-cancel enablement secrets to any CI environment.
The execution-engine workflow explicitly refuses `PMX_ALLOW_LIVE_SUBMIT=1`,
`PMX_ALLOW_LIVE_CANCEL=1`, and `PMX_REAL_FUNDS_CANARY_ARMED=1`.

For release decisions, this integration repository should record the
execution-engine workflow run ID and commit as evidence. It must not read,
store, or relay Polymarket credential secrets.
