#!/usr/bin/env python3
"""Audit v0.28 production-live-candidate readiness.

Default mode is audit-only and exits 0 with a JSON report. Use
`--require-ready` only when the release artifact, evidence, and decision have
all been refreshed together for the exact v0.28 source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.28.0"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STRUCTURED_RELEASE_DECISION_RE = re.compile(
    r"```json\s+release-decision\s*\n(?P<body>.*?)\n```",
    re.DOTALL,
)

REQUIRED_CANDIDATE_TERMS = [
    "production-live-candidate",
    "validated_release=false",
    "production_ready=false",
    "live_trading_ready=false",
    "live_submit_allowed=false",
    "live_cancel_allowed=false",
    "real_funds_canary_authorized=false",
    "fresh reviewed release decision",
    "operator approval",
    "runtime state healthy",
    "kill switch open",
    "no geoblock",
    "idempotency reservation",
    "rollback",
    "incident",
    "alert",
    "custody",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def component_matrix_versions(text: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        name = cells[0]
        version = cells[2]
        if name == "Integration suite":
            versions["suite"] = version
        elif name == "Execution engine":
            versions["engine"] = version
        elif name == "Hermes adapter":
            versions["adapter"] = version
    return versions


def require_contains(blockers: list[str], label: str, text: str, token: str) -> None:
    if token not in text:
        blockers.append(f"{label} must mention {token}")


def require_false(blockers: list[str], data: dict[str, Any], key: str, label: str) -> None:
    if data.get(key) is not False:
        blockers.append(f"{label}.{key} must remain false for v0.28 production-live-candidate")


def release_decision_structured_block(text: str) -> dict[str, Any] | None:
    match = STRUCTURED_RELEASE_DECISION_RE.search(text)
    if match is None:
        return None
    try:
        data = json.loads(match.group("body"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_release_decision_structured_block(
    blockers: list[str],
    text: str,
    target_version: str,
) -> None:
    data = release_decision_structured_block(text)
    if data is None:
        blockers.append("RELEASE_DECISION.md must include a structured release decision block")
        return
    if not data:
        blockers.append("structured release decision block must be valid JSON object")
        return
    if data.get("schema_version") != 1:
        blockers.append("structured release decision schema_version must be 1")
    if data.get("version") != target_version:
        blockers.append("structured release decision version must match target version")
    if data.get("release_posture") != "production-live-candidate":
        blockers.append("structured release decision release_posture must be production-live-candidate")
    for key in [
        "validated_release",
        "production_ready",
        "live_trading_ready",
        "live_submit_allowed",
        "live_cancel_allowed",
        "real_funds_canary_authorized",
    ]:
        if data.get(key) is not False:
            blockers.append(f"structured release decision {key} must remain false")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(root: Path = ROOT, target_version: str = TARGET_VERSION) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = [
        "External CI, reviewer identity, and operator approval references require independent verification."
    ]
    external_requirements = [
        "GitHub CI run bound to the reviewed commit and artifact digest",
        "Independent approved dual-control review with reviewer identity provenance",
        "External references package bound to the reviewed-go decision",
        "Real-funds canary execution evidence from external systems",
    ]

    suite_version = read_text(root / "VERSION").strip()
    if suite_version != target_version:
        blockers.append(f"VERSION must be {target_version}; current={suite_version or '<missing>'}")

    matrix = component_matrix_versions(read_text(root / "COMPONENT_COMPATIBILITY.md"))
    for component in ["suite", "engine", "adapter"]:
        if matrix.get(component) != target_version:
            blockers.append(f"component matrix {component} version must be {target_version}")

    release_manifest = load_json(root / "polymarket-execution-engine/release/manifest.json")
    if release_manifest.get("version") != target_version:
        blockers.append("execution-engine release manifest version must match v0.28 target")
    manifest_status = str(release_manifest.get("status", ""))
    if "production-live-candidate" not in manifest_status:
        blockers.append("execution-engine release manifest status must say production-live-candidate")
    if "not-production" not in manifest_status or "not-live" not in manifest_status:
        blockers.append("execution-engine release manifest status must preserve not-production/not-live boundary")

    evidence_manifest = load_json(root / "polymarket-execution-engine/evidence/current/manifest.json")
    if evidence_manifest.get("version") != target_version:
        blockers.append("current evidence manifest version must match v0.28 target")
    decision = evidence_manifest.get("release_decision", {})
    if not isinstance(decision, dict):
        blockers.append("current evidence manifest release_decision must be an object")
        decision = {}
    for key in ["validated_release", "production_ready", "live_trading_ready"]:
        require_false(blockers, decision, key, "current evidence release_decision")

    release_decision_text = read_text(root / "RELEASE_DECISION.md")
    validation_report_text = read_text(root / "VALIDATION_REPORT.md")
    for token in REQUIRED_CANDIDATE_TERMS:
        require_contains(blockers, "RELEASE_DECISION.md", release_decision_text, token)
    validate_release_decision_structured_block(blockers, release_decision_text, target_version)
    require_contains(blockers, "VALIDATION_REPORT.md", validation_report_text, f"v{target_version}")
    require_contains(blockers, "VALIDATION_REPORT.md", validation_report_text, "Full current gates")
    require_contains(blockers, "VALIDATION_REPORT.md", validation_report_text, "production-live-candidate")

    artifact = root / "dist" / f"polymarket-execution-suite-v{target_version}.zip"
    sha_sidecar = artifact.with_suffix(artifact.suffix + ".sha256")
    evidence_sidecar = artifact.with_suffix(artifact.suffix + ".evidence.json")
    if not artifact.exists():
        blockers.append("release artifact zip missing")
    if not sha_sidecar.exists():
        blockers.append("release artifact sha256 sidecar missing")
    if not evidence_sidecar.exists():
        blockers.append("release artifact evidence sidecar missing")
    actual_artifact_sha = sha256(artifact) if artifact.is_file() else None
    if sha_sidecar.is_file() and actual_artifact_sha is not None:
        sha_parts = sha_sidecar.read_text().strip().split()
        if (
            len(sha_parts) < 2
            or sha_parts[0] != actual_artifact_sha
            or sha_parts[1] != artifact.name
        ):
            blockers.append("sha256 sidecar must match the actual artifact SHA-256 and filename")
    sidecar = load_json(evidence_sidecar)
    if sidecar and sidecar.get("source", {}).get("version") != target_version:
        blockers.append("release artifact evidence sidecar source.version must match v0.28 target")
    sidecar_artifact_sha = sidecar.get("artifact", {}).get("sha256") if sidecar else None
    if sidecar and (not isinstance(sidecar_artifact_sha, str) or not HEX64.match(sidecar_artifact_sha)):
        blockers.append("release artifact evidence sidecar must bind artifact.sha256")
    elif actual_artifact_sha is not None and sidecar_artifact_sha != actual_artifact_sha:
        blockers.append("release artifact evidence sidecar must match the actual artifact SHA-256")
    canonical = sidecar.get("canonical_evidence", {}) if sidecar else {}
    workspace_snapshot_path = canonical.get("workspace_manifest_snapshot_path") if isinstance(canonical, dict) else None
    if sidecar and (not isinstance(workspace_snapshot_path, str) or not workspace_snapshot_path):
        blockers.append("release artifact evidence sidecar must bind canonical_evidence.workspace_manifest_snapshot_path")
    elif isinstance(workspace_snapshot_path, str) and not (root / "dist" / workspace_snapshot_path).exists():
        blockers.append("workspace manifest snapshot referenced by release artifact evidence sidecar is missing")

    dist_index = load_json(root / "dist/INDEX.json")
    indexed_artifact = dist_index.get("current_release_artifact", {}) if dist_index else {}
    if dist_index and dist_index.get("version") != target_version:
        blockers.append("dist INDEX.json version must match v0.28 target")
    if isinstance(indexed_artifact, dict):
        if indexed_artifact.get("artifact_class") != "production_live_candidate_non_live_by_default":
            blockers.append("dist INDEX.json artifact_class must be production_live_candidate_non_live_by_default")
        for key in ["validated_release", "production_ready", "live_trading_ready"]:
            require_false(blockers, indexed_artifact, key, "dist INDEX current_release_artifact")
        if actual_artifact_sha is not None and indexed_artifact.get("sha256") != actual_artifact_sha:
            blockers.append("dist INDEX current_release_artifact.sha256 must match the actual artifact SHA-256")
    elif dist_index:
        blockers.append("dist INDEX.json current_release_artifact must be an object")

    return {
        "status": "ready" if not blockers else "not_ready",
        "target_version": target_version,
        "suite_version": suite_version,
        "component_versions": matrix,
        "external_evidence": {
            "status": "not_locally_verifiable",
            "required": external_requirements,
        },
        "blockers": blockers,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-version", default=TARGET_VERSION)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    report = evaluate(ROOT, args.target_version)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_ready and report["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
