import importlib.util
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
        }
        first = self.module.compute_approval_hash(request)
        request["approval_hash"] = "y" * 64
        self.assertEqual(first, self.module.compute_approval_hash(request))

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
