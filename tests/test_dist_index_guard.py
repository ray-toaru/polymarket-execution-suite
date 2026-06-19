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
            json.dumps(
                {
                    "schema_version": 1,
                    "artifact": {"name": self.artifact.name, "sha256": self.sha},
                    "canonical_evidence": {
                        "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                        "archived_manifest_sha256": "a" * 64,
                        "workspace_manifest_sha256": "b" * 64,
                        "workspace_manifest_snapshot_path": "polymarket-execution-suite-v0.26.0.workspace-manifest.json",
                        "archived_manifest_binding_kind": "archive_normalized_current_manifest",
                        "workspace_manifest_binding_kind": "post_package_workspace_snapshot",
                    },
                }
            )
        )
        (self.dist / "polymarket-execution-suite-v0.26.0.workspace-manifest.json").write_text("{}\n")
        (self.dist / "pmx-canary-review-v0.26-current-no-go").mkdir()
        (self.dist / "pmx-canary-reviewed-go-v0.26-closed").mkdir()

    def write_index(self, **overrides):
        index = {
            "schema_version": 1,
            "version": "0.26.0",
            "current_release_artifact": {
                "path": self.artifact.name,
                "sha256": self.sha,
                "sha256_sidecar": "polymarket-execution-suite-v0.26.0.zip.sha256",
                "evidence_sidecar": "polymarket-execution-suite-v0.26.0.zip.evidence.json",
                "artifact_class": "controlled_real_funds_canary_source_candidate_non_live",
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

    def test_valid_production_live_candidate_class_passes(self):
        self.write_index(
            current_release_artifact={
                "path": self.artifact.name,
                "sha256": self.sha,
                "sha256_sidecar": "polymarket-execution-suite-v0.26.0.zip.sha256",
                "evidence_sidecar": "polymarket-execution-suite-v0.26.0.zip.evidence.json",
                "artifact_class": "production_live_candidate_non_live_by_default",
                "validated_release": False,
                "production_ready": False,
                "live_trading_ready": False,
            }
        )
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
                    "path": "pmx-v028-reviewed-go-20260527T035142Z",
                    "status": "consumed_closed",
                    "approval_reuse_allowed": True,
                    "remote_side_effects_authorized": False,
                }
            ]
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("must not be approval-reusable" in failure for failure in failures))

    def test_rejects_reviewed_go_status_mismatch_against_contents(self):
        package = self.dist / "pmx-local-material"
        package.mkdir()
        (package / "review.json").write_text(json.dumps({"status": "reviewed_go_package_ready_single_attempt"}) + "\n")
        (package / "release-decision.json").write_text(json.dumps({"status": "reviewed_go"}) + "\n")
        (package / "approval.json").write_text("{}\n")
        (package / "candidate-market.json").write_text("{}\n")
        (package / "runtime-truth.json").write_text("{}\n")
        self.write_index(
            local_material=[
                {
                    "path": "pmx-local-material",
                    "status": "consumed_closed",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                }
            ]
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("does not match reviewed-go contents" in failure for failure in failures))

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

    def test_rejects_unsafe_or_missing_local_material_path(self):
        self.write_index(
            local_material=[
                {
                    "path": "../escape",
                    "status": "review_material_not_release_artifact",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                },
                {
                    "path": "missing-material",
                    "status": "review_material_not_release_artifact",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                },
            ]
        )
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("safe relative path" in failure for failure in failures))
        self.assertTrue(any("missing from dist/" in failure for failure in failures))

    def test_rejects_evidence_sidecar_without_canonical_binding(self):
        (self.dist / "polymarket-execution-suite-v0.26.0.zip.evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": 0,
                    "artifact": {"name": self.artifact.name, "sha256": self.sha},
                    "canonical_evidence": {"manifest_path": "wrong", "archived_manifest_sha256": "bad"},
                }
            )
        )
        self.write_index()
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("schema_version must be 1" in failure for failure in failures))
        self.assertTrue(any("manifest_path is not canonical" in failure for failure in failures))
        self.assertTrue(any("archived_manifest_sha256 must be a sha256 hex string" in failure for failure in failures))

    def test_rejects_evidence_sidecar_without_manifest_binding_kinds(self):
        (self.dist / "polymarket-execution-suite-v0.26.0.zip.evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "artifact": {"name": self.artifact.name, "sha256": self.sha},
                    "canonical_evidence": {
                        "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                        "archived_manifest_sha256": "a" * 64,
                        "workspace_manifest_sha256": "b" * 64,
                        "workspace_manifest_snapshot_path": "polymarket-execution-suite-v0.26.0.workspace-manifest.json",
                    },
                }
            )
        )
        self.write_index()
        failures = self.guard.validate(self.dist, "0.26.0")
        self.assertTrue(any("archived_manifest_binding_kind is invalid" in failure for failure in failures))
        self.assertTrue(any("workspace_manifest_binding_kind is invalid" in failure for failure in failures))

    def test_rejects_unindexed_release_artifact_zip(self):
        self.write_index()
        (self.dist / "polymarket-execution-suite-v0.25.0.zip").write_bytes(b"stale artifact")

        failures = self.guard.validate(self.dist, "0.26.0")

        self.assertTrue(any("unindexed release artifact" in failure for failure in failures))

    def test_rejects_orphan_release_sidecar(self):
        self.write_index()
        (self.dist / "polymarket-execution-suite-v0.25.0.zip.sha256").write_text(
            "0" * 64 + "  polymarket-execution-suite-v0.25.0.zip\n"
        )

        failures = self.guard.validate(self.dist, "0.26.0")

        self.assertTrue(any("orphan release sidecar" in failure for failure in failures))

    def test_rejects_release_sidecar_listed_as_local_material(self):
        self.write_index(
            local_material=[
                {
                    "path": "polymarket-execution-suite-v0.25.0.zip.evidence.json",
                    "status": "local_review_material_not_release_artifact",
                    "approval_reuse_allowed": False,
                    "remote_side_effects_authorized": False,
                }
            ]
        )
        (self.dist / "polymarket-execution-suite-v0.25.0.zip.evidence.json").write_text("{}\n")

        failures = self.guard.validate(self.dist, "0.26.0")

        self.assertTrue(any("local_material must not list release artifact or sidecar" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
