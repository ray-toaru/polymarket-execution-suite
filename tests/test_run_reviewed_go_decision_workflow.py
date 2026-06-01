import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_reviewed_go_decision_workflow.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_reviewed_go_decision_workflow", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunReviewedGoDecisionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def args(self, tmp: Path):
        return self.module.argparse.Namespace(
            profile="acct_b",
            source_env_file=tmp / ".env.profiles",
            runtime_env_output=tmp / ".env.runtime",
            candidate_market_output=tmp / "candidate-market.json",
            candidate_audit_output=tmp / "candidate-market.audit.json",
            runtime_truth_output=tmp / "runtime-truth.json",
            approval_request_output=tmp / "approval-request.json",
            dual_control_template_output=tmp / "dual-control-review.template.json",
            review_packet_output_dir=tmp / "review-packet",
            release_zip=tmp / "artifact.zip",
            root_ci_run_id="1",
            hermes_ci_run_id="2",
            execution_engine_ci_run_id="3",
            credentialed_sdk_run_id="local",
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
            approved_dual_control_review_file=None,
            external_references_file=None,
            reviewed_go_output_dir=None,
            decision_id=None,
            decision_reason="approved by independent reviewer",
            run=False,
        )

    def test_build_plan_marks_promotion_blocked_without_review_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            args = self.args(Path(tmp_name))
            plan = self.module.build_workflow_plan(args)
        self.assertEqual(plan["workflow"], "reviewed_go_decision_chain")
        self.assertEqual(plan["stages"][0]["name"], "prereview_bundle")
        self.assertFalse(plan["stages"][1]["enabled"])

    def test_execute_workflow_stops_at_review_packet_without_approved_review(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.args(tmp)

            class FakePrereviewModule:
                @staticmethod
                def prepare_prereview_bundle(**kwargs):
                    return {
                        "status": "pass",
                        "profile": kwargs["profile"],
                        "review_packet_status": "dual_control_review_packet_not_authorization",
                    }

            def fake_load_module(path, name):
                if path == self.module.PREREVIEW_BUNDLE_SCRIPT:
                    return FakePrereviewModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.load_module = fake_load_module
            result = self.module.execute_workflow(args)

        self.assertEqual(result["status"], "review_packet_ready_requires_independent_review")
        self.assertEqual(result["promotion"]["status"], "blocked")

    def test_execute_workflow_promotes_when_approved_review_is_present(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.args(tmp)
            args.approved_dual_control_review_file = tmp / "dual-control-review.approved.json"
            args.external_references_file = tmp / "external-references.json"
            args.reviewed_go_output_dir = tmp / "reviewed-go"

            class FakePrereviewModule:
                @staticmethod
                def prepare_prereview_bundle(**kwargs):
                    return {
                        "status": "pass",
                        "profile": kwargs["profile"],
                        "review_packet_status": "dual_control_review_packet_not_authorization",
                    }

            class FakeReviewedGoModule:
                @staticmethod
                def prepare_reviewed_go_bundle(**kwargs):
                    return {
                        "status": "pass",
                        "package_status": "reviewed_go_package_ready_single_attempt",
                        "output_dir": str(kwargs["output_dir"]),
                    }

            def fake_load_module(path, name):
                if path == self.module.PREREVIEW_BUNDLE_SCRIPT:
                    return FakePrereviewModule()
                if path == self.module.REVIEWED_GO_BUNDLE_SCRIPT:
                    return FakeReviewedGoModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.load_module = fake_load_module
            result = self.module.execute_workflow(args)

        self.assertEqual(result["status"], "reviewed_go_package_ready")
        self.assertEqual(result["promotion"]["package_status"], "reviewed_go_package_ready_single_attempt")


if __name__ == "__main__":
    unittest.main()
