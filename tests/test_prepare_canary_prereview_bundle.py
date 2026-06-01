import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_canary_prereview_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_prereview_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareCanaryPrereviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_prepare_prereview_bundle_chains_candidate_runtime_truth_and_review_bundle(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            calls: list[tuple[str, dict]] = []

            def fake_prepare_candidate(**kwargs):
                calls.append(("candidate", kwargs))
                kwargs["candidate_market_output"].write_text("{}\n")
                if kwargs["candidate_audit_output"] is not None:
                    kwargs["candidate_audit_output"].write_text("{}\n")
                return {"candidate_market_output": str(kwargs["candidate_market_output"])}

            def fake_prepare_runtime_truth(**kwargs):
                calls.append(("runtime_truth", kwargs))
                self.assertEqual(kwargs["account_id"], "acct_b")
                kwargs["runtime_truth_output"].write_text("{}\n")
                return {"runtime_truth_output": str(kwargs["runtime_truth_output"])}

            def fake_activate_runtime_profile_env(**kwargs):
                calls.append(("activate_runtime_profile", kwargs))
                kwargs["runtime_env_output"].write_text("PMX_ACTIVE_ACCOUNT_PROFILE=acct_b\n")
                return {
                    "profile": "acct_b",
                    "account_id": "acct_b",
                    "active_profile_ref": "local-profile://acct_b",
                    "runtime_env_output": str(kwargs["runtime_env_output"]),
                    "secrets_included": False,
                }

            review_results = {
                "status": "pass",
                "profile": "acct_b",
                "review_packet_status": "dual_control_review_packet_not_authorization",
            }

            class FakeReviewBundleModule:
                @staticmethod
                def prepare_review_bundle(**kwargs):
                    calls.append(("review_bundle", kwargs))
                    return review_results

            def fake_load_module(path, name):
                if path == self.module.REVIEW_BUNDLE_SCRIPT:
                    return FakeReviewBundleModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.prepare_candidate = fake_prepare_candidate
            self.module.prepare_runtime_truth = fake_prepare_runtime_truth
            self.module.activate_runtime_profile_env = fake_activate_runtime_profile_env
            self.module.load_module = fake_load_module

            result = self.module.prepare_prereview_bundle(
                profile="acct_b",
                source_env_file=tmp / ".env.profiles",
                runtime_env_output=tmp / ".env.runtime",
                approval_request_output=tmp / "approval.json",
                dual_control_template_output=tmp / "dual-control-review.template.json",
                review_packet_output_dir=tmp / "review-packet",
                candidate_market_output=tmp / "candidate-market.json",
                runtime_truth_output=tmp / "runtime-truth.json",
                candidate_audit_output=tmp / "candidate-market.audit.json",
                release_zip=tmp / "artifact.zip",
                root_ci_run_id="1",
                hermes_ci_run_id="2",
                execution_engine_ci_run_id="3",
                credentialed_sdk_run_id="4",
                operator_identity_ref="operator://primary",
                approval_ticket_ref="ticket://approval",
                human_review_ref="ticket://market-review",
                exchange_rule_evidence_ref="ticket://reviewed-rule",
                market_url="https://polymarket.com/event/example",
                market_slug=None,
                outcome="Yes",
                gamma_url=None,
                clob_url=None,
                max_markets=200,
                target_size="5",
                max_order_notional_usd="0.20",
                max_daily_notional_usd="0.20",
                max_spread_bps=100,
                exchange_rule_valid_for_minutes=5,
                timeout_seconds=10.0,
                valid_for_minutes=15,
            )

            self.assertEqual(
                [entry[0] for entry in calls],
                ["candidate", "activate_runtime_profile", "runtime_truth", "review_bundle"],
            )
            self.assertEqual(calls[0][1]["exchange_rule_evidence_ref"], "ticket://reviewed-rule")
            self.assertEqual(result["profile"], "acct_b")
            self.assertFalse(result["secrets_included"])
            self.assertEqual(result["review_packet_status"], "dual_control_review_packet_not_authorization")
            self.assertEqual(
                calls[3][1]["candidate_market_file"],
                tmp / "candidate-market.json",
            )
            self.assertEqual(
                calls[3][1]["runtime_truth_file"],
                tmp / "runtime-truth.json",
            )


if __name__ == "__main__":
    unittest.main()
