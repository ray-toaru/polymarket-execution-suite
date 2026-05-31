from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLES = [
    ".env.example",
    "hermes-polymarket-executor-adapter/.env.example",
    "polymarket-execution-engine/.env.example",
    "polymarket-execution-engine/.env.profiles.example",
    "polymarket-execution-engine/.env.runtime.example",
    "polymarket-execution-engine/.env.runtime.secrets.example",
    "polymarket-execution-engine/deploy/single-host/env/pmx-api.env.example",
    "polymarket-execution-engine/deploy/single-host/env/pmx-real-funds-canary.env.example",
]


class EnvExampleTests(unittest.TestCase):
    def test_env_examples_have_comments_for_each_assignment(self):
        for rel in ENV_EXAMPLES:
            with self.subTest(path=rel):
                previous_comment = False
                for line in (ROOT / rel).read_text().splitlines():
                    stripped = line.strip()
                    if not stripped:
                        previous_comment = False
                        continue
                    if stripped.startswith("#"):
                        previous_comment = True
                        continue
                    self.assertIn("=", stripped)
                    self.assertTrue(previous_comment, f"{rel}: missing comment before {stripped}")
                    previous_comment = False

    def test_env_examples_do_not_hardcode_local_profile_or_user_path(self):
        combined = "\n".join((ROOT / rel).read_text() for rel in ENV_EXAMPLES)
        self.assertNotIn("hm-pdp-test", combined)
        self.assertNotIn("/home/vscode", combined)
        self.assertNotIn("hermes-agent/venv", combined)


if __name__ == "__main__":
    unittest.main()
