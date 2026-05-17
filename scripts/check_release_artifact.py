#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "target"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3"}
FORBIDDEN_FILENAMES = {".env"}
FORBIDDEN_PREFIX_SUFFIXES = (
    "docs/archive/",
    "external_reviews/",
    "validation/archive/",
    "polymarket-execution-engine/validation/archive/",
    "polymarket-execution-engine/evidence/archive/",
    "polymarket-execution-engine/docs/archive/",
)
STALE_ROOT_DOCS = [
    re.compile(r"^V0_.*\.md$"),
    re.compile(r"^VALIDATION_V0_.*\.md$"),
    re.compile(r".*_GATE_CONFIRMATION\.md$"),
    re.compile(r"^VALIDATION_CONFIRMATION_REPORT\.md$"),
    re.compile(r"^CONTINUATION_REPORT\.md$"),
    re.compile(r"^ISSUES_CONFIRMED_AND_FIXED\.md$"),
]
VERSION_SPECIFIC_AGENT_PATTERN = re.compile(
    r"(?:\b0\.\d+(?:\.\d+)?\b|\bv0\.\d+\b|\bv0_\d+\b|\bV0_\d+\b|run_v0_\d+_gates\.sh)",
    re.IGNORECASE,
)


def forbidden(member: str, expected_root: str | None = None) -> bool:
    path = Path(member)
    parts = path.parts
    name = parts[-1] if parts else member
    rel = member
    if expected_root and member.startswith(expected_root + "/"):
        rel = member[len(expected_root) + 1 :]
    return (
        any(part in FORBIDDEN_PARTS for part in parts)
        or Path(name).suffix in FORBIDDEN_SUFFIXES
        or name in FORBIDDEN_FILENAMES
        or any(rel == prefix[:-1] or rel.startswith(prefix) for prefix in FORBIDDEN_PREFIX_SUFFIXES)
    )


def stale_root_doc(member: str, expected_root: str) -> bool:
    prefix = expected_root + "/"
    if not member.startswith(prefix):
        return False
    rel = member[len(prefix) :]
    if "/" in rel:
        return False
    return any(pattern.match(rel) for pattern in STALE_ROOT_DOCS)



def stale_engine_doc(member: str, expected_root: str) -> bool:
    prefix = expected_root + "/polymarket-execution-engine/docs/"
    if not member.startswith(prefix):
        return False
    rel = member[len(prefix) :]
    if "/" in rel:
        return False
    if rel == "V0_23_SOURCE_CANDIDATE.md":
        return False
    return rel.startswith("V0_") and rel.endswith(".md")

def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_release_artifact.py <zip> <expected-version>", file=sys.stderr)
        return 2
    zip_path = Path(sys.argv[1])
    expected_version = sys.argv[2].strip()
    expected_root = f"polymarket_dual_project_v{expected_version.replace('.', '_')}"
    failures: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        roots = {name.split('/', 1)[0] for name in names if name and '/' in name}
        if roots != {expected_root}:
            failures.append(f"archive root mismatch: got {sorted(roots)}, expected {expected_root}")
        version_name = f"{expected_root}/VERSION"
        if version_name not in names:
            failures.append("VERSION missing from archive")
        else:
            actual_version = zf.read(version_name).decode().strip()
            if actual_version != expected_version:
                failures.append(f"VERSION mismatch: got {actual_version}, expected {expected_version}")
        bad = sorted({name for name in names if forbidden(name, expected_root)})
        if bad:
            failures.append("forbidden archive members: " + ", ".join(bad[:20]))
        stale_docs = sorted({name for name in names if stale_root_doc(name, expected_root)})
        if stale_docs:
            failures.append("stale root docs in archive: " + ", ".join(stale_docs[:20]))
        stale_engine_docs = sorted({name for name in names if stale_engine_doc(name, expected_root)})
        if stale_engine_docs:
            failures.append("stale execution-engine docs in archive: " + ", ".join(stale_engine_docs[:20]))
        forbidden_evidence_templates = sorted({name for name in names if f"{expected_root}/polymarket-execution-engine/evidence/v" in name})
        if forbidden_evidence_templates:
            failures.append("non-canonical evidence version directory in archive: " + ", ".join(forbidden_evidence_templates[:20]))
        required_agents = [
            f"{expected_root}/AGENTS.md",
            f"{expected_root}/hermes-polymarket-control/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-api/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-authz/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-core/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-gateway/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-policy/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-release/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-runtime/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-service/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/crates/pmx-store/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/adapters/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/openapi/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/migrations/AGENTS.md",
            f"{expected_root}/polymarket-execution-engine/validation/AGENTS.md",
        ]
        missing_agents = [name for name in required_agents if name not in names]
        if missing_agents:
            failures.append("required AGENTS.md files missing from archive: " + ", ".join(missing_agents))
        for name in required_agents:
            if name not in names:
                continue
            content = zf.read(name).decode()
            if VERSION_SPECIFIC_AGENT_PATTERN.search(content):
                failures.append(f"AGENTS.md contains version-specific release markers: {name}")
        current_manifest = f"{expected_root}/polymarket-execution-engine/evidence/current/manifest.json"
        if current_manifest not in names:
            failures.append("canonical evidence manifest missing from archive")
        else:
            data = json.loads(zf.read(current_manifest).decode())
            if data.get("version") != expected_version:
                failures.append("canonical evidence manifest version mismatch")
            if data.get("canonical_evidence_dir") != "polymarket-execution-engine/evidence/current":
                failures.append("canonical evidence manifest has bad canonical_evidence_dir")
            if data.get("release_decision", {}).get("validated_release") is True and not data.get("artifact", {}).get("sha256"):
                failures.append("validated evidence manifest must include artifact sha256")
        release_manifest = f"{expected_root}/polymarket-execution-engine/release/manifest.json"
        if release_manifest not in names:
            failures.append("release manifest missing")
        else:
            data = json.loads(zf.read(release_manifest).decode())
            binding = data.get("canonical_evidence", {})
            if binding.get("manifest_path") != "polymarket-execution-engine/evidence/current/manifest.json":
                failures.append("release manifest does not bind canonical evidence manifest")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"release artifact passed root={expected_root} version={expected_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
