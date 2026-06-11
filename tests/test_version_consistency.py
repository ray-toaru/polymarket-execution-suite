import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_version_consistency.py"


def load_version_module():
    spec = importlib.util.spec_from_file_location("check_version_consistency", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VersionConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.module = load_version_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_minimal_tree(
        self,
        *,
        suite_version: str = "0.27.3",
        engine_version: str = "0.27.3",
        adapter_version: str = "0.26.2",
    ) -> None:
        self.write("VERSION", suite_version)
        self.write(
            "COMPONENT_COMPATIBILITY.md",
            f"""# Component compatibility and ownership

## Current v{suite_version} composition

| Component | Current repository name | Current version | Pinned commit | Role |
|---|---|---:|---|---|
| integration suite | `polymarket-execution-suite` | `{suite_version}` | root branch `v0.27-development` | Pins component commits. |
| execution engine | `polymarket-execution-engine` | `{engine_version}` | submodule commit | Rust executor. |
| hermes adapter | `hermes-polymarket-executor-adapter` | `{adapter_version}` | submodule commit | Python adapter. |

The three repositories may evolve independently after the current shared release.
""",
        )
        self.write("hermes-polymarket-executor-adapter/pyproject.toml", f'version = "{adapter_version}"\n')
        self.write(
            "hermes-polymarket-executor-adapter/src/hermes_polymarket_executor_adapter/__init__.py",
            f'__version__ = "{adapter_version}"\n',
        )
        self.write("polymarket-execution-engine/Cargo.toml", f'[workspace.package]\nversion = "{engine_version}"\n')
        self.write(
            "polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.toml",
            f'[package]\nversion = "{engine_version}"\n',
        )
        self.write(
            "polymarket-execution-engine/release/manifest.json",
            json.dumps(
                {
                    "version": suite_version,
                    "status": "v0.27-controlled-real-funds-canary-source-candidate-not-production-not-live",
                }
            ),
        )
        self.write(".github/workflows/ci.yml", "name: suite\n")
        self.write(
            ".gitmodules",
            (
                "[submodule \"hermes-polymarket-executor-adapter\"]\n"
                "\tpath = hermes-polymarket-executor-adapter\n"
                "\turl = https://example.invalid/adapter.git\n"
                "\tbranch = main\n"
                "[submodule \"polymarket-execution-engine\"]\n"
                "\tpath = polymarket-execution-engine\n"
                "\turl = https://example.invalid/engine.git\n"
                "\tbranch = main\n"
            ),
        )
        self.write(
            "RELEASE_DECISION.md",
            f"v{suite_version}\nThe current governance freeze point is git tag `v{suite_version}`.\n",
        )
        self.write(
            "polymarket-execution-engine/.github/workflows/ci.yml",
            "name: engine\nrun: ./validation/run_current_gates.sh\n",
        )
        self.write("polymarket-execution-engine/validation/run_current_gates.sh", "run_current_gates_impl.sh\n")
        for lock_rel in [
            "polymarket-execution-engine/Cargo.lock",
            "polymarket-execution-engine/adapters/pmx-official-sdk-adapter/Cargo.lock",
            "polymarket-execution-engine/adapters/pmx-official-sdk-spike/Cargo.lock",
        ]:
            self.write(
                lock_rel,
                f'[[package]]\nname = "pmx-core"\nversion = "{engine_version}"\n',
            )
        for doc in self.module.ACTIVE_DOCS:
            if (self.root / doc).exists():
                continue
            self.write(doc, f"v{suite_version}\n")

    def test_independent_component_versions_are_valid_when_matrix_matches_sources(self):
        self.write_minimal_tree()
        failures = self.module.validate_versions(self.root)
        self.assertEqual(failures, [])

    def test_component_matrix_must_match_adapter_source_version(self):
        self.write_minimal_tree(adapter_version="0.26.2")
        self.write(
            "COMPONENT_COMPATIBILITY.md",
            (self.root / "COMPONENT_COMPATIBILITY.md").read_text().replace("0.26.2", "0.26.1"),
        )
        failures = self.module.validate_versions(self.root)
        self.assertIn("component matrix Hermes adapter version", "\n".join(failures))

    def test_missing_active_doc_fails(self):
        self.write_minimal_tree()
        missing = self.module.ACTIVE_DOCS[0]
        (self.root / missing).unlink()
        failures = self.module.validate_versions(self.root)
        self.assertIn(f"active docs missing from workspace: {missing}", "\n".join(failures))

    def test_submodule_branch_metadata_must_use_main(self):
        self.write_minimal_tree()
        self.write(
            ".gitmodules",
            (self.root / ".gitmodules").read_text().replace(
                "branch = main",
                "branch = v0.28-production-live-candidate",
                1,
            ),
        )
        failures = self.module.validate_versions(self.root)
        self.assertIn("submodule branch metadata", "\n".join(failures))

    def test_release_freeze_tag_must_match_suite_version(self):
        self.write_minimal_tree()
        self.write(
            "RELEASE_DECISION.md",
            "v0.27.3\nThe current governance freeze point is git tag `v0.27.4`.\n",
        )
        failures = self.module.validate_versions(self.root)
        self.assertIn("release decision freeze tag", "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
