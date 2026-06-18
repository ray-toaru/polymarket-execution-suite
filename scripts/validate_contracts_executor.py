from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_contracts_executor.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_validate_contracts_executor", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

re = _ENGINE.re
tomllib = _ENGINE.tomllib
API_E2E_TEST = _ENGINE.API_E2E_TEST
API_POSTGRES_E2E_TEST = _ENGINE.API_POSTGRES_E2E_TEST
API_SRC = _ENGINE.API_SRC
CORE_SRC = _ENGINE.CORE_SRC
EXECUTOR = _ENGINE.EXECUTOR
GATEWAY_SRC = _ENGINE.GATEWAY_SRC
LIVE_SUBMIT_GUARD = _ENGINE.LIVE_SUBMIT_GUARD
OPENAPI = _ENGINE.OPENAPI
POSTGRES_RS = _ENGINE.POSTGRES_RS
ROOT = _ENGINE.ROOT
ROOT_CARGO_TOML = _ENGINE.ROOT_CARGO_TOML
SDK_ADAPTER_RS = _ENGINE.SDK_ADAPTER_RS
SDK_ADAPTER_SRC = _ENGINE.SDK_ADAPTER_SRC
SDK_ADAPTER_TOML = _ENGINE.SDK_ADAPTER_TOML
SDK_SPIKE_RS = _ENGINE.SDK_SPIKE_RS
SDK_SPIKE_TOML = _ENGINE.SDK_SPIKE_TOML
SERVICE_RS = _ENGINE.SERVICE_RS
SERVICE_SRC = _ENGINE.SERVICE_SRC
SERVICE_TOML = _ENGINE.SERVICE_TOML
SQL = _ENGINE.SQL
STORE_SRC = _ENGINE.STORE_SRC
fail = _ENGINE.fail
rust_file_with_modules_text = _ENGINE.rust_file_with_modules_text
rust_source_text = _ENGINE.rust_source_text
import_module_from_path = _ENGINE.import_module_from_path

_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "openapi_operation",
        "git_head",
        "operation_parameter_names",
        "schema_property_names",
        "schema_required_names",
        "operation_request_ref",
        "operation_response_ref",
        "operation_response_array_item_ref",
        "require_tokens",
        "require_file_tokens",
        "validate_absent_tokens",
        "source_tree_text_without_paths",
        "validate_required_groups",
        "rust_module_names",
        "rust_pub_use_targets",
        "rust_async_fn_names",
        "rust_fn_names",
        "rust_const_names",
        "rust_struct_field_names",
        "rust_enum_variant_names",
        "rust_enum_variant_field_names",
        "ensure_match_arms",
        "rust_trait_method_signatures",
        "rust_impl_block_body",
        "rust_impl_trait_method_names",
        "rust_impl_trait_method_body",
        "rust_inherent_impl_method_names",
        "rust_impl_method_body",
        "service_backend_method_names",
        "rust_async_fn_signature",
        "rust_fn_signature",
        "rust_fn_body",
        "cargo_toml",
        "validate_v04_source_landings",
        "validate_v07_source_landings",
        "validate_v08_dependency_and_sdk_policy",
        "validate_v09_official_adapter_boundary",
        "validate_v12_service_layer",
        "validate_v15_admin_audit_and_runtime_provider",
        "validate_v16_postgres_runtime_provider",
        "validate_v19_redaction_and_live_guard",
        "validate_v20_plan_storage_and_packaging",
        "validate_v21_sign_only_and_runtime_models",
        "validate_store_and_backend_structure",
        "validate_v23_lifecycle_query_and_hardening",
        "validate_v28_non_live_portfolio_foundation",
    ]
}


def _sync_engine_state() -> None:
    for name in [
        "API_E2E_TEST",
        "API_POSTGRES_E2E_TEST",
        "API_SRC",
        "CORE_SRC",
        "EXECUTOR",
        "GATEWAY_SRC",
        "LIVE_SUBMIT_GUARD",
        "OPENAPI",
        "POSTGRES_RS",
        "ROOT",
        "ROOT_CARGO_TOML",
        "SDK_ADAPTER_RS",
        "SDK_ADAPTER_SRC",
        "SDK_ADAPTER_TOML",
        "SDK_SPIKE_RS",
        "SDK_SPIKE_TOML",
        "SERVICE_RS",
        "SERVICE_SRC",
        "SERVICE_TOML",
        "SQL",
        "STORE_SRC",
        "fail",
        "import_module_from_path",
        "rust_file_with_modules_text",
        "rust_source_text",
        "git_head",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def git_head(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["git_head"], *args, **kwargs)


def __getattr__(name: str):
    if name in _ORIGINALS:
        def wrapper(*args, **kwargs):
            return _with_engine_state(_ORIGINALS[name], *args, **kwargs)
        return wrapper
    raise AttributeError(name)
