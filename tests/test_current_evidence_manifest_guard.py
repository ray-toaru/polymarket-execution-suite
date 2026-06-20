import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "check_current_evidence_manifest.py"


def load_guard_module():
    spec = importlib.util.spec_from_file_location("check_current_evidence_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CurrentEvidenceManifestGuardTests(unittest.TestCase):
    def setUp(self):
        self.module = load_guard_module()

    def _manifest(self) -> dict:
        data = json.loads((ROOT / "polymarket-execution-engine" / "validation" / "templates" / "evidence_manifest.template.json").read_text())
        data["version"] = "0.28.0"
        data["external_artifact_sidecar"] = {
            "name": "artifact.zip",
            "path": "dist/artifact.zip",
            "sha256": "1" * 64,
            "sha256_sidecar": "artifact.zip.sha256",
            "evidence_sidecar": "artifact.zip.evidence.json",
        }
        return data

    def test_source_candidate_manifest_allows_post_package_workspace_snapshot_binding(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            engine = tmp / "polymarket-execution-engine"
            manifest_path = engine / "evidence" / "current" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            version_path = tmp / "VERSION"
            version_path.write_text("0.28.0\n")
            artifact = tmp / "dist" / "artifact.zip"
            artifact.parent.mkdir()
            artifact.write_bytes(b"new artifact bytes")
            actual_artifact_sha = self.module.sha256(artifact)
            workspace_manifest = tmp / "dist" / "artifact.workspace-manifest.json"
            workspace_manifest.write_text(
                json.dumps(
                    {
                        "external_artifact_sidecar": {
                            "path": "dist/artifact.zip",
                            "sha256": actual_artifact_sha,
                        }
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            workspace_sha = self.module.sha256(workspace_manifest)
            evidence = tmp / "dist" / "artifact.zip.evidence.json"
            evidence.write_text(
                json.dumps(
                    {
                        "artifact": {"sha256": actual_artifact_sha},
                        "canonical_evidence": {
                            "workspace_manifest_sha256": workspace_sha,
                            "workspace_manifest_snapshot_path": workspace_manifest.name,
                            "workspace_manifest_binding_kind": "post_package_workspace_snapshot",
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            manifest_path.write_text(json.dumps(self._manifest()))

            with mock.patch.object(self.module, "ROOT", engine), mock.patch.object(
                self.module, "VERSION_PATHS", [version_path]
            ):
                self.assertEqual(self.module.validate(manifest_path), 0)

    def test_source_candidate_manifest_rejects_stale_artifact_hash_without_workspace_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            engine = tmp / "polymarket-execution-engine"
            manifest_path = engine / "evidence" / "current" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            version_path = tmp / "VERSION"
            version_path.write_text("0.28.0\n")
            artifact = tmp / "dist" / "artifact.zip"
            artifact.parent.mkdir()
            artifact.write_bytes(b"new artifact bytes")
            manifest_path.write_text(json.dumps(self._manifest()))

            with mock.patch.object(self.module, "ROOT", engine), mock.patch.object(
                self.module, "VERSION_PATHS", [version_path]
            ):
                self.assertEqual(self.module.validate(manifest_path), 1)


if __name__ == "__main__":
    unittest.main()
