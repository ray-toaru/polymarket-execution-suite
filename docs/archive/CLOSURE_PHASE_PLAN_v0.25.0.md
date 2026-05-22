# Closure Phase Plan — v0.25.0

## Current state

The repository is currently at a `shadow-ready SDK sign-only candidate`
baseline with passing current full-gate evidence bound under:

```text
polymarket-execution-engine/evidence/current/manifest.json
```

This phase changes the default working mode:

- stop broad, default-on Rust module splitting;
- keep live submit and live cancel blocked;
- only continue changes that materially improve release truthfulness,
  validation repeatability, or the next explicitly approved feature batch.

## Must do

1. Treat current `v0.25.0` as a closure baseline.
   Any further code change must rerun the relevant checks and refresh current
   evidence before changing release claims.
2. Keep release truth synchronized.
   `RELEASE_DECISION.md`, artifact sidecars, submodule pins, and
   `evidence/current/manifest.json` must continue to describe the same source
   package.
3. Preserve current safety boundaries.
   Live submit, live cancel, raw signed payload exposure, and production-ready
   claims remain blocked unless a future reviewed release decision changes
   them with fresh evidence.

## Allowed next work

Only the following tracks should continue by default:

1. Validation refresh after real source changes.
2. Release/evidence consistency fixes.
3. A small, explicit structural fix when it blocks:
   - future feature work;
   - a failing gate;
   - a documentation/evidence mismatch;
   - a concrete maintainability bottleneck that is still on the critical path.

## Deferred

These items remain valid but are no longer the default mainline:

1. Remaining non-blocking Rust module splits, including larger internal files
   in `pmx-store`, `pmx-service`, and `pmx-api`.
2. Additional codebase-governance cleanup that does not change validation
   outcomes or unblock the next feature batch.
3. Broader productionization scaffolding that is not required for current
   `shadow-ready SDK sign-only candidate` truthfulness.

## Stopped by default

Do not continue these without an explicit new batch decision:

1. Sweeping large-file/module split work across remaining crates.
2. Governance-only churn that forces full-gate reruns without improving the
   release claim, safety boundary, or next approved feature path.
3. Packaging/evidence refreshes triggered only by non-material refactoring
   experiments.

## Whitelist for exceptional structural work

If a structure-only change is still proposed in this closure phase, it should
pass all of these tests:

1. It solves a specific blocker that can be named in one sentence.
2. It has a small write scope.
3. It does not widen API, auth, signing, or live-trading behavior.
4. It is worth the cost of rerunning gates and refreshing evidence.
5. Deferring it would materially slow or confuse the next approved work item.

## Exit from closure phase

Exit this phase only by making one explicit choice:

1. Freeze `v0.25.0` as the maintained shadow-ready baseline and stop code
   changes except fixes.
2. Open a new feature batch with a clearly named target and success criteria
   before resuming broader implementation work.
