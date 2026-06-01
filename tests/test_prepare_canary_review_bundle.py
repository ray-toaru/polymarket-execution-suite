import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_canary_review_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_review_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareCanaryReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def test_review_bundle_builds_runtime_env_approval_template_and_packet(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            captured_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
            approval_module = self.module.load_module(
                ROOT / "scripts" / "prepare_operator_approval_request.py",
                "prepare_operator_approval_request",
            )
            release_zip = tmp / "artifact.zip"
            release_zip.write_bytes(b"artifact")
            artifact_sha = approval_module.sha256(release_zip)
            self.write_json(
                tmp,
                "artifact.zip.evidence.json",
                {
                    "artifact": {"sha256": artifact_sha},
                    "canonical_evidence": {
                        "workspace_manifest_sha256": "b" * 64,
                        "archived_manifest_sha256": "c" * 64,
                        "manifest_sha256": "c" * 64,
                    },
                },
            )
            release_sha = tmp / "artifact.zip.sha256"
            release_sha.write_text(f"{artifact_sha}  artifact.zip\n")
            candidate = self.write_json(
                tmp,
                "candidate-market.json",
                {
                    "market_id": "condition-1",
                    "side": "BUY",
                    "order_type": "GTC",
                    "post_only": True,
                    "active": True,
                    "accepting_orders": True,
                    "closed": False,
                    "archived": False,
                    "target_size": "5",
                    "limit_price": "0.02",
                    "estimated_order_notional_usd": "0.1",
                    "book_snapshot_timestamp": captured_at,
                    "exchange_rule_snapshot": {
                        "captured_at": captured_at,
                        "expires_at": expires_at,
                    },
                },
            )
            runtime_truth = self.write_json(
                tmp,
                "runtime-truth.json",
                {
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
                },
            )
            profiles = tmp / ".env.profiles"
            profiles.write_text(
                "\n".join(
                    [
                        "# Profile-scoped account id for acct_b.",
                        "PMX_PROFILE_ACCT_B_ACCOUNT_ID=acct-canary",
                        "# Local non-secret profile reference for acct_b.",
                        "PMX_PROFILE_ACCT_B_PROFILE_REF=local-profile://acct_b",
                        "# Profile-scoped L1 private key for acct_b.",
                        "PMX_PROFILE_ACCT_B_POLYMARKET_PRIVATE_KEY=0xabc123",
                        "# Profile-scoped L2 API key for acct_b.",
                        "PMX_PROFILE_ACCT_B_POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                        "# Profile-scoped L2 API secret for acct_b.",
                        "PMX_PROFILE_ACCT_B_POLY_API_SECRET=api-secret",
                        "# Profile-scoped L2 API passphrase for acct_b.",
                        "PMX_PROFILE_ACCT_B_POLY_API_PASSPHRASE=api-pass",
                        "# Profile-scoped CLOB funder for acct_b when using deposit-wallet auth.",
                        "PMX_PROFILE_ACCT_B_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                        "# Profile-scoped signature type for acct_b.",
                        "PMX_PROFILE_ACCT_B_CLOB_SIGNATURE_TYPE=POLY_1271",
                        "",
                    ]
                )
            )
            runtime_env = tmp / ".env.runtime"
            approval_request = tmp / "operator-approval-request.json"
            dual_control_template = tmp / "dual-control-review.template.json"
            review_packet_dir = tmp / "review-packet"

            result = self.module.prepare_review_bundle(
                profile="acct_b",
                source_env_file=profiles,
                runtime_env_output=runtime_env,
                approval_request_output=approval_request,
                dual_control_template_output=dual_control_template,
                review_packet_output_dir=review_packet_dir,
                candidate_market_file=candidate,
                runtime_truth_file=runtime_truth,
                release_zip=release_zip,
                root_ci_run_id="1",
                hermes_ci_run_id="2",
                execution_engine_ci_run_id="3",
                credentialed_sdk_run_id="local",
                operator_identity_ref="operator://primary",
                approval_ticket_ref="ticket://approval",
                max_order_notional_usd="0.20",
                max_daily_notional_usd="0.20",
                valid_for_minutes=15,
            )

            self.assertEqual(result["profile"], "acct_b")
            self.assertTrue(runtime_env.exists())
            self.assertFalse(runtime_env.with_name(".env.runtime.secrets").exists())
            self.assertTrue(approval_request.exists())
            self.assertTrue(dual_control_template.exists())
            self.assertTrue((review_packet_dir / "packet.json").exists())
            approval_doc = json.loads(approval_request.read_text())
            packet = json.loads((review_packet_dir / "packet.json").read_text())
            self.assertEqual(approval_doc["account_id"], "acct-canary")
            self.assertEqual(approval_doc["active_profile_ref"], "local-profile://acct_b")
            self.assertEqual(
                approval_doc["runtime_gate_evidence_refs"]["kill_switch_open"],
                "pg://runtime/kill-switch",
            )
            self.assertEqual(packet["active_profile_ref"], "local-profile://acct_b")
            self.assertEqual(packet["status"], "dual_control_review_packet_not_authorization")


if __name__ == "__main__":
    unittest.main()
