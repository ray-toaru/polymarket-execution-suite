# Dependency and environment policy — v0.23.0

## Current baseline

```text
Rust: 1.88+
Rust edition: 2024
Python: >=3.13
Official SDK crate: polymarket_client_sdk_v2
Official SDK version: =0.6.0-canary.1
```

## Policy

- Official SDK dependencies stay isolated in adapter crates.
- Core, policy, store, service, and public API crates must not depend directly on the official SDK.
- Patch/minor dependency changes require CI evidence before release promotion.
- Major dependency changes require explicit review, rollback note, and validation evidence.
- Trading-path dependency changes must not auto-promote to production.
- The official SDK remains exactly pinned until a newer version is separately reviewed and validated.

## Current limitation

This package does not prove Rust/SDK/PostgreSQL compatibility in the local packaging environment. `cargo check --workspace --locked`, SDK adapter checks, and PostgreSQL E2E must be rerun externally before release promotion.
