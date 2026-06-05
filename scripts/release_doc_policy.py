from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "release_doc_policy.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("engine_release_doc_policy", ENGINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ENGINE = load_engine_module()

STALE_ROOT_DOC_PATTERNS = _ENGINE.STALE_ROOT_DOC_PATTERNS
HISTORICAL_ROOT_DOC_PATTERNS = _ENGINE.HISTORICAL_ROOT_DOC_PATTERNS
RELEASE_SPECIFIC_AGENT_PATTERNS = _ENGINE.RELEASE_SPECIFIC_AGENT_PATTERNS
contains_historical_root_doc_marker = _ENGINE.contains_historical_root_doc_marker
contains_release_specific_agents_marker = _ENGINE.contains_release_specific_agents_marker
