#!/usr/bin/env python3
"""Prepare a non-authorizing operator approval request for controlled canary."""
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
PLACEHOLDER_TOKENS = ("REPLACE_WITH", "TODO", "TBD")
REQUIRED_RUNTIME_TRUTH_DEPENDENCIES = {
    "kill_switch",
    "live_submit_gate",
    "idempotency_lease",
    "order_cancel_reconciliation",
    "no_geoblock",
    "market_live",
    "account_allowlist",
    "balance_allowance",
    "reconcile_worker_healthy",
    "cancel_only_fallback",
}


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

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def has_placeholder(value: object) -> bool:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return True
        upper = stripped.upper()
        return any(token in upper for token in PLACEHOLDER_TOKENS) or (stripped.startswith("<") and stripped.endswith(">"))
    if isinstance(value, dict):
        return any(has_placeholder(child) for child in value.values())
    if isinstance(value, list):
        return any(has_placeholder(child) for child in value)
    return False


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise SystemExit(f"{label} must be a lowercase 64-character SHA-256 hex digest")
    return value


def require_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or has_placeholder(value):
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


def parse_time(value: object, label: str) -> datetime:
    text = require_nonempty_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"{label} must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise SystemExit(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


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


def validate_runtime_truth(runtime_truth: dict[str, Any], sidecar: dict[str, str]) -> None:
    runtime_artifact = require_sha256(runtime_truth.get("artifact_sha256"), "runtime truth artifact_sha256")
    if runtime_artifact != sidecar["artifact_sha256"]:
        raise SystemExit("runtime truth artifact hash does not match release sidecar")
    for field in ["workspace_manifest_sha256", "archived_manifest_sha256"]:
        value = require_sha256(runtime_truth.get(field), f"runtime truth {field}")
        if value != sidecar[field]:
            raise SystemExit(f"runtime truth {field} does not match release sidecar")
    report = runtime_truth.get("preflight_report")
    if isinstance(report, dict):
        if report.get("posted") is not False or report.get("remote_side_effects") is not False:
            raise SystemExit("runtime truth preflight_report must remain non-posting and side-effect-free")
        if report.get("status") != "preflight_ready":
            raise SystemExit("runtime truth preflight_report.status must be preflight_ready")
    if runtime_truth.get("remote_side_effects") is not False:
        raise SystemExit("runtime truth must keep remote_side_effects=false")
    dependencies = runtime_truth.get("dependencies")
    if not isinstance(dependencies, list):
        raise SystemExit("runtime truth dependencies must be a list")
    ready: set[str] = set()
    for item in dependencies:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        evidence_ref = item.get("evidence_ref")
        if (
            isinstance(name, str)
            and item.get("status") == "durable_runtime_truth"
            and isinstance(evidence_ref, str)
            and not has_placeholder(evidence_ref)
        ):
            ready.add(name)
    missing = sorted(REQUIRED_RUNTIME_TRUTH_DEPENDENCIES - ready)
    if missing:
        raise SystemExit("runtime truth missing durable dependencies: " + ", ".join(missing))


