# Current progress — v0.25.0

This pass formalizes the v0.25.0 shadow-ready SDK sign-only baseline after the prior shadow-ready work.

## Done in this cleanup pass

- Reduced root document ambiguity by moving old gate/validation notes to `docs/archive/`.
- Added a clear current document map in `DOC_STATUS.md`.
- Introduced canonical evidence layout under `polymarket-execution-engine/evidence/current/`.
- Moved old validation/evidence logs to archive directories.
- Added governance checks for stale root docs, evidence layout, manifest hashes, and release-manifest binding.
- Added release package exclusions so historical docs/evidence are not included in normal release zips.
- Tightened lifecycle payload schema to a typed redacted envelope in OpenAPI and Hermes models.
- Made pre-live worker `DEGRADED` status block constraints rather than silently allowing execution.
- Renamed the active gate implementation to
  `polymarket-execution-engine/validation/run_current_gates_impl.sh`; the public
  entrypoint remains `polymarket-execution-engine/validation/run_current_gates.sh`.

## Still pending for later releases

- Live submit/cancel promotion evidence.
- Production deployment evidence and operational controls.
- Actual real-funds canary execution evidence. The current implementation target
  is program readiness only; normal gates must still record no posting and no
  remote trading side effects.
