#!/usr/bin/env python3
"""Thin wrapper over execution-engine canary closeout orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "prepare_canary_closeout.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_canary_closeout",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

argparse = _ENGINE.argparse
dt = _ENGINE.dt
hashlib = _ENGINE.hashlib
json = _ENGINE.json
Decimal = _ENGINE.Decimal
InvalidOperation = _ENGINE.InvalidOperation
Any = _ENGINE.Any
ROOT = _ENGINE.INTEGRATION_ROOT
VERSION = _ENGINE.VERSION
DEFAULT_RELEASE_ZIP = _ENGINE.DEFAULT_RELEASE_ZIP
display_path = _ENGINE.display_path
parse_args = _ENGINE.parse_args
sha256 = _ENGINE.sha256
load_json = _ENGINE.load_json
required_json = _ENGINE.required_json
optional_json = _ENGINE.optional_json
optional_package_json = _ENGINE.optional_package_json
load_stage_history = _ENGINE.load_stage_history
decimal_text = _ENGINE.decimal_text
decimal_value = _ENGINE.decimal_value
lget = _ENGINE.lget
summarize_stage_history = _ENGINE.summarize_stage_history
validate_operator_recovery = _ENGINE.validate_operator_recovery
validate_incident_recovery = _ENGINE.validate_incident_recovery
build_closeout = _ENGINE.build_closeout
markdown = _ENGINE.markdown


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
