import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "activate_pmx_profile.py"
RUNTIME_EXAMPLE = ROOT / "polymarket-execution-engine" / ".env.runtime.example"


def load_module():
    spec = importlib.util.spec_from_file_location("activate_pmx_profile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ActivatePmxProfileTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_activate_profile_builds_generic_runtime_env(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct_b",
            "PMX_PROFILE_ACCT_B_PROFILE_REF": "local-profile://acct_b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
            "PMX_PROFILE_ACCT_B_POLY_API_KEY": "api-key",
            "PMX_PROFILE_ACCT_B_POLY_API_SECRET": "api-secret",
            "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE": "api-pass",
            "PMX_PROFILE_ACCT_B_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE": "POLY_1271",
        }
        activated = self.module.activate_profile("acct_b", source)
        self.assertEqual(activated["PMX_ACTIVE_ACCOUNT_PROFILE"], "acct_b")
        self.assertEqual(activated["PMX_ACTIVE_ACCOUNT_ID"], "acct_b")
        self.assertEqual(activated["PMX_ACTIVE_PROFILE_REF"], "local-profile://acct_b")
        self.assertEqual(activated["POLYMARKET_PRIVATE_KEY"], "0xabc123")
        self.assertEqual(activated["POLY_API_KEY"], "api-key")
        self.assertEqual(activated["POLY_API_SECRET"], "api-secret")
        self.assertEqual(activated["POLY_API_PASSPHRASE"], "api-pass")
        self.assertEqual(
            activated["PMX_CLOB_FUNDER"],
            "0x00000000000000000000000000000000000000b0",
        )
        self.assertEqual(activated["PMX_CLOB_SIGNATURE_TYPE"], "POLY_1271")

    def test_activate_profile_normalizes_deposit_wallet_numeric_alias(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct_b",
            "PMX_PROFILE_ACCT_B_PROFILE_REF": "local-profile://acct_b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
            "PMX_PROFILE_ACCT_B_POLY_API_KEY": "api-key",
            "PMX_PROFILE_ACCT_B_POLY_API_SECRET": "api-secret",
            "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE": "api-pass",
            "PMX_PROFILE_ACCT_B_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE": "3",
        }
        activated = self.module.activate_profile("acct_b", source)
        self.assertEqual(activated["PMX_CLOB_SIGNATURE_TYPE"], "POLY_1271")

    def test_activate_profile_requires_complete_source_contract(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct_b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
        }
        with self.assertRaisesRegex(SystemExit, "missing required profile source variables"):
            self.module.activate_profile("acct_b", source)

    def test_activate_profile_rejects_missing_funder_for_poly1271(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct_b",
            "PMX_PROFILE_ACCT_B_PROFILE_REF": "local-profile://acct_b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
            "PMX_PROFILE_ACCT_B_POLY_API_KEY": "api-key",
            "PMX_PROFILE_ACCT_B_POLY_API_SECRET": "api-secret",
            "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE": "api-pass",
            "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE": "POLY_1271",
        }
        with self.assertRaisesRegex(SystemExit, "requires PMX_CLOB_FUNDER"):
            self.module.activate_profile("acct_b", source)

    def test_write_runtime_env_contains_comments_and_no_profile_source_vars(self):
        activated = {
            "PMX_ACTIVE_ACCOUNT_PROFILE": "acct_b",
            "PMX_ACTIVE_ACCOUNT_ID": "acct_b",
            "PMX_ACTIVE_PROFILE_REF": "local-profile://acct_b",
            "POLYMARKET_PRIVATE_KEY": "0xabc123",
            "POLY_API_KEY": "api-key",
            "POLY_API_SECRET": "api-secret",
            "POLY_API_PASSPHRASE": "api-pass",
            "PMX_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_CLOB_SIGNATURE_TYPE": "POLY_1271",
        }
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / ".env.runtime"
            self.module.write_runtime_env(output, activated)
            text = output.read_text()
        self.assertIn("# Active local account profile label.", text)
        self.assertIn("PMX_ACTIVE_ACCOUNT_PROFILE=acct_b", text)
        self.assertNotIn("PMX_PROFILE_ACCT_B_", text)

    def test_runtime_example_matches_generated_runtime_keys(self):
        activated = {
            "PMX_ACTIVE_ACCOUNT_PROFILE": "acct_b",
            "PMX_ACTIVE_ACCOUNT_ID": "acct_b",
            "PMX_ACTIVE_PROFILE_REF": "local-profile://acct_b",
            "POLYMARKET_PRIVATE_KEY": "0xabc123",
            "POLY_API_KEY": "api-key",
            "POLY_API_SECRET": "api-secret",
            "POLY_API_PASSPHRASE": "api-pass",
            "PMX_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_CLOB_SIGNATURE_TYPE": "POLY_1271",
        }
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / ".env.runtime"
            self.module.write_runtime_env(output, activated)
            generated_keys = {
                line.split("=", 1)[0]
                for line in output.read_text().splitlines()
                if line and not line.startswith("#")
            }
        example_keys = {
            line.split("=", 1)[0]
            for line in RUNTIME_EXAMPLE.read_text().splitlines()
            if line and not line.startswith("#")
        }
        self.assertEqual(example_keys, generated_keys)


if __name__ == "__main__":
    unittest.main()
