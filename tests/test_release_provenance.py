import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_release_provenance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_release_provenance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_build_and_validate_non_live_provenance(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"release")
            manifest = tmp / "manifest.json"
            manifest.write_text('{"schema_version": 1}\n')
            provenance = self.module.build_provenance(
                artifact=artifact,
                manifest=manifest,
                version="0.28.0",
                root_commit="a" * 40,
                submodules=[
                    {"path": "engine", "commit": "b" * 40},
                    {"path": "adapter", "commit": "c" * 40},
                ],
                ci_runs=[
                    {
                        "workflow_name": "ci",
                        "workflow_run_url": "https://github.com/example/repo/actions/runs/123",
                        "commit_sha": "a" * 40,
                        "workflow_status": "success",
                        "timestamp": "2026-06-11T00:00:00+00:00",
                    }
                ],
                materials=[manifest],
            )

            self.assertEqual(provenance["release_posture"], "non_live_hardened")
            self.assertEqual(
                provenance["subject"]["sha256"],
                hashlib.sha256(b"release").hexdigest(),
            )
            self.assertEqual(self.module.validate_provenance(provenance, artifact), [])

    def test_validation_rejects_live_posture_and_artifact_tampering(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            artifact = Path(tmp_name) / "artifact.zip"
            artifact.write_bytes(b"release")
            provenance = {
                "schema_version": 1,
                "release_posture": "live_ready",
                "version": "0.28.0",
                "subject": {"name": artifact.name, "sha256": "0" * 64},
                "source": {"root_commit": "a" * 40, "submodules": []},
                "ci_runs": [],
                "materials": [],
            }

            failures = self.module.validate_provenance(provenance, artifact)

            self.assertIn("release_posture must be non_live_hardened", failures)
            self.assertIn("subject.sha256 does not match artifact", failures)

    def test_validation_rejects_placeholder_ci_reference(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            artifact = Path(tmp_name) / "artifact.zip"
            artifact.write_bytes(b"release")
            digest = hashlib.sha256(b"release").hexdigest()
            provenance = {
                "schema_version": 1,
                "release_posture": "non_live_hardened",
                "version": "0.28.0",
                "subject": {"name": artifact.name, "sha256": digest},
                "source": {"root_commit": "a" * 40, "submodules": []},
                "ci_runs": [
                    {
                        "workflow_name": "ci",
                        "workflow_run_url": "REPLACE_WITH_RUN_URL",
                        "commit_sha": "a" * 40,
                        "workflow_status": "success",
                        "timestamp": "2026-06-11T00:00:00+00:00",
                    }
                ],
                "materials": [],
            }

            failures = self.module.validate_provenance(provenance, artifact)

            self.assertIn("ci_runs[0].workflow_run_url is not a concrete HTTPS URL", failures)


if __name__ == "__main__":
    unittest.main()
