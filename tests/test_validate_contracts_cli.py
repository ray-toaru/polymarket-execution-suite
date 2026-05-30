from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_contracts.py"


def load_module():
    script_dir = str(SCRIPT.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("validate_contracts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["validate_contracts"] = module
    spec.loader.exec_module(module)
    return module


class ValidateContractsCliTests(unittest.TestCase):
    def test_report_file_contains_machine_readable_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "contracts-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--report-file",
                    str(report_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            stdout_report = json.loads(result.stdout)
            file_report = json.loads(report_path.read_text())

        self.assertEqual(stdout_report["status"], "ok")
        self.assertEqual(file_report["status"], "ok")
        self.assertEqual(file_report["check_count"], len(file_report["checks"]))
        self.assertGreater(file_report["check_count"], 10)
        self.assertIn("structured", file_report["proof_mode_counts"])
        categories = {check["category"] for check in file_report["checks"]}
        self.assertEqual(categories, {"surface", "executor", "governance"})
        self.assertTrue(any(check["id"] == "v23_lifecycle_query_and_hardening" for check in file_report["checks"]))

    def test_build_report_persists_failed_check_details(self) -> None:
        module = load_module()

        def ok_validator(spec):
            return None

        def fail_validator(spec):
            raise SystemExit("contract validation failed: synthetic failure")

        validators = [
            module.ValidatorSpec("ok_check", "surface", "structured", True, ok_validator),
            module.ValidatorSpec("bad_check", "executor", "token", True, fail_validator),
        ]
        report = module.build_report({"paths": {}, "components": {"schemas": {}}}, validators=validators)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["failed_check_count"], 1)
        self.assertEqual(report["failed_check_ids"], ["bad_check"])
        self.assertEqual(report["proof_mode_counts"], {"structured": 1, "token": 1})
        self.assertEqual(report["checks"][0]["status"], "pass")
        self.assertEqual(report["checks"][0]["proof_mode"], "structured")
        self.assertEqual(report["checks"][1]["status"], "fail")
        self.assertEqual(report["checks"][1]["proof_mode"], "token")
        self.assertEqual(report["checks"][1]["error_type"], "SystemExit")
        self.assertIn("synthetic failure", report["checks"][1]["error"])

    def test_cli_writes_report_before_exiting_non_zero(self) -> None:
        module = load_module()
        original_build_report = module.build_report

        def fake_build_report(spec, validators=None):
            report = original_build_report(spec, validators=[])
            report["status"] = "fail"
            report["failed_check_count"] = 1
            report["failed_check_ids"] = ["synthetic_failure"]
            report["checks"] = [
                {
                    "id": "synthetic_failure",
                    "category": "surface",
                    "status": "fail",
                    "error_type": "SystemExit",
                    "error": "contract validation failed: synthetic failure",
                }
            ]
            report["check_count"] = 1
            return report

        module.build_report = fake_build_report

        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "contracts-report.json"
            with self.assertRaises(SystemExit) as ctx:
                module.main(["--report-file", str(report_path)])
            report = json.loads(report_path.read_text())

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["failed_check_ids"], ["synthetic_failure"])


if __name__ == "__main__":
    unittest.main()
