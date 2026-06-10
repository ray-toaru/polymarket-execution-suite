import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect_validation_environment.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "collect_validation_environment",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CollectValidationEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def git_info(self, status: str, **kwargs):
        def fake_run(command, cwd=self.module.ROOT):
            if command[:3] == ["git", "status", "--short"]:
                return {"stdout": status}
            if command[:3] == ["git", "branch", "--show-current"]:
                return {"stdout": "branch"}
            if command[:3] == ["git", "rev-parse", "HEAD"]:
                return {"stdout": "a" * 40}
            raise AssertionError(command)

        with patch.object(self.module, "run", side_effect=fake_run):
            return self.module.git_info(self.module.ROOT, **kwargs)

    def test_engine_canonical_evidence_changes_are_output_not_source_dirt(self):
        info = self.git_info(
            "M  evidence/current/environment.json\n"
            " M evidence/current/manifest.json\n"
            " D evidence/current/logs/old.log\n"
            "?? evidence/current/logs/new.log\n",
            ignored_path_prefixes=("evidence/current",),
        )
        self.assertTrue(info["status_clean"])
        self.assertEqual(info["status_entry_count"], 0)

    def test_non_evidence_engine_change_remains_dirty(self):
        info = self.git_info(
            " M evidence/current/manifest.json\n M Cargo.toml\n",
            ignored_path_prefixes=("evidence/current",),
        )
        self.assertFalse(info["status_clean"])
        self.assertEqual(info["status_entry_count"], 1)

    def test_parent_only_ignores_submodule_worktree_marker(self):
        clean = self.git_info(
            "m polymarket-execution-engine\n",
            ignored_submodule_worktree="polymarket-execution-engine",
        )
        pointer_changed = self.git_info(
            " M polymarket-execution-engine\n",
            ignored_submodule_worktree="polymarket-execution-engine",
        )
        self.assertTrue(clean["status_clean"])
        self.assertFalse(pointer_changed["status_clean"])


if __name__ == "__main__":
    unittest.main()
