#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
ARCHIVE_ROOT = f"polymarket_dual_project_v{VERSION.replace('.', '_')}"
OUT = ROOT.parent / f"polymarket-dual-project-v{VERSION}.zip"
FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "target"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3"}
FORBIDDEN_FILENAMES = {".env"}
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


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()
    if any(part in FORBIDDEN_PARTS for part in rel.parts):
        return False
    if path.suffix in FORBIDDEN_SUFFIXES:
        return False
    if path.name in FORBIDDEN_FILENAMES:
        return False
    if any(rel_posix == prefix or rel_posix.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
        return False
    return True


def main() -> int:
    if not VERSION:
        print("VERSION file is empty", file=sys.stderr)
        return 1
    if OUT.exists():
        OUT.unlink()
    with ZipFile(OUT, "w", ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and allowed(path):
                zf.write(path, str(Path(ARCHIVE_ROOT) / path.relative_to(ROOT)))
    sidecar = OUT.with_suffix(OUT.suffix + ".sha256")
    sidecar.write_text(f"{sha256(OUT)}  {OUT.name}\n")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
