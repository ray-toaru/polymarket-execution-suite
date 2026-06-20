#!/usr/bin/env python3
"""Local advisory SBOM/license tooling preflight.

This check intentionally does not build release packages, contact GitHub, or
change release posture. It only reports whether common local supply-chain tools
are available for a later explicitly requested SBOM/license scan.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


OPTIONAL_TOOLS = ["syft", "cargo-deny", "cargo-about", "cyclonedx-py"]
SCHEMA_VERSION = 1


def build_report() -> dict[str, Any]:
    available = []
    missing = []
    for name in OPTIONAL_TOOLS:
        path = shutil.which(name)
        if path:
            available.append({"name": name, "path": path})
        else:
            missing.append(name)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "available" if available else "skipped",
        "scope": "local_advisory_supply_chain_preflight",
        "remote_side_effects": False,
        "package_refresh": False,
        "release_posture_changed": False,
        "optional_tools": list(OPTIONAL_TOOLS),
        "available_tools": available,
        "missing_optional_tools": missing,
        "next_action": (
            "run explicit SBOM/license scan with selected installed tools"
            if available
            else "install syft, cargo-deny, cargo-about, or cyclonedx-py to enable local SBOM/license scans"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for writing the preflight report JSON.",
    )
    return parser.parse_args(argv)


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report()
    if args.output is not None:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
