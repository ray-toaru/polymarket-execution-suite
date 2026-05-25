import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_dual_control_review_packet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_dual_control_review_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareDualControlReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def release_sidecar(self, artifact_sha: str) -> dict:
        return {
            "artifact": {"sha256": artifact_sha},
            "canonical_evidence": {
                "workspace_manifest_sha256": "b" * 64,
                "archived_manifest_sha256": "c" * 64,
            },
        }

    def candidate(self) -> dict:
        return {"side": "BUY", "order_type": "GTC", "post_only": True}

    def runtime_truth(self, artifact_sha: str) -> dict:
        return {
            "artifact_sha256": artifact_sha,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "posted": False,
            "remote_side_effects": False,
            "preflight_ready": True,
        }

    def approval_request(self, artifact_sha: str, candidate_sha: str, runtime_sha: str) -> dict:
        return {
            "status": "operator_approval_request_not_authorization",
            "approval_hash": "d" * 64,
            "artifact_sha256": artifact_sha,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "market_candidate_sha256": candidate_sha,
            "runtime_truth_sha256": runtime_sha,
            "live_submit_authorized": False,
            "remote_side_effects_authorized": False,
        }

    def dual_control_template(
        self,
        *,
        approval_hash: str,
        approval_request_sha: str,
        artifact_sha: str,
        candidate_sha: str,
        runtime_sha: str,
    ) -> dict:
        return {
            "status": "draft_requires_independent_reviewer",
            "review_ref": "REPLACE_WITH_DUAL_CONTROL_REVIEW_REF",
            "reviewer_identity_ref": "REPLACE_WITH_INDEPENDENT_REVIEWER_IDENTITY_REF",
            "approval_hash": approval_hash,
            "approval_request_sha256": approval_request_sha,
            "artifact_sha256": artifact_sha,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "evidence_manifest_sha256": "c" * 64,
            "market_candidate_sha256": candidate_sha,
            "runtime_truth_sha256": runtime_sha,
            "required_reviewer_checks": {
                "artifact_hash_reviewed": False,
                "evidence_manifest_hash_reviewed": False,
                "market_candidate_reviewed": False,
                "runtime_truth_reviewed": False,
                "risk_limits_reviewed": False,
                "secret_custody_reviewed": False,
                "alerting_reviewed": False,
                "rollback_reviewed": False,
                "reconcile_and_cancel_fallback_reviewed": False,
            },
            "reviewer_instruction": "This template is not an authorization.",
        }

    def test_build_packet_binds_and_copies_materials(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = self.module.sha256(artifact)
            release_sidecar = self.write_json(tmp, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            release_sha = tmp / "artifact.zip.sha256"
            release_sha.write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(tmp, "candidate-market.json", self.candidate())
            candidate_sha = self.module.sha256(candidate)
            runtime = self.write_json(tmp, "runtime-truth.json", self.runtime_truth(artifact_sha))
            runtime_sha = self.module.sha256(runtime)
            approval = self.write_json(tmp, "approval-request.json", self.approval_request(artifact_sha, candidate_sha, runtime_sha))
            approval_sha = self.module.sha256(approval)
            dual_control = self.write_json(
                tmp,
                "dual-control-review.template.json",
                self.dual_control_template(
                    approval_hash="d" * 64,
                    approval_request_sha=approval_sha,
                    artifact_sha=artifact_sha,
                    candidate_sha=candidate_sha,
                    runtime_sha=runtime_sha,
                ),
            )
            out = tmp / "packet"
            packet = self.module.build_packet(
                output_dir=out,
                release_zip=artifact,
                release_sha=release_sha,
                release_evidence=release_sidecar,
                candidate=candidate,
                runtime_truth=runtime,
                approval_request=approval,
                dual_control_template=dual_control,
            )
            self.assertEqual(packet["status"], "dual_control_review_packet_not_authorization")
            self.assertEqual(packet["artifact_sha256"], artifact_sha)
            self.assertEqual(packet["candidate_market_sha256"], candidate_sha)
            self.assertEqual(packet["runtime_truth_sha256"], runtime_sha)
            self.assertFalse(packet["live_submit_authorized"])
            self.assertFalse(packet["remote_side_effects_authorized"])
            self.assertTrue((out / "approval-request.json").exists())
            self.assertTrue((out / "dual-control-review.template.json").exists())
            self.assertIn("not an authorization", self.module.packet_readme(packet))

    def test_build_packet_rejects_binding_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = self.module.sha256(artifact)
            release_sidecar = self.write_json(tmp, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            release_sha = tmp / "artifact.zip.sha256"
            release_sha.write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(tmp, "candidate-market.json", self.candidate())
            candidate_sha = self.module.sha256(candidate)
            runtime = self.write_json(tmp, "runtime-truth.json", self.runtime_truth(artifact_sha))
            runtime_sha = self.module.sha256(runtime)
            approval = self.write_json(tmp, "approval-request.json", self.approval_request(artifact_sha, "0" * 64, runtime_sha))
            approval_sha = self.module.sha256(approval)
            dual_control = self.write_json(
                tmp,
                "dual-control-review.template.json",
                self.dual_control_template(
                    approval_hash="d" * 64,
                    approval_request_sha=approval_sha,
                    artifact_sha=artifact_sha,
                    candidate_sha=candidate_sha,
                    runtime_sha=runtime_sha,
                ),
            )
            with self.assertRaisesRegex(SystemExit, "binding mismatch"):
                self.module.build_packet(
                    output_dir=tmp / "packet",
                    release_zip=artifact,
                    release_sha=release_sha,
                    release_evidence=release_sidecar,
                    candidate=candidate,
                    runtime_truth=runtime,
                    approval_request=approval,
                    dual_control_template=dual_control,
                )


if __name__ == "__main__":
    unittest.main()
