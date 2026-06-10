import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "run_real_funds_canary_blocked_rehearsal_package.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "run_real_funds_canary_blocked_rehearsal_package", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BlockedRehearsalPackageTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_blocked_rehearsal_uses_dedicated_reviewed_go_armed_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            output_dir = Path(tmp_name)
            (output_dir / "review.json").write_text(
                json.dumps(
                    {
                        "live_submit_allowed": False,
                        "real_funds_canary_authorized": False,
                    }
                )
                + "\n"
            )
            approval = {
                "artifact_sha256": "a" * 64,
                "evidence_manifest_sha256": "b" * 64,
                "market_candidate_sha256": "c" * 64,
                "account_id": "acct-canary",
                "operator_identity_ref": "operator://primary",
                "operator_identity_sha256": "31407192d4cb1a4a59550966b008ad672f660e0621b7e1c656ac10ee71e30a2f",
            }
            (output_dir / "approval.json").write_text(json.dumps(approval) + "\n")
            (output_dir / "release-decision.json").write_text(json.dumps({}) + "\n")
            (output_dir / "candidate-market.json").write_text(json.dumps({"token_id": "123"}) + "\n")

            calls = []

            class Completed:
                def __init__(self, returncode=0, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            def fake_run(command, cwd, text, capture_output, check):
                calls.append((command, cwd))
                if "prepare_real_funds_canary_review.py" in str(command[1]):
                    return Completed(returncode=0, stdout="{}", stderr="")
                return Completed(
                    returncode=1,
                    stdout="",
                    stderr=(
                        "reviewed-go decision invalid: decision must be go; "
                        "status must be reviewed_go"
                    ),
                )

            args = type(
                "Args",
                (),
                {
                    "external_references_file": self.module.EXTERNAL_REFERENCES_EXAMPLE,
                    "root_ci_run_id": "root",
                    "hermes_ci_run_id": "hermes",
                    "execution_engine_ci_run_id": "engine",
                    "credentialed_sdk_run_id": "sdk",
                    "artifact_sha256": None,
                    "evidence_manifest_sha256": None,
                    "workspace_evidence_manifest_sha256": None,
                    "archived_evidence_manifest_sha256": None,
                    "candidate_market_file": None,
                    "idempotency_key": "idem-1",
                    "execution_id": "exec-1",
                    "plan_hash": "plan-1",
                },
            )()

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                failures, code = self.module.run_rehearsal(output_dir, args)

            self.assertEqual(code, 1)
            self.assertEqual(failures, [])
            wrapper_command, wrapper_cwd = calls[1]
            self.assertEqual(wrapper_command[0], self.module.sys.executable)
            self.assertIn("run_reviewed_go_canary_armed.py", str(wrapper_command[1]))
            self.assertIn("--run", wrapper_command)
            self.assertEqual(wrapper_cwd, self.module.INTEGRATION_ROOT)

    def test_main_reports_no_live_config_overrides(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            output_dir = Path(tmp_name)

            with patch.object(self.module, "run_rehearsal", return_value=([], 1)):
                with patch.object(self.module.sys, "argv", ["blocked-rehearsal", "--output-dir", str(output_dir)]):
                    with patch("builtins.print"):
                        exit_code = self.module.main()

            self.assertEqual(exit_code, 0)
            report = json.loads((output_dir / "blocked-rehearsal.report.json").read_text())
            self.assertFalse(report["includes_live_config_overrides"])
            self.assertTrue(report["armed_requested"])


if __name__ == "__main__":
    unittest.main()
