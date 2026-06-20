#!/usr/bin/env python3
"""Local advisory SBOM/license tooling preflight.

This check intentionally does not build release packages, contact GitHub, or
change release posture. It only reports whether common local supply-chain tools
are available for a later explicitly requested SBOM/license scan.
"""
from __future__ import annotations

import json
import shutil
from typing import Any


OPTIONAL_TOOLS = ["syft", "cargo-deny", "cargo-about", "cyclonedx-py"]


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
        "status": "available" if available else "skipped",
        "scope": "local_advisory_supply_chain_preflight",
        "remote_side_effects": False,
        "package_refresh": False,
        "release_posture_changed": False,
        "available_tools": available,
        "missing_optional_tools": missing,
        "next_action": (
            "run explicit SBOM/license scan with selected installed tools"
            if available
            else "install syft, cargo-deny, cargo-about, or cyclonedx-py to enable local SBOM/license scans"
        ),
    }


def main() -> int:
    print(json.dumps(build_report(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
