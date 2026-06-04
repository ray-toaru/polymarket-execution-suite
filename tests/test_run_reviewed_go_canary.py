import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_reviewed_go_canary.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_reviewed_go_canary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunReviewedGoCanaryTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def write_json(self, directory: Path, name: str, data: dict) -> Path:
        path = directory / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def package_fixture(self, directory: Path) -> tuple[Path, Path]:
        package = directory / "reviewed-go"
        package.mkdir()
        env_file = directory / ".env.runtime"
        env_file.write_text(
            "\n".join(
                [
                    "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                    "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                    "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                    "POLYMARKET_PRIVATE_KEY=0xabc123",
                    "POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                    "POLY_API_SECRET=api-secret",
                    "POLY_API_PASSPHRASE=api-pass",
                    "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                    "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                    "",
                ]
            )
        )
        self.write_json(
            package,
            "release-decision.json",
            {
                "decision_id": "decision-1",
                "decision": "go",
                "status": "reviewed_go",
                "scope": "REAL_FUNDS_CANARY",
                "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
                "live_submit_authorized": True,
                "live_cancel_authorized": True,
                "real_funds_canary_authorized": True,
                "remote_side_effects_authorized": True,
                "production_deployment_authorized": False,
                "single_attempt": True,
                "max_order_count": 1,
                "post_cancel_required": True,
                "readback_closeout_required": True,
            },
        )
        self.write_json(
            package,
            "approval.json",
            {
                "approval_id": "approval-request-1",
                "approval_hash": "d" * 64,
                "account_id": "acct-canary",
                "condition_id": "condition-1",
                "scope": "REAL_FUNDS_CANARY",
                "expires_at": "2099-01-01T00:00:00Z",
                "artifact_sha256": "a" * 64,
                "evidence_manifest_sha256": "c" * 64,
                "workspace_manifest_sha256": "b" * 64,
                "archived_manifest_sha256": "c" * 64,
                "market_candidate_sha256": "e" * 64,
                "max_order_notional_usd": "0.2",
                "max_daily_notional_usd": "0.2",
                "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
                "operator_identity_ref": "operator://primary",
                "operator_identity_sha256": "31407192d4cb1a4a59550966b008ad672f660e0621b7e1c656ac10ee71e30a2f",
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
            },
        )
        self.write_json(
            package,
            "candidate-market.json",
            {
                "market_id": "condition-1",
                "token_id": "123",
                "outcome": "Yes",
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
                "estimated_order_notional_usd": "0.1",
                "spread_bps": 100,
                "min_order_size": "5",
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
                    "expires_at": "2099-01-01T00:00:00+00:00",
                    "evidence_ref": "ticket://reviewed-rule",
                },
                "liquidity_score": 100,
                "book_snapshot_timestamp": "2026-05-23T00:00:00+00:00",
                "human_review_ref": "ticket://candidate-review",
            },
        )
        self.write_json(
            package,
            "runtime-truth.json",
            {
                "schema_version": 1,
                "status": "reviewed_runtime_truth_candidate",
                "source_release": "v0.28.0",
                "scope": "REAL_FUNDS_CANARY",
                "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
                "account_id": "acct-canary",
                "condition_id": "condition-1",
                "artifact_sha256": "a" * 64,
                "workspace_manifest_sha256": "b" * 64,
                "archived_manifest_sha256": "c" * 64,
                "dependencies": [
                    {"name": name, "status": "durable_runtime_truth", "evidence_ref": f"pg://{name}"}
                    for name in [
                        "kill_switch",
                        "live_submit_gate",
                        "idempotency_lease",
                        "order_cancel_reconciliation",
                    ]
                ],
                "preflight_report": {
                    "status": "preflight_ready",
                    "runtime_truth_source": "postgres",
                    "posted": False,
                    "remote_side_effects": False,
                    "raw_signed_order_exposed": False,
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
                "references_only_no_secret_values": True,
                "live_submit_allowed": False,
                "live_cancel_allowed": False,
                "real_funds_canary_authorized": False,
                "remote_side_effects": False,
                "production_ready_claimed": False,
            },
        )
        return package, env_file

    def test_build_invocation_preflight_uses_package_files(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            plan = self.module.build_invocation(
                package_dir=package,
                env_file=env_file,
                mode="preflight",
                daily_used_notional_usd="0",
                idempotency_key=None,
                execution_id=None,
                plan_hash=None,
                report_file=None,
                approval_consumed_marker=None,
                include_live_config_overrides=False,
            )

            self.assertEqual(plan["mode"], "preflight")
            self.assertEqual(plan["account_id"], "acct-canary")
            self.assertEqual(plan["condition_id"], "condition-1")
            self.assertEqual(plan["active_profile_ref"], "local-profile://acct_b")
            self.assertEqual(len(plan["invocation_hash"]), 64)
            self.assertTrue(plan["runtime_gate_snapshot"]["kill_switch_open"])
            self.assertEqual(
                plan["runtime_gate_evidence_refs"]["kill_switch_open"],
                "pg://runtime/kill-switch",
            )
            self.assertIn("pmx-real-funds-canary-preflight", plan["command"])
            self.assertIn(f"canary-{plan['invocation_hash']}-preflight", plan["command"])
            self.assertIn(f"exec-{plan['invocation_hash']}", plan["command"])
            self.assertIn(str(package / "approval.json"), plan["command"])
            self.assertIn(str(package / "runtime-truth.json"), plan["command"])
            self.assertEqual(plan["required_gate_env_vars"], [])
            self.assertEqual(plan["missing_gate_env_vars"], [])
            self.assertFalse(plan["includes_live_config_overrides"])
            self.assertNotIn("--allow-live-submit-config", plan["command"])

    def test_build_invocation_accepts_explicit_secrets_env_file(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            secrets_env_file = tmp / ".env.runtime.secrets"
            env_file.write_text(
                "\n".join(
                    [
                        "PMX_ACTIVE_ACCOUNT_PROFILE=acct_b",
                        "PMX_ACTIVE_ACCOUNT_ID=acct-canary",
                        "PMX_ACTIVE_PROFILE_REF=local-profile://acct_b",
                        "",
                    ]
                )
            )
            secrets_env_file.write_text(
                "\n".join(
                    [
                        "POLYMARKET_PRIVATE_KEY=0xabc123",
                        "POLY_API_KEY=123e4567-e89b-12d3-a456-426614174000",
                        "POLY_API_SECRET=api-secret",
                        "POLY_API_PASSPHRASE=api-pass",
                        "PMX_CLOB_SIGNATURE_TYPE=POLY_1271",
                        "PMX_CLOB_FUNDER=0x00000000000000000000000000000000000000b0",
                        "",
                    ]
                )
            )
            plan = self.module.build_invocation(
                package_dir=package,
                env_file=env_file,
                secrets_env_file=secrets_env_file,
                mode="preflight",
                daily_used_notional_usd="0",
                idempotency_key=None,
                execution_id=None,
                plan_hash=None,
                report_file=None,
                approval_consumed_marker=None,
                include_live_config_overrides=False,
            )
        self.assertEqual(plan["active_profile_ref"], "local-profile://acct_b")

    def test_build_invocation_rejects_live_overrides_for_preflight(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            with self.assertRaises(SystemExit) as ctx:
                self.module.build_invocation(
                    package_dir=package,
                    env_file=env_file,
                    mode="preflight",
                    daily_used_notional_usd="0",
                    idempotency_key=None,
                    execution_id=None,
                    plan_hash=None,
                    report_file=None,
                    approval_consumed_marker=None,
                    include_live_config_overrides=True,
                )
        self.assertIn("only valid for armed", str(ctx.exception))

    def test_build_invocation_rejects_armed_mode(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            with self.assertRaisesRegex(
                SystemExit,
                "only supports preflight; use run_reviewed_go_canary_armed.py",
            ):
                self.module.build_invocation(
                    package_dir=package,
                    env_file=env_file,
                    mode="armed",
                    daily_used_notional_usd="0",
                    idempotency_key=None,
                    execution_id=None,
                    plan_hash=None,
                    report_file=None,
                    approval_consumed_marker=None,
                    include_live_config_overrides=False,
                )

    def test_build_invocation_rejects_consumed_package(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            (package / "approval-consumed-20260526T000000Z.json").write_text("{}\n")

            with self.assertRaisesRegex(SystemExit, "already consumed"):
                self.module.build_invocation(
                    package_dir=package,
                    env_file=env_file,
                    mode="preflight",
                    daily_used_notional_usd="0",
                    idempotency_key=None,
                    execution_id=None,
                    plan_hash=None,
                    report_file=None,
                    approval_consumed_marker=None,
                    include_live_config_overrides=False,
                )

    def test_main_run_does_not_require_gate_env_vars(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            completed = self.module.subprocess.CompletedProcess(args=["cargo"], returncode=0)
            try:
                argv = [
                    "--package-dir",
                    str(package),
                    "--env-file",
                    str(env_file),
                    "--mode",
                    "preflight",
                    "--run",
                ]
                original_parse_args = self.module.parse_args
                self.module.parse_args = lambda: self.module.argparse.Namespace(
                    package_dir=Path(argv[1]),
                    env_file=Path(argv[3]),
                    secrets_env_file=None,
                    mode="preflight",
                    daily_used_notional_usd="0",
                    idempotency_key=None,
                    execution_id=None,
                    plan_hash=None,
                    report_file=None,
                    approval_consumed_marker=None,
                    include_live_config_overrides=False,
                    run=True,
                )
                original_run = self.module.subprocess.run
                self.module.subprocess.run = lambda *args, **kwargs: completed
                self.assertEqual(self.module.main(), 0)
            finally:
                self.module.subprocess.run = original_run
                self.module.parse_args = original_parse_args

    def test_main_run_rejects_live_override_opt_in_on_preflight_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            try:
                original_parse_args = self.module.parse_args
                self.module.parse_args = lambda: self.module.argparse.Namespace(
                    package_dir=package,
                    env_file=env_file,
                    secrets_env_file=None,
                    mode="preflight",
                    daily_used_notional_usd="0",
                    idempotency_key=None,
                    execution_id=None,
                    plan_hash=None,
                    report_file=None,
                    approval_consumed_marker=None,
                    include_live_config_overrides=True,
                    run=True,
                )
                with self.assertRaisesRegex(
                    SystemExit,
                    "live config overrides are only valid for armed reviewed-go canary invocations",
                ):
                    self.module.main()
            finally:
                self.module.parse_args = original_parse_args


if __name__ == "__main__":
    unittest.main()
