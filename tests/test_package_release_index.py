import importlib.util
import unittest
from pathlib import Path
import tempfile
from unittest import mock
import json
import contextlib
import io


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_release.py"
CHECKER = ROOT / "scripts" / "check_release_artifact.py"


def load_package_module():
    spec = importlib.util.spec_from_file_location("package_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_checker_module():
    spec = importlib.util.spec_from_file_location("check_release_artifact", CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PackageReleaseIndexTests(unittest.TestCase):
    def setUp(self):
        self.package_release = load_package_module()
        self.checker = load_checker_module()

    def test_dist_index_classifies_consumed_closed_go_package(self):
        entry = self.package_release.classify_dist_entry(
            "pmx-canary-reviewed-go-v0.26-20260523T022339Z-gtc-post-only-size5",
            is_dir=True,
            child_names={
                "release-decision.json",
                "approval-consumed-20260523T022507Z.json",
                "closeout.json",
            },
        )
        self.assertEqual(entry["status"], "consumed_closed")
        self.assertEqual(entry["approval_reuse_allowed"], False)
        self.assertEqual(entry["remote_side_effects_authorized"], False)

    def test_dist_index_classifies_v028_consumed_closed_go_package(self):
        entry = self.package_release.classify_dist_entry(
            "pmx-v028-reviewed-go-20260527T035142Z",
            is_dir=True,
            child_names={
                "release-decision.json",
                "approval-consumed-20260527T035521Z.json",
                "closeout.json",
            },
        )
        self.assertEqual(entry["status"], "consumed_closed")
        self.assertEqual(entry["approval_reuse_allowed"], False)
        self.assertEqual(entry["remote_side_effects_authorized"], False)

    def test_dist_index_classifies_no_go_review_package(self):
        entry = self.package_release.classify_dist_entry(
            "pmx-canary-review-v0.26-20260523T020943Z-gtc-post-only-current-no-go",
            is_dir=True,
            child_names={"release-decision.json", "review.json"},
        )
        self.assertEqual(entry["status"], "current_no_go_review_material")
        self.assertEqual(entry["approval_reuse_allowed"], False)

    def test_dist_index_classifies_reviewed_go_material_from_contents_not_only_name(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            package = Path(tmp_name)
            (package / "review.json").write_text(
                json.dumps({"status": "reviewed_go_package_ready_single_attempt"}) + "\n"
            )
            (package / "release-decision.json").write_text(
                json.dumps({"status": "reviewed_go"}) + "\n"
            )
            for name in ["approval.json", "candidate-market.json", "runtime-truth.json"]:
                (package / name).write_text("{}\n")
            entry = self.package_release.classify_dist_entry(
                "opaque-local-material",
                is_dir=True,
                child_names={child.name for child in package.iterdir()},
                dir_path=package,
            )
        self.assertEqual(entry["status"], "reviewed_go_local_material_not_current_approval")

    def test_release_policy_rejects_secret_like_local_env_and_json_files(self):
        forbidden = [
            Path(".env.local"),
            Path(".env.production"),
            Path(".env.shadow"),
            Path("config/runtime.local.json"),
            Path("secrets/token.txt"),
        ]
        for path in forbidden:
            self.assertFalse(self.package_release.allowed(ROOT / path))

    def test_release_policy_allows_examples_and_rejects_logs(self):
        allowed = [
            ROOT / ".env.example",
            ROOT / "polymarket-execution-engine" / ".env.example",
        ]
        for path in allowed:
            self.assertTrue(self.package_release.allowed(path))

        self.assertFalse(
            self.package_release.allowed(
                ROOT
                / "polymarket-execution-engine"
                / "evidence"
                / "current"
                / "logs"
                / "01-cargo-fmt.log"
            )
        )
        self.assertFalse(self.package_release.allowed(ROOT / "logs" / "scratch.log"))

    def test_artifact_checker_forbidden_matches_packager_policy(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            expected_root = "polymarket_execution_suite_v0_28_0"
            names = [
                f"{expected_root}/.env.local",
                f"{expected_root}/.env.production",
                f"{expected_root}/.env.shadow",
                f"{expected_root}/config/runtime.local.json",
                f"{expected_root}/secrets/token.txt",
                f"{expected_root}/certs/client.p12",
                f"{expected_root}/vault/reviewer.kdbx",
                f"{expected_root}/polymarket-execution-engine/evidence/current/logs/25-contract-validation.report.json",
            ]
            for name in names:
                self.assertTrue(self.checker.forbidden(name, expected_root))

    def test_release_source_files_uses_tracked_files_not_workspace_rglob(self):
        tracked_root = ROOT / "README.md"
        tracked_submodule = ROOT / "polymarket-execution-engine" / "Cargo.toml"

        def fake_tracked_git_files(repo_root: Path):
            if repo_root == ROOT:
                return [tracked_root]
            if repo_root == ROOT / "polymarket-execution-engine":
                return [tracked_submodule]
            return []

        def fail_rglob(*args, **kwargs):
            raise AssertionError("release_source_files must not use workspace rglob")

        with mock.patch.object(self.package_release, "tracked_git_files", side_effect=fake_tracked_git_files):
            with mock.patch.object(
                self.package_release,
                "submodule_records",
                return_value=[{"path": "polymarket-execution-engine", "commit": "x", "checkout_status": "clean", "checkout_ref": "HEAD"}],
            ):
                with mock.patch.object(Path, "rglob", side_effect=fail_rglob):
                    files = self.package_release.release_source_files()

        self.assertIn(tracked_root, files)
        self.assertIn(tracked_submodule, files)

    def test_tracked_git_files_rejects_non_utf8_paths(self):
        with mock.patch.object(
            self.package_release,
            "require_command_output_bytes",
            return_value=b"bad-\xff-path\0",
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.package_release.tracked_git_files(ROOT)
        self.assertIn("non-utf8 path bytes", str(ctx.exception))

    def test_git_status_lines_surfaces_stderr_on_failure(self):
        with mock.patch.object(
            self.package_release,
            "require_command_output",
            side_effect=SystemExit("command failed (128) git -C /tmp status --short: fatal: not a git repository"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.package_release.git_status_lines(Path("/tmp"))
        self.assertIn("fatal: not a git repository", str(ctx.exception))

    def test_contract_validation_report_metadata_returns_path_and_hash(self):
        report = (
            ROOT
            / "polymarket-execution-engine"
            / "evidence"
            / "current"
            / "logs"
            / "25-contract-validation.report.json"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        previous = report.read_text() if report.exists() else None
        try:
            report.write_text(json.dumps({"status": "ok"}, sort_keys=True) + "\n")
            metadata = self.package_release.contract_validation_report_metadata()
            expected_sha256 = self.package_release.sha256(report)
        finally:
            if previous is None:
                report.unlink()
            else:
                report.write_text(previous)

        assert metadata is not None
        self.assertEqual(
            metadata["path"],
            "polymarket-execution-engine/evidence/current/logs/25-contract-validation.report.json",
        )
        self.assertEqual(metadata["sha256"], expected_sha256)

    def test_package_release_main_builds_archive_once_and_writes_workspace_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            root = tmp / "root"
            dist = root / "dist"
            dist.mkdir(parents=True)
            evidence_manifest = root / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json"
            evidence_manifest.parent.mkdir(parents=True)
            evidence_manifest.write_text(
                json.dumps(
                    {
                        "external_artifact_sidecar": {"sha256": None},
                        "artifact": {},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            out = dist / "artifact.zip"
            out.write_bytes(b"zip-bytes")

            original_root = self.package_release.ROOT
            original_dist = self.package_release.DIST
            original_out = self.package_release.OUT
            original_version = self.package_release.VERSION
            try:
                self.package_release.ROOT = root
                self.package_release.DIST = dist
                self.package_release.OUT = out
                self.package_release.VERSION = "0.28.0"

                with mock.patch.object(self.package_release, "build_release_zip") as build_zip, mock.patch.object(
                    self.package_release, "sha256", side_effect=lambda path: "a" * 64 if path == out else "b" * 64
                ), mock.patch.object(
                    self.package_release, "archived_manifest_sha256", return_value="c" * 64
                ), mock.patch.object(
                    self.package_release, "write_dist_index"
                ), mock.patch.object(
                    self.package_release, "command_output", return_value="deadbeef"
                ), mock.patch.object(
                    self.package_release, "git_branch", return_value="branch"
                ), mock.patch.object(
                    self.package_release, "submodule_records", return_value=[]
                ), mock.patch.object(
                    self.package_release, "contract_validation_report_metadata", return_value=None
                ):
                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = self.package_release.main()

                self.assertEqual(rc, 0)
                build_zip.assert_called_once()
                snapshot = dist / "polymarket-execution-suite-v0.28.0.workspace-manifest.json"
                self.assertTrue(snapshot.exists())
                snapshot_json = json.loads(snapshot.read_text())
                self.assertEqual(snapshot_json["external_artifact_sidecar"]["sha256"], "a" * 64)
            finally:
                self.package_release.ROOT = original_root
                self.package_release.DIST = original_dist
                self.package_release.OUT = original_out
                self.package_release.VERSION = original_version

    def test_package_release_main_fails_closed_for_dirty_submodule_checkout(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            root = tmp / "root"
            dist = root / "dist"
            dist.mkdir(parents=True)
            evidence_manifest = root / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json"
            evidence_manifest.parent.mkdir(parents=True)
            evidence_manifest.write_text("{}\n")

            original_root = self.package_release.ROOT
            original_dist = self.package_release.DIST
            original_out = self.package_release.OUT
            original_version = self.package_release.VERSION
            try:
                self.package_release.ROOT = root
                self.package_release.DIST = dist
                self.package_release.OUT = dist / "artifact.zip"
                self.package_release.VERSION = "0.28.0"

                with mock.patch.object(
                    self.package_release,
                    "submodule_records",
                    return_value=[
                        {
                            "path": "polymarket-execution-engine",
                            "commit": "deadbeef",
                            "checkout_status": "+",
                            "checkout_ref": "HEAD",
                        }
                    ],
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        self.package_release.main()
            finally:
                self.package_release.ROOT = original_root
                self.package_release.DIST = original_dist
                self.package_release.OUT = original_out
                self.package_release.VERSION = original_version

        self.assertIn("clean pinned submodules", str(ctx.exception))

    def test_write_dist_index_records_explicit_manifest_binding_kinds(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            dist = tmp / "dist"
            dist.mkdir()
            artifact = dist / "polymarket-execution-suite-v0.28.0.zip"
            artifact.write_bytes(b"artifact")
            (dist / "polymarket-execution-suite-v0.28.0.zip.sha256").write_text("x" * 64 + "  " + artifact.name + "\n")
            (dist / "polymarket-execution-suite-v0.28.0.zip.evidence.json").write_text("{}")

            original_dist = self.package_release.DIST
            original_out = self.package_release.OUT
            original_version = self.package_release.VERSION
            try:
                self.package_release.DIST = dist
                self.package_release.OUT = artifact
                self.package_release.VERSION = "0.28.0"
                self.package_release.write_dist_index("a" * 64, "b" * 64, "c" * 64, "workspace-manifest.json")
                index = json.loads((dist / "INDEX.json").read_text())
            finally:
                self.package_release.DIST = original_dist
                self.package_release.OUT = original_out
                self.package_release.VERSION = original_version

        canonical = index["canonical_evidence"]
        self.assertEqual(canonical["archived_manifest_sha256"], "b" * 64)
        self.assertEqual(canonical["workspace_manifest_sha256"], "c" * 64)
        self.assertEqual(canonical["workspace_manifest_snapshot_path"], "workspace-manifest.json")
        self.assertEqual(canonical["archived_manifest_binding_kind"], "archive_normalized_current_manifest")
        self.assertEqual(canonical["workspace_manifest_binding_kind"], "post_package_workspace_snapshot")


if __name__ == "__main__":
    unittest.main()
