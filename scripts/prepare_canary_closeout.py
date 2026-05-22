#!/usr/bin/env python3
"""Build a closeout report for a completed controlled canary package.

The script is intentionally read-only. It summarizes local package evidence and
release sidecars, and it refuses to turn partial readback into a stronger claim
than the evidence supports.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "dist" / "pmx-canary-review-v0.26-20260522T164451Z-gtc-post-only-acctb-go"
DEFAULT_RELEASE_ZIP = ROOT / "dist" / "polymarket-execution-suite-v0.26.0.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare machine-readable and human closeout reports for a controlled canary package."
    )
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--release-zip", type=Path, default=DEFAULT_RELEASE_ZIP)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def required_json(package_dir: Path, name: str) -> dict[str, Any]:
    path = package_dir / name
    if not path.exists():
        raise SystemExit(f"required closeout evidence missing: {path}")
    return load_json(path)


def optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def decimal_text(value: Any) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise SystemExit(f"invalid decimal value in closeout evidence: {value!r}")
    if not parsed.is_finite():
        raise SystemExit(f"non-finite decimal value in closeout evidence: {value!r}")
    normalized = parsed.normalize()
    text = format(normalized, "f")
    return "0" if text == "-0" else text


def decimal_value(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise SystemExit(f"invalid decimal value in closeout evidence: {value!r}")
    if not parsed.is_finite():
        raise SystemExit(f"non-finite decimal value in closeout evidence: {value!r}")
    return parsed


def lget(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def build_closeout(package_dir: Path, release_zip: Path) -> dict[str, Any]:
    report = required_json(package_dir, "post-canary-report.json")
    candidate = required_json(package_dir, "candidate-market.json")
    order_status = required_json(package_dir, "order-status-query.json")
    trade_query = required_json(package_dir, "trade-fill-query.json")
    account_activity = required_json(package_dir, "account-activity-readback.json")
    sidecar = optional_json(release_zip.with_suffix(release_zip.suffix + ".evidence.json"))

    limit_price_value = decimal_value(candidate["limit_price"])
    target_size_value = decimal_value(candidate["target_size"])
    notional_value = limit_price_value * target_size_value
    limit_price = decimal_text(limit_price_value)
    target_size = decimal_text(target_size_value)
    notional = decimal_text(notional_value)

    checks = {
        "candidate_side_buy": candidate.get("side") == "BUY",
        "candidate_order_type_gtc": candidate.get("order_type") == "GTC",
        "candidate_post_only": candidate.get("post_only") is True,
        "candidate_uses_target_size_as_size": decimal_value(
            lget(report, "market_candidate", "target_size")
        )
        == target_size_value,
        "notional_is_price_times_size": decimal_value(
            lget(report, "market_candidate", "notional_usd")
        )
        == notional_value,
        "order_remote_status_canceled": lget(order_status, "remote_status") == "CANCELED",
        "order_size_matched_zero": decimal_text(lget(order_status, "size_matched", default="0")) == "0",
        "trade_query_zero_matching_trades": lget(trade_query, "matching_trades_count") == 0,
        "trade_query_zero_matching_size": decimal_text(lget(trade_query, "matching_size_total", default="0")) == "0",
        "account_activity_zero_matching_activity": lget(account_activity, "matching_activity_count") == 0,
        "account_activity_zero_matching_trades": lget(account_activity, "matching_trade_count") == 0,
        "account_activity_zero_open_positions": lget(account_activity, "matching_open_position_count") == 0,
        "account_activity_zero_closed_positions": lget(account_activity, "matching_closed_position_count") == 0,
        "account_activity_value_zero": all(
            decimal_text(item.get("value", "0")) == "0"
            for item in account_activity.get("values", [])
            if isinstance(item, dict)
        ),
        "no_raw_signed_order_exposed": not any(
            bool(lget(item, "raw_signed_order_exposed", default=False))
            for item in [report, order_status, trade_query, account_activity]
        ),
        "no_second_order_placed_by_closeout": report.get("no_second_order_placed_by_closure") is True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit("closeout evidence checks failed: " + ", ".join(failed))

    evidence_files = []
    for path in sorted(package_dir.iterdir()):
        if path.is_file():
            evidence_files.append(
                {
                    "path": path.name,
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
            )

    release_binding: dict[str, Any] = {
        "release_zip_path": str(release_zip.relative_to(ROOT)) if release_zip.exists() else str(release_zip),
        "release_zip_sha256": sha256(release_zip) if release_zip.exists() else None,
        "release_evidence_sidecar_path": str(release_zip.with_suffix(release_zip.suffix + ".evidence.json").relative_to(ROOT))
        if release_zip.with_suffix(release_zip.suffix + ".evidence.json").exists()
        else None,
    }
    if isinstance(sidecar, dict):
        release_binding.update(
            {
                "sidecar_artifact_sha256": lget(sidecar, "artifact", "sha256"),
                "sidecar_git_head": lget(sidecar, "source", "git_head"),
                "sidecar_submodules": lget(sidecar, "source", "submodules", default=[]),
                "canonical_evidence_manifest_sha256": lget(
                    sidecar, "canonical_evidence", "manifest_sha256"
                ),
            }
        )

    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "package": str(package_dir.relative_to(ROOT)),
        "decision": "controlled_real_funds_canary_closed",
        "release_binding": release_binding,
        "remote_order_id": lget(report, "remote_order_readback", "order_id"),
        "canary_semantics": {
            "scope": "REAL_FUNDS_CANARY",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "target_size_semantics": "outcome_shares",
            "size": target_size,
            "limit_price": limit_price,
            "notional_usd": notional,
            "notional_rule": "limit_price * size",
            "min_funds_goal": "minimize expected funds at risk while satisfying current exchange size rule",
        },
        "readback_summary": {
            "remote_status": lget(order_status, "remote_status"),
            "size_matched": lget(order_status, "size_matched"),
            "matching_trades_count": lget(trade_query, "matching_trades_count"),
            "matching_size_total": lget(trade_query, "matching_size_total"),
            "matching_activity_count": lget(account_activity, "matching_activity_count"),
            "matching_trade_count": lget(account_activity, "matching_trade_count"),
            "matching_open_position_count": lget(account_activity, "matching_open_position_count"),
            "matching_closed_position_count": lget(account_activity, "matching_closed_position_count"),
            "matching_value_record_count": lget(account_activity, "matching_value_record_count"),
            "value_records": account_activity.get("values", []),
            "raw_signed_order_exposed": False,
        },
        "evidence_checks": checks,
        "evidence_files": evidence_files,
        "limitations": [
            "This is a closeout over order status, trade query, and public Data API account activity endpoints.",
            "It is not a formal exchange/account statement export.",
            "It does not authorize a second real-funds canary or production/live trading.",
        ],
        "next_required_actions": [
            "Use a fresh reviewed release decision before any future armed canary.",
            "Regenerate candidate-market.json when exchange min size, order type support, or tick rules change.",
            "Keep GTC post-only cancel semantics separate from general live submit semantics.",
        ],
    }


def markdown(closeout: dict[str, Any]) -> str:
    checks = closeout["evidence_checks"]
    release = closeout["release_binding"]
    semantics = closeout["canary_semantics"]
    readback = closeout["readback_summary"]
    lines = [
        "# Controlled Canary Closeout",
        "",
        f"- Package: `{closeout['package']}`",
        f"- Decision: `{closeout['decision']}`",
        f"- Release zip SHA-256: `{release.get('release_zip_sha256')}`",
        f"- Root git head: `{release.get('sidecar_git_head')}`",
        f"- Remote order id: `{closeout['remote_order_id']}`",
        "",
        "## Semantics",
        "",
        f"- Execution style: `{semantics['execution_style']}`",
        f"- Order: `{semantics['side']}/{semantics['order_type']}` post-only",
        f"- Size: `{semantics['size']}` outcome shares",
        f"- Limit price: `{semantics['limit_price']}`",
        f"- Notional rule: `{semantics['notional_rule']}` = `{semantics['notional_usd']}`",
        "",
        "## Readback",
        "",
        f"- Remote status: `{readback['remote_status']}`",
        f"- Size matched: `{readback['size_matched']}`",
        f"- Matching trades: `{readback['matching_trades_count']}`",
        f"- Matching account activity: `{readback['matching_activity_count']}`",
        f"- Matching open positions: `{readback['matching_open_position_count']}`",
        f"- Matching closed positions: `{readback['matching_closed_position_count']}`",
        "",
        "## Checks",
        "",
    ]
    for name, ok in checks.items():
        lines.append(f"- `{name}`: `{str(ok).lower()}`")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This is not a formal exchange/account statement export.",
            "- This does not authorize another canary or production/live trading.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    package_dir = args.package_dir.resolve()
    release_zip = args.release_zip.resolve()
    closeout = build_closeout(package_dir, release_zip)
    output_json = args.output_json or package_dir / "closeout.json"
    output_md = args.output_md or package_dir / "CLOSEOUT.md"
    output_json.write_text(json.dumps(closeout, indent=2, sort_keys=True) + "\n")
    output_md.write_text(markdown(closeout))
    print(json.dumps({"status": "ok", "json": str(output_json), "md": str(output_md)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
