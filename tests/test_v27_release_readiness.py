import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_v27_release_readiness.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_v27_release_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class V027ReleaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_ready_tree(self) -> None:
        self.write("VERSION", "0.27.0")
        self.write(
            "COMPONENT_COMPATIBILITY.md",
            """# Component compatibility and ownership

| Component | Current repository name | Current version | Pinned commit | Role |
|---|---|---:|---|---|
| Integration suite | `polymarket-execution-suite` | `0.27.0` | root tag `v0.27.0` | Pins component commits. |
| Execution engine | `polymarket-execution-engine` | `0.27.0` | submodule commit | Rust executor. |
| Hermes adapter | `hermes-polymarket-executor-adapter` | `0.26.2` | submodule commit | Python adapter. |
""",
        )
        self.write(
            "RELEASE_DECISION.md",
            "# Release Decision - v0.27.0 controlled real-funds canary source-candidate\n"
            "validated_release=false\nproduction_ready=false\nlive_trading_ready=false\n",
        )
        self.write(
            "VALIDATION_REPORT.md",
            "# Validation Report - v0.27.0\nFull current gates refreshed for v0.27.0.\n",
        )
        self.write(
            "polymarket-execution-engine/release/manifest.json",
            json.dumps(
                {
                    "version": "0.27.0",
                    "status": "v0.27.0 controlled real-funds canary source-candidate",
                }
            ),
        )
        self.write(
            "polymarket-execution-engine/evidence/current/manifest.json",
            json.dumps(
                {
                    "version": "0.27.0",
                    "artifact": {"sha256": "a" * 64},
                    "release_decision": {
                        "validated_release": False,
                        "production_ready": False,
                        "live_trading_ready": False,
                    },
                }
            ),
        )
        for suffix, body in [
            ("", "zip"),
            (".sha256", "a" * 64 + "  polymarket-execution-suite-v0.27.0.zip\n"),
            (".evidence.json", json.dumps({"source": {"version": "0.27.0"}, "artifact": {"sha256": "a" * 64}})),
        ]:
            self.write(f"dist/polymarket-execution-suite-v0.27.0.zip{suffix}", body)

    def test_current_tree_is_not_release_ready_while_version_remains_baseline(self):
        report = self.module.evaluate(ROOT)
        self.assertEqual(report["target_version"], "0.27.0")
        self.assertEqual(report["status"], "not_ready")
        self.assertIn("VERSION must be 0.27.0", "\n".join(report["blockers"]))

    def test_ready_tree_passes_when_all_release_material_matches_target(self):
        self.write_ready_tree()
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["blockers"], [])

    def test_missing_artifact_sidecar_blocks_release_readiness(self):
        self.write_ready_tree()
        (self.root / "dist/polymarket-execution-suite-v0.27.0.zip.evidence.json").unlink()
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "not_ready")
        self.assertIn("release artifact evidence sidecar missing", "\n".join(report["blockers"]))


if __name__ == "__main__":
    unittest.main()
