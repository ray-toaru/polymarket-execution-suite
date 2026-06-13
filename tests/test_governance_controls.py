import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_governance_controls as module


class GovernanceControlsTests(unittest.TestCase):
    def test_external_review_archives_stay_untracked_except_registry_placeholder(self):
        files = [
            "README.md",
            "external_reviews/reviewer-registry/lei.pending.json",
            "external_reviews/lei/final-main-posthoc-review.approved.json",
        ]

        self.assertEqual(
            module.tracked_external_review_violations(files),
            ["external_reviews/lei/final-main-posthoc-review.approved.json"],
        )

    def test_codeowners_must_cover_governance_sensitive_paths(self):
        text = "\n".join(
            f"{path} @owner"
            for path in sorted(module.REQUIRED_CODEOWNER_PATHS - {"/DOC_STATUS.md"})
        )

        self.assertEqual(module.missing_codeowner_paths(text), ["/DOC_STATUS.md"])

    def test_current_repository_governance_controls_pass(self):
        self.assertEqual(module.validate(), [])

    def test_validate_reports_tracked_external_review_archive(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            (root / ".github").mkdir()
            (root / ".github" / "CODEOWNERS").write_text(
                "\n".join(f"{path} @owner" for path in module.REQUIRED_CODEOWNER_PATHS)
            )
            (root / ".github" / "pull_request_template.md").write_text(
                "\n".join(module.REQUIRED_PR_TEMPLATE_PHRASES)
            )
            for relative_path, phrases in module.REQUIRED_GOVERNANCE_PHRASES.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(phrases))

            with mock.patch.object(
                module,
                "git_ls_files",
                return_value=[
                    "external_reviews/reviewer-registry/lei.pending.json",
                    "external_reviews/lei/review.approved.json",
                ],
            ):
                failures = module.validate(root)

        self.assertEqual(
            failures,
            ["external review archive must stay untracked: external_reviews/lei/review.approved.json"],
        )


if __name__ == "__main__":
    unittest.main()
