import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_approval_hash_excludes_approval_hash_field(self):
        request = {
            "schema_version": 1,
            "status": "operator_approval_request_not_authorization",
            "approval_hash": "x" * 64,
            "artifact_sha256": "a" * 64,
            "account_id": "acct-canary",
            "active_profile_ref": "local-profile://acct_b",
        }
        first = self.module.compute_approval_hash(request)
        request["approval_hash"] = "y" * 64
        self.assertEqual(first, self.module.compute_approval_hash(request))

    def test_active_profile_ref_must_not_be_placeholder(self):
        with self.assertRaisesRegex(SystemExit, "active_profile_ref"):
            self.module.require_nonempty_text("REPLACE_WITH_PROFILE_REF", "active_profile_ref")

    def test_runtime_env_file_can_supply_account_and_profile_ref(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(
                "\n".join(
                    [
                        "# Active local account profile label.",
                        "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                        "# Active local account id bound to the selected profile.",
                        "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                        "# Local non-secret profile reference.",
                        "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                        "# Generic runtime signer material.",
                        "POLYMARKET_PRIVATE_KEY=0xabc123",
                        "# Generic runtime L2 API key.",
                        "POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                        "# Generic runtime L2 API secret.",
                        "POLY_API_SECRET=api-secret",
                        "# Generic runtime L2 API passphrase.",
                        "POLY_API_PASSPHRASE=api-pass",
                        "# Generic runtime CLOB funder for deposit-wallet / Poly1271 auth.",
                        "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                        "# Generic runtime signature type for the active account.",
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
        self.assertEqual(profile_ref, "local-profile://acct_b")

    def test_runtime_identity_can_resolve_from_identity_only_env(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            env_file = Path(tmp_name) / ".env.runtime"
            env_file.write_text(
                "\n".join(
                    [
                        "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                        "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                        "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
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
        self.assertEqual(profile_ref, "local-profile://acct_b")

    def test_candidate_notional_must_match_limit_times_size(self):
        candidate = {
            "market_id": "condition-1",
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "active": True,
            "accepting_orders": True,
            "closed": False,
            "archived": False,
            "target_size": "5",
            "limit_price": "0.02",
            "estimated_order_notional_usd": "0.11",
            "book_snapshot_timestamp": "2099-01-01T00:00:00Z",
            "exchange_rule_snapshot": {
                "captured_at": "2099-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:10:00Z",
            },
        }
        with self.assertRaisesRegex(SystemExit, "estimated_order_notional_usd"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_candidate_notional_must_fit_requested_cap(self):
        candidate = {
            "market_id": "condition-1",
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "active": True,
            "accepting_orders": True,
            "closed": False,
            "archived": False,
            "target_size": "5",
            "limit_price": "0.05",
            "estimated_order_notional_usd": "0.25",
            "book_snapshot_timestamp": "2099-01-01T00:00:00Z",
            "exchange_rule_snapshot": {
                "captured_at": "2099-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:10:00Z",
            },
        }
        with self.assertRaisesRegex(SystemExit, "exceeds"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_candidate_must_match_runtime_state_and_fresh_snapshot_shape(self):
        future = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        candidate = {
            "market_id": "condition-1",
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "active": True,
            "accepting_orders": True,
            "closed": False,
            "archived": False,
            "target_size": "5",
            "limit_price": "0.02",
            "estimated_order_notional_usd": "0.10",
            "book_snapshot_timestamp": future,
            "exchange_rule_snapshot": {
                "captured_at": future,
                "expires_at": future,
            },
        }
        with self.assertRaisesRegex(SystemExit, "expires_at must be after captured_at"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_runtime_truth_must_bind_account_and_gate_snapshot(self):
        runtime_truth = {
            "account_id": "acct-canary",
            "condition_id": "condition-1",
            "preflight_report": {
                "status": "preflight_ready",
                "live_submit_allowed": False,
                "real_funds_canary_allowed": False,
                "preconditions_live_submit_would_pass": True,
                "preconditions_real_funds_canary_would_pass": True,
                "kill_switch_open": True,
                "runtime_worker_healthy": True,
                "geoblock_allowed": True,
                "repository_reservation_exists": True,
                "idempotency_key_written": True,
                "reconcile_worker_healthy": True,
                "cancel_only_fallback_ready": True,
                "balance_allowance_checked": True,
                "gate_evidence_refs": {
                    "live_submit_allowed": "pg://runtime/live-submit-allowed",
                    "real_funds_canary_allowed": "pg://runtime/real-funds-canary-allowed",
                    "preconditions_live_submit_would_pass": "pg://runtime/live-submit-preconditions",
                    "preconditions_real_funds_canary_would_pass": "pg://runtime/real-funds-canary-preconditions",
                    "kill_switch_open": "pg://runtime/kill-switch",
                    "runtime_worker_healthy": "pg://runtime/runtime-worker",
                    "geoblock_allowed": "pg://runtime/geoblock",
                    "repository_reservation_exists": "pg://runtime/reservation",
                    "idempotency_key_written": "pg://runtime/idempotency",
                    "reconcile_worker_healthy": "pg://runtime/reconcile",
                    "cancel_only_fallback_ready": "pg://runtime/cancel-only-fallback",
                    "balance_allowance_checked": "pg://runtime/allowance",
                },
            },
        }
        summary = self.module.validate_runtime_truth(runtime_truth, expected_account_id="acct-canary")
        self.assertEqual(summary["condition_id"], "condition-1")
        self.assertTrue(summary["gate_snapshot"]["kill_switch_open"])
        self.assertEqual(
            summary["gate_evidence_refs"]["kill_switch_open"],
            "pg://runtime/kill-switch",
        )


if __name__ == "__main__":
    unittest.main()
