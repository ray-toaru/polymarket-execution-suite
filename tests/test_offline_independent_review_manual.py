import unittest
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "OFFLINE_INDEPENDENT_REVIEW_MANUAL.md"
LEI_REGISTRY = ROOT / "external_reviews" / "reviewer-registry" / "lei.pending.json"
LEI_ACTIVE_REGISTRY = ROOT / "external_reviews" / "reviewer-registry" / "lei.active-registry.json"
FINAL_REVIEW = (
    ROOT
    / "external_reviews"
    / "lei"
    / "final-commit-package-hash-review.approved.canonical.json"
)
REVIEW_AUDIT = ROOT / "REVIEW_AUDIT.md"
DESIGN_DECISION_RECORD = ROOT / "DESIGN_DECISION_RECORD.md"
DOC_STATUS = ROOT / "DOC_STATUS.md"
VALIDATION_REPORT = ROOT / "VALIDATION_REPORT.md"
CURRENT_STATE_DOCS = [
    ROOT / "REVIEW_AUDIT.md",
    ROOT / "DOC_STATUS.md",
    ROOT / "docs" / "future" / "CANARY_DECISION_PREP_AUDIT.md",
    ROOT / "docs" / "future" / "CANARY_GO_NO_GO_REVIEW.md",
]


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

    def test_lei_active_registry_is_available_for_signed_reviews(self):
        if not LEI_ACTIVE_REGISTRY.exists():
            self.skipTest("external active reviewer registry is intentionally untracked")

        registry = json.loads(LEI_ACTIVE_REGISTRY.read_text())
        reviewer = registry["reviewers"][0]
        self.assertEqual(reviewer["reviewer_identity_ref"], "reviewer://lei")
        self.assertEqual(reviewer["status"], "active")
        self.assertEqual(reviewer["ssh_principal"], "lei@beyin.tech")
        self.assertEqual(
            reviewer["signing_key_fingerprint"],
            "SHA256:D8ZJbmZfyME4gYjZSZ117E7SU/VWIwhAcIjwXLdHS8w",
        )

    def test_final_package_hash_review_is_documented_without_live_authorization(self):
        adapter_head = subprocess.check_output(
            ["git", "-C", str(ROOT / "hermes-polymarket-executor-adapter"), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        combined = "\n".join(
            [
                REVIEW_AUDIT.read_text(),
                DESIGN_DECISION_RECORD.read_text(),
                DOC_STATUS.read_text(),
                VALIDATION_REPORT.read_text(),
            ]
        )
        normalized = " ".join(combined.split())
        required = [
            adapter_head,
            "27474066294",
            "27473948617",
            "27473806418",
            "external_reviews/lei/final-commit-package-hash-review.approved.canonical.json",
            "does not authorize live submit, live cancel, production deployment, or another canary attempt",
            "requires fresh CI",
            "fresh review",
            "detached sidecars",
        ]
        for phrase in required:
            self.assertIn(phrase, normalized)

        stale = [
            "42505d90a20a7cfb11e00a7161690e50a7d64d2a",
            "8006d7de0edf4a87371f2fb70751fa804da3f636",
            "27459730580",
            "27459730710",
        ]
        for phrase in stale:
            self.assertNotIn(phrase, normalized)

    def test_current_state_docs_do_not_reuse_stale_final_state_refs(self):
        combined = "\n".join(path.read_text() for path in CURRENT_STATE_DOCS)
        stale = [
            "42505d90a20a7cfb11e00a7161690e50a7d64d2a",
            "8006d7de0edf4a87371f2fb70751fa804da3f636",
            "27459730580",
            "27459730710",
            "26254755001",
            "26254745573",
            "bb16582e299f9e6f8da6044226e33900c4e2459d",
            "76fdb3ee136b0350e4718fff60a1edcee1f67d03",
            "80b4b7fa8ef325ffb3cff6d839176a9af1ce28ce226c4d3ebef826c6c2b981d1",
            "34fb11e9bbeb082aa30e296b85e3129abf7d9927",
            "67e9b67fe8b9bce54bd33c8fc6ba5fb42b4bea7f5e5f0819a792db26ec01b949",
        ]
        for phrase in stale:
            self.assertNotIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
