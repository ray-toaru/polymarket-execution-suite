import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_live_submit_promotion_suite.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_live_submit_promotion_suite", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunLiveSubmitPromotionSuiteTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_build_suite_plan_lists_expected_first_drill(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            plan = self.module.build_suite_plan(output_dir=tmp / "promotion-output")
        self.assertEqual(plan["suite"], "live_submit_promotion_evidence")
        self.assertEqual(plan["drills"][0]["name"], "live_submit_static_guard")
        self.assertTrue(plan["drills"][0]["stdout_path"].endswith("live_submit_static_guard.json"))

    def test_execute_suite_collects_results_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            plan = self.module.build_suite_plan(output_dir=tmp / "promotion-output")

            class Completed:
                def __init__(self, returncode=0):
                    self.returncode = returncode

            calls = []

            def fake_run(command, cwd, text, stdout=None, check=False):
                calls.append(command)
                if stdout is not None:
                    stdout.write(json.dumps({"status": "pass"}) + "\n")
                return Completed(returncode=0)

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                result = self.module.execute_suite(plan)

            self.assertEqual(result["status"], "pass")
            self.assertEqual(len(result["results"]), len(self.module.PROMOTION_DRILLS))
            self.assertTrue(calls[0][-1].endswith("check_live_submit_guard.py"))
            self.assertTrue((tmp / "promotion-output" / "live_submit_static_guard.json").exists())

    def test_execute_suite_marks_fail_when_any_drill_fails(self):
        plan = self.module.build_suite_plan(output_dir=None)

        class Completed:
            def __init__(self, returncode=0):
                self.returncode = returncode

        returns = [Completed(0), Completed(1)] + [Completed(0)] * (len(self.module.PROMOTION_DRILLS) - 2)

        with patch.object(self.module.subprocess, "run", side_effect=returns):
            result = self.module.execute_suite(plan)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["results"][1]["returncode"], 1)


if __name__ == "__main__":
    unittest.main()
