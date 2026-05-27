import importlib.util
import unittest
from pathlib import Path
import tempfile


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
            ]
            for name in names:
                self.assertTrue(self.checker.forbidden(name, expected_root))


if __name__ == "__main__":
    unittest.main()
