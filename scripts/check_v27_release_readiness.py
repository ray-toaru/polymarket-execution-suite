#!/usr/bin/env python3
"""Report whether the workspace is ready to promote a v0.27 release.

Default mode is audit-only and exits 0 with a JSON report. Use
`--require-ready` for the final release gate.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.27.3"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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


def evaluate(root: Path = ROOT, target_version: str = TARGET_VERSION) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    suite_version = read_text(root / "VERSION").strip()
    if suite_version != target_version:
        blockers.append(f"VERSION must be {target_version} before v0.27 release; current={suite_version or '<missing>'}")

    matrix = component_matrix_versions(read_text(root / "COMPONENT_COMPATIBILITY.md"))
    if matrix.get("suite") != suite_version:
        blockers.append("component matrix suite version must match VERSION")
    if matrix.get("suite") != target_version:
        blockers.append(f"component matrix suite version must be {target_version}")
    if matrix.get("engine") != target_version:
        blockers.append(f"component matrix execution engine version must be {target_version}")
    if not matrix.get("adapter"):
        blockers.append("component matrix Hermes adapter version missing")

    release_manifest = load_json(root / "polymarket-execution-engine/release/manifest.json")
    if release_manifest.get("version") != target_version:
        blockers.append("execution-engine release manifest version must match v0.27 target")

    evidence_manifest = load_json(root / "polymarket-execution-engine/evidence/current/manifest.json")
    if evidence_manifest.get("version") != target_version:
        blockers.append("current evidence manifest version must match v0.27 target")
    external_artifact = evidence_manifest.get("external_artifact_sidecar", {})
    external_artifact_sha = external_artifact.get("sha256") if isinstance(external_artifact, dict) else None
    if not isinstance(external_artifact_sha, str) or not HEX64.match(external_artifact_sha):
        blockers.append("current evidence manifest must bind final external_artifact_sidecar.sha256")
    decision = evidence_manifest.get("release_decision", {})
    for key in ["validated_release", "production_ready", "live_trading_ready"]:
        if decision.get(key) is not False:
            blockers.append(f"current evidence release_decision.{key} must remain false for source-candidate v0.27")

    release_decision_text = read_text(root / "RELEASE_DECISION.md")
    validation_report_text = read_text(root / "VALIDATION_REPORT.md")
    require_contains(blockers, "RELEASE_DECISION.md", release_decision_text, f"v{target_version}")
    require_contains(blockers, "RELEASE_DECISION.md", release_decision_text, "validated_release=false")
    require_contains(blockers, "RELEASE_DECISION.md", release_decision_text, "production_ready=false")
    require_contains(blockers, "RELEASE_DECISION.md", release_decision_text, "live_trading_ready=false")
    require_contains(blockers, "VALIDATION_REPORT.md", validation_report_text, f"v{target_version}")
    require_contains(blockers, "VALIDATION_REPORT.md", validation_report_text, "Full current gates")

    artifact = root / "dist" / f"polymarket-execution-suite-v{target_version}.zip"
    sha_sidecar = artifact.with_suffix(artifact.suffix + ".sha256")
    evidence_sidecar = artifact.with_suffix(artifact.suffix + ".evidence.json")
    if not artifact.exists():
        blockers.append("release artifact zip missing")
    if not sha_sidecar.exists():
        blockers.append("release artifact sha256 sidecar missing")
    if not evidence_sidecar.exists():
        blockers.append("release artifact evidence sidecar missing")
    sidecar = load_json(evidence_sidecar)
    if sidecar and sidecar.get("source", {}).get("version") != target_version:
        blockers.append("release artifact evidence sidecar source.version must match v0.27 target")
    sidecar_artifact_sha = sidecar.get("artifact", {}).get("sha256") if sidecar else None
    if sidecar and (not isinstance(sidecar_artifact_sha, str) or not HEX64.match(sidecar_artifact_sha)):
        blockers.append("release artifact evidence sidecar must bind artifact.sha256")

    if suite_version == "0.26.1":
        warnings.append("workspace remains on v0.26.1 development baseline; do not tag v0.27 yet")

    return {
        "status": "ready" if not blockers else "not_ready",
        "target_version": target_version,
        "suite_version": suite_version,
        "component_versions": matrix,
        "blockers": blockers,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    report = evaluate(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_ready and report["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
