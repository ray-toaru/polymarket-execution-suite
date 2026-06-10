#!/usr/bin/env python3
"""Validate local Markdown links in tracked documentation."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")


def tracked_markdown_files(root: Path = ROOT) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "*.md"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "git ls-files failed while collecting Markdown documentation: "
            + completed.stderr.decode(errors="replace").strip()
        )
    return [
        root / item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def local_link_target(source: Path, raw_target: str, root: Path = ROOT) -> Path | None:
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    path_text = unquote(target.split("#", 1)[0])
    if not path_text:
        return None
    if path_text.startswith("/"):
        return root / path_text.lstrip("/")
    return source.parent / path_text


def broken_links(files: list[Path], root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for source in files:
        text = source.read_text(errors="replace")
        for match in LINK_PATTERN.finditer(text):
            target = local_link_target(source, match.group(1), root)
            if target is not None and not target.exists():
                failures.append(
                    f"{source.relative_to(root)}: missing local link target {match.group(1)}"
                )
    return failures


def main() -> int:
    failures = broken_links(tracked_markdown_files())
    if failures:
        raise SystemExit("\n".join(failures))
    print("tracked Markdown local link check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
