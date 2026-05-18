#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RE = re.compile(r"^\d+\.\d+\.\d+$")
LOCAL_RUST_PACKAGES = {
    "pmx-api",
    "pmx-authz",
    "pmx-core",
    "pmx-gateway",
    "pmx-policy",
    "pmx-release",
    "pmx-runtime",
    "pmx-service",
    "pmx-store",
    "pmx-official-sdk-adapter",
}
ACTIVE_DOCS = [
    "README.md",
    "PROJECT_ARCHITECTURE.md",
    "DEPENDENCY_POLICY.md",
    "DESIGN_DECISION_RECORD.md",
    "CURRENT_PROGRESS.md",
    "DEVELOPMENT_HANDOFF.md",
    "TASKS.md",
    "VALIDATION_REPORT.md",
    "REVIEW_AUDIT.md",
    "DOC_STATUS.md",
    "IMPLEMENTATION_STATUS.md",
    "ROADMAP.md",
    "NO_LOCAL_ACTIONS_REMAINING.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def expect_equal(failures: list[str], label: str, actual: str, expected: str) -> None:
    if actual != expected:
        failures.append(f"{label}: got {actual!r}, expected {expected!r}")


def regex_extract(failures: list[str], label: str, text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        failures.append(f"{label}: pattern not found: {pattern}")
        return ""
    return match.group(1)


def cargo_lock_versions(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    current_name: str | None = None
    for line in path.read_text().splitlines():
        name = re.match(r'name = "([^"]+)"', line)
        if name:
            current_name = name.group(1)
            continue
        version = re.match(r'version = "([^"]+)"', line)
        if version and current_name in LOCAL_RUST_PACKAGES:
            versions[current_name] = version.group(1)
    return versions


def main() -> int:
    failures: list[str] = []
    expected = read("VERSION").strip()
    if not EXPECTED_RE.match(expected):
        failures.append(f"VERSION is not semver x.y.z: {expected!r}")

    pyproject_version = regex_extract(
        failures,
        "hermes pyproject version",
        read("hermes-polymarket-control/pyproject.toml"),
        r'^version = "([^"]+)"',
    )
    expect_equal(failures, "hermes pyproject version", pyproject_version, expected)

    init_version = regex_extract(
        failures,
        "hermes package __version__",
        read("hermes-polymarket-control/src/hermes_polymarket_control/__init__.py"),
        r'^__version__ = "([^"]+)"',
    )
    expect_equal(failures, "hermes package __version__", init_version, expected)

    workspace_version = regex_extract(
        failures,
        "execution workspace version",
        read("polymarket-execution-engine/Cargo.toml"),
        r'^version = "([^"]+)"',
    )
    expect_equal(failures, "execution workspace version", workspace_version, expected)

    adapter_version = regex_extract(
        failures,
        "official sdk adapter version",
        read("polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.toml"),
        r'^version = "([^"]+)"',
    )
    expect_equal(failures, "official sdk adapter version", adapter_version, expected)

    manifest = json.loads(read("polymarket-execution-engine/release/manifest.json"))
    expect_equal(failures, "release manifest version", manifest.get("version", ""), expected)
    if "source-candidate" not in manifest.get("status", ""):
        failures.append("release manifest status must explicitly say source-candidate")
    if "not-production" not in manifest.get("status", ""):
        failures.append("release manifest status must explicitly say not-production")

    ci = read(".github/workflows/ci.yml")
    if "./validation/run_current_gates.sh" not in ci:
        failures.append("CI must run validation/run_current_gates.sh")
    current_gate = read("polymarket-execution-engine/validation/run_current_gates.sh")
    if "run_v0_24_gates.sh" not in current_gate:
        failures.append("run_current_gates.sh must delegate to run_v0_24_gates.sh")
    if "./validation/run_v0_21_gates.sh" in ci or "./validation/run_v0_22_gates.sh" in ci or "./validation/run_v0_24_gates.sh" in ci:
        failures.append("CI must not bypass run_current_gates.sh or run stale versioned gates for current rust-prelive job")

    for lock_rel in [
        "polymarket-execution-engine/Cargo.lock",
        "polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.lock",
        "polymarket-execution-engine/adapters/pmx-official-sdk-spike/Cargo.lock",
    ]:
        versions = cargo_lock_versions(ROOT / lock_rel)
        for name, version in sorted(versions.items()):
            if name == "pmx-official-sdk-spike":
                continue
            expect_equal(failures, f"{lock_rel} package {name}", version, expected)

    expected_minor_marker = "v" + ".".join(expected.split(".")[:2])
    missing_doc_refs = []
    for doc in ACTIVE_DOCS:
        path = ROOT / doc
        if path.exists():
            text = path.read_text()
            if expected_minor_marker not in text and "validation-promotion" not in text:
                missing_doc_refs.append(doc)
    if missing_doc_refs:
        failures.append(
            f"active docs missing {expected_minor_marker} marker: "
            + ", ".join(missing_doc_refs)
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"version consistency passed version={expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
