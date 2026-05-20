# GitHub Publishing Checklist

This repository is release-sensitive because it pins independent Hermes and execution-engine submodules. Complete these checks before publishing the private GitHub repository.

## Repository wiring

- Create or select the private GitHub repositories for:
  - `polymarket-execution-suite`;
  - `hermes-polymarket-control`;
  - `polymarket-execution-engine`.
- Replace the local `.gitmodules` URLs with GitHub clone URLs that GitHub Actions can reach.
- Commit each submodule first, then commit the updated submodule pointers in this integration repository.
- Add the integration repository remote and push the release branch.

## CI requirements

- Keep `actions/checkout` configured with `submodules: recursive`.
- Because the submodules are private sibling repositories, configure `CI_SUBMODULE_TOKEN` with read access to all three repositories and wire it into checkout before enabling required checks.
- Require these workflows before merging release branches:
  - `ci`;
  - `rust-locked`.
- Keep `credentialed-sdk` manual and protected by the `credentialed-sdk` environment.

## Credentialed SDK gate

Configure the protected `credentialed-sdk` environment with these secrets only when a reviewed operator is ready to run the non-trading credentialed checks:

- `POLYMARKET_PRIVATE_KEY`
- `POLY_API_KEY`
- `POLY_API_SECRET`
- `POLY_API_PASSPHRASE`

Do not add live-submit or live-cancel enablement secrets to CI. The workflow explicitly refuses `PMX_ALLOW_LIVE_SUBMIT=1`, `PMX_ALLOW_LIVE_CANCEL=1`, and `PMX_REAL_FUNDS_CANARY_ARMED=1`.
