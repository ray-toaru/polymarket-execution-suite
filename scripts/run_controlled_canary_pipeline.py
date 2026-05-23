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
        stages.append({"stage": "candidate_supplied", "status": "pass", "path": str(path)})
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
        "stages": stages,
        "failures": failures,
    }
    (output_dir / "pipeline-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
