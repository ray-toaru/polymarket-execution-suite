import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_script(script_name: str):
    path = ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name[:-3], path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CredentialedSdkRunIdRequiredTests(unittest.TestCase):
    def assert_missing_credentialed_sdk_run_id_fails(self, script_name: str, argv: list[str]) -> None:
        module = load_script(script_name)
        with mock.patch.object(sys, "argv", [script_name, *argv]):
            with self.assertRaises(SystemExit) as raised:
                module.parse_args()
        self.assertNotEqual(raised.exception.code, 0)

    def assert_present_credentialed_sdk_run_id_parses(self, script_name: str, argv: list[str]) -> None:
        module = load_script(script_name)
        with mock.patch.object(sys, "argv", [script_name, *argv, "--credentialed-sdk-run-id", "run-current-123"]):
            args = module.parse_args()
        self.assertEqual(args.credentialed_sdk_run_id, "run-current-123")

    def test_review_bundle_requires_credentialed_sdk_run_id(self):
        argv = [
            "--profile", "acct_b",
            "--source-env-file", "source.env",
            "--runtime-env-output", "runtime.env",
            "--approval-request-output", "approval.json",
            "--dual-control-template-output", "template.json",
            "--review-packet-output-dir", "packet",
            "--candidate-market-file", "candidate.json",
            "--runtime-truth-file", "truth.json",
            "--root-ci-run-id", "root-ci",
            "--hermes-ci-run-id", "hermes-ci",
            "--execution-engine-ci-run-id", "engine-ci",
            "--operator-identity-ref", "operator://primary",
            "--approval-ticket-ref", "ticket://approval",
        ]
        self.assert_missing_credentialed_sdk_run_id_fails("prepare_canary_review_bundle.py", argv)
        self.assert_present_credentialed_sdk_run_id_parses("prepare_canary_review_bundle.py", argv)

    def test_prereview_bundle_requires_credentialed_sdk_run_id(self):
        argv = [
            "--profile", "acct_b",
            "--source-env-file", "source.env",
            "--runtime-env-output", "runtime.env",
            "--approval-request-output", "approval.json",
            "--dual-control-template-output", "template.json",
            "--review-packet-output-dir", "packet",
            "--candidate-market-output", "candidate.json",
            "--runtime-truth-output", "truth.json",
            "--root-ci-run-id", "root-ci",
            "--hermes-ci-run-id", "hermes-ci",
            "--execution-engine-ci-run-id", "engine-ci",
            "--operator-identity-ref", "operator://primary",
            "--approval-ticket-ref", "ticket://approval",
            "--human-review-ref", "ticket://market-review",
        ]
        self.assert_missing_credentialed_sdk_run_id_fails("prepare_canary_prereview_bundle.py", argv)
        self.assert_present_credentialed_sdk_run_id_parses("prepare_canary_prereview_bundle.py", argv)


if __name__ == "__main__":
    unittest.main()
