#!/usr/bin/env python3
"""Thin wrapper over execution-engine canary review bundle orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "prepare_canary_review_bundle.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_canary_review_bundle",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

argparse = _ENGINE.argparse
ROOT = _ENGINE.INTEGRATION_ROOT
RUNTIME_BUNDLE_SCRIPT = _ENGINE.RUNTIME_BUNDLE_SCRIPT
DUAL_CONTROL_TEMPLATE_SCRIPT = _ENGINE.DUAL_CONTROL_TEMPLATE_SCRIPT
REVIEW_PACKET_SCRIPT = _ENGINE.REVIEW_PACKET_SCRIPT
load_module = _ENGINE.load_module
parse_args = _ENGINE.parse_args
resolve = _ENGINE.resolve


def prepare_review_bundle(**kwargs):
    original_load_module = _ENGINE.load_module
    _ENGINE.load_module = load_module
    try:
        return _ENGINE.prepare_review_bundle(**kwargs)
    finally:
        _ENGINE.load_module = original_load_module


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
