import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "activate_pmx_profile.py"
RUNTIME_EXAMPLE = ROOT / "polymarket-execution-engine" / ".env.runtime.example"
RUNTIME_SECRETS_EXAMPLE = (
    ROOT / "polymarket-execution-engine" / ".env.runtime.secrets.example"
)


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

    def test_activate_profile_does_not_emit_funder_for_eoa_profile(self):
        source = {
            "PMX_PROFILE_ACCT_B_ACCOUNT_ID": "acct_b",
            "PMX_PROFILE_ACCT_B_PROFILE_REF": "local-profile://acct_b",
            "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY": "0xabc123",
            "PMX_PROFILE_ACCT_B_POLY_API_KEY": "api-key",
            "PMX_PROFILE_ACCT_B_POLY_API_SECRET": "api-secret",
            "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE": "api-pass",
            "PMX_PROFILE_ACCT_B_CLOB_FUNDER": "0x00000000000000000000000000000000000000b0",
            "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE": "EOA",
        }
        activated = self.module.activate_profile("acct_b", source)
        self.assertNotIn("PMX_CLOB_FUNDER", activated)

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
            self.module.write_runtime_env(output, activated, write_secrets=True)
            text = output.read_text()
        self.assertIn("# Active local account profile label.", text)
        self.assertIn("PMX_ACTIVE_ACCOUNT_PROFILE=acct_b", text)
        self.assertIn("Companion secrets file: .env.runtime.secrets", text)
        self.assertNotIn("PMX_PROFILE_ACCT_B_", text)
        self.assertNotIn("POLYMARKET_PRIVATE_KEY=", text)

    def test_runtime_examples_match_generated_runtime_keys(self):
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
            self.module.write_runtime_env(output, activated, write_secrets=True)
            generated_identity_keys = {
                line.split("=", 1)[0]
                for line in output.read_text().splitlines()
                if line and not line.startswith("#")
            }
            secrets_output = self.module.runtime_secrets_output_path(output)
            generated_secret_keys = {
                line.split("=", 1)[0]
                for line in secrets_output.read_text().splitlines()
                if line and not line.startswith("#")
            }
        identity_example_keys = {
            line.split("=", 1)[0]
            for line in RUNTIME_EXAMPLE.read_text().splitlines()
            if line and not line.startswith("#")
        }
        secrets_example_keys = {
            line.split("=", 1)[0]
            for line in RUNTIME_SECRETS_EXAMPLE.read_text().splitlines()
            if line and not line.startswith("#")
        }
        self.assertEqual(identity_example_keys, generated_identity_keys)
        self.assertEqual(secrets_example_keys, generated_secret_keys)

    def test_write_runtime_env_sets_owner_only_permissions(self):
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
            self.module.write_runtime_env(output, activated, write_secrets=True)
            mode = stat.S_IMODE(output.stat().st_mode)
            secrets_mode = stat.S_IMODE(
                self.module.runtime_secrets_output_path(output).stat().st_mode
            )
        self.assertEqual(mode, stat.S_IRUSR | stat.S_IWUSR)
        self.assertEqual(secrets_mode, stat.S_IRUSR | stat.S_IWUSR)

    def test_write_runtime_env_omits_secret_material_without_explicit_opt_in(self):
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
            self.module.write_runtime_env(output, activated, write_secrets=False)
            text = output.read_text()
        self.assertIn("PMX_ACTIVE_ACCOUNT_PROFILE=acct_b", text)
        self.assertNotIn("POLYMARKET_PRIVATE_KEY=", text)
        self.assertNotIn("POLY_API_SECRET=", text)
        self.assertIn("Secret-bearing runtime fields intentionally omitted.", text)

    def test_write_runtime_env_creates_companion_secrets_file_when_opted_in(self):
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
            self.module.write_runtime_env(output, activated, write_secrets=True)
            secrets_output = self.module.runtime_secrets_output_path(output)
            self.assertTrue(secrets_output.is_file())
            secrets_text = secrets_output.read_text()
        self.assertIn("POLYMARKET_PRIVATE_KEY=0xabc123", secrets_text)
        self.assertIn("POLY_API_SECRET=api-secret", secrets_text)

    def test_parse_env_file_preserves_unquoted_value_spacing(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env"
            env_file.write_text('KEY=value with trailing spaces   \nQUOTED=" value with edges "\n')
            values = self.module.parse_env_file(env_file)
        self.assertEqual(values["KEY"], "value with trailing spaces   ")
        self.assertEqual(values["QUOTED"], " value with edges ")

    def test_parse_env_file_rejects_unsupported_shell_syntax(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env"
            env_file.write_text("KEY=${HOME}\n")
            with self.assertRaisesRegex(SystemExit, "unsupported shell-style env value"):
                self.module.parse_env_file(env_file)

    def test_main_does_not_emit_account_identity_in_json(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            source = tmp / ".env.profiles"
            output = tmp / ".env.runtime"
            source.write_text(
                "\n".join(
                    [
                        "PMX_PROFILE_ACCT_B_ACCOUNT_ID=acct_b",
                        "PMX_PROFILE_ACCT_B_PROFILE_REF=local-profile://acct_b",
                        "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY=0xabc123",
                        "PMX_PROFILE_ACCT_B_POLY_API_KEY=api-key",
                        "PMX_PROFILE_ACCT_B_POLY_API_SECRET=api-secret",
                        "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE=api-pass",
                        "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE=EOA",
                        "",
                    ]
                )
            )
            saved_argv = os.sys.argv
            try:
                os.sys.argv = [
                    "activate_pmx_profile.py",
                    "--profile",
                    "acct_b",
                    "--source-env-file",
                    str(source),
                    "--output",
                    str(output),
                ]
                with tempfile.TemporaryFile(mode="w+") as stdout:
                    saved_stdout = os.sys.stdout
                    os.sys.stdout = stdout
                    try:
                        self.module.main()
                    finally:
                        os.sys.stdout = saved_stdout
                    stdout.seek(0)
                    payload = json.loads(stdout.read())
            finally:
                os.sys.argv = saved_argv
        self.assertNotIn("account_id", payload)
        self.assertNotIn("profile_ref", payload)

    def test_verify_runtime_outputs_rejects_profile_inventory_text(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            output = Path(tmp_name) / ".env.runtime"
            output.write_text(
                "\n".join(
                    [
                        "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                        "PMX_ACTIVE_ACCOUNT_ID=acct_b",
                        "PMX_ACTIVE_PROFILE_REF=local-profile://PMX_PROFILE_shadow",
                        "",
                    ]
                )
            )
            with self.assertRaisesRegex(SystemExit, "forbidden runtime text"):
                self.module.verify_runtime_outputs(output, write_secrets=False)


if __name__ == "__main__":
    unittest.main()
