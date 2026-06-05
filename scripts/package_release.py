#!/usr/bin/env python3
"""Thin wrapper over execution-engine release packaging implementation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "package_release.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_package_release", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()
_ORIGINALS = {
    name: getattr(_ENGINE, name)
    for name in [
        "sha256",
        "command_output",
        "command_output_bytes",
        "require_command_output",
        "require_command_output_bytes",
        "git_branch",
        "submodule_records",
        "tracked_git_files",
        "git_status_lines",
        "ensure_clean_release_submodules",
        "release_source_files",
        "allowed",
        "executable_in_archive",
        "archive_bytes",
        "write_deterministic",
        "build_release_zip",
        "load_json_if_exists",
        "is_reviewed_go_material",
        "classify_dist_entry",
        "write_dist_index",
        "workspace_manifest_snapshot_bytes",
        "write_workspace_manifest_snapshot",
        "archived_manifest_sha256",
        "contract_validation_report_metadata",
        "main",
    ]
}

Path = _ENGINE.Path
ZipFile = _ENGINE.ZipFile
ZipInfo = _ENGINE.ZipInfo
ZIP_DEFLATED = _ENGINE.ZIP_DEFLATED
hashlib = _ENGINE.hashlib
json = _ENGINE.json
subprocess = _ENGINE.subprocess
sys = _ENGINE.sys
datetime = _ENGINE.datetime
timezone = _ENGINE.timezone
Any = _ENGINE.Any
ROOT = _ENGINE.ROOT
VERSION = _ENGINE.VERSION
ARCHIVE_ROOT = _ENGINE.ARCHIVE_ROOT
DIST = _ENGINE.DIST
OUT = _ENGINE.OUT
DETERMINISTIC_MTIME = _ENGINE.DETERMINISTIC_MTIME
ARCHIVED_MANIFEST_BINDING_KIND = _ENGINE.ARCHIVED_MANIFEST_BINDING_KIND
WORKSPACE_MANIFEST_BINDING_KIND = _ENGINE.WORKSPACE_MANIFEST_BINDING_KIND


def _sync_engine_state() -> None:
    for name in [
        "ROOT",
        "VERSION",
        "ARCHIVE_ROOT",
        "DIST",
        "OUT",
        "DETERMINISTIC_MTIME",
        "ARCHIVED_MANIFEST_BINDING_KIND",
        "WORKSPACE_MANIFEST_BINDING_KIND",
        "sha256",
        "command_output",
        "command_output_bytes",
        "require_command_output",
        "require_command_output_bytes",
        "git_branch",
        "submodule_records",
        "tracked_git_files",
        "git_status_lines",
        "ensure_clean_release_submodules",
        "release_source_files",
        "allowed",
        "executable_in_archive",
        "archive_bytes",
        "write_deterministic",
        "build_release_zip",
        "load_json_if_exists",
        "is_reviewed_go_material",
        "classify_dist_entry",
        "write_dist_index",
        "workspace_manifest_snapshot_bytes",
        "write_workspace_manifest_snapshot",
        "archived_manifest_sha256",
        "contract_validation_report_metadata",
    ]:
        setattr(_ENGINE, name, globals()[name])


def _with_engine_state(callback, *args, **kwargs):
    _sync_engine_state()
    return callback(*args, **kwargs)


def sha256(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["sha256"], *args, **kwargs)


def command_output(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["command_output"], *args, **kwargs)


def command_output_bytes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["command_output_bytes"], *args, **kwargs)


def require_command_output(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["require_command_output"], *args, **kwargs)


def require_command_output_bytes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["require_command_output_bytes"], *args, **kwargs)


def git_branch(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["git_branch"], *args, **kwargs)


def submodule_records(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["submodule_records"], *args, **kwargs)


def tracked_git_files(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["tracked_git_files"], *args, **kwargs)


def git_status_lines(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["git_status_lines"], *args, **kwargs)


def ensure_clean_release_submodules(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["ensure_clean_release_submodules"], *args, **kwargs)


def release_source_files(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["release_source_files"], *args, **kwargs)


def allowed(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["allowed"], *args, **kwargs)


def executable_in_archive(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["executable_in_archive"], *args, **kwargs)


def archive_bytes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["archive_bytes"], *args, **kwargs)


def write_deterministic(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["write_deterministic"], *args, **kwargs)


def build_release_zip(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["build_release_zip"], *args, **kwargs)


def load_json_if_exists(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["load_json_if_exists"], *args, **kwargs)


def is_reviewed_go_material(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["is_reviewed_go_material"], *args, **kwargs)


def classify_dist_entry(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["classify_dist_entry"], *args, **kwargs)


def write_dist_index(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["write_dist_index"], *args, **kwargs)


def workspace_manifest_snapshot_bytes(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["workspace_manifest_snapshot_bytes"], *args, **kwargs)


def write_workspace_manifest_snapshot(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["write_workspace_manifest_snapshot"], *args, **kwargs)


def archived_manifest_sha256(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["archived_manifest_sha256"], *args, **kwargs)


def contract_validation_report_metadata(*args, **kwargs):
    return _with_engine_state(_ORIGINALS["contract_validation_report_metadata"], *args, **kwargs)


def main() -> int:
    return _with_engine_state(_ORIGINALS["main"])


if __name__ == "__main__":
    raise SystemExit(main())
