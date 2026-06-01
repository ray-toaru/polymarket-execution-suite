import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_reviewed_go_canary_closeout.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_reviewed_go_canary_closeout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunReviewedGoCanaryCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def package_fixture(self, tmp: Path) -> tuple[Path, Path]:
        package = tmp / "reviewed-go"
        package.mkdir()
        env_file = tmp / ".env.runtime"
        env_file.write_text(
            "\n".join(
                [
                    "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                    "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                    "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                    "POLYMARKET_PRIVATE_KEY=0xabc123",
                    "POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                    "POLY_API_SECRET=api-secret",
                    "POLY_API_PASSPHRASE=api-pass",
                    "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                    "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                    "",
                ]
            )
        )
        self.write_json(package / "approval.json", {"account_id": "acct-canary"})
        self.write_json(
            package / "candidate-market.json",
            {"market_id": "0xmarket", "token_id": "12345"},
        )
        self.write_json(package / "release-decision.json", {"decision": "go"})
        self.write_json(package / "runtime-truth.json", {"status": "reviewed_runtime_truth_candidate"})
        return package, env_file

    def test_build_workflow_plan_uses_funder_as_default_account_address(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            package, env_file = self.package_fixture(Path(tmp_name))
            plan = self.module.build_workflow_plan(
                package_dir=package,
                env_file=env_file,
                secrets_env_file=None,
                release_zip=None,
                daily_used_notional_usd="0",
                account_address=None,
                include_live_config_overrides=False,
            )
        self.assertEqual(plan["account_address"], "0x00000000000000000000000000000000000000b0")
        self.assertEqual(plan["steps"][2]["stdout_path"], str(package / "order-status-query.json"))
        self.assertIn("__REMOTE_ORDER_ID__", plan["steps"][2]["command"])
        self.assertIn("run_reviewed_go_canary_armed.py", str(plan["steps"][1]["command"][1]))
        self.assertTrue(plan["uses_dedicated_armed_wrapper"])

    def test_build_workflow_plan_requires_account_address_without_funder(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            package, env_file = self.package_fixture(Path(tmp_name))
            env_file.write_text(env_file.read_text().replace("PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0\n", ""))
            with self.assertRaisesRegex(SystemExit, "account address is required"):
                self.module.build_workflow_plan(
                    package_dir=package,
                    env_file=env_file,
                    secrets_env_file=None,
                    release_zip=None,
                    daily_used_notional_usd="0",
                    account_address=None,
                    include_live_config_overrides=False,
                )

    def test_build_workflow_plan_always_uses_dedicated_armed_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            package, env_file = self.package_fixture(Path(tmp_name))
            plan = self.module.build_workflow_plan(
                package_dir=package,
                env_file=env_file,
                secrets_env_file=None,
                release_zip=None,
                daily_used_notional_usd="0",
                account_address=None,
                include_live_config_overrides=True,
            )
        self.assertIn("run_reviewed_go_canary_armed.py", str(plan["steps"][1]["command"][1]))
        self.assertNotIn("--include-live-config-overrides", plan["steps"][1]["command"])
        self.assertFalse(plan["includes_live_config_overrides"])
        self.assertTrue(plan["uses_dedicated_armed_wrapper"])

    def test_execute_workflow_substitutes_remote_order_and_writes_readback_paths(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            package, env_file = self.package_fixture(Path(tmp_name))
            self.write_json(package / "post-canary-report.json", {"remote_order_id": "order-1"})
            plan = self.module.build_workflow_plan(
                package_dir=package,
                env_file=env_file,
                secrets_env_file=None,
                release_zip=None,
                daily_used_notional_usd="0",
                account_address=None,
                include_live_config_overrides=False,
            )

            class Completed:
                def __init__(self, returncode=0, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            calls = []

            def fake_run(command, cwd, text, env, check=False, stdout=None):
                calls.append(command)
                if stdout is not None:
                    stdout.write("{}\n")
                return Completed(returncode=0, stdout='{"remote_order_id":"order-1"}')

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                result = self.module.execute_workflow(plan)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["remote_order_id"], "order-1")
            self.assertEqual(calls[2][-1], "order-1")
            self.assertEqual(calls[3][-1], "order-1")
            self.assertTrue((package / "order-status-query.json").exists())
            self.assertTrue((package / "trade-fill-query.json").exists())
            self.assertTrue((package / "account-activity-readback.json").exists())


if __name__ == "__main__":
    unittest.main()
