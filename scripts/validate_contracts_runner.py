from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_contracts_runner.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_validate_contracts_runner", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

json = _ENGINE.json
Path = _ENGINE.Path
Any = _ENGINE.Any
yaml = _ENGINE.yaml
ValidatorSpec = _ENGINE.ValidatorSpec
VALIDATORS = _ENGINE.VALIDATORS
OPENAPI = _ENGINE.OPENAPI
validate_paths_and_statuses = _ENGINE.validate_paths_and_statuses
validate_critical_contract_shapes = _ENGINE.validate_critical_contract_shapes
validate_no_public_forbidden_tokens = _ENGINE.validate_no_public_forbidden_tokens
validate_additional_properties = _ENGINE.validate_additional_properties
validate_python_field_parity = _ENGINE.validate_python_field_parity
validate_sql_idempotency = _ENGINE.validate_sql_idempotency
validate_rust_deny_unknown_fields = _ENGINE.validate_rust_deny_unknown_fields
validate_v04_source_landings = _ENGINE.validate_v04_source_landings
validate_v07_source_landings = _ENGINE.validate_v07_source_landings
validate_v08_dependency_and_sdk_policy = _ENGINE.validate_v08_dependency_and_sdk_policy
validate_v09_official_adapter_boundary = _ENGINE.validate_v09_official_adapter_boundary
validate_v12_service_layer = _ENGINE.validate_v12_service_layer
validate_v15_admin_audit_and_runtime_provider = _ENGINE.validate_v15_admin_audit_and_runtime_provider
validate_v16_postgres_runtime_provider = _ENGINE.validate_v16_postgres_runtime_provider
validate_v19_redaction_and_live_guard = _ENGINE.validate_v19_redaction_and_live_guard
validate_v20_plan_storage_and_packaging = _ENGINE.validate_v20_plan_storage_and_packaging
validate_v21_sign_only_and_runtime_models = _ENGINE.validate_v21_sign_only_and_runtime_models
validate_store_and_backend_structure = _ENGINE.validate_store_and_backend_structure
validate_v23_lifecycle_query_and_hardening = _ENGINE.validate_v23_lifecycle_query_and_hardening
validate_current_hermes_client_surface = _ENGINE.validate_current_hermes_client_surface
validate_current_evidence_manifest_guard = _ENGINE.validate_current_evidence_manifest_guard
validate_current_docs_and_release_governance = _ENGINE.validate_current_docs_and_release_governance
validate_controlled_canary_release_decision_governance = _ENGINE.validate_controlled_canary_release_decision_governance
validate_canary_candidate_market_prep_boundary = _ENGINE.validate_canary_candidate_market_prep_boundary
validate_single_host_deployment_governance = _ENGINE.validate_single_host_deployment_governance
validate_v28_production_live_candidate_guard = _ENGINE.validate_v28_production_live_candidate_guard


def load_openapi_spec(*args, **kwargs):
    return _ENGINE.load_openapi_spec(*args, **kwargs)


def error_message(*args, **kwargs):
    return _ENGINE.error_message(*args, **kwargs)


def run_validator(*args, **kwargs):
    return _ENGINE.run_validator(*args, **kwargs)


def build_report(*args, **kwargs):
    return _ENGINE.build_report(*args, **kwargs)


def write_report(*args, **kwargs):
    return _ENGINE.write_report(*args, **kwargs)
