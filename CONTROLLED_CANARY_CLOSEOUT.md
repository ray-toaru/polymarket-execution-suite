# Controlled Canary Closeout — v0.26.0

This document records the tracked closeout summary for the first authorized
v0.26 controlled real-funds canary. It summarizes local package evidence under
`dist/`; it does not replace the original JSON evidence and does not authorize
another live attempt.

## Result

- Decision: `controlled_real_funds_canary_closed`
- Execution style: `GTC_LIMIT_POST_ONLY_CANCEL`
- Side/order: `BUY/GTC`, `post_only=true`
- Size: `5` outcome shares
- Limit price: `0.02`
- Notional rule: `limit_price * size`
- Notional: `0.1` USD
- Remote order id:
  `0x6513f249c1eed5703c72e3238e887f7020cc062370fa99a89fda6b9e1436f4bb`
- Order readback: `remote_status=CANCELED`, `size_matched=0`
- Trade readback: `matching_trades_count=0`, `matching_size_total=0`
- Account readback: zero matching activity, trades, open positions, and closed
  positions; matching value record is `0`
- Raw signed order exposure: `false`

## Evidence Location

Local generated evidence package:

```text
dist/pmx-canary-reviewed-go-v0.26-20260523T022339Z-gtc-post-only-size5/
```

Important files:

- `armed-report-20260523T022507Z.json`
- `order-status-query.json`
- `trade-fill-query.json`
- `account-activity-readback.json`
- `closeout.json`
- `CLOSEOUT.md`

`dist/` is ignored review material, so this root document is only a tracked
summary. This historical v0.26 closeout package predates the v0.27
append-only stage-history requirement. Do not regenerate it with the current
`scripts/prepare_canary_closeout.py` unless the package also contains
`post-canary-report.json.stages.jsonl`.

For v0.27 and later packages, recreate the machine-readable closeout from
local evidence with:

```bash
python scripts/prepare_canary_closeout.py \
  --package-dir <exact-reviewed-go-package-dir>
```

The package directory is required deliberately; closeout must bind an exact
review package/order id and must not select by local directory modification
time. The script also binds the ordered
`post-canary-report.json.stages.jsonl` hash and fails closed if stage history is
missing, references a different remote order, exposes raw signed material, or
contains unresolved `operator_required` recovery state. If an
`operator_required` stage occurred, closeout requires `operator-recovery.json`
with `recovery_decision=operator_reviewed_closed_no_retry`, the same remote
order id, the exact stage-history SHA-256, no-retry/no-second-order assertions,
and references to the order/trade/account readback evidence.

## Non-Claims

This closeout proves one controlled canary was posted, cancelled, and read back
with no observed fill or position. It does not prove production readiness, live
trading readiness, or readiness for a second canary. A future armed attempt
requires fresh market discovery, fresh reviewed release decision, explicit
operator approval, current gates, and a new closeout.
