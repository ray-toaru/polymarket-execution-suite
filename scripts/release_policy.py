from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "release_policy.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_release_policy", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

FORBIDDEN_PARTS = _ENGINE.FORBIDDEN_PARTS
FORBIDDEN_SUFFIXES = _ENGINE.FORBIDDEN_SUFFIXES
FORBIDDEN_FILENAMES = _ENGINE.FORBIDDEN_FILENAMES
FORBIDDEN_NAME_PREFIXES = _ENGINE.FORBIDDEN_NAME_PREFIXES
FORBIDDEN_NAME_SUFFIXES = _ENGINE.FORBIDDEN_NAME_SUFFIXES
EXCLUDED_PREFIXES = _ENGINE.EXCLUDED_PREFIXES
ALLOWED_ROOT_FILES = _ENGINE.ALLOWED_ROOT_FILES
ALLOWED_ROOT_DIRS = _ENGINE.ALLOWED_ROOT_DIRS
is_allowed_release_source_path = _ENGINE.is_allowed_release_source_path
is_forbidden_release_member = _ENGINE.is_forbidden_release_member
