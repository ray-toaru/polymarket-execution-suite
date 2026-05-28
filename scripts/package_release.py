#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
ARCHIVE_ROOT = f"polymarket_execution_suite_v{VERSION.replace('.', '_')}"
DIST = ROOT / "dist"
OUT = DIST / f"polymarket-execution-suite-v{VERSION}.zip"
FORBIDDEN_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "target", "dist", "secrets", ".secrets", "runtime-secrets"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}
FORBIDDEN_FILENAMES = {".env"}
FORBIDDEN_GLOBS = [".env*", "*.local.json", "*secret*", "*credential*"]
SECRET_CONTENT_PATTERNS = [
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(rb"(?i)POLYMARKET_PRIVATE_KEY\s*="),
    re.compile(rb"(?i)POLY_API_SECRET\s*="),
    re.compile(rb"(?i)POLY_API_PASSPHRASE\s*="),
]
TEXT_SCAN_SUFFIXES = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".env", ".example"}
DETERMINISTIC_MTIME = (1980, 1, 1, 0, 0, 0)
EXCLUDED_PREFIXES = {
    "docs/archive",
    "external_reviews",
    "validation/archive",
    "polymarket-execution-engine/validation/archive",
    "polymarket-execution-engine/evidence/archive",
    "polymarket-execution-engine/docs/archive",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command_output(command: list[str]) -> str | None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\n")


def git_branch(path: Path = ROOT) -> str | None:
    return command_output(["git", "-C", str(path), "branch", "--show-current"])


def submodule_records() -> list[dict[str, str]]:
    raw = command_output(["git", "submodule", "status"]) or ""
    records: list[dict[str, str]] = []
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        status = raw_line[0]
        rest = raw_line[1:].strip() if status in {" ", "+", "-", "U"} else raw_line.strip()
        parts = rest.split()
        if len(parts) < 2:
            continue
        records.append(
            {
                "path": parts[1],
                "commit": parts[0],
                "checkout_status": status if status != " " else "clean",
                "checkout_ref": " ".join(parts[2:]).strip(),
            }
        )
    return records


def path_has_forbidden_glob(rel_posix: str, name: str) -> bool:
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_posix, pattern)
        for pattern in FORBIDDEN_GLOBS
    )


