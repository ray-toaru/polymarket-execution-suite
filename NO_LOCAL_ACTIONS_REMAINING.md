# No local actions remaining? — v0.23.0

This file is retained as a compatibility entry point for older checks. It does **not** mean the project is production-ready.

After local/static checks pass, remaining validation depends on tools not guaranteed in the packaging environment:

- Rust 1.88 toolchain;
- PostgreSQL test database;
- official SDK dependency resolution;
- optional credentials for non-trading smoke and sign-only dry-run.

Live submit, live cancel, and production deployment remain blocked.
