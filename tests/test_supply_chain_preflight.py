import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_supply_chain_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_supply_chain_preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SupplyChainPreflightTests(unittest.TestCase):
    def test_report_skips_cleanly_when_optional_tools_are_missing(self):
        module = load_module()
        with patch.object(module.shutil, "which", return_value=None):
            report = module.build_report()

        self.assertEqual(report["status"], "skipped")
        self.assertFalse(report["remote_side_effects"])
        self.assertFalse(report["package_refresh"])
        self.assertFalse(report["release_posture_changed"])
        self.assertEqual(report["available_tools"], [])
        self.assertGreaterEqual(set(report["missing_optional_tools"]), {"syft", "cargo-deny", "cargo-about"})

    def test_report_is_advisory_when_tools_are_available(self):
        module = load_module()

        def fake_which(name):
            return f"/usr/bin/{name}" if name in {"syft", "cargo-deny"} else None

        with patch.object(module.shutil, "which", side_effect=fake_which):
            report = module.build_report()

        self.assertEqual(report["status"], "available")
        self.assertEqual(
            report["available_tools"],
            [
                {"name": "syft", "path": "/usr/bin/syft"},
                {"name": "cargo-deny", "path": "/usr/bin/cargo-deny"},
            ],
        )
        self.assertFalse(report["remote_side_effects"])
        self.assertFalse(report["package_refresh"])
        self.assertFalse(report["release_posture_changed"])

    def test_report_has_stable_schema_metadata(self):
        module = load_module()
        with patch.object(module.shutil, "which", return_value=None):
            report = module.build_report()

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["optional_tools"], module.OPTIONAL_TOOLS)

    def test_main_writes_optional_json_output(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / "supply-chain-preflight.json"
            stdout = io.StringIO()
            with patch.object(module.shutil, "which", return_value=None):
                with contextlib.redirect_stdout(stdout):
                    rc = module.main(["--output", str(output)])

            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            written = json.loads(output.read_text())
            printed = json.loads(stdout.getvalue())
            self.assertEqual(written, printed)
            self.assertEqual(written["status"], "skipped")
            self.assertFalse(written["remote_side_effects"])
            self.assertFalse(written["package_refresh"])
            self.assertFalse(written["release_posture_changed"])


if __name__ == "__main__":
    unittest.main()
