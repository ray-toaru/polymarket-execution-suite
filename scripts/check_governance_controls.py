#!/usr/bin/env python3
"""Validate repository-level governance controls."""
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_EXTERNAL_REVIEW_FILES = {
    "external_reviews/reviewer-registry/lei.pending.json",
}

REQUIRED_CODEOWNER_PATHS = {
    "/.github/",
    "/.gitmodules",
    "/scripts/",
    "/tests/",
    "/OFFLINE_INDEPENDENT_REVIEW_MANUAL.md",
    "/DESIGN_DECISION_RECORD.md",
    "/REVIEW_AUDIT.md",
    "/DOC_STATUS.md",
    "/RELEASE_DECISION.md",
    "/SECURITY_MODEL.md",
    "/polymarket-execution-engine",
    "/hermes-polymarket-executor-adapter",
}

REQUIRED_PR_TEMPLATE_PHRASES = [
    "No secrets, raw signatures, signed payloads, or production data added",
    "Live submit/cancel and production deployment remain blocked",
    "Submodule commits were committed and pushed before pointer updates",
    "List exact commands and results",
    "External review reference",
    "A self-review is not independent review",
    "Fresh CI is required for the final reviewed state",
    "This PR does not claim live, production, or repeat-canary authorization",
]

REQUIRED_GOVERNANCE_PHRASES = {
    "DESIGN_DECISION_RECORD.md": [
        "direct-main-push exception",
        "does not grant live submit, live cancel, production deployment, or repeat-canary authorization",
        "fresh CI and fresh independent review for the changed final state",
    ],
    "REVIEW_AUDIT.md": [
        "external posthoc independent review by `reviewer://lei`",
        "does not authorize live submit, live cancel, production deployment, or another canary attempt",
        "requires a fresh review of",
    ],
    "DOC_STATUS.md": [
        "non-live governance baseline",
        "external posthoc review archive remains outside the repository",
        "fresh CI and fresh independent review for the changed final state",
    ],
}


def git_ls_files(root: Path = ROOT) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "git ls-files failed while checking governance controls: "
            + completed.stderr.decode(errors="replace").strip()
        )
    return [
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def tracked_external_review_violations(files: list[str]) -> list[str]:
    return [
        path
        for path in files
        if path.startswith("external_reviews/")
        and path not in ALLOWED_EXTERNAL_REVIEW_FILES
    ]


def missing_codeowner_paths(text: str) -> list[str]:
    declared_paths = {
        line.split()[0]
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return sorted(REQUIRED_CODEOWNER_PATHS - declared_paths)


def missing_required_phrases(text: str, phrases: list[str]) -> list[str]:
    normalized = " ".join(text.split())
    return [phrase for phrase in phrases if phrase not in normalized]


def governance_doc_failures(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for relative_path, phrases in REQUIRED_GOVERNANCE_PHRASES.items():
        path = root / relative_path
        missing = missing_required_phrases(path.read_text(), phrases)
        failures.extend(f"{relative_path}: missing phrase {phrase!r}" for phrase in missing)
    return failures


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []

    external_review_violations = tracked_external_review_violations(git_ls_files(root))
    failures.extend(
        f"external review archive must stay untracked: {path}"
        for path in external_review_violations
    )

    codeowners_missing = missing_codeowner_paths((root / ".github" / "CODEOWNERS").read_text())
    failures.extend(f".github/CODEOWNERS missing protected path: {path}" for path in codeowners_missing)

    pr_template_missing = missing_required_phrases(
        (root / ".github" / "pull_request_template.md").read_text(),
        REQUIRED_PR_TEMPLATE_PHRASES,
    )
    failures.extend(
        f".github/pull_request_template.md missing phrase: {phrase!r}"
        for phrase in pr_template_missing
    )

    failures.extend(governance_doc_failures(root))
    return failures


def main() -> int:
    failures = validate()
    if failures:
        raise SystemExit("\n".join(failures))
    print("repository governance controls check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