def build_request(
    *,
    account_id: str,
    active_profile_ref: str,
    operator_identity_ref: str,
    approval_ticket_ref: str,
    candidate_market_file: Path,
    runtime_truth_file: Path,
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
        "account_id": require_nonempty_text(account_id, "account_id"),
        "active_profile_ref": require_nonempty_text(active_profile_ref, "active_profile_ref"),
        "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
        "requested_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=valid_for_minutes)).isoformat(),
        "operator_identity_ref": require_nonempty_text(operator_identity_ref, "operator_identity_ref"),
        "approval_ticket_ref": require_nonempty_text(approval_ticket_ref, "approval_ticket_ref"),
        "dual_control_required": True,
        "approval_replay_block_required": True,
        "approval_expiry_enforced": True,
        "artifact_sha256": sidecar["artifact_sha256"],
        "workspace_manifest_sha256": sidecar["workspace_manifest_sha256"],
        "archived_manifest_sha256": sidecar["archived_manifest_sha256"],
        "evidence_manifest_sha256": sidecar["evidence_manifest_sha256"],
        "market_candidate_sha256": sha256(candidate_market_file),
        "runtime_truth_sha256": sha256(runtime_truth_file),
        "github_evidence": {
            "root_ci_run_id": require_nonempty_text(root_ci_run_id, "root_ci_run_id"),
            "hermes_ci_run_id": require_nonempty_text(hermes_ci_run_id, "hermes_ci_run_id"),
            "execution_engine_ci_run_id": require_nonempty_text(execution_engine_ci_run_id, "execution_engine_ci_run_id"),
            "credentialed_sdk_run_id": require_nonempty_text(credentialed_sdk_run_id, "credentialed_sdk_run_id"),
        },
        "risk_limits": {
            "max_order_notional_usd": decimal_text(max_order_notional),
            "max_daily_notional_usd": decimal_text(max_daily_notional),
            "candidate_target_size": candidate_limits["target_size"],
            "candidate_limit_price": candidate_limits["limit_price"],
            "candidate_estimated_order_notional_usd": candidate_limits["estimated_order_notional_usd"],
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
        "workspace_manifest_sha256": require_sha256(canonical.get("workspace_manifest_sha256"), "canonical_evidence.workspace_manifest_sha256"),
        "archived_manifest_sha256": require_sha256(canonical.get("archived_manifest_sha256"), "canonical_evidence.archived_manifest_sha256"),
        "evidence_manifest_sha256": require_sha256(canonical.get("manifest_sha256"), "canonical_evidence.manifest_sha256"),
    }


def validate_candidate(candidate: dict[str, Any], max_order_notional: Decimal) -> dict[str, str]:
    for field, expected in {
        "side": "BUY",
        "order_type": "GTC",
        "post_only": True,
        "active": True,
        "accepting_orders": True,
        "closed": False,
        "archived": False,
    }.items():
        if candidate.get(field) != expected:
            raise SystemExit(f"candidate {field} must be {expected!r}")
    for field in ["market_id", "token_id", "human_review_ref"]:
        require_nonempty_text(candidate.get(field), f"candidate {field}")
    best_ask = decimal_value(candidate.get("best_ask"), "candidate best_ask")
    ask_size = decimal_value(candidate.get("ask_size"), "candidate ask_size")
    target_size = decimal_value(candidate.get("target_size"), "candidate target_size")
    limit_price = decimal_value(candidate.get("limit_price"), "candidate limit_price")
    min_order_size = decimal_value(candidate.get("min_order_size"), "candidate min_order_size")
    notional = decimal_value(candidate.get("estimated_order_notional_usd"), "candidate estimated_order_notional_usd")
    if notional != target_size * limit_price:
        raise SystemExit("candidate estimated_order_notional_usd must equal target_size * limit_price")
    if notional > max_order_notional:
        raise SystemExit("candidate notional exceeds requested max_order_notional_usd")
    if limit_price >= best_ask:
        raise SystemExit("candidate post-only BUY limit_price must be below best_ask")
    if ask_size < target_size:
        raise SystemExit("candidate ask_size must cover target_size")
    if min_order_size > target_size:
        raise SystemExit("candidate min_order_size must not exceed target_size")
    snapshot = candidate.get("exchange_rule_snapshot")
    if not isinstance(snapshot, dict):
        raise SystemExit("candidate exchange_rule_snapshot is required")
    required_snapshot = {
        "schema_version": 1,
        "venue": "polymarket_clob",
        "order_mode": "post_only_limit",
        "order_type": "GTC",
        "side": "BUY",
        "target_size_semantics": "outcome_shares",
    }
    for field, expected in required_snapshot.items():
        if snapshot.get(field) != expected:
            raise SystemExit(f"candidate exchange_rule_snapshot.{field} must be {expected!r}")
    require_nonempty_text(snapshot.get("source"), "candidate exchange_rule_snapshot.source")
    require_nonempty_text(snapshot.get("evidence_ref"), "candidate exchange_rule_snapshot.evidence_ref")
    min_share_size = decimal_value(snapshot.get("min_share_size"), "candidate exchange_rule_snapshot.min_share_size")
    min_tick_size = decimal_value(snapshot.get("min_tick_size"), "candidate exchange_rule_snapshot.min_tick_size")
    if min_share_size > target_size:
        raise SystemExit("candidate exchange_rule_snapshot.min_share_size must not exceed target_size")
    if (limit_price / min_tick_size) % 1 != 0:
        raise SystemExit("candidate limit_price must align with exchange_rule_snapshot.min_tick_size")
    parse_time(snapshot.get("captured_at"), "candidate exchange_rule_snapshot.captured_at")
    if parse_time(snapshot.get("expires_at"), "candidate exchange_rule_snapshot.expires_at") <= datetime.now(timezone.utc):
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
    parser.add_argument("--runtime-env-file", type=Path)
    parser.add_argument("--account-id")
    parser.add_argument("--root-ci-run-id", required=True)
    parser.add_argument("--hermes-ci-run-id", required=True)
    parser.add_argument("--execution-engine-ci-run-id", required=True)
    parser.add_argument("--credentialed-sdk-run-id", required=True)
    parser.add_argument("--operator-identity-ref", required=True)
    parser.add_argument("--approval-ticket-ref", required=True)
    parser.add_argument("--active-profile-ref")
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
    runtime_env_file = args.runtime_env_file if args.runtime_env_file is None or args.runtime_env_file.is_absolute() else ROOT / args.runtime_env_file
    account_id, active_profile_ref = resolve_runtime_identity(
        runtime_env_file=runtime_env_file,
        account_id=args.account_id,
        active_profile_ref=args.active_profile_ref,
    )
    max_order_notional = decimal_value(args.max_order_notional_usd, "max_order_notional_usd")
    max_daily_notional = decimal_value(args.max_daily_notional_usd, "max_daily_notional_usd")
    if max_order_notional > Decimal("1"):
        raise SystemExit("max_order_notional_usd must be <= 1")
    if max_daily_notional > Decimal("5"):
        raise SystemExit("max_daily_notional_usd must be <= 5")
    if max_daily_notional < max_order_notional:
        raise SystemExit("max_daily_notional_usd must be >= max_order_notional_usd")
    candidate_limits = validate_candidate(candidate, max_order_notional)
    candidate_notional = decimal_value(candidate_limits["estimated_order_notional_usd"], "candidate estimated_order_notional_usd")
    if max_order_notional < candidate_notional or max_daily_notional < candidate_notional:
        raise SystemExit("risk limits must cover candidate notional")
    validate_runtime_truth(runtime_truth, sidecar)

    request = build_request(
        account_id=account_id,
        active_profile_ref=active_profile_ref,
        operator_identity_ref=args.operator_identity_ref,
        approval_ticket_ref=args.approval_ticket_ref,
        candidate_market_file=candidate_path,
        runtime_truth_file=runtime_truth_path,
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
