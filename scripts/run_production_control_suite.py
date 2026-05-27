#!/usr/bin/env python3
"""Plan or run the local production-control evidence drills as one suite."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_VALIDATION = ROOT / "polymarket-execution-engine" / "validation"

CONTROL_DRILLS = [
    ("operations", "run_production_operations_drill.py"),
    ("authorization_block", "run_production_authorization_block_drill.py"),
    ("deployment_preflight", "run_production_deployment_preflight_drill.py"),
    ("secret_custody", "run_production_secret_custody_drill.py"),
    ("monitoring_slo", "run_production_monitoring_slo_drill.py"),
    ("incident_response", "run_production_incident_response_drill.py"),
    ("rollback_downgrade", "run_production_rollback_downgrade_drill.py"),
    ("risk_limits", "run_production_risk_limits_drill.py"),
    ("dependency_breakage", "run_production_dependency_breakage_drill.py"),
    ("audit_export", "run_production_audit_export_drill.py"),
]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def build_suite_plan(*, release_zip: Path | None, output_dir: Path | None) -> dict[str, Any]:
    release_zip = resolve(release_zip) if release_zip else None
    output_dir = resolve(output_dir) if output_dir else None
    env_overrides: dict[str, str] = {}
    if release_zip is not None:
        env_overrides["PMX_RELEASE_ARTIFACT_PATH"] = str(release_zip)

    drills = []
    for name, filename in CONTROL_DRILLS:
        command = ["python", str(ENGINE_VALIDATION / filename)]
        stdout_path = str(output_dir / f"{name}.json") if output_dir else None
        drills.append(
            {
                "name": name,
                "script": filename,
                "command": command,
                "stdout_path": stdout_path,
            }
        )

    return {
        "status": "ready",
        "suite": "production_control_evidence",
        "release_zip": str(release_zip) if release_zip else None,
        "output_dir": str(output_dir) if output_dir else None,
        "env_overrides": env_overrides,
        "drills": drills,
    }


def execute_suite(plan: dict[str, Any]) -> dict[str, Any]:
    env = dict(os.environ)
    env.update(plan["env_overrides"])
    output_dir = Path(plan["output_dir"]) if plan["output_dir"] else None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failed = False
    for drill in plan["drills"]:
        stdout_path = Path(drill["stdout_path"]) if drill["stdout_path"] else None
        if stdout_path is None:
            completed = subprocess.run(drill["command"], cwd=ROOT, text=True, env=env, check=False)
        else:
            with stdout_path.open("w") as fh:
                completed = subprocess.run(
                    drill["command"],
                    cwd=ROOT,
                    text=True,
                    env=env,
                    stdout=fh,
                    check=False,
                )
        result = {
            "name": drill["name"],
            "script": drill["script"],
            "returncode": completed.returncode,
            "stdout_path": drill["stdout_path"],
        }
        results.append(result)
        if completed.returncode != 0:
            failed = True

    return {
        "status": "fail" if failed else "pass",
        "suite": plan["suite"],
        "release_zip": plan["release_zip"],
        "output_dir": plan["output_dir"],
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-zip", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the suite. Without this flag the script only prints the suite plan.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_suite_plan(release_zip=args.release_zip, output_dir=args.output_dir)
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    result = execute_suite(plan)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
