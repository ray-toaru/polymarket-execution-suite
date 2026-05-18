#!/usr/bin/env python3
"""Remove local Python/test/build byproducts before release hygiene checks.

This script intentionally deletes only generated cache directories and files that are
already forbidden from release artifacts. It does not remove evidence, source, lock
files, or developer-authored documents.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR_NAMES = {".venv", "venv", "target", "__pycache__", ".pytest_cache", ".mypy_cache"}
FILE_SUFFIXES = {".pyc", ".pyo"}


def main() -> int:
    removed: list[str] = []

    # Delete directories top-down by collecting first, so removing a parent does not
    # disturb the active traversal.
    dirs = [path for path in ROOT.rglob("*") if path.is_dir() and path.name in DIR_NAMES]
    for path in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if path.exists():
            shutil.rmtree(path)
            removed.append(str(path.relative_to(ROOT)))

    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in FILE_SUFFIXES:
            path.unlink()
            removed.append(str(path.relative_to(ROOT)))

    print(f"local artifact cleanup complete: removed={len(removed)}")
    for rel in removed[:50]:
        print(f" - {rel}")
    if len(removed) > 50:
        print(f" - ... {len(removed) - 50} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
