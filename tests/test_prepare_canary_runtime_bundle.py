import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PK = "POLYMARKET" + "_PRIVATE_KEY"
API_SECRET = "POLY" + "_API_SECRET"
API_PASS = "POLY" + "_API_PASSPHRASE"
PROFILE_PREFIX = "PMX_PROFILE_ACCT_B_"


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_canary_runtime_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_runtime_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrepareCanaryRuntimeBundleTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def test_bundle_script_activates_profile_and_builds_approval_request(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            release_zip = tmp / "artifact.zip"
            release_zip.write_bytes(b"artifact")
            approval_module = self.module.load_module(
                ROOT / "scripts" / "prepare_operator_approval_request.py",
                "prepare_operator_approval_request",
            )
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
            candidate = self.write_json(
                tmp,
                "candidate-market.json",
                {
                    "market_id": "condition-1",
                    "token_id": "123",
                    "human_review_ref": "ticket://candidate-review",
                    "side": "BUY",
                    "order_type": "GTC",
                    "post_only": True,
                    "active": True,
                    "accepting_orders": True,
                    "closed": False,
                    "archived": False,
                    "best_ask": "0.03",
                    "limit_price": "0.02",
                    "ask_size": "20",
                    "target_size": "5",
                    "min_order_size": "5",
                    "estimated_order_notional_usd": "0.1",
                    "exchange_rule_snapshot": {
                        "schema_version": 1,
                        "venue": "polymarket_clob",
                        "order_mode": "post_only_limit",
                        "order_type": "GTC",
                        "side": "BUY",
                        "target_size_semantics": "outcome_shares",
                        "min_share_size": "5",
                        "min_tick_size": "0.01",
                        "source": "public_clob_book_plus_reviewed_remote_rule",
                        "captured_at": "2026-05-23T00:00:00+00:00",
                        "expires_at": "2099-01-01T00:00:00Z",
                        "evidence_ref": "ticket://reviewed-rule",
                    },
                },
            )
            runtime_truth = self.write_json(
                tmp,
                "runtime-truth.json",
                {
                    "artifact_sha256": artifact_sha,
                    "workspace_manifest_sha256": "b" * 64,
                    "archived_manifest_sha256": "c" * 64,
                    "preflight_report": {
                        "posted": False,
                        "remote_side_effects": False,
                        "status": "preflight_ready",
                    },
                    "dependencies": [
                        {"name": name, "status": "durable_runtime_truth", "evidence_ref": f"pg://{name}"}
                        for name in [
                            "kill_switch",
                            "live_submit_gate",
                            "idempotency_lease",
                            "order_cancel_reconciliation",
                            "no_geoblock",
                            "market_live",
                            "account_allowlist",
                            "balance_allowance",
                            "reconcile_worker_healthy",
                            "cancel_only_fallback",
                        ]
                    ],
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
                        "PMX_PROFILE_ACCT_B_PROFILE_REF=local-profile://acct-b",
                        "# Profile-scoped L1 private key for acct_b.",
                        f"{PROFILE_PREFIX}{PK}=0xabc123",
                        "# Profile-scoped L2 API key for acct_b.",
                        "PMX_PROFILE_ACCT_B_POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                        "# Profile-scoped L2 API secret for acct_b.",
                        f"{PROFILE_PREFIX}{API_SECRET}=api-secret",
                        "# Profile-scoped L2 API passphrase for acct_b.",
                        f"{PROFILE_PREFIX}{API_PASS}=api-pass",
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
            result = self.module.prepare_bundle(
                profile="acct_b",
                source_env_file=profiles,
                runtime_env_output=runtime_env,
                approval_request_output=approval_request,
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
            request = json.loads(approval_request.read_text())

            self.assertEqual(request["account_id"], "acct-canary")
            self.assertEqual(request["active_profile_ref"], "local-profile://acct-b")
            self.assertEqual(result["profile"], "acct_b")
            self.assertIn(f"{PK}=0xabc123", runtime_env.read_text())


if __name__ == "__main__":
    unittest.main()
