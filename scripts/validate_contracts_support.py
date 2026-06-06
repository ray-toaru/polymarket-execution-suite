from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_contracts_support.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_validate_contracts_support", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()
_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "fail",
        "normalize_path",
        "rust_source_text",
        "rust_file_with_modules_text",
        "find_matching_delimiter",
        "extract_string_literal_prefix",
        "rust_routes",
        "rust_handler_body",
        "python_function_body",
        "import_control_models",
        "import_control_client",
        "import_module_from_path",
    ]
}

EXCLUDED_PREFIXES = _ENGINE.EXCLUDED_PREFIXES
ROOT = _ENGINE.ROOT
EXECUTOR = _ENGINE.EXECUTOR
CONTROL = _ENGINE.CONTROL
OPENAPI = _ENGINE.OPENAPI
API_SRC = _ENGINE.API_SRC
CORE_SRC = _ENGINE.CORE_SRC
STORE_SRC = _ENGINE.STORE_SRC
SERVICE_SRC = _ENGINE.SERVICE_SRC
API_RS = _ENGINE.API_RS
SQL = _ENGINE.SQL
STORE_RS = _ENGINE.STORE_RS
POSTGRES_RS = _ENGINE.POSTGRES_RS
API_E2E_TEST = _ENGINE.API_E2E_TEST
API_POSTGRES_E2E_TEST = _ENGINE.API_POSTGRES_E2E_TEST
GATEWAY_SRC = _ENGINE.GATEWAY_SRC
SDK_SPIKE_RS = _ENGINE.SDK_SPIKE_RS
SDK_SPIKE_TOML = _ENGINE.SDK_SPIKE_TOML
SDK_ADAPTER_RS = _ENGINE.SDK_ADAPTER_RS
SDK_ADAPTER_SRC = _ENGINE.SDK_ADAPTER_SRC
SDK_ADAPTER_TOML = _ENGINE.SDK_ADAPTER_TOML
LIVE_SUBMIT_GUARD = _ENGINE.LIVE_SUBMIT_GUARD
SERVICE_RS = _ENGINE.SERVICE_RS
SERVICE_TOML = _ENGINE.SERVICE_TOML
ROOT_CARGO_TOML = _ENGINE.ROOT_CARGO_TOML
FORBIDDEN_PUBLIC_TOKEN_PATTERNS = _ENGINE.FORBIDDEN_PUBLIC_TOKEN_PATTERNS
PUBLIC_CONTRACT_SOURCE_PATHS = _ENGINE.PUBLIC_CONTRACT_SOURCE_PATHS
EXPECTED_202_PATHS = _ENGINE.EXPECTED_202_PATHS
PY_MODEL_BY_SCHEMA = _ENGINE.PY_MODEL_BY_SCHEMA
ContractValidationError = _ENGINE.ContractValidationError

fail = _ENGINE.fail
normalize_path = _ENGINE.normalize_path
rust_source_text = _ENGINE.rust_source_text
rust_file_with_modules_text = _ENGINE.rust_file_with_modules_text
find_matching_delimiter = _ENGINE.find_matching_delimiter
extract_string_literal_prefix = _ENGINE.extract_string_literal_prefix
python_function_body = _ENGINE.python_function_body
import_control_models = _ENGINE.import_control_models
import_control_client = _ENGINE.import_control_client
import_module_from_path = _ENGINE.import_module_from_path


def _sync_engine_state() -> None:
    for name in [
        "EXCLUDED_PREFIXES",
        "ROOT",
        "EXECUTOR",
        "CONTROL",
        "OPENAPI",
        "API_SRC",
        "CORE_SRC",
        "STORE_SRC",
        "SERVICE_SRC",
        "API_RS",
        "SQL",
        "STORE_RS",
        "POSTGRES_RS",
        "API_E2E_TEST",
        "API_POSTGRES_E2E_TEST",
        "GATEWAY_SRC",
        "SDK_SPIKE_RS",
        "SDK_SPIKE_TOML",
        "SDK_ADAPTER_RS",
        "SDK_ADAPTER_SRC",
        "SDK_ADAPTER_TOML",
        "LIVE_SUBMIT_GUARD",
        "SERVICE_RS",
        "SERVICE_TOML",
        "ROOT_CARGO_TOML",
        "FORBIDDEN_PUBLIC_TOKEN_PATTERNS",
        "PUBLIC_CONTRACT_SOURCE_PATHS",
        "EXPECTED_202_PATHS",
        "PY_MODEL_BY_SCHEMA",
        "ContractValidationError",
        "fail",
        "normalize_path",
        "rust_source_text",
        "rust_file_with_modules_text",
        "find_matching_delimiter",
        "extract_string_literal_prefix",
        "python_function_body",
        "import_control_models",
        "import_control_client",
        "import_module_from_path",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def rust_routes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["rust_routes"], *args, **kwargs)


def rust_handler_body(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["rust_handler_body"], *args, **kwargs)


def python_function_body(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["python_function_body"], *args, **kwargs)
