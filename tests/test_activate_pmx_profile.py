import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "activate_pmx_profile.py"


def load_module():
    spec = importlib.util.spec_from_file_location("activate_pmx_profile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ActivatePmxProfileTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def source_fixture(self):
        return {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct-b",
            "PMX_PROFILE_ACCT_B_PROFILE_REF": "local-profile://acct-b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
            "PMX_PROFILE_ACCT_B_POLY_API_KEY": "api-key",
            "PMX_PROFILE_ACCT_B_POLY_API_SECRET": "api-secret",
            "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE": "api-pass",
            "PMX_PROFILE_ACCT_B_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE": "POLY_1271",
        }

    def test_activate_profile_builds_generic_runtime_env(self):
        activated = self.module.activate_profile("acct_b", self.source_fixture())
        self.assertEqual(activated["PMX_ACTIVE_ACCOUNT_PROFILE"], "acct_b")
        self.assertEqual(activated["PMX_ACTIVE_ACCOUNT_ID"], "acct-b")
        self.assertEqual(activated["PMX_ACTIVE_PROFILE_REF"], "local-profile://acct-b")
        self.assertEqual(activated["POLYMARKET_PRIVATE_KEY"], "0xabc123")
        self.assertEqual(activated["POLY_API_KEY"], "api-key")
        self.assertEqual(activated["POLY_API_SECRET"], "api-secret")
        self.assertEqual(activated["POLY_API_PASSPHRASE"], "api-pass")
        self.assertEqual(
            activated["PMX_CLOB_FUNDER"],
            "0x00000000000000000000000000000000000000b0",
        )
        self.assertEqual(activated["PMX_CLOB_SIGNATURE_TYPE"], "POLY_1271")

    def test_activate_profile_rejects_invalid_profile_name(self):
        with self.assertRaisesRegex(SystemExit, "profile name must match"):
            self.module.activate_profile("acct-b", self.source_fixture())

    def test_activate_profile_requires_complete_source_contract(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct-b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
        }
        with self.assertRaisesRegex(SystemExit, "missing required profile source variables"):
            self.module.activate_profile("acct_b", source)

    def test_activate_profile_rejects_missing_funder_for_poly1271(self):
        source = self.source_fixture()
        source.pop("PMX_PROFILE_ACCT_B_CLOB_FUNDER")
        with self.assertRaisesRegex(SystemExit, "requires PMX_CLOB_FUNDER"):
            self.module.activate_profile("acct_b", source)

    def test_load_profile_source_defaults_to_file_only(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            source_file = Path(tmp_name) / ".env.profiles"
            source_file.write_text("PMX_PROFILE_ACCT_B_ACCOUNT_ID=file-value\n")
            original = os.environ.get("PMX_PROFILE_ACCT_B_ACCOUNT_ID")
            os.environ["PMX_PROFILE_ACCT_B_ACCOUNT_ID"] = "ambient-value"
            try:
                source = self.module.load_profile_source(source_file)
            finally:
                if original is None:
                    os.environ.pop("PMX_PROFILE_ACCT_B_ACCOUNT_ID", None)
                else:
                    os.environ["PMX_PROFILE_ACCT_B_ACCOUNT_ID"] = original
        self.assertEqual(source["PMX_PROFILE_ACCT_B_ACCOUNT_ID"], "file-value")

    def test_parse_env_file_rejects_duplicate_key(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            source_file = Path(tmp_name) / ".env.profiles"
            source_file.write_text("A=1\nA=2\n")
            with self.assertRaisesRegex(SystemExit, "duplicate env key"):
                self.module.parse_env_file(source_file)

    def test_write_runtime_env_omits_secrets_by_default_and_chmods_0600(self):
        activated = self.module.activate_profile("acct_b", self.source_fixture())
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / ".env.runtime"
            self.module.write_runtime_env(output, activated)
            text = output.read_text()
            mode = stat.S_IMODE(output.stat().st_mode)
        self.assertIn("# Active local account profile label.", text)
        self.assertIn("PMX_ACTIVE_ACCOUNT_PROFILE=acct_b", text)
        self.assertNotIn("PMX_PROFILE_ACCT_B_", text)
        self.assertNotIn("POLYMARKET_PRIVATE_KEY=0xabc123", text)
        self.assertEqual(mode, 0o600)

    def test_write_runtime_env_can_write_secrets_outside_repo(self):
        activated = self.module.activate_profile("acct_b", self.source_fixture())
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / ".env.runtime"
            self.module.write_runtime_env(output, activated, write_secrets=True)
            text = output.read_text()
        self.assertIn("POLYMARKET_PRIVATE_KEY=0xabc123", text)
        self.assertIn("POLY_API_SECRET=api-secret", text)


if __name__ == "__main__":
    unittest.main()
