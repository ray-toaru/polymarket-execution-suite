# Current progress — v0.23.0

This pass addressed release-governance and auditability problems found during v0.23 review.

## Done in this cleanup pass

- Reduced root document ambiguity by moving old gate/validation notes to `docs/archive/`.
- Added a clear current document map in `DOC_STATUS.md`.
- Introduced canonical evidence layout under `polymarket-execution-engine/evidence/current/`.
- Moved old validation/evidence logs to archive directories.
- Added governance checks for stale root docs, evidence layout, manifest hashes, and release-manifest binding.
- Added release package exclusions so historical docs/evidence are not included in normal release zips.
- Tightened lifecycle payload schema to a typed redacted envelope in OpenAPI and Hermes models.
- Made pre-live worker `DEGRADED` status block constraints rather than silently allowing execution.

## Still pending

- Full Rust/SDK/PostgreSQL validation in an external environment.
- Exact final artifact validation after this cleanup package is generated.
- Live submit/cancel promotion evidence.
