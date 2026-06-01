#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go armed orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_reviewed_go_canary_armed.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_reviewed_go_canary_armed",
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
BASE_SCRIPT = _ENGINE.BASE_SCRIPT
load_base = _ENGINE.load_base
parse_args = _ENGINE.parse_args


def build_armed_invocation(**kwargs):
    original_load_base = _ENGINE.load_base
    _ENGINE.load_base = load_base
    try:
        return _ENGINE.build_armed_invocation(**kwargs)
    finally:
        _ENGINE.load_base = original_load_base


def main() -> int:
    original_load_base = _ENGINE.load_base
    _ENGINE.load_base = load_base
    try:
        return _ENGINE.main()
    finally:
        _ENGINE.load_base = original_load_base


if __name__ == "__main__":
    raise SystemExit(main())
