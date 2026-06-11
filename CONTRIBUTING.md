# Contributing

Development targets `main`. Use a focused branch and open a pull request; do
not use version-named release branches as permanent development branches.

Before requesting review:

1. Keep changes scoped to one concern.
2. Commit component changes inside the relevant submodule first.
3. Update the integration repository's pinned submodule commit afterward.
4. Run the validation subset listed in `AGENTS.md`.
5. Update contracts, tests, documentation, and release evidence when behavior
   changes.
6. Do not include private keys, API credentials, raw signatures, signed order
   envelopes, or production data in commits, issues, logs, or test fixtures.

Squash merge is the repository merge policy. A passing CI run is required
evidence, but it is not production or live-trading approval.

Release tags must be annotated and cryptographically signed. SemVer tags are
reserved for source versions; evidence or governance snapshots must use a
descriptive prerelease suffix and a GitHub prerelease. Existing unsigned tags
are historical records and must not be rewritten.

The repository currently has one administrator. Until a second independent
reviewer is added, changes that affect credentials, signing, live-submit
boundaries, release decisions, or production deployment must remain blocked or
carry an external review reference recorded in the pull request.
