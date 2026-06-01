#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go decision workflow orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_reviewed_go_decision_workflow.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_reviewed_go_decision_workflow",
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
PREREVIEW_BUNDLE_SCRIPT = _ENGINE.PREREVIEW_BUNDLE_SCRIPT
REVIEWED_GO_BUNDLE_SCRIPT = _ENGINE.REVIEWED_GO_BUNDLE_SCRIPT
load_module = _ENGINE.load_module
resolve = _ENGINE.resolve
parse_args = _ENGINE.parse_args


def build_workflow_plan(args):
    original = _ENGINE.load_module
    _ENGINE.load_module = load_module
    try:
        return _ENGINE.build_workflow_plan(args)
    finally:
        _ENGINE.load_module = original


def execute_workflow(args):
    original = _ENGINE.load_module
    _ENGINE.load_module = load_module
    try:
        return _ENGINE.execute_workflow(args)
    finally:
        _ENGINE.load_module = original


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
