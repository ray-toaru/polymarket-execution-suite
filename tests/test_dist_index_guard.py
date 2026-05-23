import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_dist_index.py"


def load_guard_module():
    spec = importlib.util.spec_from_file_location("check_dist_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DistIndexGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = load_guard_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = Path(self.tmp.name)
        self.artifact = self.dist / "polymarket-execution-suite-v0.26.0.zip"
        self.artifact.write_bytes(b"artifact")
        self.sha = self.guard.sha256(self.artifact)
        (self.dist / "polymarket-execution-suite-v0.26.0.zip.sha256").write_text(
            f"{self.sha}  {self.artifact.name}\n"
        )
        (self.dist / "polymarket-execution-suite-v0.26.0.zip.evidence.json").write_text(
            json.dumps({"artifact": {"name": self.artifact.name, "sha256": self.sha}})
        )

    def write_index(self, **overrides):
        index = {
            "schema_version": 1,
            "version": "0.26.0",
            "current_release_artifact": {
                "path": self.artifact.name,
                "sha256": self.sha,
                "sha256_sidecar": "polymarket-execution-suite-v0.26.0.zip.sha256",
                "evidence_sidecar": "polymarket-execution-suite-v0.26.0.zip.evidence.json",
                "validated_release": False,
                "production_ready": False,
                "live_trading_ready": False,
            },
            "local_material": [
                {
                    "path": "pmx-canary-review-v0.26-current-no-go",
                    "status": "current_no_go_review_material",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                },
                {
                    "path": "pmx-canary-reviewed-go-v0.26-closed",
                    "status": "consumed_closed",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                },
            ],
        }
        index.update(overrides)
        (self.dist / "INDEX.json").write_text(json.dumps(index))

    def test_valid_index_passes(self):
        self.write_index()
        self.assertEqual(self.guard.validate(self.dist, "0.26.0"), [])

    def test_rejects_mismatched_sidecar_hash(self):
        self.write_index()
        (self.dist / "polymarket-execution-suite-v0.26.0.zip.sha256").write_text(
            f"{'0' * 64}  {self.artifact.name}\n"
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("sha256 sidecar" in failure for failure in failures))

    def test_rejects_reusable_closed_go_material(self):
        self.write_index(
            local_material=[
                {
                    "path": "pmx-canary-reviewed-go-v0.26-closed",
                    "status": "consumed_closed",
                    "approval_reuse_allowed": True,
                    "remote_side_effects_authorized": False,
                }
            ]
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("must not be approval-reusable" in failure for failure in failures))

    def test_rejects_no_go_remote_side_effect_authorization(self):
        self.write_index(
            local_material=[
                {
                    "path": "pmx-canary-review-v0.26-current-no-go",
                    "status": "current_no_go_review_material",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": True,
                }
            ]
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("must not authorize remote side effects" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
