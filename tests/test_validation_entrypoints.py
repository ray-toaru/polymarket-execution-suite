import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidationEntrypointTests(unittest.TestCase):
    def test_makefile_exposes_recommended_local_entrypoints(self):
        makefile = ROOT / "Makefile"
        self.assertTrue(makefile.exists())
        text = makefile.read_text()
        lines = text.splitlines()
        for target in ["check-local", "check-hermes", "check-package", "check-current-gates", "check-shell", "clean-local"]:
            self.assertIn(f"{target}:", lines)
            self.assertIn(target, next(line for line in lines if line.startswith(".PHONY:")))

    def test_shellcheck_entrypoint_is_optional_and_non_authorizing(self):
        makefile = ROOT / "Makefile"
        text = makefile.read_text()
        self.assertIn("command -v shellcheck", text)
        self.assertIn("shellcheck not installed; skipping", text)
        forbidden = [
            "package_release.py",
            "git push",
            "gh release",
            "run_current_gates.sh",
            "run_reviewed_go_canary_armed.py",
        ]
        target_body = text.split("check-shell:", 1)[1].split("\n\n", 1)[0]
        for token in forbidden:
            self.assertNotIn(token, target_body)

    def test_readme_points_to_unified_validation_entrypoints(self):
        text = (ROOT / "README.md").read_text()
        self.assertIn("make check-local", text)
        self.assertIn("make check-shell", text)
        self.assertIn("make check-package", text)
        self.assertIn("make check-current-gates", text)
        normalized = " ".join(text.split())
        self.assertIn("does not refresh release artifacts", normalized)


if __name__ == "__main__":
    unittest.main()
