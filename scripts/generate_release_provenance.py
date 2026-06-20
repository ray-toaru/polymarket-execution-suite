#!/usr/bin/env python3
"""Generate and validate non-live release provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/actions/runs/[0-9]+(?:/.*)?$"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def current_submodules(root: Path) -> list[dict[str, str]]:
    records = []
    for line in git_output(root, "submodule", "status", "--recursive").splitlines():
        if not line.strip():
            continue
        if line[0] in "+-U ":
            status = line[0]
            fields = line[1:].strip().split()
        else:
            status = " "
            fields = line.split()
        records.append(
            {
                "path": fields[1],
                "commit": fields[0],
                "checkout_status": {
                    " ": "clean",
                    "+": "different_commit",
                    "-": "not_initialized",
                    "U": "merge_conflict",
                }.get(status, "unknown"),
            }
        )
    return records


def build_provenance(
    *,
    artifact: Path,
    manifest: Path,
    version: str,
    root_commit: str,
    submodules: list[dict[str, str]],
    ci_runs: list[dict[str, str]],
    materials: list[Path],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_posture": "non_live_hardened",
        "version": version,
        "subject": {"name": artifact.name, "sha256": sha256(artifact)},
        "evidence_manifest": {
            "path": str(manifest),
            "sha256": sha256(manifest),
        },
        "source": {
            "repository": "https://github.com/ray-toaru/polymarket-execution-suite",
            "root_commit": root_commit,
            "submodules": submodules,
        },
        "ci_runs": ci_runs,
        "materials": [
            {"path": str(path), "sha256": sha256(path)}
            for path in sorted(materials, key=lambda item: str(item))
        ],
        "authorization": {
            "production_ready": False,
            "live_ready": False,
            "real_funds_authorized": False,
        },
    }


def load_ci_runs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("ci_runs"), list):
        return data["ci_runs"]
    raise SystemExit("--ci-evidence must contain a JSON array or an object with ci_runs")


def source_commit_by_github_repo(source: dict[str, Any]) -> dict[str, str]:
    commits: dict[str, str] = {}
    root_commit = source.get("root_commit")
    if isinstance(root_commit, str):
        commits["polymarket-execution-suite"] = root_commit
        commits["polymarket_dual_project"] = root_commit
    for record in source.get("submodules", []):
        if not isinstance(record, dict):
            continue
        path = record.get("path")
        commit = record.get("commit")
        if isinstance(path, str) and isinstance(commit, str):
            commits[Path(path).name] = commit
    return commits


def validate_provenance(
    provenance: dict[str, Any],
    artifact: Path,
    *,
    base_dir: Path | None = None,
) -> list[str]:
    failures: list[str] = []
    if provenance.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if provenance.get("release_posture") != "non_live_hardened":
        failures.append("release_posture must be non_live_hardened")
    subject = provenance.get("subject")
    if not isinstance(subject, dict):
        failures.append("subject must be an object")
    else:
        digest = subject.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            failures.append("subject.sha256 must be a SHA-256 digest")
        elif digest != sha256(artifact):
            failures.append("subject.sha256 does not match artifact")
        if subject.get("name") != artifact.name:
            failures.append("subject.name does not match artifact")

    source = provenance.get("source")
    source_commits: dict[str, str] = {}
    if not isinstance(source, dict) or not SHA1_RE.fullmatch(str(source.get("root_commit", ""))):
        failures.append("source.root_commit must be a full commit SHA")
    else:
        source_commits = source_commit_by_github_repo(source)
        for index, record in enumerate(source.get("submodules", [])):
            if not isinstance(record, dict) or not SHA1_RE.fullmatch(str(record.get("commit", ""))):
                failures.append(f"source.submodules[{index}].commit must be a full commit SHA")
            if isinstance(record, dict) and record.get("checkout_status", "clean") != "clean":
                failures.append(f"source.submodules[{index}] checkout_status must be clean")

    ci_runs = provenance.get("ci_runs")
    if not isinstance(ci_runs, list) or not ci_runs:
        failures.append("ci_runs must contain at least one successful run")
    else:
        for index, run in enumerate(ci_runs):
            if not isinstance(run, dict):
                failures.append(f"ci_runs[{index}] must be an object")
                continue
            url = str(run.get("workflow_run_url", ""))
            run_url_match = RUN_URL_RE.fullmatch(url)
            if not run_url_match:
                failures.append(f"ci_runs[{index}].workflow_run_url is not a concrete HTTPS URL")
            if run.get("workflow_status") != "success":
                failures.append(f"ci_runs[{index}].workflow_status must be success")
            commit_sha = str(run.get("commit_sha", ""))
            if not SHA1_RE.fullmatch(commit_sha):
                failures.append(f"ci_runs[{index}].commit_sha must be a full commit SHA")
            elif run_url_match:
                repo = run_url_match.group("repo")
                expected_commit = source_commits.get(repo)
                if expected_commit is not None and commit_sha != expected_commit:
                    failures.append(
                        f"ci_runs[{index}].commit_sha does not match source commit for {repo}"
                    )
            try:
                datetime.fromisoformat(str(run.get("timestamp", "")).replace("Z", "+00:00"))
            except ValueError:
                failures.append(f"ci_runs[{index}].timestamp must be RFC3339")

    authorization = provenance.get("authorization", {})
    for field in ("production_ready", "live_ready", "real_funds_authorized"):
        if authorization.get(field) is not False:
            failures.append(f"authorization.{field} must be false")

    if base_dir is not None:
        for index, material in enumerate(provenance.get("materials", [])):
            if not isinstance(material, dict):
                failures.append(f"materials[{index}] must be an object")
                continue
            path = Path(str(material.get("path", "")))
            resolved = path if path.is_absolute() else base_dir / path
            if not resolved.is_file():
                failures.append(f"materials[{index}].path does not exist")
            elif material.get("sha256") != sha256(resolved):
                failures.append(f"materials[{index}].sha256 does not match")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ci-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    ci_runs = load_ci_runs(args.ci_evidence)
    material_candidates = [
        ROOT / "VERSION",
        ROOT / "requirements-ci.txt",
        ROOT / "constraints-ci.txt",
        ROOT / "polymarket-execution-engine" / "Cargo.lock",
        ROOT / "hermes-polymarket-executor-adapter" / "pyproject.toml",
        args.manifest,
    ]
    provenance = build_provenance(
        artifact=args.artifact,
        manifest=args.manifest,
        version=(ROOT / "VERSION").read_text().strip(),
        root_commit=git_output(ROOT, "rev-parse", "HEAD"),
        submodules=current_submodules(ROOT),
        ci_runs=ci_runs,
        materials=[path for path in material_candidates if path.is_file()],
    )
    failures = validate_provenance(provenance, args.artifact)
    if failures:
        raise SystemExit("\n".join(failures))
    output = args.output or args.artifact.with_suffix(args.artifact.suffix + ".provenance.json")
    output.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
