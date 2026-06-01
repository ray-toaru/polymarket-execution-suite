# Controlled Canary Closeout Summary — v0.28.0

This document is the current tracked summary for the latest consumed
reviewed-go controlled canary package on the v0.28 line. It summarizes the
closeout boundary and evidence expectations for the single local v0.28
BUY/GTC/post-only attempt that has already been consumed and closed.

Historical v0.26 closeout context now lives under:

```text
docs/archive/CONTROLLED_CANARY_CLOSEOUT_v0.26.0.md
```

## Current Summary

- Scope: one local reviewed-go single-attempt controlled canary package
- Decision status: consumed and closed
- Execution style: `GTC_LIMIT_POST_ONLY_CANCEL`
- Side/order: `BUY/GTC`, `post_only=true`
- Local closeout outcome: `remote_status=CANCELED`, `size_matched=0`
- Readback outcome: zero matching trades, zero matching activity, zero matching
  open positions, zero matching closed positions, and value `0`
- Reuse policy: not reusable for another armed attempt

## Evidence Boundary

Current local closeout evidence is bound to the reviewed-go package directory
and its closeout/readback files. The tracked summary does not replace those
JSON records and does not authorize another live attempt.

Relevant material includes:

- reviewed-go package directory under `dist/`
- `closeout.json`
- `CLOSEOUT.md`
- `order-status-query.json`
- `trade-fill-query.json`
- account/activity readback artifacts

Closeout regeneration must still bind an exact package directory:

```bash
python scripts/prepare_canary_closeout.py \
  --package-dir <exact-reviewed-go-package-dir>
```

The script must fail closed if stage history is missing, references a different
remote order, exposes raw signed material, or leaves unresolved
`operator_required` recovery state.

## Non-Claims

This closeout summary is current governance context for one consumed local
attempt only. It is not production readiness evidence, not live-trading
readiness evidence, and not authorization for another attempt. Any future armed
canary still requires fresh market discovery, fresh reviewed release decision,
explicit operator approval, current gates, and a new closeout package.
