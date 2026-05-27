import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_reviewed_go_decision.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_reviewed_go_decision", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareReviewedGoDecisionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def approval_request(self, **overrides):
        data = {
            "schema_version": 1,
            "status": "operator_approval_request_not_authorization",
            "approval_id": "approval-request-1",
            "approval_hash": "a" * 64,
            "scope": "REAL_FUNDS_CANARY",
            "active_profile_ref": "local-profile://acct_b",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "operator_identity_ref": "chat-authorization://operator",
            "dual_control_required": True,
            "artifact_sha256": "b" * 64,
            "workspace_manifest_sha256": "c" * 64,
            "archived_manifest_sha256": "d" * 64,
            "evidence_manifest_sha256": "d" * 64,
            "market_candidate_sha256": "e" * 64,
            "runtime_truth_sha256": "f" * 64,
            "github_evidence": {
                "root_ci_run_id": "1",
                "hermes_ci_run_id": "2",
                "execution_engine_ci_run_id": "3",
                "credentialed_sdk_run_id": "local",
            },
            "risk_limits": {
                "max_order_notional_usd": "0.2",
                "max_daily_notional_usd": "0.2",
            },
            "live_submit_authorized": False,
            "remote_side_effects_authorized": False,
            "secrets_included": False,
        }
        data.update(overrides)
        return data

    def external_references(self):
        return {
            "secret_custody": {"provider_ref": "local-keyring://pmx"},
            "operator_approval": {"ticket_ref": "ticket://approval"},
            "alert_routing": {
                "route_ref": "pager://route",
                "dashboard_ref": "dashboard://pmx",
            },
            "runbooks": {
                "rollback_runbook_ref": "runbook://rollback",
                "incident_runbook_ref": "runbook://incident",
            },
        }

    def dual_control_review(self, **overrides):
        request = self.approval_request()
        data = {
            "schema_version": 1,
            "status": "approved",
            "scope": "REAL_FUNDS_CANARY",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "review_ref": "dual://review",
            "reviewer_identity_ref": "operator://second-reviewer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "approval_request_sha256": "8" * 64,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "approval_hash": request["approval_hash"],
            "artifact_sha256": request["artifact_sha256"],
            "workspace_manifest_sha256": request["workspace_manifest_sha256"],
            "archived_manifest_sha256": request["archived_manifest_sha256"],
            "evidence_manifest_sha256": request["evidence_manifest_sha256"],
            "market_candidate_sha256": request["market_candidate_sha256"],
            "runtime_truth_sha256": request["runtime_truth_sha256"],
            "risk_limits": {
                "max_order_notional_usd": request["risk_limits"]["max_order_notional_usd"],
                "max_daily_notional_usd": request["risk_limits"]["max_daily_notional_usd"],
            },
            "required_reviewer_checks": {
                "artifact_hash_reviewed": True,
                "evidence_manifest_hash_reviewed": True,
                "market_candidate_reviewed": True,
                "runtime_truth_reviewed": True,
                "risk_limits_reviewed": True,
                "secret_custody_reviewed": True,
                "alerting_reviewed": True,
                "rollback_reviewed": True,
                "reconcile_and_cancel_fallback_reviewed": True,
            },
            "secrets_included": False,
        }
        data.update(overrides)
        return data

    def test_requires_approved_dual_control_review(self):
        with self.assertRaisesRegex(SystemExit, "status"):
            self.module.build_decision(
                self.approval_request(),
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=self.dual_control_review(status="draft"),
            )

    def test_rejects_expired_approval_request(self):
        expired = self.approval_request(
            expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        )
        with self.assertRaisesRegex(SystemExit, "expired"):
            self.module.build_decision(
                expired,
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=self.dual_control_review(),
            )

    def test_rejects_same_operator_and_reviewer(self):
        request = self.approval_request()
        with self.assertRaisesRegex(SystemExit, "differ"):
            self.module.build_decision(
                request,
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=self.dual_control_review(
                    reviewer_identity_ref=request["operator_identity_ref"]
                ),
            )

    def test_rejects_dual_control_hash_mismatch(self):
        with self.assertRaisesRegex(SystemExit, "artifact_sha256"):
            self.module.build_decision(
                self.approval_request(),
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=self.dual_control_review(artifact_sha256="1" * 64),
            )

    def test_rejects_missing_required_reviewer_check(self):
        review = self.dual_control_review()
        review["required_reviewer_checks"]["runtime_truth_reviewed"] = False
        with self.assertRaisesRegex(SystemExit, "runtime_truth_reviewed"):
            self.module.build_decision(
                self.approval_request(),
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=review,
            )

    def test_rejects_approval_request_sha_mismatch(self):
        with self.assertRaisesRegex(SystemExit, "approval_request_sha256"):
            self.module.build_decision(
                self.approval_request(),
                self.external_references(),
                decision_id="decision-1",
                decision_reason="test",
                dual_control_review=self.dual_control_review(approval_request_sha256="7" * 64),
                approval_request_sha256="8" * 64,
            )

    def test_builds_reviewed_go_with_strict_notional_limit(self):
        decision = self.module.build_decision(
            self.approval_request(),
            self.external_references(),
            decision_id="decision-1",
            decision_reason="test",
            dual_control_review=self.dual_control_review(),
            dual_control_review_sha256="9" * 64,
            approval_request_sha256="8" * 64,
        )
        self.assertEqual(decision["decision"], "go")
        self.assertEqual(decision["status"], "reviewed_go")
        self.assertEqual(decision["risk_limits"]["max_order_notional_usd"], "0.2")
        self.assertTrue(decision["required_review_signals"]["operator_dual_control_reviewed"])
        self.assertFalse(decision["production_deployment_authorized"])
        self.assertEqual(decision["external_references"]["operator_dual_control_review_ref"], "dual://review")
        self.assertEqual(decision["external_references"]["operator_dual_control_review_sha256"], "9" * 64)


if __name__ == "__main__":
    unittest.main()
