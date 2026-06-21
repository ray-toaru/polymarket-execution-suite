import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


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
                            "workspace_manifest_snapshot_path": "artifact.workspace-manifest.json",
                            "archived_manifest_binding_kind": "archive_normalized_current_manifest",
                            "workspace_manifest_binding_kind": "post_package_workspace_snapshot",
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
            self.assertFalse(any("workspace_manifest_snapshot_path is missing" in item for item in failures))

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
                            "workspace_manifest_snapshot_path": "artifact.workspace-manifest.json",
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
                zf.writestr(
                    "polymarket_execution_suite_v0_28_0/polymarket-execution-engine/.env.validation",
                    "PMX_TEST_DATABASE_URL=postgres://example\n",
                )
                zf.writestr(
                    "polymarket_execution_suite_v0_28_0/polymarket-execution-engine/.env.runtime.secrets",
                    "POLY_API_SECRET=example\n",
                )
                zf.writestr(
                    "polymarket_execution_suite_v0_28_0/polymarket-execution-engine/.env.validation.example",
                    "PMX_TEST_DATABASE_URL=\n",
                )
                zf.writestr("polymarket_execution_suite_v0_28_0/V0_OLD.md", "old\n")
            with zipfile.ZipFile(zip_path) as zf:
                failures = self.module.validate_archive_members(
                    zf,
                    expected_root="polymarket_execution_suite_v0_28_0",
                    expected_version="0.28.0",
                )
            self.assertTrue(any("forbidden archive members" in item for item in failures))
            self.assertTrue(any("stale root docs in archive" in item for item in failures))
            joined = "\n".join(failures)
            self.assertIn(".env.validation", joined)
            self.assertIn(".env.runtime.secrets", joined)
            self.assertNotIn(".env.validation.example", joined)

    def test_secret_content_scan_rejects_common_assignment_and_json_spellings(self):
        secret_key = "api_" + "secret"
        signature_key = "sign" + "ature"
        signed_key = "signed_" + "payload"
        private_key = "private_" + "key"
        clob_key = "clob" + "Secret"
        passphrase_key = "pass" + "phrase"
        cases = [
            f"{secret_key}=leaked",
            f"{signature_key} : leaked",
            f'"{signed_key}": "leaked"',
            f"{private_key}: leaked",
            f"{clob_key} = leaked",
            f"{passphrase_key}: leaked",
        ]
        for content in cases:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as tmp_name:
                    tmp = Path(tmp_name)
                    zip_path = tmp / "artifact.zip"
                    with zipfile.ZipFile(zip_path, "w") as zf:
                        zf.writestr("polymarket_execution_suite_v0_28_0/VERSION", "0.28.0\n")
                        zf.writestr("polymarket_execution_suite_v0_28_0/README.md", content)
                    with zipfile.ZipFile(zip_path) as zf:
                        failures = self.module.validate_archive_members(
                            zf,
                            expected_root="polymarket_execution_suite_v0_28_0",
                            expected_version="0.28.0",
                        )
                self.assertTrue(
                    any("forbidden secret-like content" in item for item in failures),
                    failures,
                )

    def test_secret_content_scan_allows_registered_negative_test_fixtures(self):
        expected_root = "polymarket_execution_suite_v0_28_0"
        cases = {
            "tests/test_check_release_artifact.py": (
                b"class CheckReleaseArtifactTests",
                b'{"api_secret": "should-not-ship"}',
            ),
            "tests/test_package_release_index.py": (
                b"class PackageReleaseIndexTests",
                b'{"api_secret": "should-not-ship"}',
            ),
            "tests/test_prepare_canary_candidate_market.py": (
                b"class PrepareCanaryCandidateMarketTests",
                b"api_secret=lowercase-secret Signature=mixed-signature",
            ),
        }
        for rel, parts in cases.items():
            with self.subTest(rel=rel):
                data = b"\n".join(parts)
                with tempfile.TemporaryDirectory() as tmp_name:
                    tmp = Path(tmp_name)
                    zip_path = tmp / "artifact.zip"
                    with zipfile.ZipFile(zip_path, "w") as zf:
                        zf.writestr(f"{expected_root}/VERSION", "0.28.0\n")
                        zf.writestr(f"{expected_root}/{rel}", data)
                    with zipfile.ZipFile(zip_path) as zf:
                        failures = self.module.validate_archive_members(
                            zf,
                            expected_root=expected_root,
                            expected_version="0.28.0",
                        )
                self.assertFalse(
                    any("forbidden secret-like content" in item for item in failures),
                    failures,
                )

    def test_validate_archive_members_rejects_historical_marker_beyond_first_line(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            zip_path = tmp / "artifact.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("polymarket_execution_suite_v0_28_0/VERSION", "0.28.0\n")
                zf.writestr(
                    "polymarket_execution_suite_v0_28_0/REVIEW_AUDIT.md",
                    "# Review Audit\n\n> Historical v0.27 continuation note.\n",
                )
            with zipfile.ZipFile(zip_path) as zf:
                failures = self.module.validate_archive_members(
                    zf,
                    expected_root="polymarket_execution_suite_v0_28_0",
                    expected_version="0.28.0",
                )
        self.assertTrue(any("historical root docs in archive" in item for item in failures))

    def test_validate_agents_in_archive_ignores_non_release_numeric_content(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            zip_path = tmp / "artifact.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                for name in self.module.required_agents("polymarket_execution_suite_v0_28_0"):
                    zf.writestr(
                        name,
                        "# AGENTS.md\n\nUse Python >=3.11 and keep 1. 2. 3. examples concise.\n"
                        "Current validation entrypoint is run_current_gates.sh.\n",
                    )
            with zipfile.ZipFile(zip_path) as zf:
                failures = self.module.validate_agents_in_archive(
                    zf, expected_root="polymarket_execution_suite_v0_28_0"
                )
        self.assertEqual(failures, [])

    def test_validate_sidecars_rejects_git_head_mismatch(self):
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
                            "git_head": "deadbeef",
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
                            "workspace_manifest_snapshot_path": "artifact.workspace-manifest.json",
                            "archived_manifest_binding_kind": "archive_normalized_current_manifest",
                            "workspace_manifest_binding_kind": "post_package_workspace_snapshot",
                        },
                    }
                )
            )
            failures, _ = self.module.validate_sidecars(
                artifact,
                expected_version="0.28.0",
                expected_hash=sha,
                expected_git_head="cafebabe",
                expected_submodules=None,
            )
        self.assertTrue(any("source.git_head does not match" in item for item in failures))

    def test_validate_sidecars_rejects_submodule_pin_mismatch(self):
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
                            "workspace_manifest_snapshot_path": "artifact.workspace-manifest.json",
                            "archived_manifest_binding_kind": "archive_normalized_current_manifest",
                            "workspace_manifest_binding_kind": "post_package_workspace_snapshot",
                        },
                    }
                )
            )
            failures, _ = self.module.validate_sidecars(
                artifact,
                expected_version="0.28.0",
                expected_hash=sha,
                expected_git_head=None,
                expected_submodules=[
                    {
                        "path": "polymarket-execution-engine",
                        "commit": "def",
                        "checkout_status": "clean",
                        "checkout_ref": "HEAD",
                    }
                ],
            )
        self.assertTrue(any("source.submodules do not match" in item for item in failures))

    def test_validate_workspace_source_coverage_rejects_missing_member(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            zip_path = tmp / "artifact.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("polymarket_execution_suite_v0_28_0/README.md", "ok\n")
            with zipfile.ZipFile(zip_path) as zf:
                with mock.patch.object(
                    self.module,
                    "release_source_files",
                    return_value=[ROOT / "README.md", ROOT / "VERSION"],
                ):
                    failures = self.module.validate_workspace_source_coverage(
                        zf,
                        expected_root="polymarket_execution_suite_v0_28_0",
                    )
        self.assertTrue(any("missing tracked release source files" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
