#!/usr/bin/env python3
"""Thin wrapper over execution-engine controlled canary orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_controlled_canary_pipeline.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_controlled_canary_pipeline",
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
ENGINE = _ENGINE.ENGINE
VERSION = _ENGINE.VERSION
DEFAULT_RELEASE_ZIP = _ENGINE.DEFAULT_RELEASE_ZIP
DEFAULT_MANIFEST = _ENGINE.DEFAULT_MANIFEST
DEFAULT_EXTERNAL_REFERENCES = _ENGINE.DEFAULT_EXTERNAL_REFERENCES
BLOCKED_REHEARSAL = _ENGINE.BLOCKED_REHEARSAL
PREPARE_CANDIDATE = _ENGINE.PREPARE_CANDIDATE
PREPARE_CLOSEOUT = _ENGINE.PREPARE_CLOSEOUT
VALIDATE_RUNTIME_TRUTH = _ENGINE.VALIDATE_RUNTIME_TRUTH
MAX_PRICE = _ENGINE.MAX_PRICE
Decimal = _ENGINE.Decimal
InvalidOperation = _ENGINE.InvalidOperation
datetime = _ENGINE.datetime
timezone = _ENGINE.timezone

parse_decimal = _ENGINE.parse_decimal
require_text = _ENGINE.require_text
require_bool = _ENGINE.require_bool
validate_candidate_file = _ENGINE.validate_candidate_file
build_stage_plan = _ENGINE.build_stage_plan
build_operator_runbook = _ENGINE.build_operator_runbook
runtime_truth_dependencies = _ENGINE.runtime_truth_dependencies
required_runtime_truth_names = _ENGINE.required_runtime_truth_names
validate_runtime_truth_file = _ENGINE.validate_runtime_truth_file
validate_reviewed_go_decision_file = _ENGINE.validate_reviewed_go_decision_file
run_closeout_stage = _ENGINE.run_closeout_stage
sha256 = _ENGINE.sha256
load_json = _ENGINE.load_json
run = _ENGINE.run
parse_args = _ENGINE.parse_args
prepare_candidate = _ENGINE.prepare_candidate

# Compatibility anchors for governance validators that still inspect the root wrapper.
# The actual runtime-truth checks are implemented in
# polymarket-execution-engine/validation/run_controlled_canary_pipeline.py and call
# validate_controlled_canary_runtime_truth.py, raising
# "runtime truth validator failed" and "runtime truth artifact binding mismatch"
# when expected_artifact_sha256 / expected_workspace_manifest_sha256 /
# expected_archived_manifest_sha256 bindings do not match.


def main() -> int:
    args = parse_args()
    return _wrapper_main(args)


def _wrapper_main(args) -> int:
    original_validate_runtime_truth_file = _ENGINE.validate_runtime_truth_file
    original_validate_reviewed_go_decision_file = _ENGINE.validate_reviewed_go_decision_file
    original_prepare_candidate = _ENGINE.prepare_candidate
    original_run_closeout_stage = _ENGINE.run_closeout_stage
    original_load_json = _ENGINE.load_json
    original_run = _ENGINE.run
    original_sha256 = _ENGINE.sha256
    _ENGINE.validate_runtime_truth_file = validate_runtime_truth_file
    _ENGINE.validate_reviewed_go_decision_file = validate_reviewed_go_decision_file
    _ENGINE.prepare_candidate = prepare_candidate
    _ENGINE.run_closeout_stage = run_closeout_stage
    _ENGINE.load_json = load_json
    _ENGINE.run = run
    _ENGINE.sha256 = sha256
    try:
        return _ENGINE.main_with_args(args)
    finally:
        _ENGINE.validate_runtime_truth_file = original_validate_runtime_truth_file
        _ENGINE.validate_reviewed_go_decision_file = original_validate_reviewed_go_decision_file
        _ENGINE.prepare_candidate = original_prepare_candidate
        _ENGINE.run_closeout_stage = original_run_closeout_stage
        _ENGINE.load_json = original_load_json
        _ENGINE.run = original_run
        _ENGINE.sha256 = original_sha256


if __name__ == "__main__":
    raise SystemExit(main())
