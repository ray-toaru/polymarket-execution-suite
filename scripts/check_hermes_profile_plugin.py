#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PACKAGE = "hermes_polymarket_executor_adapter"
ENTRYPOINT_GROUP = "hermes_agent.plugins"
ENTRYPOINT_NAME = "polymarket-executor"
REQUIRED_TOOLSETS = ["polymarket_executor", "polymarket_executor_admin"]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def infer_hermes_python(profile_cmd: str) -> Path | None:
    explicit = os.environ.get("HERMES_RUNTIME_PYTHON", "").strip()
    if explicit:
        return Path(explicit)

    hermes_cmd = shutil.which("hermes")
    candidates: list[Path] = []
    if hermes_cmd:
        hermes_path = Path(hermes_cmd)
        candidates.append(hermes_path.with_name("python"))
        try:
            text = hermes_path.read_text(errors="ignore")
        except OSError:
            text = ""
        match = re.search(r'exec\s+"([^"]*/bin/hermes)"', text)
        if match:
            candidates.append(Path(match.group(1)).with_name("python"))

    profile_executable = shutil.which(profile_cmd)
    if profile_executable:
        profile_path = Path(profile_executable)
        candidates.append(profile_path.with_name("python"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def check_runtime_python(python_path: Path) -> list[str]:
    code = f"""
import importlib.metadata
import importlib.util
spec = importlib.util.find_spec({PLUGIN_PACKAGE!r})
if spec is None:
    raise SystemExit({PLUGIN_PACKAGE!r} + " is not importable")
entrypoints = importlib.metadata.entry_points().select(group={ENTRYPOINT_GROUP!r})
values = {{ep.name: ep.value for ep in entrypoints}}
expected = "hermes_polymarket_executor_adapter.hermes_plugin"
if values.get({ENTRYPOINT_NAME!r}) != expected:
    raise SystemExit("missing entrypoint " + {ENTRYPOINT_NAME!r})
print("runtime_python_import=pass")
"""
    result = run([str(python_path), "-c", code])
    if result.returncode == 0:
        return []
    return [result.stdout.strip() or f"{python_path} import check failed"]


def check_profile_tools(profile_cmd: str, platform: str) -> list[str]:
    executable = shutil.which(profile_cmd)
    if executable is None:
        return [f"profile command not found: {profile_cmd}"]

    result = run([executable, "tools", "list", "--platform", platform])
    if result.returncode != 0:
        return [result.stdout.strip() or f"{profile_cmd} tools list failed"]

    failures: list[str] = []
    for toolset in REQUIRED_TOOLSETS:
        if toolset not in result.stdout:
            failures.append(f"missing Hermes toolset in {profile_cmd}: {toolset}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate local Hermes profile discovery for the Polymarket executor plugin."
    )
    parser.add_argument(
        "--profile-cmd",
        default=os.environ.get("HERMES_PROFILE_CMD"),
        help="Hermes profile command or alias. Can also be set with HERMES_PROFILE_CMD.",
    )
    parser.add_argument("--platform", default="cli")
    parser.add_argument(
        "--hermes-python",
        type=Path,
        default=None,
        help="Python interpreter used by the Hermes runtime. Defaults to HERMES_RUNTIME_PYTHON or best-effort inference from the hermes command.",
    )
    args = parser.parse_args()

    if not args.profile_cmd:
        print("missing --profile-cmd or HERMES_PROFILE_CMD")
        return 1

    hermes_python = args.hermes_python or infer_hermes_python(args.profile_cmd)
    if hermes_python is None:
        print("missing --hermes-python or HERMES_RUNTIME_PYTHON; could not infer Hermes runtime Python")
        return 1

    failures: list[str] = []
    failures.extend(check_runtime_python(hermes_python))
    failures.extend(check_profile_tools(args.profile_cmd, args.platform))

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(
        "hermes profile plugin check passed "
        f"profile_cmd={args.profile_cmd} platform={args.platform}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
