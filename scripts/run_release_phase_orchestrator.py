#!/usr/bin/env python3
"""Thin wrapper over execution-engine release-phase orchestration."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_release_phase_orchestrator.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_release_phase_orchestrator",
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
PRODUCTION_CONTROL_SUITE = _ENGINE.PRODUCTION_CONTROL_SUITE
DEPLOYMENT_VALIDATION_SUITE = _ENGINE.DEPLOYMENT_VALIDATION_SUITE
LIVE_SUBMIT_PROMOTION_SUITE = _ENGINE.LIVE_SUBMIT_PROMOTION_SUITE
REVIEWED_GO_DECISION_WORKFLOW = _ENGINE.REVIEWED_GO_DECISION_WORKFLOW
CONTRACT_VALIDATION_SCRIPT = _ENGINE.CONTRACT_VALIDATION_SCRIPT
load_module = _ENGINE.load_module
resolve = _ENGINE.resolve
sha256 = _ENGINE.sha256
contract_validation_output_dir = _ENGINE.contract_validation_output_dir
parse_args = _ENGINE.parse_args
parse_args_for_reviewed_go = _ENGINE.parse_args_for_reviewed_go


def execute_contract_validation(plan):
    return _ENGINE.execute_contract_validation(plan)


def build_stage_plans(args):
    original_load_module = _ENGINE.load_module
    _ENGINE.load_module = load_module
    try:
        return _ENGINE.build_stage_plans(args)
    finally:
        _ENGINE.load_module = original_load_module


def execute_orchestrator(args):
    original_load_module = _ENGINE.load_module
    original_execute_contract_validation = _ENGINE.execute_contract_validation
    _ENGINE.load_module = load_module
    _ENGINE.execute_contract_validation = execute_contract_validation
    try:
        return _ENGINE.execute_orchestrator(args)
    finally:
        _ENGINE.load_module = original_load_module
        _ENGINE.execute_contract_validation = original_execute_contract_validation


def main() -> int:
    args = parse_args()
    if not args.run:
        print(json.dumps(build_stage_plans(args), indent=2, sort_keys=True))
        return 0
    result = execute_orchestrator(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
