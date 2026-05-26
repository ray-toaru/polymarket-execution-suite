import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_reviewed_go_package.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_reviewed_go_package", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareReviewedGoPackageTests(unittest.TestCase):
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
            "preflight_report": {
                "posted": False,
                "remote_side_effects": False,
                "status": "preflight_ready",
            },
            "remote_side_effects": False,
        }

    def approval_request(self, artifact_sha: str, candidate_sha: str, runtime_sha: str) -> dict:
        return {
            "schema_version": 1,
            "status": "operator_approval_request_not_authorization",
            "approval_id": "approval-request-1",
            "approval_hash": "d" * 64,
            "scope": "REAL_FUNDS_CANARY",
            "account_id": "acct-canary",
            "active_profile_ref": "local-profile://acct-b",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "operator_identity_ref": "operator://primary",
            "dual_control_required": True,
            "artifact_sha256": artifact_sha,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "evidence_manifest_sha256": "c" * 64,
            "market_candidate_sha256": candidate_sha,
            "runtime_truth_sha256": runtime_sha,
            "github_evidence": {
                "root_ci_run_id": "1",
                "hermes_ci_run_id": "2",
                "execution_engine_ci_run_id": "3",
                "credentialed_sdk_run_id": "local",
            },
            "risk_limits": {
                "max_order_notional_usd": "0.2",
                "max_daily_notional_usd": "0.2",
            },
            "live_submit_authorized": False,
            "remote_side_effects_authorized": False,
            "secrets_included": False,
        }

    def external_references(self) -> dict:
        return {
            "secret_custody": {"provider_ref": "local-keyring://pmx"},
            "operator_approval": {"ticket_ref": "ticket://approval"},
            "alert_routing": {
                "route_ref": "pager://route",
                "dashboard_ref": "dashboard://pmx",
            },
            "runbooks": {
                "rollback_runbook_ref": "runbook://rollback",
                "incident_runbook_ref": "runbook://incident",
            },
        }

    def dual_control_review(self, request: dict, approval_request_sha: str, **overrides) -> dict:
        data = {
            "schema_version": 1,
            "status": "approved",
            "scope": "REAL_FUNDS_CANARY",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "review_ref": "dual://review",
            "reviewer_identity_ref": "operator://second-reviewer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "approval_request_sha256": approval_request_sha,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "approval_hash": request["approval_hash"],
            "artifact_sha256": request["artifact_sha256"],
            "workspace_manifest_sha256": request["workspace_manifest_sha256"],
            "archived_manifest_sha256": request["archived_manifest_sha256"],
            "evidence_manifest_sha256": request["evidence_manifest_sha256"],
            "market_candidate_sha256": request["market_candidate_sha256"],
            "runtime_truth_sha256": request["runtime_truth_sha256"],
            "risk_limits": request["risk_limits"],
            "required_reviewer_checks": {
                "artifact_hash_reviewed": True,
                "evidence_manifest_hash_reviewed": True,
                "market_candidate_reviewed": True,
                "runtime_truth_reviewed": True,
                "risk_limits_reviewed": True,
                "secret_custody_reviewed": True,
                "alerting_reviewed": True,
                "rollback_reviewed": True,
                "reconcile_and_cancel_fallback_reviewed": True,
            },
            "secrets_included": False,
        }
        data.update(overrides)
        return data

    def test_build_package_writes_self_contained_reviewed_go_material(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = self.module.sha256(artifact)
            self.write_json(tmp, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            (tmp / "artifact.zip.sha256").write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(tmp, "candidate-market.json", self.candidate())
            candidate_sha = self.module.sha256(candidate)
            runtime = self.write_json(tmp, "runtime-truth.json", self.runtime_truth(artifact_sha))
            runtime_sha = self.module.sha256(runtime)
            approval_doc = self.approval_request(artifact_sha, candidate_sha, runtime_sha)
            approval = self.write_json(tmp, "approval-request.json", approval_doc)
            approval_sha = self.module.sha256(approval)
            review = self.write_json(
                tmp,
                "dual-control-review.json",
                self.dual_control_review(approval_doc, approval_sha),
            )
            external = self.write_json(tmp, "external-references.json", self.external_references())

            out = tmp / "reviewed-go"
            package = self.module.build_package(
                output_dir=out,
                release_zip=artifact,
                release_sha=tmp / "artifact.zip.sha256",
                release_evidence=tmp / "artifact.zip.evidence.json",
                candidate_market=candidate,
                runtime_truth=runtime,
                approval_request=approval,
                dual_control_review=review,
                external_references=external,
                decision_id="decision-1",
                decision_reason="approved by independent reviewer",
            )

            self.assertEqual(package["status"], "reviewed_go_package_ready_single_attempt")
            self.assertTrue(package["live_submit_authorized"])
            self.assertEqual(package["active_profile_ref"], "local-profile://acct-b")
            self.assertTrue((out / "release-decision.json").exists())
            self.assertTrue((out / "approval.json").exists())
            self.assertTrue((out / "approval-request.json").exists())
            self.assertTrue((out / "dual-control-review.json").exists())
            decision = json.loads((out / "release-decision.json").read_text())
            approval = json.loads((out / "approval.json").read_text())
            self.assertEqual(decision["status"], "reviewed_go")
            self.assertTrue(decision["single_attempt"])
            self.assertEqual(decision["max_order_count"], 1)
            self.assertTrue(decision["remote_side_effects_authorized"])
            self.assertEqual(approval["account_id"], "acct-canary")
            self.assertEqual(approval["approval_hash"], approval_doc["approval_hash"])
            self.assertEqual(
                decision["external_references"]["operator_dual_control_review_ref"],
                "dual://review",
            )

    def test_build_package_rejects_inconsistent_runtime_truth_binding(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = self.module.sha256(artifact)
            self.write_json(tmp, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            (tmp / "artifact.zip.sha256").write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(tmp, "candidate-market.json", self.candidate())
            candidate_sha = self.module.sha256(candidate)
            runtime = self.write_json(tmp, "runtime-truth.json", self.runtime_truth("0" * 64))
            runtime_sha = self.module.sha256(runtime)
            approval_doc = self.approval_request(artifact_sha, candidate_sha, runtime_sha)
            approval = self.write_json(tmp, "approval-request.json", approval_doc)
            approval_sha = self.module.sha256(approval)
            review = self.write_json(
                tmp,
                "dual-control-review.json",
                self.dual_control_review(approval_doc, approval_sha),
            )
            external = self.write_json(tmp, "external-references.json", self.external_references())

            with self.assertRaisesRegex(SystemExit, "binding mismatch"):
                self.module.build_package(
                    output_dir=tmp / "reviewed-go",
                    release_zip=artifact,
                    release_sha=tmp / "artifact.zip.sha256",
                    release_evidence=tmp / "artifact.zip.evidence.json",
                    candidate_market=candidate,
                    runtime_truth=runtime,
                    approval_request=approval,
                    dual_control_review=review,
                    external_references=external,
                    decision_id="decision-1",
                    decision_reason="approved by independent reviewer",
                )

    def test_build_package_rejects_non_approved_review(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifact = tmp / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = self.module.sha256(artifact)
            self.write_json(tmp, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            (tmp / "artifact.zip.sha256").write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(tmp, "candidate-market.json", self.candidate())
            candidate_sha = self.module.sha256(candidate)
            runtime = self.write_json(tmp, "runtime-truth.json", self.runtime_truth(artifact_sha))
            runtime_sha = self.module.sha256(runtime)
            approval_doc = self.approval_request(artifact_sha, candidate_sha, runtime_sha)
            approval = self.write_json(tmp, "approval-request.json", approval_doc)
            approval_sha = self.module.sha256(approval)
            review = self.write_json(
                tmp,
                "dual-control-review.json",
                self.dual_control_review(approval_doc, approval_sha, status="draft"),
            )
            external = self.write_json(tmp, "external-references.json", self.external_references())

            with self.assertRaisesRegex(SystemExit, "status must be approved"):
                self.module.build_package(
                    output_dir=tmp / "reviewed-go",
                    release_zip=artifact,
                    release_sha=tmp / "artifact.zip.sha256",
                    release_evidence=tmp / "artifact.zip.evidence.json",
                    candidate_market=candidate,
                    runtime_truth=runtime,
                    approval_request=approval,
                    dual_control_review=review,
                    external_references=external,
                    decision_id="decision-1",
                    decision_reason="approved by independent reviewer",
                )


if __name__ == "__main__":
    unittest.main()
