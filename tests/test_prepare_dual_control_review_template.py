import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_dual_control_review_template.py"
REVIEWED_GO_SCRIPT = ROOT / "scripts" / "prepare_reviewed_go_decision.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareDualControlReviewTemplateTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module(SCRIPT, "prepare_dual_control_review_template")
        self.reviewed_go = load_module(REVIEWED_GO_SCRIPT, "prepare_reviewed_go_decision")

    def approval_request(self, **overrides):
        data = {
            "schema_version": 1,
            "status": "operator_approval_request_not_authorization",
            "approval_hash": "a" * 64,
            "scope": "REAL_FUNDS_CANARY",
            "active_profile_ref": "local-profile://acct_b",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "expires_at": "2099-01-01T00:15:00Z",
            "operator_identity_ref": "operator://requester",
            "artifact_sha256": "b" * 64,
            "workspace_manifest_sha256": "c" * 64,
            "archived_manifest_sha256": "d" * 64,
            "evidence_manifest_sha256": "d" * 64,
            "market_candidate_sha256": "e" * 64,
            "runtime_truth_sha256": "f" * 64,
            "risk_limits": {
                "max_order_notional_usd": "0.2",
                "max_daily_notional_usd": "0.2",
                "candidate_target_size": "5",
                "candidate_limit_price": "0.02",
                "candidate_estimated_order_notional_usd": "0.1",
            },
            "live_submit_authorized": False,
            "remote_side_effects_authorized": False,
            "secrets_included": False,
        }
        data.update(overrides)
        return data

    def test_template_binds_approval_request_without_authorizing(self):
        template = self.module.build_template(
            self.approval_request(),
            approval_request_sha256="1" * 64,
        )
        self.assertEqual(template["status"], "draft_requires_independent_reviewer")
        self.assertEqual(template["approval_request_sha256"], "1" * 64)
        self.assertEqual(template["artifact_sha256"], "b" * 64)
        self.assertEqual(template["risk_limits"]["candidate_target_size"], "5")
        self.assertFalse(template["live_submit_authorized"])
        self.assertFalse(template["remote_side_effects_authorized"])

    def test_template_is_rejected_by_reviewed_go_until_independently_approved(self):
        template = self.module.build_template(
            self.approval_request(),
            approval_request_sha256="1" * 64,
        )
        with self.assertRaisesRegex(SystemExit, "status"):
            self.reviewed_go.validate_dual_control_review(template, self.approval_request())

    def test_rejects_authorizing_approval_request(self):
        with self.assertRaisesRegex(SystemExit, "live submit"):
            self.module.build_template(
                self.approval_request(live_submit_authorized=True),
                approval_request_sha256="1" * 64,
            )


if __name__ == "__main__":
    unittest.main()
