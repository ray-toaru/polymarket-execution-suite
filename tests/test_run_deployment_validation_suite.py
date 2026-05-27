import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_deployment_validation_suite.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_deployment_validation_suite", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunDeploymentValidationSuiteTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_build_suite_plan_lists_expected_drills(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            plan = self.module.build_suite_plan(
                release_zip=tmp / "artifact.zip",
                output_dir=tmp / "deploy-output",
            )
        self.assertEqual(plan["suite"], "deployment_validation_evidence")
        self.assertEqual(plan["drills"][0]["name"], "production_deployment_preflight")
        self.assertEqual(plan["drills"][1]["name"], "single_host_deployment")
        self.assertTrue(plan["drills"][0]["stdout_path"].endswith("production_deployment_preflight.json"))
        self.assertIn("PMX_RELEASE_ARTIFACT_PATH", plan["env_overrides"])

    def test_execute_suite_collects_results_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            plan = self.module.build_suite_plan(release_zip=None, output_dir=tmp / "deploy-output")

            class Completed:
                def __init__(self, returncode=0):
                    self.returncode = returncode

            calls = []

            def fake_run(command, cwd, text, env, stdout=None, check=False):
                calls.append(command)
                if stdout is not None:
                    stdout.write(json.dumps({"status": "pass"}) + "\n")
                return Completed(returncode=0)

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                result = self.module.execute_suite(plan)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(len(result["results"]), len(self.module.DEPLOYMENT_DRILLS))
            self.assertTrue(calls[1][-1].endswith("run_single_host_deployment_drill.py"))
            self.assertTrue((tmp / "deploy-output" / "single_host_deployment.json").exists())

    def test_execute_suite_marks_fail_when_any_drill_fails(self):
        plan = self.module.build_suite_plan(release_zip=None, output_dir=None)

        class Completed:
            def __init__(self, returncode=0):
                self.returncode = returncode

        returns = [Completed(0), Completed(1)] + [Completed(0)] * (len(self.module.DEPLOYMENT_DRILLS) - 2)

        with patch.object(self.module.subprocess, "run", side_effect=returns):
            result = self.module.execute_suite(plan)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["results"][1]["returncode"], 1)


if __name__ == "__main__":
    unittest.main()
