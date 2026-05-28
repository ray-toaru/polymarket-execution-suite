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
REQUIRED_SUBMODULE_FILES = [
    "hermes-polymarket-executor-adapter/pyproject.toml",
    "hermes-polymarket-executor-adapter/src/hermes_polymarket_executor_adapter/__init__.py",
    "polymarket-execution-engine/Cargo.toml",
    "polymarket-execution-engine/release/manifest.json",
    "polymarket-execution-engine/.github/workflows/ci.yml",
    "polymarket-execution-engine/validation/run_current_gates.sh",
]
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
    "docs/future/CANARY_DECISION_PREP_AUDIT.md",
    "docs/future/CANARY_GO_NO_GO_REVIEW.md",
    "docs/future/CANARY_PRODUCTION_ROADMAP.md",
    "NO_LOCAL_ACTIONS_REMAINING.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def read_from(root: Path, path: str) -> str:
    return (root / path).read_text()


def expect_equal(failures: list[str], label: str, actual: str, expected: str) -> None:
    if actual != expected:
        failures.append(f"{label}: got {actual!r}, expected {expected!r}")


def regex_extract(failures: list[str], label: str, text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        failures.append(f"{label}: pattern not found: {pattern}")
        return ""
    return match.group(1)


def require_submodules_initialized(root: Path, failures: list[str]) -> bool:
    missing = [rel for rel in REQUIRED_SUBMODULE_FILES if not (root / rel).is_file()]
    if missing:
        failures.append(
            "required submodule files are missing; run `git submodule update --init --recursive`: "
            + ", ".join(missing)
        )
        return False
    return True


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


def component_versions(root: Path, failures: list[str]) -> dict[str, str]:
    path = root / "COMPONENT_COMPATIBILITY.md"
    if not path.exists():
        failures.append("COMPONENT_COMPATIBILITY.md missing")
        return {}

    versions: dict[str, str] = {}
    text = path.read_text()
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Component", "---"}:
            continue
        component = cells[0].lower()
        version = cells[2].strip("`")
        if component == "integration suite":
            versions["suite"] = version
        elif component == "execution engine":
            versions["engine"] = version
        elif component == "hermes adapter":
            versions["adapter"] = version

    for key in ["suite", "engine", "adapter"]:
        version = versions.get(key, "")
        if not EXPECTED_RE.match(version):
            failures.append(f"component matrix {key} version is not semver x.y.z: {version!r}")
    return versions


def validate_versions(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    suite_version = read_from(root, "VERSION").strip()
    if not EXPECTED_RE.match(suite_version):
        failures.append(f"VERSION is not semver x.y.z: {suite_version!r}")

    submodules_ready = require_submodules_initialized(root, failures)
    matrix_versions = component_versions(root, failures)
    matrix_suite_version = matrix_versions.get("suite", "")
    matrix_engine_version = matrix_versions.get("engine", "")
    matrix_adapter_version = matrix_versions.get("adapter", "")
    expect_equal(failures, "component matrix suite version", matrix_suite_version, suite_version)
    if not submodules_ready:
        return failures

    pyproject_version = regex_extract(failures, "hermes pyproject version", read_from(root, "hermes-polymarket-executor-adapter/pyproject.toml"), r'^version = "([^"]+)"')
    expect_equal(failures, "component matrix Hermes adapter version", matrix_adapter_version, pyproject_version)

    init_version = regex_extract(failures, "hermes package __version__", read_from(root, "hermes-polymarket-executor-adapter/src/hermes_polymarket_executor_adapter/__init__.py"), r'^__version__ = "([^"]+)"')
    expect_equal(failures, "hermes package __version__", init_version, pyproject_version)

    workspace_version = regex_extract(failures, "execution workspace version", read_from(root, "polymarket-execution-engine/Cargo.toml"), r'^version = "([^"]+)"')
    expect_equal(failures, "component matrix execution engine version", matrix_engine_version, workspace_version)

    adapter_version = regex_extract(failures, "official sdk adapter version", read_from(root, "polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.toml"), r'^version = "([^"]+)"')
    expect_equal(failures, "official sdk adapter version", adapter_version, workspace_version)

    manifest = json.loads(read_from(root, "polymarket-execution-engine/release/manifest.json"))
    expect_equal(failures, "release manifest version", manifest.get("version", ""), suite_version)
    status = manifest.get("status", "")
    if "source-candidate" not in status and "shadow-ready-candidate" not in status and "production-live-candidate" not in status:
        failures.append("release manifest status must explicitly say source-candidate, shadow-ready-candidate, or production-live-candidate")
    if "not-production" not in manifest.get("status", ""):
        failures.append("release manifest status must explicitly say not-production")

    ci = read_from(root, ".github/workflows/ci.yml")
    execution_ci = read_from(root, "polymarket-execution-engine/.github/workflows/ci.yml")
    if "./validation/run_current_gates.sh" in ci:
        failures.append("integration CI must not own execution-engine current gates")
    if "./validation/run_current_gates.sh" not in execution_ci:
        failures.append("execution-engine CI must run validation/run_current_gates.sh")
    current_gate = read_from(root, "polymarket-execution-engine/validation/run_current_gates.sh")
    if "run_current_gates_impl.sh" not in current_gate:
        failures.append("run_current_gates.sh must delegate to run_current_gates_impl.sh")
    if re.search(r"\./validation/run_v0_\d+_gates\.sh", ci + execution_ci):
        failures.append("CI must not bypass run_current_gates.sh or run stale versioned gates for current rust-prelive job")

    for lock_rel in [
        "polymarket-execution-engine/Cargo.lock",
        "polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.lock",
        "polymarket-execution-engine/adapters/pmx-official-sdk-spike/Cargo.lock",
    ]:
        versions = cargo_lock_versions(root / lock_rel)
        for name, version in sorted(versions.items()):
            if name == "pmx-official-sdk-spike":
                continue
            expect_equal(failures, f"{lock_rel} package {name}", version, workspace_version)

    expected_minor_marker = "v" + ".".join(suite_version.split(".")[:2])
    missing_doc_refs = []
    for doc in ACTIVE_DOCS:
        path = root / doc
        if path.exists():
            text = path.read_text()
            if expected_minor_marker not in text and "validation-promotion" not in text:
                missing_doc_refs.append(doc)
    if missing_doc_refs:
        failures.append(f"active docs missing {expected_minor_marker} marker: " + ", ".join(missing_doc_refs))
    return failures


def main() -> int:
    failures = validate_versions(ROOT)
    expected = read("VERSION").strip()

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"version consistency passed version={expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
