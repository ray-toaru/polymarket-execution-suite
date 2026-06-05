#!/usr/bin/env python3
"""Thin wrapper over execution-engine release artifact validation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "check_release_artifact.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_check_release_artifact", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()
_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "validate_dist_index",
        "release_source_files",
        "command_output",
        "submodule_records",
        "forbidden",
        "outside_release_allowlist",
        "sha256",
        "stale_root_doc",
        "historical_root_doc_content",
        "stale_engine_doc",
        "load_json_object",
        "git_head",
        "validate_sidecars",
        "validate_archive_members",
        "validate_workspace_source_coverage",
        "validate_shebang_modes",
        "required_agents",
        "validate_agents_in_archive",
        "validate_manifest_bindings",
        "main",
    ]
}

json = _ENGINE.json
hashlib = _ENGINE.hashlib
sys = _ENGINE.sys
zipfile = _ENGINE.zipfile
Path = _ENGINE.Path
validate_dist_index = _ENGINE.validate_dist_index
release_source_files = _ENGINE.release_source_files
command_output = _ENGINE.command_output
submodule_records = _ENGINE.submodule_records


def _sync_engine_state() -> None:
    for name in [
        "forbidden",
        "outside_release_allowlist",
        "sha256",
        "stale_root_doc",
        "historical_root_doc_content",
        "stale_engine_doc",
        "load_json_object",
        "git_head",
        "validate_sidecars",
        "validate_archive_members",
        "validate_workspace_source_coverage",
        "validate_shebang_modes",
        "required_agents",
        "validate_agents_in_archive",
        "validate_manifest_bindings",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def forbidden(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["forbidden"], *args, **kwargs)


def outside_release_allowlist(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["outside_release_allowlist"], *args, **kwargs)


def sha256(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["sha256"], *args, **kwargs)


def stale_root_doc(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["stale_root_doc"], *args, **kwargs)


def historical_root_doc_content(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["historical_root_doc_content"], *args, **kwargs)


def stale_engine_doc(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["stale_engine_doc"], *args, **kwargs)


def load_json_object(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["load_json_object"], *args, **kwargs)


def git_head(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["git_head"], *args, **kwargs)


def validate_sidecars(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_sidecars"], *args, **kwargs)


def validate_archive_members(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_archive_members"], *args, **kwargs)


def validate_workspace_source_coverage(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_workspace_source_coverage"], *args, **kwargs)


def validate_shebang_modes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_shebang_modes"], *args, **kwargs)


def required_agents(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["required_agents"], *args, **kwargs)


def validate_agents_in_archive(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_agents_in_archive"], *args, **kwargs)


def validate_manifest_bindings(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["validate_manifest_bindings"], *args, **kwargs)


def main(*args, **kwargs) -> int:
    return _with_engine_state(_ORIGINALS["main"], *args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(main())
