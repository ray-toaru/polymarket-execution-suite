#!/usr/bin/env python3
"""Thin wrapper over execution-engine dual-control signature verification."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "verify_dual_control_review_signature.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_verify_dual_control_review_signature",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

load_json = _ENGINE.load_json
sha256 = _ENGINE.sha256
verify_review_signature = _ENGINE.verify_review_signature
parse_args = _ENGINE.parse_args


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
