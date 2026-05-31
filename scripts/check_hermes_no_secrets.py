#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "hermes-polymarket-executor-adapter"

FORBIDDEN = [
    "POLYMARKET_PRIVATE_KEY",
    "POLY_API_SECRET",
    "POLY_API_PASSPHRASE",
    "private_key",
    "clob_secret",
    "api_secret",
    "raw_signature",
    "raw_signed_payload",
    "SignedOrderEnvelope",
    "post_order(",
    "post_orders(",
]

FORBIDDEN_PATTERNS = [re.compile(re.escape(token), re.IGNORECASE) for token in FORBIDDEN]

ALLOWLIST = {
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/ROADMAP.md"),
}


def main() -> int:
    failures: list[str] = []
    for path in sorted(CONTROL.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(CONTROL)
        if rel in ALLOWLIST:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        if path.suffix not in {".py", ".md", ".toml", ".txt", ".json"}:
            continue
        text = path.read_text(errors="ignore")
        for token, pattern in zip(FORBIDDEN, FORBIDDEN_PATTERNS, strict=True):
            if pattern.search(text):
                failures.append(f"{rel}: forbidden token {token}")
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("hermes no-secret static check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
