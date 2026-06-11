import importlib.util
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_dual_control_review_signature.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_dual_control_review_signature", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VerifyDualControlReviewSignatureTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def fixture(self, tmp: Path, *, status: str = "active", method: str = "gpg") -> dict[str, Path]:
        identity = "reviewer://lei"
        attestation = self.write_json(
            tmp,
            "lei-signing-key-attestation.json",
            {
                "schema_version": 1,
                "reviewer_identity_ref": identity,
                "signing_method": method,
                "signing_key_fingerprint": "ABCDEF123456",
                "status": "active",
            },
        )
        review = {
            "reviewer_identity_ref": identity,
            "review_signature_evidence_sha256": self.module.sha256(attestation),
        }
        approved = self.write_json(tmp, "dual-control-review.approved.json", review)
        canonical = self.write_json(tmp, "dual-control-review.approved.canonical.json", review)
        signature = tmp / "dual-control-review.signature"
        signature.write_text("test-signature\n")
        public_key = tmp / "lei-public-key.asc"
        public_key.write_text("test-public-key\n")
        allowed_signers = tmp / "allowed_signers"
        allowed_signers.write_text("lei@example.invalid ssh-ed25519 AAAA\n")
        registry = self.write_json(
            tmp,
            "reviewer-registry.json",
            {
                "schema_version": 1,
                "reviewers": [
                    {
                        "reviewer_identity_ref": identity,
                        "status": status,
                        "allowed_signing_method": method,
                        "signing_key_fingerprint": "ABCDEF123456",
                        "public_key_file": "lei-public-key.asc",
                        "allowed_signers_file": "allowed_signers",
                        "ssh_principal": "lei@example.invalid",
                        "signing_key_attestation_file": "lei-signing-key-attestation.json",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    }
                ],
            },
        )
        return {
            "approved": approved,
            "canonical": canonical,
            "signature": signature,
            "registry": registry,
        }

    def test_verifies_gpg_signature_with_registered_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            paths = self.fixture(Path(tmp_name), method="gpg")

            def fake_run(cmd, **kwargs):
                if "--import" in cmd:
                    return subprocess.CompletedProcess(cmd, 0, stdout="imported\n", stderr="")
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="[GNUPG:] VALIDSIG ABCDEF123456 2026-06-11\n",
                    stderr="",
                )

            result = self.module.verify_review_signature(
                approved_review_file=paths["approved"],
                canonical_review_file=paths["canonical"],
                signature_file=paths["signature"],
                reviewer_registry_file=paths["registry"],
                run_command=fake_run,
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["signature_method"], "gpg")

    def test_rejects_pending_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            paths = self.fixture(Path(tmp_name), status="pending_key_registration")
            with self.assertRaisesRegex(SystemExit, "status must be active"):
                self.module.verify_review_signature(
                    approved_review_file=paths["approved"],
                    canonical_review_file=paths["canonical"],
                    signature_file=paths["signature"],
                    reviewer_registry_file=paths["registry"],
                )

    def test_rejects_canonical_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            paths = self.fixture(Path(tmp_name))
            paths["canonical"].write_text('{"reviewer_identity_ref":"reviewer://other"}\n')
            with self.assertRaisesRegex(SystemExit, "canonical"):
                self.module.verify_review_signature(
                    approved_review_file=paths["approved"],
                    canonical_review_file=paths["canonical"],
                    signature_file=paths["signature"],
                    reviewer_registry_file=paths["registry"],
                )

    def test_rejects_unregistered_gpg_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            paths = self.fixture(Path(tmp_name), method="gpg")

            def fake_run(cmd, **kwargs):
                return subprocess.CompletedProcess(cmd, 0, stdout="[GNUPG:] VALIDSIG 0000\n", stderr="")

            with self.assertRaisesRegex(SystemExit, "registered fingerprint"):
                self.module.verify_review_signature(
                    approved_review_file=paths["approved"],
                    canonical_review_file=paths["canonical"],
                    signature_file=paths["signature"],
                    reviewer_registry_file=paths["registry"],
                    run_command=fake_run,
                )


if __name__ == "__main__":
    unittest.main()
