#!/usr/bin/env python3
"""Activate one local Polymarket account profile into generic runtime env vars."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_SIGNATURE_TYPES = {"EOA", "POLY_1271"}
PROFILE_RE = re.compile(r"^[A-Za-z0-9_]+$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SECRET_KEYS = {"POLYMARKET_PRIVATE_KEY", "POLY_API_SECRET", "POLY_API_PASSPHRASE"}
RUNTIME_SECRET_DIR_PARTS = {".secrets", "secrets", "runtime-secrets"}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            raise SystemExit(f"unsupported export syntax in {path}:{line_number}")
        if "=" not in line:
            raise SystemExit(f"invalid env assignment in {path}:{line_number}: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not ENV_KEY_RE.fullmatch(key):
            raise SystemExit(f"invalid env key in {path}:{line_number}: {key}")
        if key in values:
            raise SystemExit(f"duplicate env key in {path}:{line_number}: {key}")
        if any(token in value for token in ["\n", "\r"]):
            raise SystemExit(f"unsupported multiline env value in {path}:{line_number}: {key}")
        if (value.startswith("'") or value.startswith('"')) and not (
            len(value) >= 2 and value[0] == value[-1]
        ):
            raise SystemExit(f"unterminated quoted env value in {path}:{line_number}: {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_profile_source(source_env_file: Path | None, *, allow_ambient_env: bool = False) -> dict[str, str]:
    values = dict(os.environ) if allow_ambient_env else {}
    if source_env_file is not None:
        values.update(parse_env_file(source_env_file))
    if source_env_file is None and not allow_ambient_env:
        raise SystemExit("source env file is required unless --allow-ambient-env is set")
    return values


def normalize_profile_name(profile: str) -> str:
    cleaned = profile.strip()
    if not cleaned:
        raise SystemExit("profile name must not be empty")
    if not PROFILE_RE.fullmatch(cleaned):
        raise SystemExit("profile name must match ^[A-Za-z0-9_]+$")
    return cleaned


def profile_prefix(profile: str) -> str:
    return f"PMX_PROFILE_{profile.upper()}_"


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
    signature_type = activated["PMX_CLOB_SIGNATURE_TYPE"]
    if signature_type not in VALID_SIGNATURE_TYPES:
        raise SystemExit(
            "PMX_CLOB_SIGNATURE_TYPE must be one of "
            + ", ".join(sorted(VALID_SIGNATURE_TYPES))
        )
    funder = source_values.get(f"{prefix}CLOB_FUNDER", "").strip()
    if signature_type == "POLY_1271":
        if not funder:
            raise SystemExit("POLY_1271 profile requires PMX_CLOB_FUNDER")
        activated["PMX_CLOB_FUNDER"] = funder
    elif funder:
        activated["PMX_CLOB_FUNDER"] = funder
    return activated


def path_inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def allowed_secret_output_path(output: Path) -> bool:
    resolved = output.resolve()
    if not path_inside_repo(resolved):
        return True
    rel_parts = set(resolved.relative_to(ROOT.resolve()).parts)
    return bool(rel_parts & RUNTIME_SECRET_DIR_PARTS)


def chmod_owner_rw(path: Path) -> None:
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def write_runtime_env(output: Path, activated: dict[str, str], *, write_secrets: bool = False) -> None:
    if write_secrets and not allowed_secret_output_path(output):
        raise SystemExit(
            "refusing to write runtime secrets inside repository outside .secrets/, secrets/, or runtime-secrets/"
        )
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
        "# Generic runtime L2 API key.",
        f"POLY_API_KEY={activated['POLY_API_KEY']}",
        "",
        "# Generic runtime signature type for the active account.",
        f"PMX_CLOB_SIGNATURE_TYPE={activated['PMX_CLOB_SIGNATURE_TYPE']}",
    ]
    if write_secrets:
        lines.extend(
            [
                "",
                "# Generic runtime signer material.",
                f"POLYMARKET_PRIVATE_KEY={activated['POLYMARKET_PRIVATE_KEY']}",
                "",
                "# Generic runtime L2 API secret.",
                f"POLY_API_SECRET={activated['POLY_API_SECRET']}",
                "",
                "# Generic runtime L2 API passphrase.",
                f"POLY_API_PASSPHRASE={activated['POLY_API_PASSPHRASE']}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "# Secret values intentionally omitted. Re-run with --write-secrets and an approved runtime secret path when needed.",
            ]
        )
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
    chmod_owner_rw(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="profile label, for example acct_b")
    parser.add_argument(
        "--source-env-file",
        type=Path,
        help="optional local source inventory file containing PMX_PROFILE_<PROFILE>_* values",
    )
    parser.add_argument("--allow-ambient-env", action="store_true", help="allow PMX_PROFILE_* source values from the current process environment")
    parser.add_argument("--write-secrets", action="store_true", help="write private key/API secret/passphrase to the runtime env file")
    parser.add_argument("--output", required=True, type=Path, help="runtime env output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = load_profile_source(args.source_env_file, allow_ambient_env=args.allow_ambient_env)
    activated = activate_profile(args.profile, source)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_runtime_env(output, activated, write_secrets=args.write_secrets)
    print(
        json.dumps(
            {
                "status": "pass",
                "profile": activated["PMX_ACTIVE_ACCOUNT_PROFILE"],
                "account_id": activated["PMX_ACTIVE_ACCOUNT_ID"],
                "profile_ref": activated["PMX_ACTIVE_PROFILE_REF"],
                "output": str(output),
                "secrets_written": bool(args.write_secrets),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
