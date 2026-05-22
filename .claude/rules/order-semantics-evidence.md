---
title: Order Semantics Evidence
paths:
  - "polymarket-execution-engine/adapters/**/*.rs"
  - "polymarket-execution-engine/validation/**/*.py"
  - "polymarket-execution-engine/docs/**/*.md"
---

# Order Semantics Evidence

Trading order semantics must be justified by exchange documentation, SDK tests, or live remote evidence. Builder names such as `limit_order()` are not sufficient evidence when `order_type` changes execution behavior.

## Incorrect

Assume a canary is a normal limit order because the SDK builder is named `limit_order()`, then approve `FOK BUY price=0.024 size=5` using only the Web/GTC minimum share size.

```rust
client.limit_order().size(size).order_type(OrderType::FOK)
// Treated as ordinary resting limit order without checking marketable BUY notional.
```

## Correct

Use the effective order type and time-in-force as the semantic source of truth, then encode the relevant remote rule as a local fail-closed guard.

```rust
client.limit_order().size(size).order_type(OrderType::FOK)
// FOK BUY is an immediate marketable path; require price * size >= observed floor.
```

## Reference

Polymarket Create Order documentation: FOK/FAK are market order types; GTC/GTD are limit order types.
