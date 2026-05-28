import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_operator_approval_request.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_operator_approval_request", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareOperatorApprovalRequestTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def candidate_fixture(self):
        return {
            "market_id": "condition-1",
            "token_id": "123",
            "human_review_ref": "ticket://candidate-review",
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "active": True,
            "accepting_orders": True,
            "closed": False,
            "archived": False,
            "best_ask": "0.03",
            "limit_price": "0.02",
            "ask_size": "20",
            "target_size": "5",
            "min_order_size": "5",
            "estimated_order_notional_usd": "0.1",
            "exchange_rule_snapshot": {
                "schema_version": 1,
                "venue": "polymarket_clob",
                "order_mode": "post_only_limit",
                "order_type": "GTC",
                "side": "BUY",
                "target_size_semantics": "outcome_shares",
                "min_share_size": "5",
                "min_tick_size": "0.01",
                "source": "public_clob_book_plus_reviewed_remote_rule",
                "captured_at": "2026-05-23T00:00:00+00:00",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "evidence_ref": "ticket://reviewed-rule",
            },
        }

    def test_approval_hash_excludes_approval_hash_field(self):
        request = {
            "schema_version": 1,
            "status": "operator_approval_request_not_authorization",
            "approval_hash": "x" * 64,
            "artifact_sha256": "a" * 64,
            "account_id": "acct-canary",
            "active_profile_ref": "local-profile://acct-b",
        }
        first = self.module.compute_approval_hash(request)
        request["approval_hash"] = "y" * 64
        self.assertEqual(first, self.module.compute_approval_hash(request))

    def test_active_profile_ref_must_not_be_placeholder(self):
        with self.assertRaisesRegex(SystemExit, "active_profile_ref"):
            self.module.require_nonempty_text("ticket://TODO-profile", "active_profile_ref")

    def test_runtime_env_file_can_supply_account_and_profile_ref(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(
                "\n".join(
                    [
                        "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                        "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                        "PMX_ACTIVE_PROFILE_REF=local-profile://acct-b",
                        "POLYMARKET_PRIVATE_KEY=0xabc123",
                        "POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                        "POLY_API_SECRET=api-secret",
                        "POLY_API_PASSPHRASE=api-pass",
                        "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                        "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                        "",
                    ]
                )
            )
            account_id, profile_ref = self.module.resolve_runtime_identity(
                runtime_env_file=env_file,
                account_id=None,
                active_profile_ref=None,
            )
        self.assertEqual(account_id, "acct-canary")
        self.assertEqual(profile_ref, "local-profile://acct-b")

    def test_candidate_notional_must_match_limit_times_size(self):
        candidate = self.candidate_fixture()
        candidate["estimated_order_notional_usd"] = "0.11"
        with self.assertRaisesRegex(SystemExit, "estimated_order_notional_usd"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_candidate_notional_must_fit_requested_cap(self):
        candidate = self.candidate_fixture()
        candidate["limit_price"] = "0.05"
        candidate["best_ask"] = "0.06"
        candidate["estimated_order_notional_usd"] = "0.25"
        with self.assertRaisesRegex(SystemExit, "exceeds"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_candidate_must_be_live_and_accepting(self):
        candidate = self.candidate_fixture()
        candidate["accepting_orders"] = False
        with self.assertRaisesRegex(SystemExit, "accepting_orders"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_runtime_truth_requires_all_v28_dependencies(self):
        sidecar = {
            "artifact_sha256": "a" * 64,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "evidence_manifest_sha256": "c" * 64,
        }
        runtime_truth = {
            "artifact_sha256": "a" * 64,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "remote_side_effects": False,
            "dependencies": [
                {"name": "kill_switch", "status": "durable_runtime_truth", "evidence_ref": "pg://kill_switch"}
            ],
        }
        with self.assertRaisesRegex(SystemExit, "missing durable dependencies"):
            self.module.validate_runtime_truth(runtime_truth, sidecar)


if __name__ == "__main__":
    unittest.main()
