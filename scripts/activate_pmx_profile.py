#!/usr/bin/env python3
"""Activate one local Polymarket account profile into generic runtime env vars.

The profile label is a local selector such as ``acct_b``. The source inventory
also provides opaque ``ACCOUNT_ID`` and ``PROFILE_REF`` values. Those runtime
identity fields are copied through as-is and are not normalized by this script.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNATURE_TYPE_ALIASES = {
    "EOA": "EOA",
    "0": "EOA",
    "POLY_1271": "POLY_1271",
    "POLY1271": "POLY_1271",
    "DEPOSIT_WALLET": "POLY_1271",
    "3": "POLY_1271",
}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"invalid env assignment in {path}: {raw_line}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_profile_source(source_env_file: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    if source_env_file is not None:
        values.update(parse_env_file(source_env_file))
    return values


def normalize_profile_name(profile: str) -> str:
    cleaned = profile.strip()
    if not cleaned:
        raise SystemExit("profile name must not be empty")
    return cleaned


def profile_prefix(profile: str) -> str:
    return f"PMX_PROFILE_{profile.upper()}_"


def normalize_signature_type(raw: str) -> str:
    normalized = raw.strip().upper()
    try:
        return SIGNATURE_TYPE_ALIASES[normalized]
    except KeyError as exc:
        raise SystemExit(
            "PMX_CLOB_SIGNATURE_TYPE must be EOA or POLY_1271; numeric aliases 0 and 3 are accepted"
        ) from exc


def activate_profile(profile: str, source_values: dict[str, str]) -> dict[str, str]:
    normalized = normalize_profile_name(profile)
    prefix = profile_prefix(normalized)
    required_fields = {
        "ACCOUNT_ID": "PMX_ACTIVE_ACCOUNT_ID",
        "PROFILE_REF": "PMX_ACTIVE_PROFILE_REF",
        "POLYMARKET_PRIVATE_KEY": "POLYMARKET_PRIVATE_KEY",
        "POLY_API_KEY": "POLY_API_KEY",
        "POLY_API_SECRET": "POLY_API_SECRET",
        "POLY_API_PASSPHRASE": "POLY_API_PASSPHRASE",
        "CLOB_SIGNATURE_TYPE": "PMX_CLOB_SIGNATURE_TYPE",
    }
    missing = [
        f"{prefix}{field}"
        for field in required_fields
        if not source_values.get(f"{prefix}{field}", "").strip()
    ]
    if missing:
        raise SystemExit(
            "missing required profile source variables: " + ", ".join(sorted(missing))
        )
    activated = {"PMX_ACTIVE_ACCOUNT_PROFILE": normalized}
    for source_suffix, target_key in required_fields.items():
        activated[target_key] = source_values[f"{prefix}{source_suffix}"].strip()
    signature_type = normalize_signature_type(activated["PMX_CLOB_SIGNATURE_TYPE"])
    activated["PMX_CLOB_SIGNATURE_TYPE"] = signature_type
    funder = source_values.get(f"{prefix}CLOB_FUNDER", "").strip()
    if signature_type == "POLY_1271":
        if not funder:
            raise SystemExit("POLY_1271 profile requires PMX_CLOB_FUNDER")
        activated["PMX_CLOB_FUNDER"] = funder
    elif funder:
        activated["PMX_CLOB_FUNDER"] = funder
    return activated


def write_runtime_env(output: Path, activated: dict[str, str]) -> None:
    lines = [
        "# Generated runtime env for a single active Polymarket account profile.",
        "# This file is runtime-facing only; do not store PMX_PROFILE_* source inventory here.",
        "",
        "# Active local account profile label.",
        f"PMX_ACTIVE_ACCOUNT_PROFILE={activated['PMX_ACTIVE_ACCOUNT_PROFILE']}",
        "",
        "# Active local account id bound to the selected profile.",
        f"PMX_ACTIVE_ACCOUNT_ID={activated['PMX_ACTIVE_ACCOUNT_ID']}",
        "",
        "# Local non-secret profile reference.",
        f"PMX_ACTIVE_PROFILE_REF={activated['PMX_ACTIVE_PROFILE_REF']}",
        "",
        "# Generic runtime signer material.",
        f"POLYMARKET_PRIVATE_KEY={activated['POLYMARKET_PRIVATE_KEY']}",
        "",
        "# Generic runtime L2 API key.",
        f"POLY_API_KEY={activated['POLY_API_KEY']}",
        "",
        "# Generic runtime L2 API secret.",
        f"POLY_API_SECRET={activated['POLY_API_SECRET']}",
        "",
        "# Generic runtime L2 API passphrase.",
        f"POLY_API_PASSPHRASE={activated['POLY_API_PASSPHRASE']}",
        "",
        "# Generic runtime signature type for the active account.",
        f"PMX_CLOB_SIGNATURE_TYPE={activated['PMX_CLOB_SIGNATURE_TYPE']}",
    ]
    funder = activated.get("PMX_CLOB_FUNDER")
    if funder:
        lines.extend(
            [
                "",
                "# Generic runtime CLOB funder for deposit-wallet / Poly1271 auth.",
                f"PMX_CLOB_FUNDER={funder}",
            ]
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="profile label, for example acct_b")
    parser.add_argument(
        "--source-env-file",
        type=Path,
        help="optional local source inventory file containing PMX_PROFILE_<PROFILE>_* values",
    )
    parser.add_argument("--output", required=True, type=Path, help="runtime env output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = load_profile_source(args.source_env_file)
    activated = activate_profile(args.profile, source)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_runtime_env(output, activated)
    print(
        json.dumps(
            {
                "status": "pass",
                "profile": activated["PMX_ACTIVE_ACCOUNT_PROFILE"],
                "account_id": activated["PMX_ACTIVE_ACCOUNT_ID"],
                "profile_ref": activated["PMX_ACTIVE_PROFILE_REF"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
