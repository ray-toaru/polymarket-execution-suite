#!/usr/bin/env python3
"""Prepare a non-authorizing dual-control review template for controlled canary."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SystemExit(f"{label} must be a 64-character SHA-256 hex digest")
    return value.lower()


def require_approval_request(request: dict[str, Any]) -> None:
    if request.get("status") != "operator_approval_request_not_authorization":
        raise SystemExit("approval request status must be operator_approval_request_not_authorization")
    if request.get("scope") != "REAL_FUNDS_CANARY":
        raise SystemExit("approval request scope must be REAL_FUNDS_CANARY")
    if request.get("execution_style") != "GTC_LIMIT_POST_ONLY_CANCEL":
        raise SystemExit("approval request execution_style must be GTC_LIMIT_POST_ONLY_CANCEL")
    if request.get("live_submit_authorized") is not False:
        raise SystemExit("approval request must not authorize live submit")
    if request.get("remote_side_effects_authorized") is not False:
        raise SystemExit("approval request must not authorize remote side effects")
    if request.get("secrets_included") is not False:
        raise SystemExit("approval request must not include secrets")
    for field in [
        "approval_hash",
        "artifact_sha256",
        "workspace_manifest_sha256",
        "archived_manifest_sha256",
        "evidence_manifest_sha256",
        "market_candidate_sha256",
        "runtime_truth_sha256",
    ]:
        require_sha256(request.get(field), f"approval request {field}")


def build_template(request: dict[str, Any], *, approval_request_sha256: str) -> dict[str, Any]:
    require_approval_request(request)
    risk_limits = request.get("risk_limits")
    if not isinstance(risk_limits, dict):
        raise SystemExit("approval request risk_limits must be an object")
    return {
        "schema_version": 1,
        "status": "draft_requires_independent_reviewer",
        "scope": "REAL_FUNDS_CANARY",
        "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
        "review_ref": "REPLACE_WITH_DUAL_CONTROL_REVIEW_REF",
        "reviewer_identity_ref": "REPLACE_WITH_INDEPENDENT_REVIEWER_IDENTITY_REF",
        "reviewed_at": "REPLACE_WITH_RFC3339_REVIEW_TIME",
        "expires_at": request["expires_at"],
        "approval_request_sha256": approval_request_sha256,
        "approval_hash": request["approval_hash"],
        "artifact_sha256": request["artifact_sha256"],
        "workspace_manifest_sha256": request["workspace_manifest_sha256"],
        "archived_manifest_sha256": request["archived_manifest_sha256"],
        "evidence_manifest_sha256": request["evidence_manifest_sha256"],
        "market_candidate_sha256": request["market_candidate_sha256"],
        "runtime_truth_sha256": request["runtime_truth_sha256"],
        "risk_limits": {
            "max_order_notional_usd": risk_limits.get("max_order_notional_usd"),
            "max_daily_notional_usd": risk_limits.get("max_daily_notional_usd"),
            "candidate_target_size": risk_limits.get("candidate_target_size"),
            "candidate_limit_price": risk_limits.get("candidate_limit_price"),
            "candidate_estimated_order_notional_usd": risk_limits.get("candidate_estimated_order_notional_usd"),
        },
        "required_reviewer_checks": {
            "artifact_hash_reviewed": False,
            "evidence_manifest_hash_reviewed": False,
            "market_candidate_reviewed": False,
            "runtime_truth_reviewed": False,
            "risk_limits_reviewed": False,
            "secret_custody_reviewed": False,
            "alerting_reviewed": False,
            "rollback_reviewed": False,
            "reconcile_and_cancel_fallback_reviewed": False,
        },
        "reviewer_instruction": (
            "This template is not an authorization. An independent reviewer must replace review_ref, "
            "reviewer_identity_ref, reviewed_at, set status to approved, and set each required_reviewer_checks "
            "entry to true only after reviewing the bound artifacts."
        ),
        "live_submit_authorized": False,
        "live_cancel_authorized": False,
        "real_funds_canary_authorized": False,
        "remote_side_effects_authorized": False,
        "production_deployment_authorized": False,
        "secrets_included": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-request-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    approval_path = args.approval_request_file if args.approval_request_file.is_absolute() else ROOT / args.approval_request_file
    output = args.output if args.output.is_absolute() else ROOT / args.output
    template = build_template(load_json(approval_path), approval_request_sha256=sha256(approval_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
