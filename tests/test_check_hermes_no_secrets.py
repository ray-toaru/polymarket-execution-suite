import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_hermes_no_secrets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_hermes_no_secrets", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CheckHermesNoSecretsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_allowlist_skips_known_doc(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            control = tmp / "adapter"
            control.mkdir()
            (control / "README.md").write_text("POLYMARKET_PRIVATE_KEY\n")
            original_control = self.module.CONTROL
            try:
                self.module.CONTROL = control
                self.assertEqual(self.module.main(), 0)
            finally:
                self.module.CONTROL = original_control

    def test_repo_wide_scan_catches_secret_outside_src(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            control = tmp / "adapter"
            docs = control / "docs"
            docs.mkdir(parents=True)
            (docs / "REVIEW.md").write_text("raw_signed_payload\n")
            original_control = self.module.CONTROL
            try:
                self.module.CONTROL = control
                self.assertEqual(self.module.main(), 1)
            finally:
                self.module.CONTROL = original_control


if __name__ == "__main__":
    unittest.main()
