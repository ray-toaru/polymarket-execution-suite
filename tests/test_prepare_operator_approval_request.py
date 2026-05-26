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
                        "PMX_ACTIVE_PROFILE_REF=local-profile://acct-b",
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
        self.assertEqual(profile_ref, "local-profile://acct-b")

    def test_candidate_notional_must_match_limit_times_size(self):
        candidate = {
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "target_size": "5",
            "limit_price": "0.02",
            "estimated_order_notional_usd": "0.11",
            "exchange_rule_snapshot": {"expires_at": "2099-01-01T00:00:00Z"},
        }
        with self.assertRaisesRegex(SystemExit, "estimated_order_notional_usd"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))

    def test_candidate_notional_must_fit_requested_cap(self):
        candidate = {
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "target_size": "5",
            "limit_price": "0.05",
            "estimated_order_notional_usd": "0.25",
            "exchange_rule_snapshot": {"expires_at": "2099-01-01T00:00:00Z"},
        }
        with self.assertRaisesRegex(SystemExit, "exceeds"):
            self.module.validate_candidate(candidate, self.module.Decimal("0.20"))


if __name__ == "__main__":
    unittest.main()
