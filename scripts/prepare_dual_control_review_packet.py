#!/usr/bin/env python3
"""Bundle current controlled-canary review materials into one packet directory."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_validation_utils import load_json_object, sha256_file

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


def load_json(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def sha256(path: Path) -> str:
    return sha256_file(path)


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SystemExit(f"{label} must be a 64-character SHA-256 hex digest")
    return value.lower()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"{label} missing: {path}")
    return path


def validate_release_sidecar(path: Path) -> dict[str, Any]:
    data = load_json(path)
    artifact = data.get("artifact", {})
    canonical = data.get("canonical_evidence", {})
    return {
        "artifact_sha256": require_sha256(artifact.get("sha256"), "release sidecar artifact.sha256"),
        "workspace_manifest_sha256": require_sha256(
            canonical.get("workspace_manifest_sha256"),
            "release sidecar workspace_manifest_sha256",
        ),
        "archived_manifest_sha256": require_sha256(
            canonical.get("archived_manifest_sha256"),
            "release sidecar archived_manifest_sha256",
        ),
    }


def validate_candidate(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("side") != "BUY":
        raise SystemExit("candidate side must be BUY")
    if data.get("order_type") != "GTC":
        raise SystemExit("candidate order_type must be GTC")
    if data.get("post_only") is not True:
        raise SystemExit("candidate post_only must be true")
    return data


def validate_runtime_truth(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data.get("account_id"), str) or not data["account_id"].strip():
        raise SystemExit("runtime truth account_id must be a non-empty string")
    if not isinstance(data.get("condition_id"), str) or not data["condition_id"].strip():
        raise SystemExit("runtime truth condition_id must be a non-empty string")
    report = data.get("preflight_report")
    if not isinstance(report, dict):
        raise SystemExit("runtime truth preflight_report must be an object")
    if report.get("posted") is not False:
        raise SystemExit("runtime truth must keep preflight_report.posted=false")
    if report.get("remote_side_effects") is not False:
        raise SystemExit("runtime truth must keep preflight_report.remote_side_effects=false")
    if report.get("status") != "preflight_ready":
        raise SystemExit("runtime truth must keep preflight_report.status=preflight_ready")
    for field in PREFLIGHT_GATE_FIELDS:
        if report.get(field) is not True:
            raise SystemExit(f"runtime truth must keep preflight_report.{field}=true")
    gate_evidence_refs = report.get("gate_evidence_refs")
    if not isinstance(gate_evidence_refs, dict):
        raise SystemExit("runtime truth must keep preflight_report.gate_evidence_refs as an object")
    for field in PREFLIGHT_GATE_EVIDENCE_FIELDS:
        evidence_ref = gate_evidence_refs.get(field)
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SystemExit(f"runtime truth must keep preflight_report.gate_evidence_refs.{field} as a non-empty string")
    if data.get("remote_side_effects") is not False:
        raise SystemExit("runtime truth must keep remote_side_effects=false")
    return data


def validate_approval_request(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("status") != "operator_approval_request_not_authorization":
        raise SystemExit("approval request status must be operator_approval_request_not_authorization")
    if not isinstance(data.get("active_profile_ref"), str) or not data["active_profile_ref"].strip():
        raise SystemExit("approval request active_profile_ref is required")
    if not isinstance(data.get("condition_id"), str) or not data["condition_id"].strip():
        raise SystemExit("approval request condition_id is required")
    gate_snapshot = data.get("runtime_gate_snapshot")
    if not isinstance(gate_snapshot, dict):
        raise SystemExit("approval request runtime_gate_snapshot must be an object")
    for field in PREFLIGHT_GATE_FIELDS:
        if gate_snapshot.get(field) is not True:
            raise SystemExit(f"approval request runtime_gate_snapshot.{field} must be true")
    gate_evidence_refs = data.get("runtime_gate_evidence_refs")
    if not isinstance(gate_evidence_refs, dict):
        raise SystemExit("approval request runtime_gate_evidence_refs must be an object")
    for field in PREFLIGHT_GATE_EVIDENCE_FIELDS:
        evidence_ref = gate_evidence_refs.get(field)
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise SystemExit(f"approval request runtime_gate_evidence_refs.{field} must be a non-empty string")
    if data.get("live_submit_authorized") is not False:
        raise SystemExit("approval request must not authorize live submit")
    if data.get("remote_side_effects_authorized") is not False:
        raise SystemExit("approval request must not authorize remote side effects")
    return data


def validate_dual_control_template(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if data.get("status") != "draft_requires_independent_reviewer":
        raise SystemExit("dual-control template status must be draft_requires_independent_reviewer")
    if data.get("review_ref") != "REPLACE_WITH_DUAL_CONTROL_REVIEW_REF":
        raise SystemExit("dual-control template must keep review_ref placeholder")
    if data.get("reviewer_identity_ref") != "REPLACE_WITH_INDEPENDENT_REVIEWER_IDENTITY_REF":
        raise SystemExit("dual-control template must keep reviewer_identity_ref placeholder")
    if data.get("reviewer_identity_sha256") != "REPLACE_WITH_REVIEWER_IDENTITY_SHA256":
        raise SystemExit("dual-control template must keep reviewer_identity_sha256 placeholder")
    checks = data.get("required_reviewer_checks")
    if not isinstance(checks, dict) or any(value is not False for value in checks.values()):
        raise SystemExit("dual-control template must keep all required_reviewer_checks false")
    return data


def require_packet_member_name(name: str) -> str:
    candidate = Path(name)
    if (
        not name
        or "\\" in name
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.name != name
        or name in {".", ".."}
    ):
        raise SystemExit("packet target_name must be a plain filename")
    return name


def copy_into_packet(src: Path, output_dir: Path, *, target_name: str | None = None) -> dict[str, Any]:
    member_name = require_packet_member_name(src.name if target_name is None else target_name)
    dest = output_dir / member_name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return {"path": dest.name, "sha256": sha256(dest)}


def build_packet(
    *,
    output_dir: Path,
    release_zip: Path,
    release_sha: Path,
    release_evidence: Path,
    candidate: Path,
    runtime_truth: Path,
    approval_request: Path,
    dual_control_template: Path,
) -> dict[str, Any]:
    release_sidecar = validate_release_sidecar(release_evidence)
    validate_candidate(candidate)
    runtime_doc = validate_runtime_truth(runtime_truth)
    approval_doc = validate_approval_request(approval_request)
    dual_control_doc = validate_dual_control_template(dual_control_template)

    expected_pairs = [
        ("artifact_sha256", release_sidecar["artifact_sha256"], approval_doc.get("artifact_sha256")),
        ("artifact_sha256", release_sidecar["artifact_sha256"], runtime_doc.get("artifact_sha256")),
        ("workspace_manifest_sha256", release_sidecar["workspace_manifest_sha256"], approval_doc.get("workspace_manifest_sha256")),
        ("workspace_manifest_sha256", release_sidecar["workspace_manifest_sha256"], runtime_doc.get("workspace_manifest_sha256")),
        ("archived_manifest_sha256", release_sidecar["archived_manifest_sha256"], approval_doc.get("archived_manifest_sha256")),
        ("archived_manifest_sha256", release_sidecar["archived_manifest_sha256"], runtime_doc.get("archived_manifest_sha256")),
        ("market_candidate_sha256", sha256(candidate), approval_doc.get("market_candidate_sha256")),
        ("runtime_truth_sha256", sha256(runtime_truth), approval_doc.get("runtime_truth_sha256")),
        ("condition_id", runtime_doc.get("condition_id"), approval_doc.get("condition_id")),
        ("approval_hash", approval_doc.get("approval_hash"), dual_control_doc.get("approval_hash")),
        ("approval_request_sha256", sha256(approval_request), dual_control_doc.get("approval_request_sha256")),
    ]
    mismatches = [
        f"{field} expected {expected}, got {actual!r}"
        for field, expected, actual in expected_pairs
        if expected != actual
    ]
    if mismatches:
        raise SystemExit("review packet binding mismatch: " + "; ".join(mismatches))
    runtime_gate_evidence_refs = runtime_doc["preflight_report"].get("gate_evidence_refs")
    approval_gate_evidence_refs = approval_doc.get("runtime_gate_evidence_refs")
    if not isinstance(runtime_gate_evidence_refs, dict) or not isinstance(approval_gate_evidence_refs, dict):
        raise SystemExit("review packet requires runtime gate evidence refs in runtime truth and approval request")
    evidence_mismatches = [
        field
        for field in PREFLIGHT_GATE_EVIDENCE_FIELDS
        if runtime_gate_evidence_refs.get(field) != approval_gate_evidence_refs.get(field)
    ]
    if evidence_mismatches:
        raise SystemExit(
            "review packet runtime gate evidence mismatch: " + ", ".join(sorted(evidence_mismatches))
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    copied = {
        "release_zip": copy_into_packet(release_zip, output_dir),
        "release_sha256": copy_into_packet(release_sha, output_dir),
        "release_evidence": copy_into_packet(release_evidence, output_dir),
        "candidate_market": copy_into_packet(candidate, output_dir),
        "runtime_truth": copy_into_packet(runtime_truth, output_dir),
        "approval_request": copy_into_packet(approval_request, output_dir, target_name="approval-request.json"),
        "dual_control_review_template": copy_into_packet(
            dual_control_template,
            output_dir,
            target_name="dual-control-review.template.json",
        ),
    }
    packet = {
        "schema_version": 1,
        "status": "dual_control_review_packet_not_authorization",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_sha256": release_sidecar["artifact_sha256"],
        "workspace_manifest_sha256": release_sidecar["workspace_manifest_sha256"],
        "archived_manifest_sha256": release_sidecar["archived_manifest_sha256"],
        "candidate_market_sha256": sha256(candidate),
        "runtime_truth_sha256": sha256(runtime_truth),
        "approval_hash": approval_doc["approval_hash"],
        "active_profile_ref": approval_doc["active_profile_ref"],
        "approval_request_sha256": sha256(approval_request),
        "review_scope": "REAL_FUNDS_CANARY",
        "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
        "remote_side_effects_authorized": False,
        "live_submit_authorized": False,
        "files": copied,
        "reviewer_instruction": dual_control_doc["reviewer_instruction"],
    }
    return packet


def packet_readme(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Controlled Canary Dual-Control Review Packet",
            "",
            "This directory is a non-authorizing review packet.",
            "It does not grant permission to submit or cancel live orders.",
            "",
            f"- Packet status: `{packet['status']}`",
            f"- Artifact SHA-256: `{packet['artifact_sha256']}`",
            f"- Candidate SHA-256: `{packet['candidate_market_sha256']}`",
            f"- Runtime-truth SHA-256: `{packet['runtime_truth_sha256']}`",
            f"- Approval hash: `{packet['approval_hash']}`",
            f"- Active profile ref: `{packet['active_profile_ref']}`",
            "",
            "Required reviewer output:",
            "",
            "- Update `dual-control-review.template.json` into an approved dual-control review file.",
            "- Keep all bound SHA-256 fields unchanged.",
            "- Replace placeholders and set all `required_reviewer_checks` entries to `true` only after review.",
            "",
            "Safety boundary:",
            "",
            "- `approval-request.json` is not an authorization.",
            "- `dual-control-review.template.json` is not an authorization.",
            "- A later `reviewed_go` decision is still required before any armed live step.",
            "",
        ]
    ) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--release-zip", required=True, type=Path)
    parser.add_argument("--candidate-market-file", required=True, type=Path)
    parser.add_argument("--runtime-truth-file", required=True, type=Path)
    parser.add_argument("--approval-request-file", required=True, type=Path)
    parser.add_argument("--dual-control-review-template-file", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = resolve(args.output_dir)
    release_zip = require_file(resolve(args.release_zip), "release zip")
    release_sha = require_file(release_zip.with_suffix(release_zip.suffix + ".sha256"), "release sha sidecar")
    release_evidence = require_file(
        release_zip.with_suffix(release_zip.suffix + ".evidence.json"),
        "release evidence sidecar",
    )
    candidate = require_file(resolve(args.candidate_market_file), "candidate market")
    runtime_truth = require_file(resolve(args.runtime_truth_file), "runtime truth")
    approval_request = require_file(resolve(args.approval_request_file), "approval request")
    dual_control_template = require_file(
        resolve(args.dual_control_review_template_file),
        "dual-control review template",
    )

    packet = build_packet(
        output_dir=output_dir,
        release_zip=release_zip,
        release_sha=release_sha,
        release_evidence=release_evidence,
        candidate=candidate,
        runtime_truth=runtime_truth,
        approval_request=approval_request,
        dual_control_template=dual_control_template,
    )
    (output_dir / "packet.json").write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    (output_dir / "README.md").write_text(packet_readme(packet))
    print(json.dumps({"status": "pass", "output_dir": str(output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
