import importlib.util
import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_canary_candidate_market.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_candidate_market", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PrepareCanaryCandidateMarketTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_candidate_json_binds_estimated_notional_to_limit_price_times_size(self):
        candidate = self.module.Candidate(
            market_id="condition-1",
            token_id="123",
            outcome="Yes",
            market_slug="slug",
            active=True,
            accepting_orders=True,
            closed=False,
            archived=False,
            best_ask=Decimal("0.024"),
            limit_price=Decimal("0.02"),
            ask_size=Decimal("100"),
            target_size=Decimal("5"),
            spread_bps=10,
            min_order_size=Decimal("5"),
            min_tick_size=Decimal("0.01"),
            liquidity_score=100,
            source_market_hash="a" * 64,
            book_snapshot_timestamp="2026-05-23T00:00:00+00:00",
            human_review_ref="ticket://review",
        )
        self.assertEqual(candidate.to_engine_json()["estimated_order_notional_usd"], "0.1")


if __name__ == "__main__":
    unittest.main()
