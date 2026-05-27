from __future__ import annotations

from pathlib import Path


FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "target",
    "dist",
    "secrets",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".crt"}
FORBIDDEN_FILENAMES = {".env", "config/secrets.json"}
FORBIDDEN_NAME_PREFIXES = (".env.",)
FORBIDDEN_NAME_SUFFIXES = (".local.json",)
EXCLUDED_PREFIXES = {
    "docs/archive",
    "external_reviews",
    "validation/archive",
    "polymarket-execution-engine/validation/archive",
    "polymarket-execution-engine/evidence/archive",
    "polymarket-execution-engine/docs/archive",
}


def is_forbidden_release_member(path: str | Path, *, expected_root: str | None = None) -> bool:
    raw = path.as_posix() if isinstance(path, Path) else str(path)
    normalized = raw.rstrip("/")
    rel = normalized
    if expected_root:
        prefix = expected_root + "/"
        if rel.startswith(prefix):
            rel = rel[len(prefix) :]
        elif rel == expected_root:
            rel = ""
    rel_path = Path(rel)
    parts = rel_path.parts
    name = rel_path.name if parts else rel

    if any(part in FORBIDDEN_PARTS for part in parts):
        return True
    if "logs" in parts and parts[:4] != (
        "polymarket-execution-engine",
        "evidence",
        "current",
        "logs",
    ):
        return True
    if any(part.endswith(".egg-info") for part in parts):
        return True
    if rel in FORBIDDEN_FILENAMES or name in FORBIDDEN_FILENAMES:
        return True
    if any(name.startswith(prefix) for prefix in FORBIDDEN_NAME_PREFIXES) and not name.endswith(".example"):
        return True
    if any(name.endswith(suffix) for suffix in FORBIDDEN_NAME_SUFFIXES):
        return True
    if rel_path.suffix in FORBIDDEN_SUFFIXES:
        return True
    if any(rel == prefix or rel.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
        return True
    return False
