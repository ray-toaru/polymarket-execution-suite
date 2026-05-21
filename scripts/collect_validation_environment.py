#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path = ROOT) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return {"available": False, "command": command, "error": "not found"}
    except subprocess.TimeoutExpired:
        return {"available": False, "command": command, "error": "timeout"}
    return {
        "available": completed.returncode == 0,
        "command": command,
        "exit_status": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_info(path: Path) -> dict[str, object]:
    status = run(["git", "status", "--short"], cwd=path).get("stdout")
    status_lines = [line for line in str(status).splitlines() if line.strip()]
    return {
        "path": str(path.relative_to(ROOT)) if path != ROOT else ".",
        "branch": run(["git", "branch", "--show-current"], cwd=path).get("stdout"),
        "head": run(["git", "rev-parse", "HEAD"], cwd=path).get("stdout"),
        "status_clean": not status_lines,
        "status_entry_count": len(status_lines),
    }


def main() -> int:
    executor = ROOT / "polymarket-execution-engine"
    locks = [
        executor / "Cargo.lock",
        executor / "adapters" / "pmx-official-sdk-adapter" / "Cargo.lock",
        executor / "adapters" / "pmx-official-sdk-spike" / "Cargo.lock",
    ]
    data = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "integration_root": str(ROOT),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "PMX_TEST_DATABASE_URL_set": bool(os.environ.get("PMX_TEST_DATABASE_URL")),
            "PMX_RUN_AUTHENTICATED_NON_TRADING_SMOKE": os.environ.get(
                "PMX_RUN_AUTHENTICATED_NON_TRADING_SMOKE"
            ),
            "PMX_RUN_SIGN_ONLY_DRY_RUN": os.environ.get("PMX_RUN_SIGN_ONLY_DRY_RUN"),
        },
        "tools": {
            "rustc": run(["rustc", "--version"]),
            "cargo": run(["cargo", "--version"]),
            "psql": run(["psql", "--version"]),
            "python": run([sys.executable, "--version"]),
            "pip_freeze": run([sys.executable, "-m", "pip", "freeze", "--all"]),
        },
        "git": {
            "integration": git_info(ROOT),
            "hermes": git_info(ROOT / "hermes-polymarket-control"),
            "execution": git_info(executor),
            "submodules": run(["git", "submodule", "status"]).get("stdout"),
        },
        "dependency_locks": {
            str(path.relative_to(ROOT)): {"exists": path.exists(), "sha256": sha256(path)}
            for path in locks
        },
    }
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
