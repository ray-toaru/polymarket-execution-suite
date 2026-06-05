from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_contracts_governance.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_validate_contracts_governance", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()
_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "require_existing_paths",
        "validate_absent_tokens",
        "validate_current_hermes_client_surface",
        "validate_current_evidence_manifest_guard",
        "validate_current_docs_and_release_governance",
        "validate_controlled_canary_release_decision_governance",
        "validate_canary_candidate_market_prep_boundary",
        "validate_single_host_deployment_governance",
        "validate_v28_production_live_candidate_guard",
    ]
}

inspect = _ENGINE.inspect
json = _ENGINE.json
re = _ENGINE.re
SimpleNamespace = _ENGINE.SimpleNamespace
CONTROL = _ENGINE.CONTROL
CORE_SRC = _ENGINE.CORE_SRC
EXECUTOR = _ENGINE.EXECUTOR
EXCLUDED_PREFIXES = _ENGINE.EXCLUDED_PREFIXES
OPENAPI = _ENGINE.OPENAPI
ROOT = _ENGINE.ROOT
SDK_ADAPTER_SRC = _ENGINE.SDK_ADAPTER_SRC
fail = _ENGINE.fail
import_control_client = _ENGINE.import_control_client
import_control_models = _ENGINE.import_control_models
import_module_from_path = _ENGINE.import_module_from_path
rust_source_text = _ENGINE.rust_source_text


def _sync_engine_state() -> None:
    for name in [
        "CONTROL",
        "CORE_SRC",
        "EXECUTOR",
        "EXCLUDED_PREFIXES",
        "OPENAPI",
        "ROOT",
        "SDK_ADAPTER_SRC",
        "fail",
        "import_control_client",
        "import_control_models",
        "import_module_from_path",
        "rust_source_text",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def require_existing_paths(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["require_existing_paths"], *args, **kwargs)


def validate_absent_tokens(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_absent_tokens"], *args, **kwargs)


def validate_current_hermes_client_surface(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_current_hermes_client_surface"], *args, **kwargs)


def validate_current_evidence_manifest_guard(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_current_evidence_manifest_guard"], *args, **kwargs)


def validate_current_docs_and_release_governance(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_current_docs_and_release_governance"], *args, **kwargs)


def validate_controlled_canary_release_decision_governance(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_controlled_canary_release_decision_governance"], *args, **kwargs)


def validate_canary_candidate_market_prep_boundary(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_canary_candidate_market_prep_boundary"], *args, **kwargs)


def validate_single_host_deployment_governance(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_single_host_deployment_governance"], *args, **kwargs)


def validate_v28_production_live_candidate_guard(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_v28_production_live_candidate_guard"], *args, **kwargs)
