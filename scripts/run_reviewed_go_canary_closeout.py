#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go canary closeout orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_reviewed_go_canary_closeout.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_reviewed_go_canary_closeout",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

resolve = _ENGINE.resolve
require_file = _ENGINE.require_file
load_json = _ENGINE.load_json
parse_env_file = _ENGINE.parse_env_file
require_text = _ENGINE.require_text
resolve_account_address = _ENGINE.resolve_account_address
build_workflow_plan = _ENGINE.build_workflow_plan
run_step = _ENGINE.run_step
parse_remote_order_id = _ENGINE.parse_remote_order_id
execute_workflow = _ENGINE.execute_workflow
parse_args = _ENGINE.parse_args
subprocess = _ENGINE.subprocess


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
