import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_release_phase_orchestrator.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_release_phase_orchestrator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunReleasePhaseOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def base_args(self, tmp: Path):
        return self.module.argparse.Namespace(
            release_zip=tmp / "artifact.zip",
            output_dir=tmp / "phase-output",
            profile=None,
            source_env_file=None,
            runtime_env_output=None,
            candidate_market_output=None,
            candidate_audit_output=None,
            runtime_truth_output=None,
            approval_request_output=None,
            dual_control_template_output=None,
            review_packet_output_dir=None,
            root_ci_run_id=None,
            hermes_ci_run_id=None,
            execution_engine_ci_run_id=None,
            credentialed_sdk_run_id="local-current-gates-20260523",
            operator_identity_ref=None,
            approval_ticket_ref=None,
            human_review_ref=None,
            market_url=None,
            market_slug=None,
            outcome=None,
            gamma_url=None,
            clob_url=None,
            max_markets=200,
            target_size=None,
            max_order_notional_usd="0.20",
            max_daily_notional_usd="0.20",
            max_spread_bps=100,
            timeout_seconds=10.0,
            valid_for_minutes=15,
            approved_dual_control_review_file=None,
            external_references_file=None,
            reviewed_go_output_dir=None,
            decision_id=None,
            decision_reason="approved by independent reviewer",
            run=False,
        )

    def test_build_stage_plans_blocks_reviewed_go_without_required_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.base_args(tmp)
            plan = self.module.build_stage_plans(args)
        self.assertEqual(plan["workflow"], "release_phase_orchestrator")
        self.assertEqual(plan["stages"]["contract_validation"]["suite"], "contract_validation")
        self.assertEqual(plan["stages"]["production_control"]["suite"], "production_control_evidence")
        self.assertEqual(plan["stages"]["deployment_validation"]["suite"], "deployment_validation_evidence")
        self.assertEqual(plan["stages"]["live_submit_promotion"]["suite"], "live_submit_promotion_evidence")
        self.assertEqual(plan["stages"]["reviewed_go_decision_chain"]["status"], "blocked")

    def test_execute_orchestrator_runs_available_suites_and_keeps_reviewed_go_blocked(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.base_args(tmp)

            class FakeProductionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "production_control_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            class FakeDeploymentModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "deployment_validation_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            class FakePromotionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "live_submit_promotion_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            def fake_execute_contract_validation(plan):
                return {"status": "pass", "suite": plan["suite"], "report_status": "ok"}

            def fake_load_module(path, name):
                if path == self.module.PRODUCTION_CONTROL_SUITE:
                    return FakeProductionModule()
                if path == self.module.DEPLOYMENT_VALIDATION_SUITE:
                    return FakeDeploymentModule()
                if path == self.module.LIVE_SUBMIT_PROMOTION_SUITE:
                    return FakePromotionModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.load_module = fake_load_module
            self.module.execute_contract_validation = fake_execute_contract_validation
            result = self.module.execute_orchestrator(args)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["stages"]["contract_validation"]["status"], "pass")
        self.assertEqual(result["stages"]["reviewed_go_decision_chain"]["status"], "blocked")

    def test_execute_orchestrator_runs_reviewed_go_when_inputs_are_present(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.base_args(tmp)
            args.profile = "acct_b"
            args.source_env_file = tmp / ".env.profiles"
            args.runtime_env_output = tmp / ".env.runtime"
            args.candidate_market_output = tmp / "candidate-market.json"
            args.runtime_truth_output = tmp / "runtime-truth.json"
            args.approval_request_output = tmp / "approval-request.json"
            args.dual_control_template_output = tmp / "dual-control-review.template.json"
            args.review_packet_output_dir = tmp / "review-packet"
            args.root_ci_run_id = "1"
            args.hermes_ci_run_id = "2"
            args.execution_engine_ci_run_id = "3"
            args.operator_identity_ref = "operator://primary"
            args.approval_ticket_ref = "ticket://approval"
            args.human_review_ref = "ticket://market-review"

            class FakeProductionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "production_control_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            class FakeDeploymentModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "deployment_validation_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            class FakePromotionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "live_submit_promotion_evidence"}

                @staticmethod
                def execute_suite(plan):
                    return {"status": "pass", "suite": plan["suite"]}

            class FakeReviewedGoModule:
                argparse = __import__("argparse")

                @staticmethod
                def build_workflow_plan(args):
                    return {"status": "ready", "workflow": "reviewed_go_decision_chain"}

                @staticmethod
                def execute_workflow(args):
                    return {"status": "review_packet_ready_requires_independent_review"}

            def fake_execute_contract_validation(plan):
                return {"status": "pass", "suite": plan["suite"], "report_status": "ok"}

            def fake_load_module(path, name):
                if path == self.module.PRODUCTION_CONTROL_SUITE:
                    return FakeProductionModule()
                if path == self.module.DEPLOYMENT_VALIDATION_SUITE:
                    return FakeDeploymentModule()
                if path == self.module.LIVE_SUBMIT_PROMOTION_SUITE:
                    return FakePromotionModule()
                if path == self.module.REVIEWED_GO_DECISION_WORKFLOW:
                    return FakeReviewedGoModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.load_module = fake_load_module
            self.module.execute_contract_validation = fake_execute_contract_validation
            result = self.module.execute_orchestrator(args)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            result["stages"]["reviewed_go_decision_chain"]["status"],
            "review_packet_ready_requires_independent_review",
        )

    def test_execute_orchestrator_blocks_downstream_stages_when_contract_validation_fails(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            args = self.base_args(tmp)

            class FakeProductionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "production_control_evidence"}

                @staticmethod
                def execute_suite(plan):
                    raise AssertionError("downstream suite should not run after contract validation failure")

            class FakeDeploymentModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "deployment_validation_evidence"}

                @staticmethod
                def execute_suite(plan):
                    raise AssertionError("downstream suite should not run after contract validation failure")

            class FakePromotionModule:
                @staticmethod
                def build_suite_plan(**kwargs):
                    return {"status": "ready", "suite": "live_submit_promotion_evidence"}

                @staticmethod
                def execute_suite(plan):
                    raise AssertionError("downstream suite should not run after contract validation failure")

            def fake_load_module(path, name):
                if path == self.module.PRODUCTION_CONTROL_SUITE:
                    return FakeProductionModule()
                if path == self.module.DEPLOYMENT_VALIDATION_SUITE:
                    return FakeDeploymentModule()
                if path == self.module.LIVE_SUBMIT_PROMOTION_SUITE:
                    return FakePromotionModule()
                raise AssertionError(f"unexpected module load: {path}")

            self.module.load_module = fake_load_module
            self.module.execute_contract_validation = lambda plan: {
                "status": "fail",
                "suite": plan["suite"],
                "report_status": "fail",
                "failed_check_ids": ["synthetic_failure"],
            }
            result = self.module.execute_orchestrator(args)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["stages"]["contract_validation"]["status"], "fail")
        self.assertEqual(result["stages"]["production_control"]["status"], "blocked")
        self.assertEqual(result["stages"]["deployment_validation"]["status"], "blocked")
        self.assertEqual(result["stages"]["live_submit_promotion"]["status"], "blocked")
        self.assertEqual(result["stages"]["reviewed_go_decision_chain"]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
