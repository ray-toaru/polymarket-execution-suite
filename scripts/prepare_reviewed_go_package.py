#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go package orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "prepare_reviewed_go_package.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_reviewed_go_package",
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
REVIEWED_GO_DECISION = _ENGINE.REVIEWED_GO_DECISION
REVIEW_PACKET = _ENGINE.REVIEW_PACKET
load_json = _ENGINE.load_json
sha256 = _ENGINE.sha256
resolve = _ENGINE.resolve
require_file = _ENGINE.require_file
load_module = _ENGINE.load_module
copy_into_package = _ENGINE.copy_into_package
build_cli_approval = _ENGINE.build_cli_approval
package_readme = _ENGINE.package_readme
parse_args = _ENGINE.parse_args


def build_package(**kwargs):
    original_load_module = _ENGINE.load_module
    _ENGINE.load_module = load_module
    try:
        return _ENGINE.build_package(**kwargs)
    finally:
        _ENGINE.load_module = original_load_module


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
