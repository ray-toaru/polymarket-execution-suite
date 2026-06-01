import importlib.util
import sys
import argparse
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


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
            exchange_rule_evidence_ref="ticket://reviewed-rule",
        )
        self.assertEqual(candidate.to_engine_json()["outcome"], "Yes")
        self.assertEqual(candidate.to_engine_json()["estimated_order_notional_usd"], "0.1")
        self.assertEqual(
            candidate.to_engine_json()["exchange_rule_snapshot"]["evidence_ref"],
            "ticket://reviewed-rule",
        )

    def test_load_market_by_slug_requires_outcome_disambiguation(self):
        args = argparse.Namespace(gamma_url="https://gamma", timeout_seconds=1.0)
        markets = [
            {"slug": "shared-slug", "outcomes": ["Yes", "No"], "clobTokenIds": ["1", "2"]},
            {"slug": "shared-slug", "outcomes": ["Yes", "No"], "clobTokenIds": ["3", "4"]},
        ]
        with patch.object(self.module, "fetch_json", side_effect=[markets]):
            with self.assertRaisesRegex(self.module.CandidateError, "multiple markets") as ctx:
                self.module.load_market_by_slug(args, "shared-slug", "Yes")
        message = str(ctx.exception)
        self.assertIn("Candidates:", message)
        self.assertIn('"token_ids": ["1", "2"]', message)
        self.assertIn('"token_ids": ["3", "4"]', message)

    def test_scan_uses_deterministic_tie_break_for_equal_liquidity(self):
        args = argparse.Namespace(
            gamma_url="https://gamma",
            clob_url="https://clob",
            timeout_seconds=1.0,
            max_order_notional_usd="1.00",
            target_size="5",
            max_markets=10,
            max_spread_bps=100,
            human_review_ref="ticket://review",
            exchange_rule_evidence_ref="ticket://reviewed-rule",
            market_url=None,
            market_slug=None,
            outcome=None,
        )
        markets = [
            {
                "id": "condition-b",
                "slug": "slug-b",
                "active": True,
                "acceptingOrders": True,
                "closed": False,
                "archived": False,
                "outcomes": ["Yes"],
                "clobTokenIds": ["200"],
            },
            {
                "id": "condition-a",
                "slug": "slug-a",
                "active": True,
                "acceptingOrders": True,
                "closed": False,
                "archived": False,
                "outcomes": ["Yes"],
                "clobTokenIds": ["100"],
            },
        ]
        book = {"asks": [{"price": "0.03", "size": "10"}], "min_order_size": "5", "min_tick_size": "0.01"}
        spread = {"spread": "0.01"}
        with patch.object(self.module, "fetch_json", side_effect=[markets, book, spread, book, spread]):
            candidate, _audit = self.module.scan(args)
        self.assertEqual(candidate.market_id, "condition-a")
        self.assertEqual(candidate.token_id, "100")

    def test_scan_requires_distinct_concrete_review_refs(self):
        args = argparse.Namespace(
            gamma_url="https://gamma",
            clob_url="https://clob",
            timeout_seconds=1.0,
            max_order_notional_usd="1.00",
            target_size="5",
            max_markets=10,
            max_spread_bps=100,
            human_review_ref="review",
            exchange_rule_evidence_ref="review",
            market_url=None,
            market_slug=None,
            outcome=None,
        )
        with self.assertRaisesRegex(self.module.CandidateError, "--human-review-ref"):
            self.module.scan(args)

    def test_candidate_from_market_requires_positive_tick_and_min_order(self):
        args = argparse.Namespace(
            clob_url="https://clob",
            timeout_seconds=1.0,
            max_spread_bps=100,
            market_slug="slug",
        )
        market = {
            "id": "condition-1",
            "slug": "slug",
            "active": True,
            "acceptingOrders": True,
            "closed": False,
            "archived": False,
            "outcomes": ["Yes"],
            "clobTokenIds": ["1"],
        }
        book = {"asks": [{"price": "0.03", "size": "10"}], "min_order_size": None, "min_tick_size": None}
        spread = {"spread": "0.01"}
        audit = {}
        with patch.object(self.module, "fetch_json_or_error", side_effect=[book, spread]):
            with self.assertRaisesRegex(self.module.CandidateError, "min_order_size is unavailable"):
                self.module.candidate_from_market(
                    args,
                    market,
                    requested_outcome="Yes",
                    order_cap=Decimal("1"),
                    requested_target_size=None,
                    snapshot_at="2026-05-23T00:00:00+00:00",
                    human_review_ref="ticket://review",
                    exchange_rule_evidence_ref="ticket://reviewed-rule",
                    audit=audit,
                )

    def test_fetch_json_retries_before_succeeding(self):
        calls = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{\"status\": \"ok\"}"

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, timeout))
            if len(calls) < 3:
                raise self.module.urllib.error.URLError("temporary")
            return FakeResponse()

        with patch.object(self.module.urllib.request, "urlopen", side_effect=fake_urlopen):
            with patch.object(self.module.time, "sleep"):
                data = self.module.fetch_json("https://gamma", "/markets", {}, 1.0)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
