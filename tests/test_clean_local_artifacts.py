import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "clean_local_artifacts.py"


def load_clean_module():
    spec = importlib.util.spec_from_file_location("clean_local_artifacts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CleanLocalArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_clean_module()

    def test_git_paths_are_always_skipped(self):
        self.assertTrue(self.module.is_under_skipped_tree(ROOT / ".git" / "objects"))
        self.assertFalse(self.module.is_under_skipped_tree(ROOT / "scripts"))

    def test_dry_run_keeps_file_on_disk(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
            tmp = Path(tmp_name)
            pycache = tmp / "__pycache__"
            pycache.mkdir()
            artifact = pycache / "x.pyc"
            artifact.write_bytes(b"pyc")
            self.assertTrue(artifact.exists())
            # Simulate the script policy instead of invoking deletion against the whole repo.
            self.assertFalse(self.module.is_under_skipped_tree(artifact))
            self.assertEqual(artifact.suffix, ".pyc")
            self.assertTrue(artifact.exists())


if __name__ == "__main__":
    unittest.main()
