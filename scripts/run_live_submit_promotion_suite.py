#!/usr/bin/env python3
"""Plan or run the local live-submit promotion evidence drills as one suite."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_VALIDATION = ROOT / "polymarket-execution-engine" / "validation"

PROMOTION_DRILLS = [
    ("live_submit_static_guard", "check_live_submit_guard.py"),
    ("live_canary_readiness", "run_live_canary_readiness_drill.py"),
    ("live_canary_preflight", "run_live_canary_preflight_drill.py"),
    ("live_canary_blocked", "run_live_canary_blocked_drill.py"),
    ("live_canary_rehearsal", "run_live_canary_rehearsal_drill.py"),
    ("live_canary_controlled_prep", "run_live_canary_controlled_prep_drill.py"),
    ("real_funds_canary_preflight", "run_real_funds_canary_preflight_drill.py"),
    ("real_funds_canary_ready", "run_real_funds_canary_ready_drill.py"),
    ("real_funds_canary_lifecycle", "run_real_funds_canary_lifecycle_drill.py"),
    ("real_funds_canary_review_package", "run_real_funds_canary_review_package_drill.py"),
]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def build_suite_plan(*, output_dir: Path | None) -> dict[str, Any]:
    output_dir = resolve(output_dir) if output_dir else None
    drills = []
    for name, filename in PROMOTION_DRILLS:
        command = ["python", str(ENGINE_VALIDATION / filename)]
        drills.append(
            {
                "name": name,
                "script": filename,
                "command": command,
                "stdout_path": str(output_dir / f"{name}.json") if output_dir else None,
            }
        )
    return {
        "status": "ready",
        "suite": "live_submit_promotion_evidence",
        "output_dir": str(output_dir) if output_dir else None,
        "drills": drills,
    }


def execute_suite(plan: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(plan["output_dir"]) if plan["output_dir"] else None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failed = False
    for drill in plan["drills"]:
        stdout_path = Path(drill["stdout_path"]) if drill["stdout_path"] else None
        if stdout_path is None:
            completed = subprocess.run(drill["command"], cwd=ROOT, text=True, check=False)
        else:
            with stdout_path.open("w") as fh:
                completed = subprocess.run(
                    drill["command"],
                    cwd=ROOT,
                    text=True,
                    stdout=fh,
                    check=False,
                )
        results.append(
            {
                "name": drill["name"],
                "script": drill["script"],
                "returncode": completed.returncode,
                "stdout_path": drill["stdout_path"],
            }
        )
        if completed.returncode != 0:
            failed = True

    return {
        "status": "fail" if failed else "pass",
        "suite": plan["suite"],
        "output_dir": plan["output_dir"],
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the suite. Without this flag the script only prints the suite plan.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_suite_plan(output_dir=args.output_dir)
    if not args.run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    result = execute_suite(plan)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
