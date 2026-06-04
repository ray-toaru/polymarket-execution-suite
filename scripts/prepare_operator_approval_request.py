#!/usr/bin/env python3
"""Prepare a non-authorizing operator approval request for controlled canary.

`account_id` and `active_profile_ref` are opaque runtime identity fields. They
may differ in spelling from the local `--profile` selector and are validated by
presence/exact equality, not by normalization.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path


def load_helper_module():
    helper_path = (
        Path(__file__).resolve().parents[1]
        / "polymarket-execution-engine"
        / "validation"
        / "prepare_operator_approval_request_helpers.py"
    )
    spec = importlib.util.spec_from_file_location("prepare_operator_approval_request_helpers", helper_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_helpers = load_helper_module()
DEFAULT_RELEASE_ZIP = _helpers.DEFAULT_RELEASE_ZIP
ROOT = _helpers.ROOT
build_request = _helpers.build_request
compute_approval_hash = _helpers.compute_approval_hash
canonical_approval_payload = _helpers.canonical_approval_payload
decimal_value = _helpers.decimal_value
load_json = _helpers.load_json
load_release_sidecar = _helpers.load_release_sidecar
require_nonempty_text = _helpers.require_nonempty_text
require_sha256 = _helpers.require_sha256
resolve_runtime_identity = _helpers.resolve_runtime_identity
sha256 = _helpers.sha256
validate_candidate = _helpers.validate_candidate
validate_runtime_truth = _helpers.validate_runtime_truth


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--release-zip", default=DEFAULT_RELEASE_ZIP, type=Path)
    parser.add_argument("--candidate-market-file", required=True, type=Path)
    parser.add_argument("--runtime-truth-file", required=True, type=Path)
    parser.add_argument(
        "--runtime-env-file",
        type=Path,
        help="runtime-facing env file containing PMX_ACTIVE_ACCOUNT_ID and PMX_ACTIVE_PROFILE_REF",
    )
    parser.add_argument(
        "--account-id",
        help="opaque runtime account id; if --runtime-env-file is also provided this must match it exactly",
    )
    parser.add_argument("--root-ci-run-id", required=True)
    parser.add_argument("--hermes-ci-run-id", required=True)
    parser.add_argument("--execution-engine-ci-run-id", required=True)
    parser.add_argument("--credentialed-sdk-run-id", default="local-current-gates-20260523")
    parser.add_argument("--operator-identity-ref", required=True)
    parser.add_argument("--approval-ticket-ref", required=True)
    parser.add_argument(
        "--active-profile-ref",
        help="opaque runtime profile reference; if --runtime-env-file is also provided this must match it exactly",
    )
    parser.add_argument("--max-order-notional-usd", default="0.20")
    parser.add_argument("--max-daily-notional-usd", default="0.20")
    parser.add_argument("--valid-for-minutes", type=int, default=15)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    release_zip = args.release_zip if args.release_zip.is_absolute() else ROOT / args.release_zip
    candidate_path = args.candidate_market_file if args.candidate_market_file.is_absolute() else ROOT / args.candidate_market_file
    runtime_truth_path = args.runtime_truth_file if args.runtime_truth_file.is_absolute() else ROOT / args.runtime_truth_file
    output = args.output if args.output.is_absolute() else ROOT / args.output

    sidecar = load_release_sidecar(release_zip)
    candidate = load_json(candidate_path)
    runtime_truth = load_json(runtime_truth_path)
    runtime_env_file = (
        args.runtime_env_file
        if args.runtime_env_file is None or args.runtime_env_file.is_absolute()
        else ROOT / args.runtime_env_file
    )
    account_id, active_profile_ref = resolve_runtime_identity(
        runtime_env_file=runtime_env_file,
        account_id=args.account_id,
        active_profile_ref=args.active_profile_ref,
    )
    runtime_summary = validate_runtime_truth(runtime_truth, expected_account_id=account_id)
    max_order_notional = decimal_value(args.max_order_notional_usd, "max_order_notional_usd")
    max_daily_notional = decimal_value(args.max_daily_notional_usd, "max_daily_notional_usd")
    if max_order_notional > Decimal("1"):
        raise SystemExit("max_order_notional_usd must be <= 1")
    if max_daily_notional > max_order_notional:
        raise SystemExit("max_daily_notional_usd must be <= max_order_notional_usd for single-attempt canary")
    if args.valid_for_minutes < 1 or args.valid_for_minutes > 60:
        raise SystemExit("valid_for_minutes must be between 1 and 60")
    candidate_limits = validate_candidate(candidate, max_order_notional)
    if candidate_limits["market_id"] != runtime_summary["condition_id"]:
        raise SystemExit("candidate market_id must match runtime truth condition_id")

    runtime_artifact = require_sha256(runtime_truth.get("artifact_sha256"), "runtime truth artifact_sha256")
    if runtime_artifact != sidecar["artifact_sha256"]:
        raise SystemExit("runtime truth artifact hash does not match release sidecar")
    runtime_workspace_manifest = require_sha256(
        runtime_truth.get("workspace_manifest_sha256"), "runtime truth workspace_manifest_sha256"
    )
    if runtime_workspace_manifest != sidecar["workspace_manifest_sha256"]:
        raise SystemExit("runtime truth workspace manifest hash does not match release sidecar")
    runtime_archived_manifest = require_sha256(
        runtime_truth.get("archived_manifest_sha256"), "runtime truth archived_manifest_sha256"
    )
    if runtime_archived_manifest != sidecar["archived_manifest_sha256"]:
        raise SystemExit("runtime truth archived manifest hash does not match release sidecar")

    request = build_request(
        account_id=account_id,
        condition_id=runtime_summary["condition_id"],
        active_profile_ref=active_profile_ref,
        operator_identity_ref=args.operator_identity_ref,
        approval_ticket_ref=args.approval_ticket_ref,
        candidate_market_file=candidate_path,
        runtime_truth_file=runtime_truth_path,
        runtime_gate_snapshot=runtime_summary["gate_snapshot"],
        runtime_gate_evidence_refs=runtime_summary["gate_evidence_refs"],
        sidecar=sidecar,
        candidate_limits=candidate_limits,
        max_order_notional=max_order_notional,
        max_daily_notional=max_daily_notional,
        root_ci_run_id=args.root_ci_run_id,
        hermes_ci_run_id=args.hermes_ci_run_id,
        execution_engine_ci_run_id=args.execution_engine_ci_run_id,
        credentialed_sdk_run_id=args.credentialed_sdk_run_id,
        valid_for_minutes=args.valid_for_minutes,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "output": str(output), "approval_hash": request["approval_hash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
