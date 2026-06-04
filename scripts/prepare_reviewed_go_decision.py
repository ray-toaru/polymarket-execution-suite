#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go decision governance."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "prepare_reviewed_go_decision.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_reviewed_go_decision",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

argparse = _ENGINE.argparse
hashlib = _ENGINE.hashlib
json = _ENGINE.json
re = _ENGINE.re
datetime = _ENGINE.datetime
timezone = _ENGINE.timezone
Any = _ENGINE.Any
ROOT = _ENGINE.INTEGRATION_ROOT
VERSION = _ENGINE.VERSION
VALIDATOR = _ENGINE.VALIDATOR
REQUIRED_EXTERNAL_REFS = _ENGINE.REQUIRED_EXTERNAL_REFS
REVIEW_SIGNALS = _ENGINE.REVIEW_SIGNALS
REQUIRED_DUAL_CONTROL_CHECKS = _ENGINE.REQUIRED_DUAL_CONTROL_CHECKS
PREFLIGHT_GATE_FIELDS = _ENGINE.PREFLIGHT_GATE_FIELDS
DECISION_ID_RE = _ENGINE.DECISION_ID_RE
load_json = _ENGINE.load_json
sha256 = _ENGINE.sha256
has_placeholder = _ENGINE.has_placeholder
require_sha256 = _ENGINE.require_sha256
require_nonempty_text = _ENGINE.require_nonempty_text
require_concrete_text = _ENGINE.require_concrete_text
require_decision_id = _ENGINE.require_decision_id
parse_time = _ENGINE.parse_time
validate_approval_request = _ENGINE.validate_approval_request
validate_dual_control_review = _ENGINE.validate_dual_control_review
build_decision = _ENGINE.build_decision
validate_decision_output = _ENGINE.validate_decision_output
parse_args = _ENGINE.parse_args


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
