import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile_remaining_issues.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_remaining_issues", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReconcileRemainingIssuesTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_input(self, data: dict) -> Path:
        path = self.root / "remaining.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def test_reconcile_closes_accepted_debt_without_live_ready_claim(self):
        input_path = self.write_input(
            {
                "accepted_non_live_non_blocking": [
                    {
                        "id": "F-009",
                        "category": "release",
                        "severity": "S2",
                        "issue": "dist INDEX reviewed-go debt",
                    },
                    {
                        "id": "F-147",
                        "category": "quality",
                        "severity": "S3",
                        "issue": "logging cleanup",
                    },
                ],
                "accepted_non_live_non_blocking_count": 2,
                "locally_closed": [],
                "locally_closed_count": 0,
                "remaining": [
                    {
                        "id": "B-001",
                        "current_tracker_status": "intentional_non_live_control",
                        "issue": "must not be live ready",
                    },
                    {
                        "id": "B-009",
                        "current_tracker_status": "external_evidence_required",
                        "issue": "fresh signature required",
                    },
                    {
                        "id": "B-010",
                        "current_tracker_status": "intentional_non_live_control",
                        "issue": "manifest blockers",
                    },
                    {
                        "id": "F-001",
                        "current_tracker_status": "intentional_non_live_control",
                        "issue": "non-live branch posture",
                    },
                    {
                        "id": "F-100",
                        "current_tracker_status": "external_evidence_required",
                        "issue": "review signature required",
                    },
                ],
                "remaining_count": 5,
                "summary": {},
            }
        )

        report = self.module.reconcile(input_path)

        self.assertEqual(report["accepted_non_live_non_blocking"], [])
        self.assertEqual(report["accepted_non_live_non_blocking_count"], 0)
        self.assertEqual(report["counts"]["accepted_non_live_non_blocking"], 0)
        self.assertEqual(report["closed_non_live_debt_count"], 2)
        self.assertEqual(
            {item["id"] for item in report["closed_non_live_debt"]},
            {"F-009", "F-147"},
        )
        self.assertEqual(
            {item["current_tracker_status"] for item in report["policy_promotion_gates"]},
            {"blocked_policy_promotion_gate"},
        )
        self.assertEqual(
            {item["id"] for item in report["policy_promotion_gates"]},
            {"B-001", "B-010", "F-001"},
        )
        self.assertEqual(
            {item["id"] for item in report["remaining"]},
            {"B-009", "F-100", "B-001", "B-010", "F-001"},
        )
        self.assertFalse(report["summary"]["production_ready"])
        self.assertFalse(report["summary"]["live_trading_ready"])
        self.assertFalse(report["summary"]["validated_release"])
        self.assertIn("non-live", report["status_summary"])

    def test_reconcile_rejects_unknown_accepted_debt_id(self):
        input_path = self.write_input(
            {
                "accepted_non_live_non_blocking": [{"id": "F-999", "issue": "unknown"}],
                "locally_closed": [],
                "remaining": [],
            }
        )

        with self.assertRaisesRegex(ValueError, "unknown accepted debt id"):
            self.module.reconcile(input_path)

    def test_reconcile_is_idempotent_after_accepted_bucket_is_empty(self):
        input_path = self.write_input(
            {
                "accepted_non_live_non_blocking": [],
                "accepted_non_live_non_blocking_count": 0,
                "closed_non_live_debt": [
                    {
                        "id": "F-009",
                        "current_tracker_status": "closed_by_existing_hardening",
                        "issue": "already reconciled",
                    }
                ],
                "closed_non_live_debt_count": 1,
                "locally_closed": [
                    {
                        "id": "F-009",
                        "current_tracker_status": "closed_by_existing_hardening",
                        "issue": "already reconciled",
                    }
                ],
                "locally_closed_count": 1,
                "remaining": [
                    {
                        "id": "B-001",
                        "current_tracker_status": "blocked_policy_promotion_gate",
                        "issue": "must remain blocked",
                    }
                ],
                "remaining_count": 1,
                "summary": {},
            }
        )

        report = self.module.reconcile(input_path)

        self.assertEqual(report["closed_non_live_debt_count"], 1)
        self.assertEqual(report["closed_non_live_debt"][0]["id"], "F-009")
        self.assertEqual(report["locally_closed_count"], 1)
        self.assertEqual([item["id"] for item in report["locally_closed"]], ["F-009"])
        self.assertEqual(report["policy_promotion_gate_count"], 1)


if __name__ == "__main__":
    unittest.main()
