import re
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROOT_CI = ROOT / ".github" / "workflows" / "ci.yml"
ADAPTER_CI = ROOT / "hermes-polymarket-executor-adapter" / ".github" / "workflows" / "ci.yml"
ENGINE_CI = ROOT / "polymarket-execution-engine" / ".github" / "workflows" / "ci.yml"

FULL_SHA_USES = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        text=True,
    ).strip()


def workflow_on(data):
    return data.get("on", data.get(True, {}))


class CiWorkflowTests(unittest.TestCase):
    def test_root_ci_pins_actions_and_uploads_proof_artifacts(self):
        text = ROOT_CI.read_text()
        data = load_yaml(ROOT_CI)
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertEqual(data["permissions"]["actions"], "write")

        uses_values = []
        for job in data["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    uses_values.append(step["uses"])
        for uses in uses_values:
            self.assertRegex(uses, FULL_SHA_USES)

        self.assertIn("python -m pip install --upgrade pip==25.3", text)
        self.assertIn("actions/upload-artifact@", text)
        self.assertIn("integration-proof-artifacts", text)
        self.assertIn("check_v28_production_live_candidate.py --require-ready", text)
        self.assertIn("cargo test --workspace --exclude pmx-api --locked", text)
        self.assertIn("PyYAML==6.0.3", (ROOT / "requirements-ci.txt").read_text())
        self.assertIn("hermes-polymarket-executor-adapter/tests", text)
        self.assertIn("polymarket-execution-engine/scripts", text)

    def test_adapter_ci_pins_actions_and_pip(self):
        text = ADAPTER_CI.read_text()
        data = load_yaml(ADAPTER_CI)
        self.assertIn("workflow_call", workflow_on(data))
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertEqual(data["permissions"]["actions"], "write")

        uses_values = []
        for step in data["jobs"]["python"].get("steps", []):
            if "uses" in step:
                uses_values.append(step["uses"])
        for uses in uses_values:
            self.assertRegex(uses, FULL_SHA_USES)

        self.assertIn("python -m pip install --upgrade pip==25.3", text)
        self.assertIn('"3.12"', text)

    def test_root_ci_references_current_submodule_workflows(self):
        data = load_yaml(ROOT_CI)
        adapter_sha = git_head(ROOT / "hermes-polymarket-executor-adapter")
        engine_sha = git_head(ROOT / "polymarket-execution-engine")
        self.assertEqual(
            data["jobs"]["adapter-required-ci"]["uses"],
            f"ray-toaru/hermes-polymarket-executor-adapter/.github/workflows/ci.yml@{adapter_sha}",
        )
        self.assertEqual(
            data["jobs"]["engine-required-ci"]["uses"],
            f"ray-toaru/polymarket-execution-engine/.github/workflows/ci.yml@{engine_sha}",
        )

    def test_engine_ci_supports_workflow_call(self):
        data = load_yaml(ENGINE_CI)
        self.assertIn("workflow_call", workflow_on(data))


if __name__ == "__main__":
    unittest.main()
