#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate(dist: Path, expected_version: str) -> list[str]:
    failures: list[str] = []
    index_path = dist / "INDEX.json"
    if not index_path.exists():
        return [f"dist index missing: {index_path}"]
    index = load_json(index_path)
    if index.get("schema_version") != 1:
        failures.append("INDEX.json schema_version must be 1")
    if index.get("version") != expected_version:
        failures.append("INDEX.json version does not match expected version")

    artifact = index.get("current_release_artifact")
    if not isinstance(artifact, dict):
        failures.append("INDEX.json current_release_artifact must be an object")
        artifact = {}
    artifact_path = dist / str(artifact.get("path", ""))
    if artifact_path.name != f"polymarket-execution-suite-v{expected_version}.zip":
        failures.append("current_release_artifact.path must name the expected versioned zip")
    if not artifact_path.exists():
        failures.append(f"current release artifact missing: {artifact_path}")
        artifact_sha = None
    else:
        artifact_sha = sha256(artifact_path)
        if artifact.get("sha256") != artifact_sha:
            failures.append("INDEX.json current_release_artifact.sha256 does not match artifact")

    current_zip_entries = sorted(dist.glob(f"polymarket-execution-suite-v{expected_version}.zip"))
    if len(current_zip_entries) != 1:
        failures.append("dist must contain exactly one current versioned release artifact")

    artifact_class = artifact.get("artifact_class")
    allowed_classes = {
        "controlled_real_funds_canary_source_candidate_non_live",
        "production_live_candidate_non_live_by_default",
    }
    if artifact_class not in allowed_classes:
        failures.append("INDEX.json current_release_artifact.artifact_class is not recognized")
    if artifact.get("validated_release") is not False:
        failures.append("INDEX.json must keep validated_release=false for this non-live candidate")
    if artifact.get("production_ready") is not False:
        failures.append("INDEX.json must keep production_ready=false")
    if artifact.get("live_trading_ready") is not False:
        failures.append("INDEX.json must keep live_trading_ready=false")

    sidecar_name = artifact.get("sha256_sidecar")
    if not isinstance(sidecar_name, str):
        failures.append("current_release_artifact.sha256_sidecar is required")
    else:
        sidecar_path = dist / sidecar_name
        if not sidecar_path.exists():
            failures.append(f"sha256 sidecar missing: {sidecar_path}")
        elif artifact_sha is not None:
            parts = sidecar_path.read_text().strip().split()
            if len(parts) < 2 or parts[0] != artifact_sha or parts[1] != artifact_path.name:
                failures.append("sha256 sidecar does not match current release artifact")

    evidence_name = artifact.get("evidence_sidecar")
    if not isinstance(evidence_name, str):
        failures.append("current_release_artifact.evidence_sidecar is required")
    else:
        evidence_path = dist / evidence_name
        if not evidence_path.exists():
            failures.append(f"evidence sidecar missing: {evidence_path}")
        elif artifact_sha is not None:
            evidence = load_json(evidence_path)
            evidence_artifact = evidence.get("artifact", {})
            if evidence_artifact.get("name") != artifact_path.name:
                failures.append("evidence sidecar artifact.name does not match INDEX artifact")
            if evidence_artifact.get("sha256") != artifact_sha:
                failures.append("evidence sidecar artifact.sha256 does not match artifact")

    local_material = index.get("local_material")
    if not isinstance(local_material, list):
        failures.append("INDEX.json local_material must be a list")
        local_material = []
    for item in local_material:
        if not isinstance(item, dict):
            failures.append("INDEX.json local_material entries must be objects")
            continue
        path = str(item.get("path", ""))
        status = item.get("status")
        approval_reuse_allowed = item.get("approval_reuse_allowed")
        remote_side_effects_authorized = item.get("remote_side_effects_authorized")
        if path.startswith("pmx-canary-reviewed-go-") and status in {"consumed_closed", "consumed_not_closed"}:
            if approval_reuse_allowed is not False:
                failures.append(f"{path}: consumed reviewed-go material must not be approval-reusable")
            if remote_side_effects_authorized is not False:
                failures.append(f"{path}: consumed reviewed-go material must not authorize remote side effects")
        if status == "current_no_go_review_material":
            if approval_reuse_allowed is not False:
                failures.append(f"{path}: no-go material must not be approval-reusable")
            if remote_side_effects_authorized is not False:
                failures.append(f"{path}: no-go material must not authorize remote side effects")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dist/INDEX.json release-material boundaries.")
    parser.add_argument("dist", type=Path)
    parser.add_argument("expected_version")
    args = parser.parse_args()
    failures = validate(args.dist, args.expected_version)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"dist index passed version={args.expected_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
