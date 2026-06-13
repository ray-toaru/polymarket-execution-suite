import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "OFFLINE_INDEPENDENT_REVIEW_MANUAL.md"
LEI_REGISTRY = ROOT / "external_reviews" / "reviewer-registry" / "lei.pending.json"
REVIEW_AUDIT = ROOT / "REVIEW_AUDIT.md"
DESIGN_DECISION_RECORD = ROOT / "DESIGN_DECISION_RECORD.md"
DOC_STATUS = ROOT / "DOC_STATUS.md"


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

    def test_manual_preserves_independent_reviewer_and_non_live_boundaries(self):
        text = MANUAL.read_text()
        normalized = " ".join(text.split())
        required_phrases = [
            "The reviewer must be an accountable natural person who is distinct from the operator",
            "does not change that decision or enable live execution by itself",
            "The repository validator now requires this cryptographic verification",
            '"signed_reviewer_approval": false',
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
        self.assertIn("scripts/verify_dual_control_review_signature.py", text)
        self.assertIn("scripts/prepare_dual_control_review_template.py", text)
        self.assertIn("scripts/prepare_dual_control_review_packet.py", text)
        self.assertIn("scripts/prepare_canary_reviewed_go_bundle.py", text)

    def test_lei_registry_is_pending_not_authorizing(self):
        registry = json.loads(LEI_REGISTRY.read_text())
        reviewer = registry["reviewers"][0]
        self.assertEqual(reviewer["reviewer_identity_ref"], "reviewer://lei")
        self.assertEqual(reviewer["status"], "pending_key_registration")
        self.assertIn("REPLACE_WITH_", reviewer["allowed_signers_file"])

    def test_posthoc_main_review_is_documented_without_live_authorization(self):
        combined = "\n".join(
            [
                REVIEW_AUDIT.read_text(),
                DESIGN_DECISION_RECORD.read_text(),
                DOC_STATUS.read_text(),
            ]
        )
        normalized = " ".join(combined.split())
        required = [
            "42505d90a20a7cfb11e00a7161690e50a7d64d2a",
            "8006d7de0edf4a87371f2fb70751fa804da3f636",
            "27459730580",
            "27459730710",
            "81797dfae7a58f4c6f5a928244940657e69d7935bf8c47602814223f5da0fe47",
            "304b7b3db5dd4eec7d6c1c7cf53fb1f9a14a7e377edb802d631eb354d0478887",
            "external_reviews/lei/final-main-posthoc-review.approved.json",
            "does not authorize live submit, live cancel, production deployment, or another canary attempt",
            "requires fresh CI and fresh independent review for the changed final state",
        ]
        for phrase in required:
            self.assertIn(phrase, normalized)


if __name__ == "__main__":
    unittest.main()
