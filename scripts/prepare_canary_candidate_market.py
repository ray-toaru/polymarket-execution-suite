#!/usr/bin/env python3
"""Prepare a reviewed canary market candidate from public read-only APIs.

This is release-prep tooling for the integration repository. It must not sign,
submit, cancel, or hold trading secrets. The output shape matches the execution
engine RealFundsCanaryMarketCandidate. The execution engine remains responsible
for validating the resulting candidate immediately before any dry run or
controlled canary attempt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DEFAULT_GAMMA_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_URL = "https://clob.polymarket.com"
USER_AGENT = "pmx-canary-candidate-prep/0.1"


@dataclass(frozen=True)
class Candidate:
    market_id: str
    token_id: str
    active: bool
    accepting_orders: bool
    closed: bool
    archived: bool
    best_ask: Decimal
    ask_size: Decimal
    spread_bps: int
    min_order_size: Decimal
    liquidity_score: int
    source_market_hash: str
    book_snapshot_timestamp: str
    human_review_ref: str

    def to_engine_json(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "token_id": self.token_id,
            "side": "BUY",
            "order_type": "FOK",
            "active": self.active,
            "accepting_orders": self.accepting_orders,
            "closed": self.closed,
            "archived": self.archived,
            "best_ask": decimal_text(self.best_ask),
            "ask_size": decimal_text(self.ask_size),
            "spread_bps": self.spread_bps,
            "min_order_size": decimal_text(self.min_order_size),
            "liquidity_score": self.liquidity_score,
            "book_snapshot_timestamp": self.book_snapshot_timestamp,
            "human_review_ref": self.human_review_ref,
        }


class CandidateError(RuntimeError):
    def __init__(self, message: str, audit: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.audit = audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare candidate-market.json for a controlled canary review from "
            "public read-only Polymarket APIs."
        )
    )
    parser.add_argument("--output", required=True, type=Path, help="Path for candidate-market.json")
    parser.add_argument("--audit-output", type=Path, help="Optional audit sidecar JSON path")
    parser.add_argument(
        "--human-review-ref",
        required=True,
        help="External operator review/ticket reference approving this candidate market for BUY/FOK canary only.",
    )
    parser.add_argument("--gamma-url", default=DEFAULT_GAMMA_URL, help="Gamma API base URL")
    parser.add_argument("--clob-url", default=DEFAULT_CLOB_URL, help="CLOB API base URL")
    parser.add_argument("--max-markets", type=int, default=200, help="Maximum Gamma markets to inspect")
    parser.add_argument(
        "--max-order-notional-usd",
        default="1.00",
        help="Controlled canary order cap; candidate top ask notional must cover it",
    )
    parser.add_argument("--max-spread-bps", type=int, default=100, help="Maximum allowed spread in bps")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="HTTP timeout per request")
    return parser.parse_args()


def fetch_json(base_url: str, path: str, query: dict[str, str], timeout_seconds: float) -> Any:
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes"}
    return bool(value)


def as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal if decimal.is_finite() else None


def decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return "0" if text == "-0" else text


def parse_token_ids(market: dict[str, Any]) -> list[str]:
    for key in ("clobTokenIds", "clob_token_ids", "clobTokenIDs"):
        raw = market.get(key)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = [part.strip() for part in raw.split(",")]
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
    tokens = market.get("tokens")
    if isinstance(tokens, list):
        ids = []
        for token in tokens:
            if isinstance(token, dict):
                token_id = token.get("token_id") or token.get("tokenId") or token.get("id")
                if token_id:
                    ids.append(str(token_id))
        return ids
    return []


def market_id(market: dict[str, Any]) -> str:
    value = market.get("conditionId") or market.get("condition_id") or market.get("id")
    return "" if value is None else str(value)


def best_ask(book: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    asks = book.get("asks")
    if not isinstance(asks, list):
        return None
    parsed: list[tuple[Decimal, Decimal]] = []
    for ask in asks:
        if not isinstance(ask, dict):
            continue
        price = as_decimal(ask.get("price"))
        size = as_decimal(ask.get("size"))
        if price is not None and size is not None and price > 0 and size > 0:
            parsed.append((price, size))
    if not parsed:
        return None
    return min(parsed, key=lambda item: item[0])


def spread_bps(spread: dict[str, Any]) -> int | None:
    raw = spread.get("spread")
    value = as_decimal(raw)
    if value is None or value < 0:
        return None
    return int((value * Decimal("10000")).to_integral_value())


def liquidity_score(ask_size: Decimal) -> int:
    return max(0, int((ask_size * Decimal("1000000")).to_integral_value()))


def market_fingerprint(market: dict[str, Any]) -> str:
    compact = json.dumps(market, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def scan(args: argparse.Namespace) -> tuple[Candidate, dict[str, Any]]:
    order_cap = as_decimal(args.max_order_notional_usd)
    if order_cap is None or order_cap <= 0:
        raise CandidateError("--max-order-notional-usd must be a positive decimal")
    if args.max_markets <= 0:
        raise CandidateError("--max-markets must be positive")
    if args.max_spread_bps < 0:
        raise CandidateError("--max-spread-bps must be non-negative")
    human_review_ref = args.human_review_ref.strip()
    if not human_review_ref or "REPLACE_WITH" in human_review_ref:
        raise CandidateError("--human-review-ref must be a concrete external review reference")
    snapshot_at = dt.datetime.now(dt.UTC).isoformat()

    markets = fetch_json(
        args.gamma_url,
        "/markets",
        {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": str(args.max_markets),
            "order": "volume24hr",
            "ascending": "false",
        },
        args.timeout_seconds,
    )
    if not isinstance(markets, list):
        raise CandidateError("Gamma /markets response was not a JSON array")

    audit: dict[str, Any] = {
        "generated_at": snapshot_at,
        "source": "public-read-only",
        "remote_side_effects": False,
        "authorized_for_live": False,
        "side": "BUY",
        "order_type": "FOK",
        "human_review_ref_hash": hashlib.sha256(human_review_ref.encode()).hexdigest(),
        "gamma_url": args.gamma_url,
        "clob_url": args.clob_url,
        "max_markets": args.max_markets,
        "max_order_notional_usd": decimal_text(order_cap),
        "max_spread_bps": args.max_spread_bps,
        "inspected_markets": 0,
        "inspected_tokens": 0,
        "rejections": {
            "inactive": 0,
            "not_accepting_orders": 0,
            "closed": 0,
            "archived": 0,
            "missing_market_id": 0,
            "missing_token_id": 0,
            "book_unavailable": 0,
            "spread_unavailable": 0,
            "spread_too_wide": 0,
            "insufficient_top_ask_notional": 0,
            "min_order_size_above_order_size": 0,
        },
    }

    candidates: list[Candidate] = []
    for market in markets[: args.max_markets]:
        if not isinstance(market, dict):
            continue
        audit["inspected_markets"] += 1
        active = as_bool(market.get("active"))
        accepting_orders = as_bool(
            market.get("acceptingOrders", market.get("accepting_orders", market.get("enableOrderBook")))
        )
        closed = as_bool(market.get("closed"))
        archived = as_bool(market.get("archived"))
        if not active:
            audit["rejections"]["inactive"] += 1
            continue
        if not accepting_orders:
            audit["rejections"]["not_accepting_orders"] += 1
            continue
        if closed:
            audit["rejections"]["closed"] += 1
            continue
        if archived:
            audit["rejections"]["archived"] += 1
            continue
        condition_id = market_id(market)
        if not condition_id:
            audit["rejections"]["missing_market_id"] += 1
            continue
        token_ids = parse_token_ids(market)
        if not token_ids:
            audit["rejections"]["missing_token_id"] += 1
            continue
        for token_id in token_ids:
            audit["inspected_tokens"] += 1
            try:
                book = fetch_json(args.clob_url, "/book", {"token_id": token_id}, args.timeout_seconds)
            except Exception:
                audit["rejections"]["book_unavailable"] += 1
                continue
            if not isinstance(book, dict):
                audit["rejections"]["book_unavailable"] += 1
                continue
            top_ask = best_ask(book)
            min_order_size = as_decimal(book.get("min_order_size")) or Decimal("0")
            if top_ask is None:
                audit["rejections"]["book_unavailable"] += 1
                continue
            price, size = top_ask
            try:
                spread = fetch_json(args.clob_url, "/spread", {"token_id": token_id}, args.timeout_seconds)
            except Exception:
                audit["rejections"]["spread_unavailable"] += 1
                continue
            if not isinstance(spread, dict):
                audit["rejections"]["spread_unavailable"] += 1
                continue
            bps = spread_bps(spread)
            if bps is None:
                audit["rejections"]["spread_unavailable"] += 1
                continue
            if bps > args.max_spread_bps:
                audit["rejections"]["spread_too_wide"] += 1
                continue
            if price * size < order_cap:
                audit["rejections"]["insufficient_top_ask_notional"] += 1
                continue
            implied_order_size = order_cap / price
            if min_order_size > implied_order_size:
                audit["rejections"]["min_order_size_above_order_size"] += 1
                continue
            candidates.append(
                Candidate(
                    market_id=condition_id,
                    token_id=token_id,
                    active=True,
                    accepting_orders=True,
                    closed=False,
                    archived=False,
                    best_ask=price,
                    ask_size=size,
                    spread_bps=bps,
                    min_order_size=min_order_size,
                    liquidity_score=liquidity_score(size),
                    source_market_hash=market_fingerprint(market),
                    book_snapshot_timestamp=snapshot_at,
                    human_review_ref=human_review_ref,
                )
            )

    if not candidates:
        raise CandidateError("no candidate satisfied the configured canary market constraints", audit)
    selected = max(candidates, key=lambda item: item.liquidity_score)
    audit["candidate_count"] = len(candidates)
    audit["selected"] = {
        "market_id": selected.market_id,
        "token_id": selected.token_id,
        "source_market_hash": selected.source_market_hash,
        "spread_bps": selected.spread_bps,
        "implied_order_size": decimal_text(order_cap / selected.best_ask),
        "top_ask_notional_usd": decimal_text(selected.best_ask * selected.ask_size),
        "liquidity_score": selected.liquidity_score,
    }
    return selected, audit


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> int:
    args = parse_args()
    try:
        candidate, audit = scan(args)
    except CandidateError as exc:
        if args.audit_output and exc.audit is not None:
            exc.audit["status"] = "failed"
            exc.audit["error"] = str(exc)
            write_json(args.audit_output, exc.audit)
        print(f"candidate preparation failed: {exc}", file=sys.stderr)
        return 1
    write_json(args.output, candidate.to_engine_json())
    if args.audit_output:
        write_json(args.audit_output, audit)
    print(
        json.dumps(
            {
                "status": "ok",
                "candidate_market": str(args.output),
                "audit_output": str(args.audit_output) if args.audit_output else None,
                "remote_side_effects": False,
                "authorized_for_live": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
