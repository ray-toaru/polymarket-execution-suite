import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "polymarket-execution-engine" / "scripts" / "check_release_hygiene.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_release_hygiene", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseHygieneTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_zip_hygiene_rejects_local_env_layers_but_allows_examples(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            archive = Path(tmp_name) / "artifact.zip"
            with ZipFile(archive, "w") as zf:
                zf.writestr("release-root/.env.validation", "PMX_TEST_DATABASE_URL=postgres://example\n")
                zf.writestr("release-root/.env.runtime", "PMX_ACTIVE_PROFILE=acct\n")
                zf.writestr("release-root/.env.runtime.secrets", "POLY_API_SECRET=example\n")
                zf.writestr("release-root/.env.validation.example", "PMX_TEST_DATABASE_URL=\n")

            _, problems = self.module.scan_zip(archive)

        joined = "\n".join(problems)
        self.assertIn("release-root/.env.validation", joined)
        self.assertIn("release-root/.env.runtime", joined)
        self.assertIn("release-root/.env.runtime.secrets", joined)
        self.assertNotIn("release-root/.env.validation.example", joined)

    def test_dev_worktree_hygiene_allows_ignored_local_env_layers(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            for name in [".env", ".env.validation", ".env.runtime", ".env.runtime.secrets"]:
                (root / name).write_text("local-only\n")

            _, problems = self.module.scan_directory(root, dev_worktree=True)

        self.assertEqual(problems, [])

    def test_directory_hygiene_rejects_local_env_layers_outside_dev_mode(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            for name in [".env.validation", ".env.runtime.secrets"]:
                (root / name).write_text("local-only\n")

            _, problems = self.module.scan_directory(root, dev_worktree=False)

        self.assertEqual(set(problems), {".env.validation", ".env.runtime.secrets"})


if __name__ == "__main__":
    unittest.main()
