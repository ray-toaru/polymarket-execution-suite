import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "OFFLINE_INDEPENDENT_REVIEW_MANUAL.md"


class OfflineIndependentReviewManualTests(unittest.TestCase):
    def test_manual_is_current_and_indexed(self):
        text = MANUAL.read_text()
        self.assertIn("v0.28.0", text)
        self.assertIn(
            '"OFFLINE_INDEPENDENT_REVIEW_MANUAL.md"',
            (ROOT / "scripts" / "active_docs.py").read_text(),
        )
        self.assertIn(
            '"OFFLINE_INDEPENDENT_REVIEW_MANUAL.md"',
            (
                ROOT
                / "polymarket-execution-engine"
                / "validation"
                / "release_policy.py"
            ).read_text(),
        )

    def test_manual_preserves_independent_human_and_non_live_boundaries(self):
        text = MANUAL.read_text()
        normalized = " ".join(text.split())
        required_phrases = [
            "The reviewer must be a real person who is not the operator.",
            "does not change that decision or enable live execution by itself",
            "The repository validator checks the signature-evidence reference and hash.",
            '"independent_human_review": false',
            '"authorization_effect": "none"',
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, normalized)

    def test_manual_covers_all_required_review_checks(self):
        text = MANUAL.read_text()
        required_checks = [
            "artifact_hash_reviewed",
            "evidence_manifest_hash_reviewed",
            "market_candidate_reviewed",
            "runtime_truth_reviewed",
            "risk_limits_reviewed",
            "secret_custody_reviewed",
            "alerting_reviewed",
            "rollback_reviewed",
            "reconcile_and_cancel_fallback_reviewed",
        ]
        for check in required_checks:
            self.assertIn(check, text)

    def test_manual_uses_existing_packet_and_reviewed_go_entrypoints(self):
        text = MANUAL.read_text()
        self.assertIn("scripts/prepare_dual_control_review_template.py", text)
        self.assertIn("scripts/prepare_dual_control_review_packet.py", text)
        self.assertIn("scripts/prepare_canary_reviewed_go_bundle.py", text)


if __name__ == "__main__":
    unittest.main()
