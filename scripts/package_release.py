#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
ARCHIVE_ROOT = f"polymarket_execution_suite_v{VERSION.replace('.', '_')}"
DIST = ROOT / "dist"
OUT = DIST / f"polymarket-execution-suite-v{VERSION}.zip"
FORBIDDEN_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", "target", "dist"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3"}
FORBIDDEN_FILENAMES = {".env"}
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
    return completed.stdout.strip()


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    if any(part in FORBIDDEN_PARTS for part in rel.parts):
        return False
    if any(part.endswith(".egg-info") for part in rel.parts):
        return False
    if path.suffix in FORBIDDEN_SUFFIXES:
        return False
    if path.name in FORBIDDEN_FILENAMES:
        return False
    if any(rel_posix == prefix or rel_posix.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
        return False
    return True


def executable_in_archive(path: Path) -> bool:
    try:
        first = path.open("rb").read(2)
    except OSError:
        return False
    return first == b"#!"


def write_deterministic(zf: ZipFile, path: Path) -> None:
    archive_name = str(Path(ARCHIVE_ROOT) / path.relative_to(ROOT))
    info = ZipInfo(archive_name, DETERMINISTIC_MTIME)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    mode = 0o755 if executable_in_archive(path) else 0o644
    info.external_attr = (mode & 0xFFFF) << 16
    with path.open("rb") as fh:
        zf.writestr(info, fh.read())


def main() -> int:
    if not VERSION:
        print("VERSION file is empty", file=sys.stderr)
        return 1
    DIST.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with ZipFile(OUT, "w", ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and allowed(path):
                write_deterministic(zf, path)
    sidecar = OUT.with_suffix(OUT.suffix + ".sha256")
    artifact_sha256 = sha256(OUT)
    sidecar.write_text(f"{artifact_sha256}  {OUT.name}\n")
    evidence_manifest = ROOT / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json"
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
                    "submodules": command_output(["git", "submodule", "status"]),
                },
                "canonical_evidence": {
                    "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                    "manifest_sha256": sha256(evidence_manifest) if evidence_manifest.exists() else None,
                },
                "release_decision_path": "RELEASE_DECISION.md",
                "note": "This external sidecar binds the final zip hash; files inside the zip do not self-assert the final containing-archive hash.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
