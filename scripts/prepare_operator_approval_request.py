#!/usr/bin/env python3
"""Prepare a non-authorizing operator approval request for controlled canary.

`account_id` and `active_profile_ref` are opaque runtime identity fields. They
may differ in spelling from the local `--profile` selector and are validated by
presence/exact equality, not by normalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
DEFAULT_RELEASE_ZIP = ROOT / "dist" / f"polymarket-execution-suite-v{VERSION}.zip"
ACTIVE_PROFILE_CHECK = ROOT / "polymarket-execution-engine" / "validation" / "check_active_profile_consistency.py"
PREFLIGHT_GATE_FIELDS = (
    "preconditions_live_submit_would_pass",
    "preconditions_real_funds_canary_would_pass",
    "kill_switch_open",
    "runtime_worker_healthy",
    "geoblock_allowed",
    "repository_reservation_exists",
    "idempotency_key_written",
    "reconcile_worker_healthy",
    "cancel_only_fallback_ready",
    "balance_allowance_checked",
)
PREFLIGHT_GATE_EVIDENCE_FIELDS = (
    "kill_switch_open",
    "runtime_worker_healthy",
    "geoblock_allowed",
    "repository_reservation_exists",
    "idempotency_key_written",
    "reconcile_worker_healthy",
    "cancel_only_fallback_ready",
    "balance_allowance_checked",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_module(path: Path, name: str):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SystemExit(f"{label} must be a 64-character SHA-256 hex digest")
    return value.lower()


def require_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.startswith("REPLACE_WITH_"):
        raise SystemExit(f"{label} must be a non-empty non-placeholder string")
    return value.strip()


def decimal_value(value: object, label: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SystemExit(f"{label} must be a decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise SystemExit(f"{label} must be positive")
    return parsed


def decimal_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return "0" if text == "-0" else text


def validate_runtime_truth(
    runtime_truth: dict[str, Any],
    *,
    expected_account_id: str,
) -> dict[str, Any]:
    account_id = require_nonempty_text(runtime_truth.get("account_id"), "runtime truth account_id")
    if account_id != expected_account_id:
        raise SystemExit("runtime truth account_id does not match active runtime account")
    condition_id = require_nonempty_text(runtime_truth.get("condition_id"), "runtime truth condition_id")
    preflight_report = runtime_truth.get("preflight_report")
    if not isinstance(preflight_report, dict):
        raise SystemExit("runtime truth preflight_report must be an object")
    if preflight_report.get("status") != "preflight_ready":
        raise SystemExit("runtime truth preflight_report.status must be preflight_ready")
    gate_snapshot: dict[str, bool] = {}
    for field in PREFLIGHT_GATE_FIELDS:
        if preflight_report.get(field) is not True:
            raise SystemExit(f"runtime truth preflight_report.{field} must be true")
        gate_snapshot[field] = True
    gate_evidence_refs = preflight_report.get("gate_evidence_refs")
    if not isinstance(gate_evidence_refs, dict):
        raise SystemExit("runtime truth preflight_report.gate_evidence_refs must be an object")
    validated_gate_evidence_refs: dict[str, str] = {}
    for field in PREFLIGHT_GATE_EVIDENCE_FIELDS:
        evidence_ref = gate_evidence_refs.get(field)
        if not isinstance(evidence_ref, str) or not evidence_ref.strip() or "REPLACE_WITH" in evidence_ref:
            raise SystemExit(f"runtime truth preflight_report.gate_evidence_refs.{field} must be a concrete string")
        validated_gate_evidence_refs[field] = evidence_ref.strip()
    return {
        "account_id": account_id,
        "condition_id": condition_id,
        "gate_snapshot": gate_snapshot,
        "gate_evidence_refs": validated_gate_evidence_refs,
    }


def resolve_runtime_identity(
    *,
    runtime_env_file: Path | None,
    account_id: str | None,
    active_profile_ref: str | None,
) -> tuple[str, str]:
    resolved_account = account_id.strip() if isinstance(account_id, str) and account_id.strip() else None
    resolved_profile_ref = (
        active_profile_ref.strip()
        if isinstance(active_profile_ref, str) and active_profile_ref.strip()
        else None
    )
    if runtime_env_file is not None:
        checker = load_module(ACTIVE_PROFILE_CHECK, "check_active_profile_consistency")
        report = checker.evaluate_env_file(runtime_env_file, expected_account_id=resolved_account)
        env_account = require_nonempty_text(report.get("active_account_id"), "runtime env active_account_id")
        env_profile_ref = require_nonempty_text(report.get("active_profile_ref"), "runtime env active_profile_ref")
        if resolved_account is not None and resolved_account != env_account:
            raise SystemExit("runtime env account_id does not match explicit --account-id")
        if resolved_profile_ref is not None and resolved_profile_ref != env_profile_ref:
            raise SystemExit("runtime env active_profile_ref does not match explicit --active-profile-ref")
        return env_account, env_profile_ref
    if resolved_account is None:
        raise SystemExit("either --account-id or --runtime-env-file is required")
    if resolved_profile_ref is None:
        raise SystemExit("either --active-profile-ref or --runtime-env-file is required")
    return resolved_account, resolved_profile_ref


def build_request(
    *,
    account_id: str,
    condition_id: str,
    active_profile_ref: str,
    operator_identity_ref: str,
    approval_ticket_ref: str,
    candidate_market_file: Path,
    runtime_truth_file: Path,
    runtime_gate_snapshot: dict[str, bool],
    runtime_gate_evidence_refs: dict[str, str],
    sidecar: dict[str, str],
    candidate_limits: dict[str, str],
    max_order_notional: Decimal,
    max_daily_notional: Decimal,
    root_ci_run_id: str,
    hermes_ci_run_id: str,
    execution_engine_ci_run_id: str,
    credentialed_sdk_run_id: str,
    valid_for_minutes: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    request = {
        "schema_version": 1,
        "status": "operator_approval_request_not_authorization",
        "approval_id": f"approval-request-controlled-canary-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "scope": "REAL_FUNDS_CANARY",
        "account_id": account_id,
        "condition_id": condition_id,
        "active_profile_ref": active_profile_ref,
        "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
        "requested_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=valid_for_minutes)).isoformat(),
        "operator_identity_ref": require_nonempty_text(
            operator_identity_ref, "operator_identity_ref"
        ),
        "approval_ticket_ref": require_nonempty_text(
            approval_ticket_ref, "approval_ticket_ref"
        ),
        "dual_control_required": True,
        "approval_replay_block_required": True,
        "approval_expiry_enforced": True,
        "artifact_sha256": sidecar["artifact_sha256"],
        "workspace_manifest_sha256": sidecar["workspace_manifest_sha256"],
        "archived_manifest_sha256": sidecar["archived_manifest_sha256"],
        "evidence_manifest_sha256": sidecar["evidence_manifest_sha256"],
        "market_candidate_sha256": sha256(candidate_market_file),
        "runtime_truth_sha256": sha256(runtime_truth_file),
        "runtime_gate_snapshot": runtime_gate_snapshot,
        "runtime_gate_evidence_refs": runtime_gate_evidence_refs,
        "github_evidence": {
            "root_ci_run_id": root_ci_run_id,
            "hermes_ci_run_id": hermes_ci_run_id,
            "execution_engine_ci_run_id": execution_engine_ci_run_id,
            "credentialed_sdk_run_id": credentialed_sdk_run_id,
        },
        "risk_limits": {
            "max_order_notional_usd": decimal_text(max_order_notional),
            "max_daily_notional_usd": decimal_text(max_daily_notional),
            "candidate_target_size": candidate_limits["target_size"],
            "candidate_limit_price": candidate_limits["limit_price"],
            "candidate_estimated_order_notional_usd": candidate_limits[
                "estimated_order_notional_usd"
            ],
        },
        "live_submit_authorized": False,
        "live_cancel_authorized": False,
        "real_funds_canary_authorized": False,
        "remote_side_effects_authorized": False,
        "production_deployment_authorized": False,
        "secrets_included": False,
    }
    request["approval_hash"] = compute_approval_hash(request)
    return request


def load_release_sidecar(release_zip: Path) -> dict[str, Any]:
    sidecar = release_zip.with_suffix(release_zip.suffix + ".evidence.json")
    if not sidecar.exists():
        raise SystemExit(f"release evidence sidecar missing: {sidecar}")
    data = load_json(sidecar)
    artifact = data.get("artifact", {})
    canonical = data.get("canonical_evidence", {})
    return {
        "artifact_sha256": require_sha256(artifact.get("sha256"), "artifact.sha256"),
        "workspace_manifest_sha256": require_sha256(
            canonical.get("workspace_manifest_sha256"),
            "canonical_evidence.workspace_manifest_sha256",
        ),
        "archived_manifest_sha256": require_sha256(
            canonical.get("archived_manifest_sha256"),
            "canonical_evidence.archived_manifest_sha256",
        ),
        "evidence_manifest_sha256": require_sha256(
            canonical.get("manifest_sha256"),
            "canonical_evidence.manifest_sha256",
        ),
    }


def validate_candidate(candidate: dict[str, Any], max_order_notional: Decimal) -> dict[str, str]:
    if candidate.get("side") != "BUY":
        raise SystemExit("candidate side must be BUY")
    if candidate.get("order_type") != "GTC":
        raise SystemExit("candidate order_type must be GTC")
    if candidate.get("post_only") is not True:
        raise SystemExit("candidate post_only must be true")
    target_size = decimal_value(candidate.get("target_size"), "candidate target_size")
    limit_price = decimal_value(candidate.get("limit_price"), "candidate limit_price")
    notional = decimal_value(candidate.get("estimated_order_notional_usd"), "candidate estimated_order_notional_usd")
    if notional != target_size * limit_price:
        raise SystemExit("candidate estimated_order_notional_usd must equal target_size * limit_price")
    if notional > max_order_notional:
        raise SystemExit("candidate notional exceeds requested max_order_notional_usd")
    snapshot = candidate.get("exchange_rule_snapshot")
    if not isinstance(snapshot, dict):
        raise SystemExit("candidate exchange_rule_snapshot is required")
    expires_at = snapshot.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at.strip():
        raise SystemExit("candidate exchange_rule_snapshot.expires_at is required")
    try:
        parsed_expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit("candidate exchange_rule_snapshot.expires_at must be RFC3339") from exc
    if parsed_expiry.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise SystemExit("candidate exchange_rule_snapshot.expires_at must be in the future")
    return {
        "target_size": decimal_text(target_size),
        "limit_price": decimal_text(limit_price),
        "estimated_order_notional_usd": decimal_text(notional),
    }


def canonical_approval_payload(request: dict[str, Any]) -> dict[str, Any]:
    payload = dict(request)
    payload.pop("approval_hash", None)
    return payload


def compute_approval_hash(request: dict[str, Any]) -> str:
    payload = canonical_approval_payload(request)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
    if max_daily_notional > Decimal("5"):
        raise SystemExit("max_daily_notional_usd must be <= 5")
    candidate_limits = validate_candidate(candidate, max_order_notional)

    runtime_artifact = require_sha256(runtime_truth.get("artifact_sha256"), "runtime truth artifact_sha256")
    if runtime_artifact != sidecar["artifact_sha256"]:
        raise SystemExit("runtime truth artifact hash does not match release sidecar")

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
