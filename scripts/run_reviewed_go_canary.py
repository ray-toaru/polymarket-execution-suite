#!/usr/bin/env python3
"""Thin wrapper over execution-engine reviewed-go preflight orchestration."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "run_reviewed_go_canary.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_run_reviewed_go_canary",
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
os = _ENGINE.os
subprocess = _ENGINE.subprocess
datetime = datetime
timezone = timezone
Any = _ENGINE.Any
ROOT = _ENGINE.INTEGRATION_ROOT
PIPELINE_SCRIPT = _ENGINE.PIPELINE_SCRIPT
ENV_CHECK_SCRIPT = _ENGINE.ENV_CHECK_SCRIPT
ADAPTER_MANIFEST = _ENGINE.ADAPTER_MANIFEST
RUNTIME_TRUTH_PREFLIGHT_ENV_BINDINGS = _ENGINE.RUNTIME_TRUTH_PREFLIGHT_ENV_BINDINGS
load_module = _ENGINE.load_module
load_json = _ENGINE.load_json
resolve = _ENGINE.resolve
require_file = _ENGINE.require_file
require_text = _ENGINE.require_text
validate_approval = _ENGINE.validate_approval
plan_hash_from_package = _ENGINE.plan_hash_from_package
invocation_hash_from_package = _ENGINE.invocation_hash_from_package
timestamp_tag = _ENGINE.timestamp_tag
default_marker_path = _ENGINE.default_marker_path
require_runtime_truth_gate_alignment = _ENGINE.require_runtime_truth_gate_alignment
require_approval_runtime_gate_alignment = _ENGINE.require_approval_runtime_gate_alignment
build_invocation = _ENGINE.build_invocation
parse_args = _ENGINE.parse_args


def main() -> int:
    args = parse_args()
    invocation = build_invocation(
        package_dir=args.package_dir,
        env_file=args.env_file,
        secrets_env_file=args.secrets_env_file,
        mode=args.mode,
        daily_used_notional_usd=args.daily_used_notional_usd,
        idempotency_key=args.idempotency_key,
        execution_id=args.execution_id,
        plan_hash=args.plan_hash,
        report_file=args.report_file,
        approval_consumed_marker=resolve(args.approval_consumed_marker)
        if args.approval_consumed_marker
        else None,
        include_live_config_overrides=args.include_live_config_overrides,
    )
    if not args.run:
        print(json.dumps(invocation, indent=2, sort_keys=True))
        return 0
    completed = subprocess.run(
        invocation["command"],
        cwd=ROOT,
        text=True,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
