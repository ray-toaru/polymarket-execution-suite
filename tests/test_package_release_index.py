import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_release.py"


def load_package_module():
    spec = importlib.util.spec_from_file_location("package_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PackageReleaseIndexTests(unittest.TestCase):
    def setUp(self):
        self.package_release = load_package_module()

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

    def test_dist_index_classifies_no_go_review_package(self):
        entry = self.package_release.classify_dist_entry(
            "pmx-canary-review-v0.26-20260523T020943Z-gtc-post-only-current-no-go",
            is_dir=True,
            child_names={"release-decision.json", "review.json"},
        )
        self.assertEqual(entry["status"], "current_no_go_review_material")
        self.assertEqual(entry["approval_reuse_allowed"], False)


if __name__ == "__main__":
    unittest.main()
