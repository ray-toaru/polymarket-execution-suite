#!/usr/bin/env python3
"""Validate a generated non-live release provenance document."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_release_provenance import validate_provenance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provenance", type=Path)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    data = json.loads(args.provenance.read_text())
    failures = validate_provenance(data, args.artifact, base_dir=Path.cwd())
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures))
        return 1
    print("release provenance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
