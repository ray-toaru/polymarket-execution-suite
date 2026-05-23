#!/usr/bin/env python3
"""Run the fail-closed controlled canary preparation pipeline.

This script intentionally stops at a no-go blocked rehearsal. It never creates a
reviewed-go decision, never submits an order, and never cancels a live order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "polymarket-execution-engine"
VERSION = (ROOT / "VERSION").read_text().strip()
DEFAULT_RELEASE_ZIP = ROOT / "dist" / f"polymarket-execution-suite-v{VERSION}.zip"
DEFAULT_MANIFEST = ENGINE / "evidence" / "current" / "manifest.json"
DEFAULT_EXTERNAL_REFERENCES = ENGINE / "config" / "controlled-canary.external-references.example.json"
BLOCKED_REHEARSAL = ENGINE / "validation" / "run_real_funds_canary_blocked_rehearsal_package.py"
PREPARE_CANDIDATE = ROOT / "scripts" / "prepare_canary_candidate_market.py"


def parse_decimal(value: Any, field: str) -> Decimal:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise SystemExit(f"candidate {field} must be a decimal")
    if not decimal.is_finite():
        raise SystemExit(f"candidate {field} must be finite")
    return decimal


def require_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip() or "REPLACE_WITH" in value:
        raise SystemExit(f"candidate {field} is required")
    return value.strip()


def require_bool(data: dict[str, Any], field: str, expected: bool) -> None:
    if data.get(field) is not expected:
        raise SystemExit(f"candidate {field} must be {str(expected).lower()}")


def validate_candidate_file(path: Path) -> dict[str, Any]:
    candidate = load_json(path)
    require_text(candidate, "market_id")
    require_text(candidate, "token_id")
    require_text(candidate, "human_review_ref")
    if candidate.get("side") != "BUY":
        raise SystemExit("candidate side must be BUY")
    if candidate.get("order_type") != "GTC":
        raise SystemExit("candidate order_type must be GTC")
    require_bool(candidate, "post_only", True)
    require_bool(candidate, "active", True)
    require_bool(candidate, "accepting_orders", True)
    require_bool(candidate, "closed", False)
    require_bool(candidate, "archived", False)

    best_ask = parse_decimal(candidate.get("best_ask"), "best_ask")
    limit_price = parse_decimal(candidate.get("limit_price"), "limit_price")
    ask_size = parse_decimal(candidate.get("ask_size"), "ask_size")
    target_size = parse_decimal(candidate.get("target_size"), "target_size")
    min_order_size = parse_decimal(candidate.get("min_order_size"), "min_order_size")
    if best_ask <= 0 or limit_price <= 0 or ask_size <= 0 or target_size <= 0:
        raise SystemExit("candidate best_ask, limit_price, ask_size, and target_size must be positive")
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
    require_text(snapshot, "source")
    require_text(snapshot, "evidence_ref")
    min_share_size = parse_decimal(snapshot.get("min_share_size"), "exchange_rule_snapshot.min_share_size")
    min_tick_size = parse_decimal(snapshot.get("min_tick_size"), "exchange_rule_snapshot.min_tick_size")
    if min_share_size <= 0 or min_tick_size <= 0:
        raise SystemExit("candidate exchange_rule_snapshot min_share_size and min_tick_size must be positive")
    if min_share_size > target_size:
        raise SystemExit("candidate exchange_rule_snapshot.min_share_size must not exceed target_size")
    if (limit_price / min_tick_size) % 1 != 0:
        raise SystemExit("candidate limit_price must align with exchange_rule_snapshot.min_tick_size")
    for field in ("captured_at", "expires_at"):
        value = require_text(snapshot, field)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise SystemExit(f"candidate exchange_rule_snapshot.{field} must be RFC3339")
        if field == "expires_at" and parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise SystemExit("candidate exchange_rule_snapshot.expires_at must be in the future")
    return candidate


def build_stage_plan(*, reviewed_go: bool, closeout_package_dir: Path | None) -> list[dict[str, Any]]:
    return [
        {"stage": "candidate", "status": "required", "remote_side_effects": False},
        {"stage": "no_go_review", "status": "required", "remote_side_effects": False},
        {"stage": "blocked_rehearsal", "status": "required", "remote_side_effects": False},
        {
            "stage": "reviewed_go_decision",
            "status": "provided" if reviewed_go else "blocked",
            "remote_side_effects": False,
        },
        {
            "stage": "armed_post_cancel",
            "status": "blocked" if not reviewed_go else "requires_explicit_operator_run",
            "remote_side_effects": reviewed_go,
        },
        {
            "stage": "readback",
            "status": "blocked" if not reviewed_go else "required_after_armed_run",
            "remote_side_effects": False,
        },
        {
            "stage": "closeout",
            "status": "available" if closeout_package_dir else "blocked",
            "remote_side_effects": False,
        },
    ]


def runtime_truth_dependencies() -> list[dict[str, Any]]:
    return [
        {
            "name": "kill_switch",
            "required_before_live": True,
            "current_pipeline_state": "local_evidence_only",
            "required_truth": "durable runtime state checked before post and cancel",
        },
        {
            "name": "live_submit_gate",
            "required_before_live": True,
            "current_pipeline_state": "release_decision_only",
            "required_truth": "runtime gate evaluated immediately before remote side effect",
        },
        {
            "name": "idempotency_lease",
            "required_before_live": True,
            "current_pipeline_state": "local_package_binding_only",
            "required_truth": "leased owner token with recovery for remote-unknown attempts",
        },
        {
            "name": "order_cancel_reconciliation",
            "required_before_live": True,
            "current_pipeline_state": "closeout_evidence_only",
            "required_truth": "durable order/cancel state machine with operator-required escalation",
        },
    ]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--release-zip", type=Path, default=DEFAULT_RELEASE_ZIP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--external-references-file", type=Path, default=DEFAULT_EXTERNAL_REFERENCES)
    parser.add_argument("--candidate-market-file", type=Path)
    parser.add_argument("--market-url")
    parser.add_argument("--market-slug")
    parser.add_argument("--outcome")
    parser.add_argument("--human-review-ref")
    parser.add_argument("--target-size")
    parser.add_argument("--max-order-notional-usd", default="1.00")
    parser.add_argument(
        "--reviewed-go-decision-file",
        type=Path,
        help="Optional future reviewed-go decision input. The current pipeline records its presence but still does not run armed live phases.",
    )
    parser.add_argument(
        "--closeout-package-dir",
        type=Path,
        help="Optional existing completed canary package directory for closeout/readback staging metadata.",
    )
    parser.add_argument("--root-ci-run-id", default="local-pipeline")
    parser.add_argument("--hermes-ci-run-id", default="local-pipeline")
    parser.add_argument("--execution-engine-ci-run-id", default="local-pipeline")
    parser.add_argument("--credentialed-sdk-run-id", default="local-pipeline")
    return parser.parse_args()


def prepare_candidate(args: argparse.Namespace, output_dir: Path) -> tuple[Path | None, list[dict[str, Any]]]:
    stages: list[dict[str, Any]] = []
    if args.candidate_market_file:
        path = args.candidate_market_file
        path = path if path.is_absolute() else ROOT / path
        validate_candidate_file(path)
        stages.append(
            {
                "stage": "candidate_supplied",
                "status": "pass",
                "path": str(path),
                "exchange_rule_snapshot_bound": True,
            }
        )
        return path, stages

    if not (args.market_url or args.market_slug):
        stages.append(
            {
                "stage": "candidate_discovery",
                "status": "skipped",
                "reason": "no market-url or market-slug supplied; blocked rehearsal will use placeholder candidate",
            }
        )
        return None, stages

    if not args.outcome or not args.human_review_ref:
        raise SystemExit("--outcome and --human-review-ref are required when preparing a fresh candidate")

    candidate = output_dir / "candidate-market.json"
    audit = output_dir / "candidate-market.audit.json"
    command = [
        sys.executable,
        str(PREPARE_CANDIDATE),
        "--output",
        str(candidate),
        "--audit-output",
        str(audit),
        "--outcome",
        args.outcome,
        "--human-review-ref",
        args.human_review_ref,
        "--max-order-notional-usd",
        args.max_order_notional_usd,
    ]
    if args.market_url:
        command.extend(["--market-url", args.market_url])
    if args.market_slug:
        command.extend(["--market-slug", args.market_slug])
    if args.target_size:
        command.extend(["--target-size", args.target_size])
    completed = run(command, cwd=ROOT)
    (output_dir / "candidate-prep.stdout").write_text(completed.stdout)
    (output_dir / "candidate-prep.stderr").write_text(completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(f"candidate preparation failed: {completed.stderr.strip() or completed.stdout.strip()}")
    stages.append(
        {
            "stage": "candidate_discovery",
            "status": "pass",
            "candidate_market_sha256": sha256(candidate),
            "path": str(candidate),
            "audit_path": str(audit),
        }
    )
    return candidate, stages


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    closeout_package_dir = (
        args.closeout_package_dir if args.closeout_package_dir is None or args.closeout_package_dir.is_absolute() else ROOT / args.closeout_package_dir
    )
    reviewed_go_present = args.reviewed_go_decision_file is not None

    release_zip = args.release_zip if args.release_zip.is_absolute() else ROOT / args.release_zip
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    if not release_zip.exists():
        raise SystemExit(f"release zip missing: {release_zip}")
    if not manifest.exists():
        raise SystemExit(f"manifest missing: {manifest}")

    sidecar = release_zip.with_suffix(release_zip.suffix + ".evidence.json")
    sidecar_data = load_json(sidecar) if sidecar.exists() else {}
    canonical = sidecar_data.get("canonical_evidence", {}) if isinstance(sidecar_data, dict) else {}
    artifact_sha = sha256(release_zip)
    workspace_manifest_sha = canonical.get("workspace_manifest_sha256") or sha256(manifest)
    archived_manifest_sha = canonical.get("archived_manifest_sha256") or canonical.get("manifest_sha256")
    if not archived_manifest_sha:
        raise SystemExit("release evidence sidecar missing archived manifest SHA-256")

    candidate, stages = prepare_candidate(args, output_dir)

    rehearsal_dir = output_dir / "no-go-blocked-rehearsal"
    command = [
        sys.executable,
        str(BLOCKED_REHEARSAL),
        "--output-dir",
        str(rehearsal_dir),
        "--external-references-file",
        str(args.external_references_file),
        "--artifact-sha256",
        artifact_sha,
        "--evidence-manifest-sha256",
        archived_manifest_sha,
        "--workspace-evidence-manifest-sha256",
        workspace_manifest_sha,
        "--archived-evidence-manifest-sha256",
        archived_manifest_sha,
        "--root-ci-run-id",
        args.root_ci_run_id,
        "--hermes-ci-run-id",
        args.hermes_ci_run_id,
        "--execution-engine-ci-run-id",
        args.execution_engine_ci_run_id,
        "--credentialed-sdk-run-id",
        args.credentialed_sdk_run_id,
    ]
    if candidate:
        command.extend(["--candidate-market-file", str(candidate)])
    completed = run(command, cwd=ENGINE)
    (output_dir / "blocked-rehearsal.stdout").write_text(completed.stdout)
    (output_dir / "blocked-rehearsal.stderr").write_text(completed.stderr)
    stages.append(
        {
            "stage": "no_go_blocked_rehearsal",
            "status": "pass" if completed.returncode == 0 else "fail",
            "exit_code": completed.returncode,
            "output_dir": str(rehearsal_dir),
        }
    )
    failures = []
    if completed.returncode != 0:
        failures.append("no-go blocked rehearsal failed")

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not failures else "fail",
        "pipeline": "controlled_canary_fail_closed_preparation",
        "artifact_sha256": artifact_sha,
        "workspace_manifest_sha256": workspace_manifest_sha,
        "archived_manifest_sha256": archived_manifest_sha,
        "candidate_market_sha256": sha256(candidate) if candidate else None,
        "live_submit_authorized": False,
        "live_cancel_authorized": False,
        "real_funds_canary_authorized": False,
        "remote_side_effects": False,
        "reviewed_go_created": False,
        "armed_cli_rehearsal_invoked": True,
        "armed_live_attempted": False,
        "stage_plan": build_stage_plan(
            reviewed_go=reviewed_go_present,
            closeout_package_dir=closeout_package_dir,
        ),
        "runtime_truth_dependencies": runtime_truth_dependencies(),
        "stages": stages,
        "failures": failures,
    }
    (output_dir / "pipeline-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
