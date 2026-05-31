import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "check_active_profile_consistency.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("check_active_profile_consistency", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ActiveProfileConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def valid_env(self) -> str:
        return "\n".join(
            [
                "# Active local account profile label.",
                "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                "# Active local account id bound to the selected profile.",
                "PMX_ACTIVE_ACCOUNT_ID=acct_b",
                "# Local non-secret profile reference.",
                "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                "# Generic runtime signer material.",
                "POLYMARKET_PRIVATE_KEY=0xabc123",
                "# Generic runtime L2 API key.",
                "POLY_API_KEY=api-key",
                "# Generic runtime L2 API secret.",
                "POLY_API_SECRET=api-secret",
                "# Generic runtime L2 API passphrase.",
                "POLY_API_PASSPHRASE=api-pass",
                "# Generic runtime CLOB funder.",
                "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                "# Generic runtime signature type.",
                "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                "",
            ]
        )

    def valid_identity_env(self) -> str:
        return "\n".join(
            [
                "# Active local account profile label.",
                "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                "# Active local account id bound to the selected profile.",
                "PMX_ACTIVE_ACCOUNT_ID=acct_b",
                "# Local non-secret profile reference.",
                "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                "",
            ]
        )

    def valid_secrets_env(self) -> str:
        return "\n".join(
            [
                "# Generic runtime signer material.",
                "POLYMARKET_PRIVATE_KEY=0xabc123",
                "# Generic runtime L2 API key.",
                "POLY_API_KEY=api-key",
                "# Generic runtime L2 API secret.",
                "POLY_API_SECRET=api-secret",
                "# Generic runtime L2 API passphrase.",
                "POLY_API_PASSPHRASE=api-pass",
                "# Generic runtime CLOB funder.",
                "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                "# Generic runtime signature type.",
                "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                "",
            ]
        )

    def test_check_accepts_consistent_runtime_env(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(self.valid_env())
            report = self.module.evaluate_env_file(env_file, expected_account_id="acct_b")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["active_account_profile"], "acct_b")
        self.assertEqual(report["active_account_id"], "acct_b")

    def test_check_normalizes_deposit_wallet_numeric_alias(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(self.valid_env().replace("PMX_CLOB_SIGNATURE_TYPE=POLY_1271", "PMX_CLOB_SIGNATURE_TYPE=3"))
            report = self.module.evaluate_env_file(env_file, expected_account_id="acct_b")
        self.assertEqual(report["signature_type"], "POLY_1271")

    def test_check_rejects_runtime_file_with_profile_source_inventory(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(
                self.valid_env()
                + "# Private profile inventory should not appear in runtime env.\n"
                + "PMX_PROFILE_ACCT_B_POLY_API_SECRET=secret\n"
            )
            with self.assertRaisesRegex(SystemExit, "must not contain profile source variables"):
                self.module.evaluate_env_file(env_file, expected_account_id="acct_b")

    def test_check_rejects_account_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(self.valid_env())
            with self.assertRaisesRegex(SystemExit, "active account id mismatch"):
                self.module.evaluate_env_file(env_file, expected_account_id="acct-a")

    def test_check_rejects_poly1271_without_funder(self):
        text = self.valid_env().replace(
            "# Generic runtime CLOB funder.\nPMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0\n",
            "",
        )
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(text)
            with self.assertRaisesRegex(SystemExit, "PMX_CLOB_FUNDER is required"):
                self.module.evaluate_env_file(env_file, expected_account_id="acct_b")

    def test_check_accepts_identity_env_with_companion_secrets_file(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(self.valid_identity_env())
            env_file.with_name(".env.runtime.secrets").write_text(self.valid_secrets_env())
            report = self.module.evaluate_env_file(env_file, expected_account_id="acct_b")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["active_account_id"], "acct_b")


if __name__ == "__main__":
    unittest.main()
