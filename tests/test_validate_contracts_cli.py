from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidateContractsCliTests(unittest.TestCase):
    def test_report_file_contains_machine_readable_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "contracts-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/validate_contracts.py"),
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
        categories = {check["category"] for check in file_report["checks"]}
        self.assertEqual(categories, {"surface", "executor", "governance"})
        self.assertTrue(any(check["id"] == "v23_lifecycle_query_and_hardening" for check in file_report["checks"]))


if __name__ == "__main__":
    unittest.main()