def content_scan_required(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SCAN_SUFFIXES or path.name.startswith(".env")


def contains_forbidden_content(path: Path) -> bool:
    if not content_scan_required(path):
        return False
    try:
        data = path.read_bytes()
    except OSError:
        return True
    return any(pattern.search(data) for pattern in SECRET_CONTENT_PATTERNS)


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    if any(part in FORBIDDEN_PARTS for part in rel.parts):
        return False
    if any(part.endswith(".egg-info") for part in rel.parts):
        return False
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return False
    if path.name in FORBIDDEN_FILENAMES:
        return False
    if path_has_forbidden_glob(rel_posix, path.name):
        return False
    if any(rel_posix == prefix or rel_posix.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
        return False
    if contains_forbidden_content(path):
        return False
    return True


def executable_in_archive(path: Path) -> bool:
    try:
        first = path.open("rb").read(2)
    except OSError:
        return False
    return first == b"#!"


def archive_bytes(path: Path) -> bytes:
    rel = path.relative_to(ROOT).as_posix()
    data = path.read_bytes()
    if rel == "polymarket-execution-engine/evidence/current/manifest.json":
        manifest = json.loads(data.decode())
        manifest["generated_at"] = "archive-normalized"
        manifest["archive_normalization"] = {
            "reason": (
                "The workspace manifest records the post-package artifact hash and generation "
                "timestamp. The copy embedded in the artifact normalizes volatile fields so the "
                "archive can be deterministically bound by external sidecars without self-reference."
            ),
            "normalized_fields": [
                "generated_at",
                "external_artifact_sidecar.sha256",
            ],
        }
        external = manifest.get("external_artifact_sidecar")
        if isinstance(external, dict):
            external["sha256"] = None
            external["binding_note"] = (
                "Archived manifest copy: external artifact hash is normalized to null "
                "to avoid archive self-reference. Use the external .zip.sha256 and "
                ".zip.evidence.json sidecars, or the post-package workspace manifest, "
                "for final artifact binding."
            )
        data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return data


def write_deterministic(zf: ZipFile, path: Path) -> None:
    archive_name = str(Path(ARCHIVE_ROOT) / path.relative_to(ROOT))
    info = ZipInfo(archive_name, DETERMINISTIC_MTIME)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    mode = 0o755 if executable_in_archive(path) else 0o644
    info.external_attr = (mode & 0xFFFF) << 16
    zf.writestr(info, archive_bytes(path))


def build_archive() -> None:
    if OUT.exists():
        OUT.unlink()
    with ZipFile(OUT, "w", ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and allowed(path):
                write_deterministic(zf, path)


def classify_dist_entry(name: str, *, is_dir: bool, child_names: set[str] | None = None) -> dict[str, object]:
    child_names = child_names or set()
    status = "local_review_material_not_release_artifact"
    approval_reuse_allowed = False
    remote_side_effects_authorized = False
    if name.startswith("pmx-canary-reviewed-go-"):
        if "closeout.json" in child_names or "CLOSEOUT.md" in child_names:
            status = "consumed_closed"
        elif any(child.startswith("approval-consumed") for child in child_names):
            status = "consumed_not_closed"
        else:
            status = "reviewed_go_local_material_not_current_approval"
    elif name.startswith("pmx-canary-review-") and "no-go" in name:
        status = "current_no_go_review_material"
    elif name.startswith("pmx-canary-review-"):
        status = "review_material_not_release_artifact"
    elif name.startswith("pmx-canary-"):
        status = "historical_or_local_canary_material"
    return {
        "path": name,
        "kind": "directory" if is_dir else "file",
        "status": status,
        "approval_reuse_allowed": approval_reuse_allowed,
        "remote_side_effects_authorized": remote_side_effects_authorized,
    }


def write_dist_index(artifact_sha256: str, manifest_sha256: str | None) -> None:
    current_release_files = {OUT.name, OUT.with_suffix(OUT.suffix + ".sha256").name, OUT.with_suffix(OUT.suffix + ".evidence.json").name}
    local_material = []
    for path in sorted(DIST.iterdir()):
        if path.name in current_release_files or path.name in {"INDEX.json", "README.md"}:
            continue
        child_names = {child.name for child in path.iterdir()} if path.is_dir() else set()
        local_material.append(classify_dist_entry(path.name, is_dir=path.is_dir(), child_names=child_names))
    index = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "current_release_artifact": {
            "path": OUT.name,
            "sha256": artifact_sha256,
            "sha256_sidecar": OUT.with_suffix(OUT.suffix + ".sha256").name,
            "evidence_sidecar": OUT.with_suffix(OUT.suffix + ".evidence.json").name,
            "artifact_class": "production_live_candidate_non_live_by_default",
            "validated_release": False,
            "production_ready": False,
            "live_trading_ready": False,
        },
        "canonical_evidence": {
            "path": "polymarket-execution-engine/evidence/current/manifest.json",
            "sha256": manifest_sha256,
        },
        "local_material": local_material,
        "operator_warning": (
            "Only current_release_artifact and its sidecars form the source release artifact. "
            "Other dist entries are local review material and must not be treated as current approval."
        ),
    }
    (DIST / "INDEX.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    (DIST / "README.md").write_text(
        "\n".join(
            [
                f"# Polymarket Execution Suite dist index v{VERSION}",
                "",
                "Current source artifact:",
                "",
                f"- `{OUT.name}`",
                f"- SHA-256: `{artifact_sha256}`",
                "- Status: production-live-candidate, non-live",
                "- Not production-ready; not live-trading-ready; not a `go` approval",
                "",
                "`INDEX.json` is the machine-readable index. Any other files or directories in",
                "`dist/` are local review material unless listed as the current release artifact.",
                "",
            ]
        )
    )


def bind_workspace_manifest(evidence_manifest: Path, artifact_sha256: str) -> None:
    if not evidence_manifest.exists():
        return
    data = json.loads(evidence_manifest.read_text())
    external = data.setdefault("external_artifact_sidecar", {})
    if isinstance(external, dict):
        external.update(
            {
                "name": OUT.name,
                "path": f"dist/{OUT.name}",
                "sha256": artifact_sha256,
                "sha256_sidecar": f"{OUT.name}.sha256",
                "evidence_sidecar": f"{OUT.name}.evidence.json",
                "binding_note": (
                    "Current workspace evidence binds the final release artifact here. "
                    "When this manifest is archived inside the artifact, package_release.py "
                    "normalizes this volatile hash to null to avoid archive self-reference."
                ),
            }
        )
    data.setdefault("artifact", {}).update(
        {
            "name": None,
            "path": None,
            "sha256": None,
            "binding_note": (
                "The canonical manifest does not self-bind a containing zip. "
                "Release artifacts are bound by external .zip.sha256 and .zip.evidence.json sidecars."
            ),
        }
    )
    evidence_manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> int:
    if not VERSION:
        print("VERSION file is empty", file=sys.stderr)
        return 1
    DIST.mkdir(exist_ok=True)
    evidence_manifest = ROOT / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json"
    build_archive()
    initial_artifact_sha256 = sha256(OUT)
    bind_workspace_manifest(evidence_manifest, initial_artifact_sha256)
    build_archive()
    artifact_sha256 = sha256(OUT)
    bind_workspace_manifest(evidence_manifest, artifact_sha256)
    workspace_manifest_sha256 = sha256(evidence_manifest) if evidence_manifest.exists() else None
    manifest_sha256 = (
        hashlib.sha256(archive_bytes(evidence_manifest)).hexdigest()
        if evidence_manifest.exists()
        else None
    )
    sidecar = OUT.with_suffix(OUT.suffix + ".sha256")
    sidecar.write_text(f"{artifact_sha256}  {OUT.name}\n")
    evidence_sidecar = OUT.with_suffix(OUT.suffix + ".evidence.json")
    evidence_sidecar.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "artifact": {
                    "name": OUT.name,
                    "sha256": artifact_sha256,
                    "sha256_sidecar": sidecar.name,
                },
                "source": {
                    "version": VERSION,
                    "git_head": command_output(["git", "rev-parse", "HEAD"]),
                    "git_branch": git_branch(),
                    "submodules": submodule_records(),
                    "submodule_status_raw": command_output(["git", "submodule", "status"]),
                },
                "canonical_evidence": {
                    "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                    "manifest_sha256": manifest_sha256,
                    "archived_manifest_sha256": manifest_sha256,
                    "workspace_manifest_sha256": workspace_manifest_sha256,
                },
                "release_decision_path": "RELEASE_DECISION.md",
                "note": "This external sidecar binds the final zip hash; files inside the zip do not self-assert the final containing-archive hash.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    write_dist_index(artifact_sha256, manifest_sha256)
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
