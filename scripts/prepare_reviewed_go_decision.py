#!/usr/bin/env python3
"""Promote a canary approval request into a reviewed-go decision."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "polymarket-execution-engine"
VERSION = (ROOT / "VERSION").read_text().strip()
VALIDATOR = ENGINE / "validation" / "validate_controlled_canary_release_decision.py"


REQUIRED_EXTERNAL_REFS = {
    "secret_custody_ref": ("secret_custody", "provider_ref"),
    "operator_approval_ref": ("operator_approval", "ticket_ref"),
    "alert_routing_ref": ("alert_routing", "route_ref"),
    "dashboard_ref": ("alert_routing", "dashboard_ref"),
    "rollback_runbook_ref": ("runbooks", "rollback_runbook_ref"),
    "incident_runbook_ref": ("runbooks", "incident_runbook_ref"),
}
REVIEW_SIGNALS = [
    "artifact_hash_reviewed",
    "evidence_manifest_hash_reviewed",
    "market_candidate_reviewed",
    "operator_dual_control_reviewed",
    "secret_custody_reviewed",
    "alerting_reviewed",
    "rollback_reviewed",
    "runtime_health_reviewed",
    "reconcile_and_cancel_fallback_reviewed",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def has_placeholder(value: object) -> bool:
    if isinstance(value, str):
        return value.startswith("REPLACE_WITH_") or not value.strip()
    if isinstance(value, dict):
        return any(has_placeholder(child) for child in value.values())
    if isinstance(value, list):
        return any(has_placeholder(child) for child in value)
    return False


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SystemExit(f"{label} must be a 64-character SHA-256 hex digest")
    return value.lower()


def parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{label} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"{label} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_approval_request(request: dict[str, Any]) -> None:
    if request.get("status") != "operator_approval_request_not_authorization":
        raise SystemExit("approval request status must be operator_approval_request_not_authorization")
    if request.get("scope") != "REAL_FUNDS_CANARY":
        raise SystemExit("approval request scope must be REAL_FUNDS_CANARY")
    if request.get("execution_style") != "GTC_LIMIT_POST_ONLY_CANCEL":
        raise SystemExit("approval request execution_style must be GTC_LIMIT_POST_ONLY_CANCEL")
    if request.get("dual_control_required") is not True:
        raise SystemExit("approval request must require dual control")
    if request.get("live_submit_authorized") is not False:
        raise SystemExit("approval request must not itself authorize live submit")
    if request.get("remote_side_effects_authorized") is not False:
        raise SystemExit("approval request must not itself authorize remote side effects")
    if request.get("secrets_included") is not False:
        raise SystemExit("approval request must not include secrets")
    if parse_time(request.get("expires_at"), "approval request expires_at") <= datetime.now(timezone.utc):
        raise SystemExit("approval request is expired")
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
    if request.get("archived_manifest_sha256") != request.get("evidence_manifest_sha256"):
        raise SystemExit("approval request archived/evidence manifest hashes must match")


def external_refs(external: dict[str, Any], dual_control_review_ref: str) -> dict[str, str]:
    if has_placeholder(external):
        raise SystemExit("external references must not contain placeholders")
    refs: dict[str, str] = {}
    for output_key, path in REQUIRED_EXTERNAL_REFS.items():
        current: object = external
        for part in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if not isinstance(current, str) or not current.strip():
            raise SystemExit(f"external reference missing {'.'.join(path)}")
        refs[output_key] = current
    refs["operator_dual_control_review_ref"] = dual_control_review_ref
    return refs


def build_decision(
    request: dict[str, Any],
    external: dict[str, Any],
    *,
    decision_id: str,
    decision_reason: str,
    dual_control_review_ref: str,
) -> dict[str, Any]:
    if not dual_control_review_ref.strip() or dual_control_review_ref.startswith("REPLACE_WITH_"):
        raise SystemExit("dual-control review ref is required")
    validate_approval_request(request)
    refs = external_refs(external, dual_control_review_ref)
    return {
        "schema_version": 1,
        "decision_id": decision_id,
        "status": "reviewed_go",
        "source_release": f"v{VERSION}",
        "decision": "go",
        "decision_reason": decision_reason,
        "scope": "REAL_FUNDS_CANARY",
        "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
        "expires_at": request["expires_at"],
        "artifact_sha256": request["artifact_sha256"],
        "evidence_manifest_sha256": request["evidence_manifest_sha256"],
        "workspace_manifest_sha256": request["workspace_manifest_sha256"],
        "archived_manifest_sha256": request["archived_manifest_sha256"],
        "market_candidate_sha256": request["market_candidate_sha256"],
        "github_evidence": request["github_evidence"],
        "external_references": refs,
        "risk_limits": {
            "max_order_notional_usd": request["risk_limits"]["max_order_notional_usd"],
            "max_daily_notional_usd": request["risk_limits"]["max_daily_notional_usd"],
        },
        "required_review_signals": {signal: True for signal in REVIEW_SIGNALS},
        "live_submit_authorized": True,
        "live_cancel_authorized": True,
        "production_deployment_authorized": False,
        "real_funds_canary_authorized": True,
        "remote_side_effects_authorized": True,
        "allow_real_funds_canary": True,
        "reviewed_release_decision_present": True,
        "operator_identity_ref": request["operator_identity_ref"],
        "secrets_included": False,
    }


def validate_decision_output(decision: dict[str, Any]) -> None:
    spec = importlib.util.spec_from_file_location("validate_controlled_canary_release_decision", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    failures = module.validate_decision(decision, "reviewed_go_output")
    if failures:
        raise SystemExit("reviewed-go decision validation failed: " + "; ".join(failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-request-file", required=True, type=Path)
    parser.add_argument("--external-references-file", required=True, type=Path)
    parser.add_argument("--dual-control-review-ref", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--decision-reason", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    approval_path = args.approval_request_file if args.approval_request_file.is_absolute() else ROOT / args.approval_request_file
    external_path = args.external_references_file if args.external_references_file.is_absolute() else ROOT / args.external_references_file
    output = args.output if args.output.is_absolute() else ROOT / args.output
    decision = build_decision(
        load_json(approval_path),
        load_json(external_path),
        decision_id=args.decision_id,
        decision_reason=args.decision_reason,
        dual_control_review_ref=args.dual_control_review_ref,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_decision_output(decision)
    output.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
