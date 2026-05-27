#!/usr/bin/env python3
"""Prepare or run a reviewed-go canary CLI invocation from a fresh package."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = ROOT / "scripts" / "run_controlled_canary_pipeline.py"
ENV_CHECK_SCRIPT = (
    ROOT / "polymarket-execution-engine" / "validation" / "check_active_profile_consistency.py"
)
ADAPTER_MANIFEST = (
    ROOT
    / "polymarket-execution-engine"
    / "adapters"
    / "pmx-official-sdk-adapter"
    / "Cargo.toml"
)
REQUIRED_GATE_ENV_VARS = [
    "PMX_ALLOW_LIVE_SUBMIT",
    "PMX_ALLOW_REAL_FUNDS_CANARY",
    "PMX_KILL_SWITCH_OPEN",
    "PMX_RUNTIME_WORKER_HEALTHY",
    "PMX_GEOBLOCK_ALLOWED",
    "PMX_REPOSITORY_RESERVATION_EXISTS",
    "PMX_IDEMPOTENCY_KEY_WRITTEN",
    "PMX_RECONCILE_WORKER_HEALTHY",
    "PMX_CANCEL_ONLY_FALLBACK_READY",
    "PMX_BALANCE_ALLOWANCE_CHECKED",
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"{label} missing: {path}")
    return path


def require_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{field} is required")
    return value.strip()


def validate_approval(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("scope") != "REAL_FUNDS_CANARY":
        raise SystemExit("approval scope must be REAL_FUNDS_CANARY")
    if data.get("execution_style") != "GTC_LIMIT_POST_ONLY_CANCEL":
        raise SystemExit("approval execution_style must be GTC_LIMIT_POST_ONLY_CANCEL")
    for field in [
        "approval_hash",
        "artifact_sha256",
        "evidence_manifest_sha256",
        "workspace_manifest_sha256",
        "archived_manifest_sha256",
        "market_candidate_sha256",
    ]:
        require_text(data, field)
    require_text(data, "account_id")
    return data


def plan_hash_from_package(approval: dict[str, Any]) -> str:
    raw = "|".join(
        [
            approval["approval_hash"],
            approval["artifact_sha256"],
            approval["evidence_manifest_sha256"],
            approval["market_candidate_sha256"],
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def timestamp_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_marker_path(package_dir: Path) -> Path:
    return package_dir / f"approval-consumed-{timestamp_tag()}.json"


def missing_gate_env() -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_GATE_ENV_VARS:
        if str(os.environ.get(key, "")).strip() != "1":
            missing.append(key)
    return missing


def build_invocation(
    *,
    package_dir: Path,
    env_file: Path,
    mode: str,
    daily_used_notional_usd: str,
    idempotency_key: str | None,
    execution_id: str | None,
    plan_hash: str | None,
    report_file: Path | None,
    approval_consumed_marker: Path | None,
) -> dict[str, Any]:
    pipeline = load_module(PIPELINE_SCRIPT, "run_controlled_canary_pipeline")
    env_check = load_module(ENV_CHECK_SCRIPT, "check_active_profile_consistency")

    release_decision_file = require_file(package_dir / "release-decision.json", "release decision")
    approval_file = require_file(package_dir / "approval.json", "approval")
    market_file = require_file(package_dir / "candidate-market.json", "candidate market")
    runtime_truth_file = require_file(package_dir / "runtime-truth.json", "runtime truth")

    decision_summary = pipeline.validate_reviewed_go_decision_file(release_decision_file)
    runtime_truth_summary = pipeline.validate_runtime_truth_file(runtime_truth_file)
    pipeline.validate_candidate_file(market_file)
    approval = validate_approval(approval_file)
    env_summary = env_check.evaluate_env_file(env_file, expected_account_id=approval["account_id"])

    if approval["artifact_sha256"] != runtime_truth_summary["artifact_sha256"]:
        raise SystemExit("approval artifact_sha256 does not match runtime truth artifact_sha256")
    if approval["workspace_manifest_sha256"] != runtime_truth_summary["workspace_manifest_sha256"]:
        raise SystemExit("approval workspace_manifest_sha256 does not match runtime truth")
    if approval["archived_manifest_sha256"] != runtime_truth_summary["archived_manifest_sha256"]:
        raise SystemExit("approval archived_manifest_sha256 does not match runtime truth")

    mode_flag = {
        "preflight": "--preflight-only",
        "armed": "--armed",
    }.get(mode)
    if mode_flag is None:
        raise SystemExit(f"unsupported mode: {mode}")

    idempotency = idempotency_key or f"canary-{approval['approval_hash'][:12]}-{mode}"
    execution = execution_id or f"exec-{approval['approval_hash'][:12]}"
    plan = plan_hash or plan_hash_from_package(approval)
    report = report_file or (package_dir / "post-canary-report.json")
    marker = approval_consumed_marker or default_marker_path(package_dir)

    command = [
        "cargo",
        "run",
        "--manifest-path",
        str(ADAPTER_MANIFEST),
        "--features",
        "live-submit",
        "--bin",
        "pmx-real-funds-canary",
        "--",
        mode_flag,
        "--env-file",
        str(env_file),
        "--approval-file",
        str(approval_file),
        "--release-decision-file",
        str(release_decision_file),
        "--runtime-truth-file",
        str(runtime_truth_file),
        "--market-file",
        str(market_file),
        "--artifact-sha256",
        approval["artifact_sha256"],
        "--evidence-manifest-sha256",
        approval["evidence_manifest_sha256"],
        "--idempotency-key",
        idempotency,
        "--account-id",
        approval["account_id"],
        "--execution-id",
        execution,
        "--plan-hash",
        plan,
        "--daily-used-notional-usd",
        daily_used_notional_usd,
        "--allow-live-submit-config",
        "--allow-real-funds-canary-config",
    ]
    if mode == "armed":
        command.extend(
            [
                "--approval-consumed-marker",
                str(marker),
                "--report-file",
                str(report),
            ]
        )

    return {
        "status": "ready",
        "mode": mode,
        "package_dir": str(package_dir),
        "env_file": str(env_file),
        "account_id": approval["account_id"],
        "active_profile_ref": env_summary["active_profile_ref"],
        "approval_hash": approval["approval_hash"],
        "decision_id": decision_summary["decision_id"],
        "runtime_truth_sha256": runtime_truth_summary["sha256"],
        "command": command,
        "required_gate_env_vars": REQUIRED_GATE_ENV_VARS,
        "missing_gate_env_vars": missing_gate_env(),
        "report_file": str(report) if mode == "armed" else None,
        "approval_consumed_marker": str(marker) if mode == "armed" else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--mode", choices=["preflight", "armed"], default="preflight")
    parser.add_argument("--daily-used-notional-usd", default="0")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--execution-id")
    parser.add_argument("--plan-hash")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--approval-consumed-marker", type=Path)
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the resolved cargo command. Without this flag the script only prints the invocation plan.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    invocation = build_invocation(
        package_dir=resolve(args.package_dir),
        env_file=resolve(args.env_file),
        mode=args.mode,
        daily_used_notional_usd=args.daily_used_notional_usd,
        idempotency_key=args.idempotency_key,
        execution_id=args.execution_id,
        plan_hash=args.plan_hash,
        report_file=resolve(args.report_file) if args.report_file else None,
        approval_consumed_marker=resolve(args.approval_consumed_marker)
        if args.approval_consumed_marker
        else None,
    )
    if not args.run:
        print(json.dumps(invocation, indent=2, sort_keys=True))
        return 0

    missing = invocation["missing_gate_env_vars"]
    if missing:
        raise SystemExit(
            "cannot execute reviewed-go canary; missing required gate env vars: "
            + ", ".join(missing)
        )

    completed = subprocess.run(
        invocation["command"],
        cwd=ROOT,
        text=True,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
