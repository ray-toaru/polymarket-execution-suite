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
    "polymarket-execution-engine/.env.validation.example",
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

    def test_engine_runtime_example_separates_api_auth_from_validation_and_secret_keys(self):
        text = (ROOT / "polymarket-execution-engine/.env.example").read_text()
        required = [
            "PMX_API_SERVICE_TOKEN",
            "PMX_API_ADMIN_TOKEN",
        ]
        for name in required:
            with self.subTest(name=name):
                self.assertIn(name, text)
        forbidden = [
            "PMX_TEST_DATABASE_URL",
            "PM_EXEC_SERVICE_TOKEN",
            "PM_EXEC_ADMIN_TOKEN",
            "PMX_SERVICE_TOKEN",
            "PMX_ADMIN_TOKEN",
            "PMX_GATEWAY_MODE",
            "POLYMARKET_PRIVATE_KEY",
            "POLY_API_SECRET",
            "PMX_PROFILE_",
            "PMX_ACTIVE_ACCOUNT_PROFILE",
        ]
        for name in forbidden:
            with self.subTest(name=name):
                self.assertNotIn(name, text)

    def test_engine_validation_example_excludes_runtime_adapter_and_secret_keys(self):
        text = (ROOT / "polymarket-execution-engine/.env.validation.example").read_text()
        self.assertIn("PMX_TEST_DATABASE_URL", text)
        forbidden = [
            "PMX_DATABASE_URL",
            "PM_EXEC_SERVICE_TOKEN",
            "PM_EXEC_ADMIN_TOKEN",
            "POLYMARKET_PRIVATE_KEY",
            "POLY_API_SECRET",
            "PMX_PROFILE_",
            "PMX_ACTIVE_ACCOUNT_PROFILE",
        ]
        for name in forbidden:
            with self.subTest(name=name):
                self.assertNotIn(name, text)

    def test_adapter_example_excludes_engine_database_and_sdk_secret_keys(self):
        text = (ROOT / "hermes-polymarket-executor-adapter/.env.example").read_text()
        required = ["PM_EXEC_SERVICE_URL", "PM_EXEC_SERVICE_TOKEN", "PM_EXEC_ADMIN_TOKEN"]
        for name in required:
            with self.subTest(name=name):
                self.assertIn(name, text)
        forbidden = [
            "PMX_DATABASE_URL",
            "PMX_TEST_DATABASE_URL",
            "POLYMARKET_PRIVATE_KEY",
            "POLY_API_SECRET",
            "PMX_PROFILE_",
        ]
        for name in forbidden:
            with self.subTest(name=name):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
