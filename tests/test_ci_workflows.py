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
    def _compileall_targets(self, workflow_text: str) -> set[str]:
        match = re.search(
            r"python -m compileall -q \\\s*(.*?)\n\n",
            workflow_text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "compileall command block missing from workflow")
        targets = set()
        for line in match.group(1).splitlines():
            value = line.strip().rstrip("\\").strip()
            if value:
                targets.add(value)
        return targets

    def test_root_ci_pins_actions_and_uploads_proof_artifacts(self):
        text = ROOT_CI.read_text()
        data = load_yaml(ROOT_CI)
        triggers = workflow_on(data)
        self.assertIn("pull_request", triggers)
        self.assertIn("push", triggers)
        self.assertEqual(triggers["push"]["tags"], ["v*"])
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
        self.assertIn("jsonschema==4.25.1", (ROOT / "requirements-ci.txt").read_text())
        self.assertEqual(
            self._compileall_targets(text),
            {
                "scripts",
                "tests",
                "hermes-polymarket-executor-adapter/src",
                "hermes-polymarket-executor-adapter/tests",
                "polymarket-execution-engine/scripts",
                "polymarket-execution-engine/validation",
            },
        )

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
        self.assertIn(
            "python -m pip install ruff==0.15.15 mypy==2.1.0 bandit==1.9.4 build==1.4.0",
            text,
        )
        self.assertIn("run: python -m pytest -q tests", text)
        self.assertIn("python -m ruff check src tests", text)
        self.assertIn("python -m mypy src", text)
        self.assertIn("python -m bandit -q -r src", text)

    def test_root_ci_runs_pinned_submodule_gates_locally(self):
        data = load_yaml(ROOT_CI)
        self.assertNotIn("adapter-required-ci", data["jobs"])
        self.assertNotIn("engine-required-ci", data["jobs"])

        rust_steps = data["jobs"]["engine-rust-locked"]["steps"]
        rust_commands = "\n".join(
            str(step.get("run", "")) for step in rust_steps
        )
        self.assertIn("cargo clippy --workspace --all-targets --all-features", rust_commands)
        self.assertIn("pmx-official-sdk-spike/Cargo.toml", rust_commands)
        self.assertIn("pmx-official-sdk-adapter/Cargo.toml", rust_commands)

        postgres = data["jobs"]["engine-postgres"]
        self.assertEqual(postgres["services"]["postgres"]["image"], "postgres:16")
        postgres_commands = "\n".join(
            str(step.get("run", "")) for step in postgres["steps"]
        )
        self.assertIn("migrations/[0-9]*.sql", postgres_commands)
        self.assertIn("http_postgres_e2e", postgres_commands)
        self.assertIn("run_migration_drift_dry_run.py", postgres_commands)

        static_commands = "\n".join(
            str(step.get("run", ""))
            for step in data["jobs"]["integration-static"]["steps"]
        )
        self.assertIn(
            "python -m pip install ruff==0.15.15 mypy==2.1.0 bandit==1.9.4",
            static_commands,
        )
        self.assertIn("python -m ruff check hermes-polymarket-executor-adapter", static_commands)
        self.assertIn("python -m mypy hermes-polymarket-executor-adapter/src", static_commands)
        self.assertIn("python -m bandit -q -r hermes-polymarket-executor-adapter/src", static_commands)

    def test_root_static_ci_provides_pinned_hermes_dependency(self):
        data = load_yaml(ROOT_CI)
        steps = data["jobs"]["integration-static"]["steps"]
        hermes_checkout = next(
            step for step in steps if step["name"] == "Checkout pinned Hermes Agent test dependency"
        )
        self.assertRegex(hermes_checkout["uses"], FULL_SHA_USES)
        self.assertEqual(hermes_checkout["with"]["repository"], "NousResearch/hermes-agent")
        self.assertRegex(hermes_checkout["with"]["ref"], r"^[0-9a-f]{40}$")
        self.assertEqual(hermes_checkout["with"]["path"], "hermes-agent")

        adapter_tests = next(step for step in steps if step["name"] == "Run adapter tests")
        self.assertEqual(adapter_tests["env"]["HERMES_AGENT_ROOT"], "${{ github.workspace }}/hermes-agent")

        compile_step = next(
            step for step in steps if step["name"] == "Compile integration Python sources"
        )
        self.assertEqual(
            compile_step["run"].count("polymarket-execution-engine/validation"),
            1,
        )

    def test_engine_ci_supports_workflow_call(self):
        data = load_yaml(ENGINE_CI)
        self.assertIn("workflow_call", workflow_on(data))


if __name__ == "__main__":
    unittest.main()
