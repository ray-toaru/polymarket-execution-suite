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
import re
import shlex
import stat


ROOT = Path(__file__).resolve().parents[1]
SIGNATURE_TYPE_ALIASES = {
    "EOA": "EOA",
    "0": "EOA",
    "POLY_1271": "POLY_1271",
    "POLY1271": "POLY_1271",
    "DEPOSIT_WALLET": "POLY_1271",
    "3": "POLY_1271",
}

IDENTITY_KEYS = {
    "PMX_ACTIVE_ACCOUNT_PROFILE",
    "PMX_ACTIVE_ACCOUNT_ID",
    "PMX_ACTIVE_PROFILE_REF",
}
SECRET_KEYS = {
    "POLYMARKET_PRIVATE_KEY",
    "POLY_API_KEY",
    "POLY_API_SECRET",
    "POLY_API_PASSPHRASE",
    "PMX_CLOB_SIGNATURE_TYPE",
    "PMX_CLOB_FUNDER",
}
UNSUPPORTED_ENV_TOKENS = ("`", "$(", "${", "&&", "||", ";")
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
RUNTIME_FORBIDDEN_TEXT = (
    "PMX_PROFILE_",
    "PMX_ACCT_",
    "raw_signed_payload",
    "raw_signature",
    "SignedOrderEnvelope",
)


def parse_env_value(raw_value: str, *, path: Path, raw_line: str) -> str:
    value = raw_value
    if any(token in value for token in UNSUPPORTED_ENV_TOKENS):
        raise SystemExit(
            f"unsupported shell-style env value in {path}: {raw_line}"
        )
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped[0] in {"'", '"'}:
        try:
            parsed = shlex.split(stripped, posix=True)
        except ValueError as exc:
            raise SystemExit(f"invalid quoted env value in {path}: {raw_line}") from exc
        if len(parsed) != 1:
            raise SystemExit(f"invalid quoted env value in {path}: {raw_line}")
        return parsed[0]
    return value


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        stripped = raw_line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            raise SystemExit(f"unsupported export syntax in {path}: {raw_line}")
        if "=" not in raw_line:
            raise SystemExit(f"invalid env assignment in {path}: {raw_line}")
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_PATTERN.fullmatch(key):
            raise SystemExit(f"invalid env variable name in {path}: {key!r}")
        if key in values:
            raise SystemExit(f"duplicate env variable in {path}: {key}")
        values[key] = parse_env_value(value, path=path, raw_line=raw_line)
    return values


def load_profile_source(source_env_file: Path | None) -> dict[str, str]:
    if source_env_file is None:
        return dict(os.environ)
    return parse_env_file(source_env_file)


def normalize_profile_name(profile: str) -> str:
    cleaned = profile.strip()
    if not cleaned:
        raise SystemExit("profile name must not be empty")
    if not PROFILE_NAME_PATTERN.fullmatch(cleaned):
        raise SystemExit("profile name may contain only letters, numbers, and underscores")
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
        raise SystemExit(f"missing required profile source variables for profile {normalized}")
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
    return activated


def runtime_secrets_output_path(output: Path) -> Path:
    if output.suffix == ".example":
        return output.with_name(output.stem + ".secrets" + output.suffix)
    return output.with_name(output.name + ".secrets")


def write_restrictive_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise SystemExit(f"failed to set restrictive permissions on {path}: {exc}") from exc


def verify_runtime_outputs(output: Path, *, write_secrets: bool) -> None:
    identity_values = parse_env_file(output)
    if set(identity_values) != IDENTITY_KEYS:
        raise SystemExit(f"runtime identity env keys do not match expected contract in {output}")
    for key, value in identity_values.items():
        haystack = f"{key}={value}"
        for forbidden in RUNTIME_FORBIDDEN_TEXT:
            if forbidden in haystack:
                raise SystemExit(f"forbidden runtime text {forbidden!r} present in {output}")
    secrets_output = runtime_secrets_output_path(output)
    if not write_secrets:
        if secrets_output.exists():
            raise SystemExit(f"unexpected companion secrets file present at {secrets_output}")
        return
    if not secrets_output.is_file():
        raise SystemExit(f"expected companion secrets file at {secrets_output}")
    secret_values = parse_env_file(secrets_output)
    unexpected = set(secret_values) - SECRET_KEYS
    if unexpected:
        raise SystemExit(
            f"unexpected runtime secret keys in {secrets_output}: {', '.join(sorted(unexpected))}"
        )
    required_secret_keys = SECRET_KEYS - {"PMX_CLOB_FUNDER"}
    if not required_secret_keys.issubset(secret_values):
        raise SystemExit(f"missing required runtime secret keys in {secrets_output}")
    for key, value in secret_values.items():
        haystack = f"{key}={value}"
        for forbidden in RUNTIME_FORBIDDEN_TEXT:
            if forbidden in haystack:
                raise SystemExit(f"forbidden runtime text {forbidden!r} present in {secrets_output}")


def write_runtime_env(output: Path, activated: dict[str, str], *, write_secrets: bool) -> None:
    if write_secrets:
        raise SystemExit(
            "local runtime secret file generation is disabled; provide secrets via an external env file only"
        )
    lines = [
        "# Generated runtime env for a single active Polymarket account profile.",
        "# This file carries active identity only; do not store PMX_PROFILE_* source inventory here.",
        "",
        "# Active local account profile label.",
        f"PMX_ACTIVE_ACCOUNT_PROFILE={activated['PMX_ACTIVE_ACCOUNT_PROFILE']}",
        "",
        "# Active local account id bound to the selected profile.",
        f"PMX_ACTIVE_ACCOUNT_ID={activated['PMX_ACTIVE_ACCOUNT_ID']}",
        "",
        "# Local non-secret profile reference.",
        f"PMX_ACTIVE_PROFILE_REF={activated['PMX_ACTIVE_PROFILE_REF']}",
    ]
    lines.extend(
        [
            "",
            "# Secret-bearing runtime fields intentionally omitted.",
            "# Local secret file generation is disabled; supply an explicit external secrets env file at runtime.",
        ]
    )
    write_restrictive_file(output, "\n".join(lines) + "\n")
    verify_runtime_outputs(output, write_secrets=write_secrets)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="profile label, for example acct_b")
    parser.add_argument(
        "--source-env-file",
        type=Path,
        help="optional local source inventory file containing PMX_PROFILE_<PROFILE>_* values",
    )
    parser.add_argument("--output", required=True, type=Path, help="runtime env output path")
    parser.add_argument(
        "--write-secrets",
        action="store_true",
        help=(
            "Deprecated and rejected. Local secret-bearing runtime env generation is disabled; "
            "use an external explicit secrets env file instead."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = load_profile_source(args.source_env_file)
    activated = activate_profile(args.profile, source)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_runtime_env(output, activated, write_secrets=args.write_secrets)
    print(
        json.dumps(
            {
                "status": "pass",
                "profile": activated["PMX_ACTIVE_ACCOUNT_PROFILE"],
                "secret_material_written": args.write_secrets,
                "output": str(output),
                "secrets_output": (
                    str(runtime_secrets_output_path(output)) if args.write_secrets else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
