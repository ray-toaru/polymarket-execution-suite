import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_canary_reviewed_go_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_reviewed_go_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareCanaryReviewedGoBundleTests(unittest.TestCase):
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
            "account_id": "acct-canary",
            "condition_id": "condition-1",
            "artifact_sha256": artifact_sha,
            "workspace_manifest_sha256": "b" * 64,
            "archived_manifest_sha256": "c" * 64,
            "preflight_report": {
                "posted": False,
                "remote_side_effects": False,
                "status": "preflight_ready",
                "live_submit_allowed": False,
                "real_funds_canary_allowed": False,
                "preconditions_live_submit_would_pass": True,
                "preconditions_real_funds_canary_would_pass": True,
                "kill_switch_open": True,
                "runtime_worker_healthy": True,
                "geoblock_allowed": True,
                "repository_reservation_exists": True,
                "idempotency_key_written": True,
                "reconcile_worker_healthy": True,
                "cancel_only_fallback_ready": True,
                "balance_allowance_checked": True,
                "gate_evidence_refs": {
                    "kill_switch_open": "pg://runtime/kill-switch",
                    "runtime_worker_healthy": "pg://runtime/runtime-worker",
                    "geoblock_allowed": "pg://runtime/geoblock",
                    "repository_reservation_exists": "pg://runtime/reservation",
                    "idempotency_key_written": "pg://runtime/idempotency",
                    "reconcile_worker_healthy": "pg://runtime/reconcile",
                    "cancel_only_fallback_ready": "pg://runtime/cancel-only-fallback",
                    "balance_allowance_checked": "pg://runtime/allowance",
                },
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
            "condition_id": "condition-1",
            "active_profile_ref": "local-profile://acct_b",
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
            "runtime_gate_snapshot": {
                "preconditions_live_submit_would_pass": True,
                "preconditions_real_funds_canary_would_pass": True,
                "kill_switch_open": True,
                "runtime_worker_healthy": True,
                "geoblock_allowed": True,
                "repository_reservation_exists": True,
                "idempotency_key_written": True,
                "reconcile_worker_healthy": True,
                "cancel_only_fallback_ready": True,
                "balance_allowance_checked": True,
            },
            "runtime_gate_evidence_refs": {
                "kill_switch_open": "pg://runtime/kill-switch",
                "runtime_worker_healthy": "pg://runtime/runtime-worker",
                "geoblock_allowed": "pg://runtime/geoblock",
                "repository_reservation_exists": "pg://runtime/reservation",
                "idempotency_key_written": "pg://runtime/idempotency",
                "reconcile_worker_healthy": "pg://runtime/reconcile",
                "cancel_only_fallback_ready": "pg://runtime/cancel-only-fallback",
                "balance_allowance_checked": "pg://runtime/allowance",
            },
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

    def dual_control_review(self, request: dict, approval_request_sha: str) -> dict:
        return {
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

    def test_prepare_reviewed_go_bundle_promotes_review_packet(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            reviewed_go_package = self.module.load_module(
                ROOT / "scripts" / "prepare_reviewed_go_package.py",
                "prepare_reviewed_go_package",
            )
            packet_dir = tmp / "review-packet"
            packet_dir.mkdir()
            artifact = packet_dir / "artifact.zip"
            artifact.write_bytes(b"artifact")
            artifact_sha = reviewed_go_package.sha256(artifact)
            self.write_json(packet_dir, "artifact.zip.evidence.json", self.release_sidecar(artifact_sha))
            (packet_dir / "artifact.zip.sha256").write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(packet_dir, "candidate-market.json", self.candidate())
            candidate_sha = reviewed_go_package.sha256(candidate)
            runtime = self.write_json(packet_dir, "runtime-truth.json", self.runtime_truth(artifact_sha))
            runtime_sha = reviewed_go_package.sha256(runtime)
            approval_doc = self.approval_request(artifact_sha, candidate_sha, runtime_sha)
            approval = self.write_json(packet_dir, "approval-request.json", approval_doc)
            approval_sha = reviewed_go_package.sha256(approval)
            self.write_json(
                packet_dir,
                "dual-control-review.template.json",
                {
                    "status": "draft_requires_independent_reviewer",
                    "review_ref": "REPLACE_WITH_DUAL_CONTROL_REVIEW_REF",
                    "reviewer_identity_ref": "REPLACE_WITH_INDEPENDENT_REVIEWER_IDENTITY_REF",
                    "approval_hash": approval_doc["approval_hash"],
                    "approval_request_sha256": approval_sha,
                    "required_reviewer_checks": {"artifact_hash_reviewed": False},
                },
            )
            self.write_json(
                packet_dir,
                "packet.json",
                {
                    "status": "dual_control_review_packet_not_authorization",
                    "files": {
                        "release_zip": {"path": "artifact.zip"},
                        "release_sha256": {"path": "artifact.zip.sha256"},
                        "release_evidence": {"path": "artifact.zip.evidence.json"},
                        "candidate_market": {"path": "candidate-market.json"},
                        "runtime_truth": {"path": "runtime-truth.json"},
                        "approval_request": {"path": "approval-request.json"},
                        "dual_control_review_template": {"path": "dual-control-review.template.json"},
                    },
                },
            )
            approved_review = self.write_json(
                tmp,
                "dual-control-review.approved.json",
                self.dual_control_review(approval_doc, approval_sha),
            )
            external = self.write_json(tmp, "external-references.json", self.external_references())

            result = self.module.prepare_reviewed_go_bundle(
                review_packet_dir=packet_dir,
                approved_dual_control_review_file=approved_review,
                external_references_file=external,
                output_dir=tmp / "reviewed-go",
                decision_id="decision-1",
                decision_reason="approved by independent reviewer",
            )

            self.assertEqual(result["package_status"], "reviewed_go_package_ready_single_attempt")
            self.assertEqual(result["active_profile_ref"], "local-profile://acct_b")
            self.assertTrue((tmp / "reviewed-go" / "release-decision.json").exists())
            self.assertTrue((tmp / "reviewed-go" / "approval.json").exists())


if __name__ == "__main__":
    unittest.main()
