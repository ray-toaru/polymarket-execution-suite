#!/usr/bin/env python3
"""Thin wrapper over execution-engine prereview bundle orchestration."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "prepare_canary_prereview_bundle.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_canary_prereview_bundle",
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
PREPARE_CANDIDATE_SCRIPT = _ENGINE.PREPARE_CANDIDATE_SCRIPT
REVIEW_BUNDLE_SCRIPT = _ENGINE.REVIEW_BUNDLE_SCRIPT
APPROVAL_REQUEST_SCRIPT = _ENGINE.APPROVAL_REQUEST_SCRIPT
ACTIVATE_PROFILE_SCRIPT = _ENGINE.ACTIVATE_PROFILE_SCRIPT
STORE_TRUTH_SCRIPT = _ENGINE.STORE_TRUTH_SCRIPT
load_module = _ENGINE.load_module
resolve = _ENGINE.resolve
prepare_candidate = _ENGINE.prepare_candidate
prepare_runtime_truth = _ENGINE.prepare_runtime_truth
activate_runtime_profile_env = _ENGINE.activate_runtime_profile_env
parse_args = _ENGINE.parse_args


def prepare_prereview_bundle(**kwargs):
    original_load_module = _ENGINE.load_module
    original_prepare_candidate = _ENGINE.prepare_candidate
    original_prepare_runtime_truth = _ENGINE.prepare_runtime_truth
    original_activate_runtime_profile_env = _ENGINE.activate_runtime_profile_env
    _ENGINE.load_module = load_module
    _ENGINE.prepare_candidate = prepare_candidate
    _ENGINE.prepare_runtime_truth = prepare_runtime_truth
    _ENGINE.activate_runtime_profile_env = activate_runtime_profile_env
    try:
        return _ENGINE.prepare_prereview_bundle(**kwargs)
    finally:
        _ENGINE.load_module = original_load_module
        _ENGINE.prepare_candidate = original_prepare_candidate
        _ENGINE.prepare_runtime_truth = original_prepare_runtime_truth
        _ENGINE.activate_runtime_profile_env = original_activate_runtime_profile_env


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
