from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_contracts_surface.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_validate_contracts_surface", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

re = _ENGINE.re
Iterator = _ENGINE.Iterator
API_SRC = _ENGINE.API_SRC
CONTROL = _ENGINE.CONTROL
CORE_SRC = _ENGINE.CORE_SRC
EXPECTED_202_PATHS = _ENGINE.EXPECTED_202_PATHS
FORBIDDEN_PUBLIC_TOKEN_PATTERNS = _ENGINE.FORBIDDEN_PUBLIC_TOKEN_PATTERNS
PUBLIC_CONTRACT_SOURCE_PATHS = _ENGINE.PUBLIC_CONTRACT_SOURCE_PATHS
PY_MODEL_BY_SCHEMA = _ENGINE.PY_MODEL_BY_SCHEMA
SQL = _ENGINE.SQL
fail = _ENGINE.fail
import_control_models = _ENGINE.import_control_models
rust_handler_body = _ENGINE.rust_handler_body
rust_routes = _ENGINE.rust_routes
rust_source_text = _ENGINE.rust_source_text
operation_request_ref = _ENGINE.operation_request_ref
operation_response_ref = _ENGINE.operation_response_ref
schema_property_names = _ENGINE.schema_property_names
schema_required_names = _ENGINE.schema_required_names

_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "iter_json_strings",
        "split_top_level_csv",
        "rust_struct_has_deny_unknown_fields",
        "validate_paths_and_statuses",
        "validate_critical_contract_shapes",
        "validate_no_public_forbidden_tokens",
        "validate_additional_properties",
        "validate_python_field_parity",
        "validate_sql_idempotency",
        "validate_rust_deny_unknown_fields",
    ]
}


def _sync_engine_state() -> None:
    for name in [
        "API_SRC",
        "CONTROL",
        "CORE_SRC",
        "EXPECTED_202_PATHS",
        "FORBIDDEN_PUBLIC_TOKEN_PATTERNS",
        "PUBLIC_CONTRACT_SOURCE_PATHS",
        "PY_MODEL_BY_SCHEMA",
        "SQL",
        "fail",
        "import_control_models",
        "rust_handler_body",
        "rust_routes",
        "rust_source_text",
        "operation_request_ref",
        "operation_response_ref",
        "schema_property_names",
        "schema_required_names",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def __getattr__(name: str):
    if name in _ORIGINALS:
        def wrapper(*args, **kwargs):
            return _with_engine_state(_ORIGINALS[name], *args, **kwargs)
        return wrapper
    raise AttributeError(name)
