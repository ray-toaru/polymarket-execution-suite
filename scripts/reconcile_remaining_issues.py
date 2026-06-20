#!/usr/bin/env python3
"""Reconcile non-live remaining issues after local debt hardening.

This script does not promote a release. It moves the historical accepted
non-live debt bucket into explicit closure/defer records and preserves
production/live policy blockers as promotion gates.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACCEPTED_DEBT_DISPOSITION: dict[str, tuple[str, str]] = {
    "F-009": ("closed_by_existing_hardening", "dist reviewed-go material guard added"),
    "F-010": ("closed_by_existing_hardening", "release source secret assignment scan added"),
    "F-051": ("closed_by_existing_hardening", "v0.28 guard accepts explicit target-version"),
    "F-057": ("closed_by_existing_hardening", "structured release-decision guard added"),
    "F-081": ("closed_by_existing_hardening", "candidate audit output and failed-book negative coverage added"),
    "F-094": ("closed_by_existing_hardening", "candidate audit summary redacts token details and errors"),
    "F-127": ("closed_by_existing_hardening", "Makefile validation entrypoints simplify README flow"),
    "F-133": ("deferred_non_blocking_with_reason", "manual operator recovery remains required before production promotion"),
    "F-134": ("deferred_non_blocking_with_reason", "general live cancel remains blocked outside reviewed canary flow"),
    "F-135": ("deferred_non_blocking_with_reason", "release archive policy needs final RC packaging review"),
    "F-136": ("deferred_non_blocking_with_reason", "production-live-candidate naming retained but bounded by false readiness claims"),
    "F-137": ("deferred_non_blocking_with_reason", "historical context cleanup is documentation hygiene, not non-live blocker"),
    "F-138": ("closed_by_existing_hardening", "README and Makefile now reduce validation-source duplication"),
    "F-144": ("deferred_non_blocking_with_reason", "candidate naming change deferred to future versioned posture rename"),
    "F-145": ("closed_by_existing_hardening", "shared release_validation_utils helpers introduced and adopted"),
    "F-146": ("closed_by_existing_hardening", "shared helper failure paths reduce direct ad hoc exits"),
    "F-147": ("deferred_non_blocking_with_reason", "unified logging framework is quality cleanup, not release blocker"),
    "F-149": ("closed_by_existing_hardening", "optional make check-shell entrypoint added"),
    "F-150": ("deferred_non_blocking_with_reason", "central clock abstraction deferred; current evidence records concrete UTC times"),
    "F-151": ("deferred_non_blocking_with_reason", "approval-id redesign deferred; current reviewed canary approvals are consumed"),
    "F-152": ("deferred_non_blocking_with_reason", "canonical JSON schema program deferred beyond non-live closure"),
    "F-153": ("deferred_non_blocking_with_reason", "Decimal formatting hardening deferred unless a gate exposes ambiguity"),
    "F-154": ("deferred_non_blocking_with_reason", "central path traversal utility deferred; package guards remain active"),
    "F-155": ("deferred_non_blocking_with_reason", "write-permission separation deferred; scripts remain local operator tools"),
    "F-156": ("deferred_non_blocking_with_reason", "urllib replacement deferred; public-read scripts keep redaction guards"),
    "F-157": ("deferred_non_blocking_with_reason", "mock-style test reduction deferred to broader test refactor"),
    "F-158": ("deferred_non_blocking_with_reason", "historical test renames deferred to avoid noisy churn"),
    "F-159": ("deferred_non_blocking_with_reason", "script risk docstring taxonomy deferred"),
    "F-160": ("deferred_non_blocking_with_reason", "error-message copy cleanup deferred"),
    "F-161": ("closed_by_existing_hardening", "root Makefile entrypoints added"),
    "F-162": ("closed_by_existing_hardening", "README now documents quick validation entrypoints"),
    "F-163": ("closed_by_existing_hardening", "advisory supply-chain preflight with schema/output added"),
    "F-164": ("closed_by_existing_hardening", "advisory license-tool preflight with skipped semantics added"),
}

POLICY_GATE_IDS = {"B-001", "B-010", "F-001"}


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reconciled_debt_item(item: dict[str, Any]) -> dict[str, Any]:
    debt_id = item.get("id")
    if not isinstance(debt_id, str) or debt_id not in ACCEPTED_DEBT_DISPOSITION:
        raise ValueError(f"unknown accepted debt id: {debt_id!r}")
    status, evidence = ACCEPTED_DEBT_DISPOSITION[debt_id]
    output = deepcopy(item)
    output["current_tracker_status"] = status
    output["current_close_condition"] = (
        "closed for non-live posture by local hardening evidence"
        if status == "closed_by_existing_hardening"
        else "deferred as non-blocking future cleanup; not a production/live approval"
    )
    output["current_evidence"] = evidence
    output["production_ready"] = False
    output["live_trading_ready"] = False
    return output


def promotion_gate_item(item: dict[str, Any]) -> dict[str, Any]:
    output = deepcopy(item)
    output["current_tracker_status"] = "blocked_policy_promotion_gate"
    output["current_close_condition"] = (
        "requires a separate formally reviewed production/live release decision; "
        "must remain blocked for the current non-live posture"
    )
    output["production_ready"] = False
    output["live_trading_ready"] = False
    return output


def existing_closed_debt(source: dict[str, Any]) -> list[dict[str, Any]]:
    closed_debt = source.get("closed_non_live_debt", [])
    if not isinstance(closed_debt, list):
        raise ValueError("closed_non_live_debt must be a list")
    return [deepcopy(item) for item in closed_debt if isinstance(item, dict)]


def merge_by_id(existing: list[Any], additions: list[dict[str, Any]]) -> list[Any]:
    merged = list(existing)
    seen = {item.get("id") for item in merged if isinstance(item, dict)}
    for item in additions:
        item_id = item.get("id")
        if item_id not in seen:
            merged.append(deepcopy(item))
            seen.add(item_id)
    return merged


def reconcile(input_path: Path) -> dict[str, Any]:
    source = load_json_object(input_path)
    output = deepcopy(source)

    accepted = source.get("accepted_non_live_non_blocking", [])
    if not isinstance(accepted, list):
        raise ValueError("accepted_non_live_non_blocking must be a list")
    closed_debt = (
        [reconciled_debt_item(item) for item in accepted]
        if accepted
        else existing_closed_debt(source)
    )

    remaining = source.get("remaining", [])
    if not isinstance(remaining, list):
        raise ValueError("remaining must be a list")
    policy_gates = [
        promotion_gate_item(item)
        for item in remaining
        if isinstance(item, dict) and item.get("id") in POLICY_GATE_IDS
    ]
    policy_gate_by_id = {item["id"]: item for item in policy_gates}
    reconciled_remaining: list[dict[str, Any]] = []
    for item in remaining:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        reconciled_remaining.append(policy_gate_by_id.get(item_id, deepcopy(item)))

    locally_closed = list(source.get("locally_closed", []))
    if not isinstance(locally_closed, list):
        raise ValueError("locally_closed must be a list")
    locally_closed = merge_by_id(locally_closed, closed_debt)

    output["accepted_non_live_non_blocking"] = []
    output["accepted_non_live_non_blocking_count"] = 0
    output["closed_non_live_debt"] = closed_debt
    output["closed_non_live_debt_count"] = len(closed_debt)
    output["policy_promotion_gates"] = policy_gates
    output["policy_promotion_gate_count"] = len(policy_gates)
    output["locally_closed"] = locally_closed
    output["locally_closed_count"] = len(locally_closed)
    output["remaining"] = reconciled_remaining
    output["remaining_count"] = len(reconciled_remaining)
    output["generated_at"] = utc_now()
    output["generation_method"] = "scripts/reconcile_remaining_issues.py"
    output["status_summary"] = (
        "Accepted non-live debt has been reconciled into explicit closed/deferred records; "
        "production/live remains blocked by policy promotion gates and external signature gates."
    )

    counts = dict(output.get("counts", {})) if isinstance(output.get("counts"), dict) else {}
    counts["accepted_non_live_non_blocking"] = 0
    counts["closed_non_live_debt"] = len(closed_debt)
    counts["policy_promotion_gates"] = len(policy_gates)
    counts["locally_closed"] = len(locally_closed)
    counts["remaining"] = len(reconciled_remaining)
    output["counts"] = counts

    summary = dict(output.get("summary", {})) if isinstance(output.get("summary"), dict) else {}
    summary.update(
        {
            "accepted_non_live_non_blocking_count": 0,
            "closed_non_live_debt_count": len(closed_debt),
            "policy_promotion_gate_count": len(policy_gates),
            "validated_release": False,
            "production_ready": False,
            "live_trading_ready": False,
            "release_posture": "production-live-candidate_non_live_by_default",
            "reconciliation_policy": (
                "accepted debt is no longer an unresolved bucket; policy gates remain blocked "
                "until a future reviewed production/live promotion"
            ),
        }
    )
    output["summary"] = summary
    return output


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_markdown_matrix(path: Path, data: dict[str, Any]) -> None:
    rows = []
    for item in data.get("closed_non_live_debt", []):
        rows.append(
            "| `{id}` | `{status}` | {issue} | {evidence} |".format(
                id=item.get("id", ""),
                status=item.get("current_tracker_status", ""),
                issue=str(item.get("issue", "")).replace("|", "\\|"),
                evidence=str(item.get("current_evidence", "")).replace("|", "\\|"),
            )
        )
    for item in data.get("policy_promotion_gates", []):
        rows.append(
            "| `{id}` | `{status}` | {issue} | {condition} |".format(
                id=item.get("id", ""),
                status=item.get("current_tracker_status", ""),
                issue=str(item.get("issue", "")).replace("|", "\\|"),
                condition=str(item.get("current_close_condition", "")).replace("|", "\\|"),
            )
        )
    body = "\n".join(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Accepted Debt Closure Matrix\n\n"
        f"Generated: {data.get('generated_at')}\n\n"
        "This matrix preserves the non-live boundary. It is not a production or live authorization.\n\n"
        "| ID | Status | Issue | Evidence / Close Condition |\n"
        "| --- | --- | --- | --- |\n"
        f"{body}\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--matrix-md", type=Path)
    args = parser.parse_args(argv)

    report = reconcile(args.input)
    if args.output is not None:
        write_json(args.output, report)
    if args.matrix_md is not None:
        write_markdown_matrix(args.matrix_md, report)
    if args.output is None and args.matrix_md is None:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
