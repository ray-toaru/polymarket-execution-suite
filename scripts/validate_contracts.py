#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from validate_contracts_runner import (
    VALIDATORS,
    ValidatorSpec,
    build_report,
    load_openapi_spec,
    write_report,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate integration contracts across OpenAPI, Rust, Hermes, SQL, and release governance."
    )
    parser.add_argument("--report-file", help="Optional JSON file path for the machine-readable validation report.")
    args = parser.parse_args(argv)
    spec = load_openapi_spec()
    report = build_report(spec)
    if args.report_file:
        write_report(report, args.report_file)
    print(json.dumps(report, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
