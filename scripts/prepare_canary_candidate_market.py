#!/usr/bin/env python3
"""Thin wrapper over execution-engine canary candidate prep."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "prepare_canary_candidate_market.py"
)


def load_engine_module():
    spec = importlib.util.spec_from_file_location(
        "engine_prepare_canary_candidate_market",
        ENGINE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

argparse = _ENGINE.argparse
dt = _ENGINE.dt
hashlib = _ENGINE.hashlib
json = _ENGINE.json
sys = _ENGINE.sys
time = _ENGINE.time
urllib = _ENGINE.urllib
Path = _ENGINE.Path
Any = _ENGINE.Any
Decimal = _ENGINE.Decimal
InvalidOperation = _ENGINE.InvalidOperation
ROUND_CEILING = _ENGINE.ROUND_CEILING
ROUND_FLOOR = _ENGINE.ROUND_FLOOR
DEFAULT_GAMMA_URL = _ENGINE.DEFAULT_GAMMA_URL
DEFAULT_CLOB_URL = _ENGINE.DEFAULT_CLOB_URL
VERSION = _ENGINE.VERSION
USER_AGENT = _ENGINE.USER_AGENT
MAX_PRICE = _ENGINE.MAX_PRICE
FETCH_RETRY_ATTEMPTS = _ENGINE.FETCH_RETRY_ATTEMPTS
Candidate = _ENGINE.Candidate
CandidateError = _ENGINE.CandidateError
parse_args = _ENGINE.parse_args
fetch_json = _ENGINE.fetch_json
is_json_content_type = _ENGINE.is_json_content_type
should_retry_http_error = _ENGINE.should_retry_http_error
retry_delay_seconds = _ENGINE.retry_delay_seconds
audit_url_ref = _ENGINE.audit_url_ref
as_bool = _ENGINE.as_bool
as_decimal = _ENGINE.as_decimal
decimal_text = _ENGINE.decimal_text
parse_token_ids = _ENGINE.parse_token_ids
parse_outcomes = _ENGINE.parse_outcomes
parse_jsonish_list = _ENGINE.parse_jsonish_list
market_id = _ENGINE.market_id
best_ask = _ENGINE.best_ask
best_bid = _ENGINE.best_bid
post_only_buy_limit_price = _ENGINE.post_only_buy_limit_price
spread_bps = _ENGINE.spread_bps
liquidity_score = _ENGINE.liquidity_score
market_fingerprint = _ENGINE.market_fingerprint
slug_from_market_url = _ENGINE.slug_from_market_url
normalized_outcome = _ENGINE.normalized_outcome
candidate_sort_key = _ENGINE.candidate_sort_key
market_disambiguation_summary = _ENGINE.market_disambiguation_summary
is_concrete_external_ref = _ENGINE.is_concrete_external_ref
fetch_json_or_error = _ENGINE.fetch_json_or_error
clob_request_limit = _ENGINE.clob_request_limit
select_market_for_outcome = _ENGINE.select_market_for_outcome
write_json = _ENGINE.write_json


def _with_engine_overrides(callback, *args, **kwargs):
    original_fetch_json = _ENGINE.fetch_json
    original_fetch_json_or_error = _ENGINE.fetch_json_or_error
    original_load_market_by_slug = _ENGINE.load_market_by_slug
    original_candidate_from_market = _ENGINE.candidate_from_market
    try:
        _ENGINE.fetch_json = fetch_json
        _ENGINE.fetch_json_or_error = fetch_json_or_error
        _ENGINE.load_market_by_slug = load_market_by_slug
        _ENGINE.candidate_from_market = candidate_from_market
        return callback(*args, **kwargs)
    finally:
        _ENGINE.fetch_json = original_fetch_json
        _ENGINE.fetch_json_or_error = original_fetch_json_or_error
        _ENGINE.load_market_by_slug = original_load_market_by_slug
        _ENGINE.candidate_from_market = original_candidate_from_market


def candidate_from_market(*args, **kwargs):
    return _with_engine_overrides(_ENGINE.candidate_from_market, *args, **kwargs)


def load_market_by_slug(*args, **kwargs):
    return _with_engine_overrides(_ENGINE.load_market_by_slug, *args, **kwargs)


def scan(*args, **kwargs):
    return _with_engine_overrides(_ENGINE.scan, *args, **kwargs)


def main() -> int:
    return _ENGINE.main()


if __name__ == "__main__":
    raise SystemExit(main())
