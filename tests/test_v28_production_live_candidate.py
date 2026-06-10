import importlib.util
import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_v28_production_live_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_v28_production_live_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class V028ProductionLiveCandidateTests(unittest.TestCase):
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
        self.write("VERSION", "0.28.0")
        self.write(
            "COMPONENT_COMPATIBILITY.md",
            """# Component compatibility and ownership

| Component | Current repository name | Current version | Pinned commit | Role |
|---|---|---:|---|---|
| Integration suite | `polymarket-execution-suite` | `0.28.0` | root tag `v0.28.0` | Pins component commits. |
| Execution engine | `polymarket-execution-engine` | `0.28.0` | submodule commit | Rust executor. |
| Hermes adapter | `hermes-polymarket-executor-adapter` | `0.28.0` | submodule commit | Python adapter. |
""",
        )
        self.write(
            "RELEASE_DECISION.md",
            "# Release Decision - v0.28.0 production-live-candidate\n"
            "production-live-candidate\n"
            "validated_release=false\nproduction_ready=false\nlive_trading_ready=false\n"
            "live_submit_allowed=false\nlive_cancel_allowed=false\nreal_funds_canary_authorized=false\n"
            "fresh reviewed release decision\noperator approval\nruntime state healthy\n"
            "kill switch open\nno geoblock\nidempotency reservation\nrollback\nincident\nalert\ncustody\n",
        )
        self.write(
            "VALIDATION_REPORT.md",
            "# Validation Report - v0.28.0 production-live-candidate\n"
            "Full current gates refreshed for v0.28.0.\n",
        )
        self.write(
            "polymarket-execution-engine/release/manifest.json",
            json.dumps(
                {
                    "version": "0.28.0",
                    "status": "v0.28-production-live-candidate-not-production-not-live-by-default",
                }
            ),
        )
        self.write(
            "polymarket-execution-engine/evidence/current/manifest.json",
            json.dumps(
                {
                    "version": "0.28.0",
                    "release_decision": {
                        "validated_release": False,
                        "production_ready": False,
                        "live_trading_ready": False,
                    },
                }
            ),
        )
        self.write(
            "dist/INDEX.json",
            json.dumps(
                {
                    "version": "0.28.0",
                    "current_release_artifact": {
                        "artifact_class": "production_live_candidate_non_live_by_default",
                        "validated_release": False,
                        "production_ready": False,
                        "live_trading_ready": False,
                    },
                }
            ),
        )
        for suffix, body in [
            ("", "zip"),
            (".sha256", "a" * 64 + "  polymarket-execution-suite-v0.28.0.zip\n"),
            (
                ".evidence.json",
                json.dumps(
                    {
                        "source": {"version": "0.28.0"},
                        "artifact": {"sha256": "a" * 64},
                        "canonical_evidence": {
                            "workspace_manifest_snapshot_path": "polymarket-execution-suite-v0.28.0.workspace-manifest.json"
                        },
                    }
                ),
            ),
        ]:
            self.write(f"dist/polymarket-execution-suite-v0.28.0.zip{suffix}", body)
        self.write("dist/polymarket-execution-suite-v0.28.0.workspace-manifest.json", "{}")

    def test_ready_tree_passes_when_candidate_boundary_is_explicit(self):
        self.write_ready_tree()
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["external_evidence"]["status"], "not_locally_verifiable")
        self.assertEqual(len(report["external_evidence"]["required"]), 4)

    def test_live_ready_claim_blocks_candidate(self):
        self.write_ready_tree()
        path = self.root / "polymarket-execution-engine/evidence/current/manifest.json"
        manifest = json.loads(path.read_text())
        manifest["release_decision"]["live_trading_ready"] = True
        path.write_text(json.dumps(manifest))
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "not_ready")
        self.assertIn("live_trading_ready", "\n".join(report["blockers"]))

    def test_missing_operator_and_runtime_terms_block_candidate(self):
        self.write_ready_tree()
        self.write(
            "RELEASE_DECISION.md",
            "# Release Decision - v0.28.0 production-live-candidate\n"
            "validated_release=false\nproduction_ready=false\nlive_trading_ready=false\n"
            "live_submit_allowed=false\nlive_cancel_allowed=false\nreal_funds_canary_authorized=false\n",
        )
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "not_ready")
        blockers = "\n".join(report["blockers"])
        self.assertIn("operator approval", blockers)
        self.assertIn("runtime state healthy", blockers)

    def test_audit_only_not_ready_report_is_not_release_pass(self):
        report = self.module.evaluate(self.root)
        self.assertEqual(report["status"], "not_ready")

        original_root = self.module.ROOT
        self.module.ROOT = self.root
        self.addCleanup(lambda: setattr(self.module, "ROOT", original_root))

        audit_stdout = io.StringIO()
        with contextlib.redirect_stdout(audit_stdout):
            audit_rc = self.module.main([])
        self.assertEqual(audit_rc, 0)
        self.assertEqual(json.loads(audit_stdout.getvalue())["status"], "not_ready")

        require_stdout = io.StringIO()
        with contextlib.redirect_stdout(require_stdout):
            require_rc = self.module.main(["--require-ready"])
        self.assertEqual(require_rc, 1)
        self.assertEqual(json.loads(require_stdout.getvalue())["status"], "not_ready")


if __name__ == "__main__":
    unittest.main()
