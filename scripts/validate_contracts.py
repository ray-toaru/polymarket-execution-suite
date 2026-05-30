#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from validate_contracts_executor import (
    validate_store_and_backend_structure,
    validate_v04_source_landings,
    validate_v07_source_landings,
    validate_v08_dependency_and_sdk_policy,
    validate_v09_official_adapter_boundary,
    validate_v12_service_layer,
    validate_v15_admin_audit_and_runtime_provider,
    validate_v16_postgres_runtime_provider,
    validate_v19_redaction_and_live_guard,
    validate_v20_plan_storage_and_packaging,
    validate_v21_sign_only_and_runtime_models,
    validate_v23_lifecycle_query_and_hardening,
)
from validate_contracts_governance import (
    validate_canary_candidate_market_prep_boundary,
    validate_controlled_canary_release_decision_governance,
    validate_current_docs_and_release_governance,
    validate_current_evidence_manifest_guard,
    validate_current_hermes_client_surface,
    validate_single_host_deployment_governance,
    validate_v28_production_live_candidate_guard,
)
from validate_contracts_support import OPENAPI
from validate_contracts_surface import (
    validate_additional_properties,
    validate_no_public_forbidden_tokens,
    validate_paths_and_statuses,
    validate_python_field_parity,
    validate_rust_deny_unknown_fields,
    validate_sql_idempotency,
)


@dataclass(frozen=True)
class ValidatorSpec:
    id: str
    category: str
    uses_spec: bool
    fn: object


VALIDATORS = [
    ValidatorSpec("paths_and_statuses", "surface", True, validate_paths_and_statuses),
    ValidatorSpec("no_public_forbidden_tokens", "surface", True, validate_no_public_forbidden_tokens),
    ValidatorSpec("additional_properties", "surface", True, validate_additional_properties),
    ValidatorSpec("python_field_parity", "surface", True, validate_python_field_parity),
    ValidatorSpec("sql_idempotency", "surface", False, validate_sql_idempotency),
    ValidatorSpec("rust_deny_unknown_fields", "surface", False, validate_rust_deny_unknown_fields),
    ValidatorSpec("v04_source_landings", "executor", False, validate_v04_source_landings),
    ValidatorSpec("v07_source_landings", "executor", False, validate_v07_source_landings),
    ValidatorSpec("v08_dependency_and_sdk_policy", "executor", False, validate_v08_dependency_and_sdk_policy),
    ValidatorSpec("v09_official_adapter_boundary", "executor", False, validate_v09_official_adapter_boundary),
    ValidatorSpec("v12_service_layer", "executor", True, validate_v12_service_layer),
    ValidatorSpec("v15_admin_audit_and_runtime_provider", "executor", True, validate_v15_admin_audit_and_runtime_provider),
    ValidatorSpec("v16_postgres_runtime_provider", "executor", True, validate_v16_postgres_runtime_provider),
    ValidatorSpec("v19_redaction_and_live_guard", "executor", True, validate_v19_redaction_and_live_guard),
    ValidatorSpec("v20_plan_storage_and_packaging", "executor", True, validate_v20_plan_storage_and_packaging),
    ValidatorSpec("v21_sign_only_and_runtime_models", "executor", True, validate_v21_sign_only_and_runtime_models),
    ValidatorSpec("store_and_backend_structure", "executor", False, validate_store_and_backend_structure),
    ValidatorSpec("v23_lifecycle_query_and_hardening", "executor", True, validate_v23_lifecycle_query_and_hardening),
    ValidatorSpec("current_hermes_client_surface", "governance", False, validate_current_hermes_client_surface),
    ValidatorSpec("current_evidence_manifest_guard", "governance", False, validate_current_evidence_manifest_guard),
    ValidatorSpec("current_docs_and_release_governance", "governance", False, validate_current_docs_and_release_governance),
    ValidatorSpec("controlled_canary_release_decision_governance", "governance", False, validate_controlled_canary_release_decision_governance),
    ValidatorSpec("canary_candidate_market_prep_boundary", "governance", False, validate_canary_candidate_market_prep_boundary),
    ValidatorSpec("single_host_deployment_governance", "governance", False, validate_single_host_deployment_governance),
    ValidatorSpec("v28_production_live_candidate_guard", "governance", False, validate_v28_production_live_candidate_guard),
]


def error_message(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__


def run_validator(validator: ValidatorSpec, spec: dict[str, Any]) -> dict[str, str]:
    try:
        if validator.uses_spec:
            validator.fn(spec)
        else:
            validator.fn()
    except BaseException as exc:
        return {
            "id": validator.id,
            "category": validator.category,
            "status": "fail",
            "error_type": exc.__class__.__name__,
            "error": error_message(exc),
        }
    return {
        "id": validator.id,
        "category": validator.category,
        "status": "pass",
    }


def build_report(spec: dict[str, Any], validators: list[ValidatorSpec] | None = None) -> dict[str, Any]:
    active_validators = validators or VALIDATORS
    checks = []
    for validator in active_validators:
        checks.append(run_validator(validator, spec))
    failed_checks = [check for check in checks if check["status"] != "pass"]
    return {
        "status": "ok" if not failed_checks else "fail",
        "paths": len(spec["paths"]),
        "schemas": len(spec["components"]["schemas"]),
        "check_count": len(checks),
        "failed_check_count": len(failed_checks),
        "failed_check_ids": [check["id"] for check in failed_checks],
        "checks": checks,
    }


def write_report(report: dict[str, Any], report_file: str | Path) -> None:
    path = Path(report_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate integration contracts across OpenAPI, Rust, Hermes, SQL, and release governance."
    )
    parser.add_argument("--report-file", help="Optional JSON file path for the machine-readable validation report.")
    args = parser.parse_args(argv)
    spec = yaml.safe_load(OPENAPI.read_text())
    report = build_report(spec)
    if args.report_file:
        write_report(report, args.report_file)
    print(json.dumps(report, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
