#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import yaml

from validate_contracts_executor import (
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate integration contracts across OpenAPI, Rust, Hermes, SQL, and release governance."
    )
    parser.parse_args(argv)
    spec = yaml.safe_load(OPENAPI.read_text())
    validate_paths_and_statuses(spec)
    validate_no_public_forbidden_tokens(spec)
    validate_additional_properties(spec)
    validate_python_field_parity(spec)
    validate_sql_idempotency()
    validate_rust_deny_unknown_fields()
    validate_v04_source_landings()
    validate_v07_source_landings()
    validate_v08_dependency_and_sdk_policy()
    validate_v09_official_adapter_boundary()
    validate_v12_service_layer()
    validate_v15_admin_audit_and_runtime_provider()
    validate_v16_postgres_runtime_provider()
    validate_v19_redaction_and_live_guard()
    validate_v20_plan_storage_and_packaging()
    validate_v21_sign_only_and_runtime_models()
    validate_v23_lifecycle_query_and_hardening()
    validate_current_hermes_client_surface()
    validate_current_evidence_manifest_guard()
    validate_current_docs_and_release_governance()
    validate_controlled_canary_release_decision_governance()
    validate_canary_candidate_market_prep_boundary()
    validate_single_host_deployment_governance()
    validate_v28_production_live_candidate_guard()
    print(json.dumps({"status": "ok", "paths": len(spec["paths"]), "schemas": len(spec["components"]["schemas"])}))


if __name__ == "__main__":
    main()
