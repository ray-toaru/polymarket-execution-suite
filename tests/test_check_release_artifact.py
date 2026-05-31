import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_artifact.py"


def load_checker_module():
    spec = importlib.util.spec_from_file_location("check_release_artifact", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CheckReleaseArtifactTests(unittest.TestCase):
    def setUp(self):
        self.module = load_checker_module()

    def test_validate_sidecars_rejects_missing_workspace_manifest_sha(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"zip-bytes")
            sha = self.module.sha256(artifact)
            artifact.with_suffix(".zip.sha256").write_text(f"{sha}  {artifact.name}\n")
            artifact.with_suffix(".zip.evidence.json").write_text(
                json.dumps(
                    {
                        "artifact": {
                            "name": artifact.name,
                            "sha256": sha,
                            "sha256_sidecar": artifact.with_suffix(".zip.sha256").name,
                        },
                        "source": {
                            "version": "0.28.0",
                            "git_head": "abc",
                            "submodules": [
                                {
                                    "path": "polymarket-execution-engine",
                                    "commit": "abc",
                                    "checkout_status": "clean",
                                    "checkout_ref": "HEAD",
                                }
                            ],
                        },
                        "canonical_evidence": {
                            "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                            "archived_manifest_sha256": "a" * 64,
                            "archived_manifest_binding_kind": "archive_normalized_current_manifest",
                            "workspace_manifest_binding_kind": "post_package_workspace_binding",
                        },
                    }
                )
            )
            failures, evidence = self.module.validate_sidecars(
                artifact,
                expected_version="0.28.0",
                expected_hash=sha,
            )
            self.assertIsNotNone(evidence)
            self.assertTrue(any("workspace_manifest_sha256 is missing" in item for item in failures))

    def test_validate_sidecars_rejects_invalid_manifest_binding_kinds(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"zip-bytes")
            sha = self.module.sha256(artifact)
            artifact.with_suffix(".zip.sha256").write_text(f"{sha}  {artifact.name}\n")
            artifact.with_suffix(".zip.evidence.json").write_text(
                json.dumps(
                    {
                        "artifact": {
                            "name": artifact.name,
                            "sha256": sha,
                            "sha256_sidecar": artifact.with_suffix(".zip.sha256").name,
                        },
                        "source": {
                            "version": "0.28.0",
                            "git_head": "abc",
                            "submodules": [
                                {
                                    "path": "polymarket-execution-engine",
                                    "commit": "abc",
                                    "checkout_status": "clean",
                                    "checkout_ref": "HEAD",
                                }
                            ],
                        },
                        "canonical_evidence": {
                            "manifest_path": "polymarket-execution-engine/evidence/current/manifest.json",
                            "archived_manifest_sha256": "a" * 64,
                            "workspace_manifest_sha256": "b" * 64,
                            "archived_manifest_binding_kind": "wrong",
                            "workspace_manifest_binding_kind": "wrong",
                        },
                    }
                )
            )
            failures, _ = self.module.validate_sidecars(
                artifact,
                expected_version="0.28.0",
                expected_hash=sha,
            )
        self.assertTrue(any("archived_manifest_binding_kind is invalid" in item for item in failures))
        self.assertTrue(any("workspace_manifest_binding_kind is invalid" in item for item in failures))

    def test_validate_archive_members_rejects_forbidden_and_stale_docs(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            zip_path = tmp / "artifact.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("polymarket_execution_suite_v0_28_0/VERSION", "0.28.0\n")
                zf.writestr("polymarket_execution_suite_v0_28_0/.env.local", "bad\n")
                zf.writestr("polymarket_execution_suite_v0_28_0/V0_OLD.md", "old\n")
            with zipfile.ZipFile(zip_path) as zf:
                failures = self.module.validate_archive_members(
                    zf,
                    expected_root="polymarket_execution_suite_v0_28_0",
                    expected_version="0.28.0",
                )
            self.assertTrue(any("forbidden archive members" in item for item in failures))
            self.assertTrue(any("stale root docs in archive" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
