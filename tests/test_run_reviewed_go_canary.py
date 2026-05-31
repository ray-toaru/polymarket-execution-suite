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
            self.assertEqual(plan["active_profile_ref"], "local-profile://acct_b")
            self.assertIn("--preflight-only", plan["command"])
            self.assertIn(str(package / "approval.json"), plan["command"])
            self.assertIn(str(package / "runtime-truth.json"), plan["command"])
            self.assertIn("PMX_ALLOW_LIVE_SUBMIT", plan["required_gate_env_vars"])
            self.assertFalse(plan["includes_live_config_overrides"])
            self.assertNotIn("--allow-live-submit-config", plan["command"])

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

    def test_build_invocation_armed_defaults_report_and_marker_in_package(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            plan = self.module.build_invocation(
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

            self.assertEqual(plan["mode"], "armed")
            self.assertIn("--armed", plan["command"])
            self.assertIn("--report-file", plan["command"])
            self.assertIn("--approval-consumed-marker", plan["command"])
            self.assertTrue(plan["report_file"].endswith("post-canary-report.json"))
            self.assertIn(str(package), plan["approval_consumed_marker"])
            self.assertTrue(plan["requires_explicit_live_config_overrides"])
            self.assertNotIn("--allow-live-submit-config", plan["command"])

    def test_build_invocation_armed_requires_explicit_live_overrides_to_include_flags(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            plan = self.module.build_invocation(
                package_dir=package,
                env_file=env_file,
                mode="armed",
                daily_used_notional_usd="0",
                idempotency_key=None,
                execution_id=None,
                plan_hash=None,
                report_file=None,
                approval_consumed_marker=None,
                include_live_config_overrides=True,
            )

            self.assertFalse(plan["requires_explicit_live_config_overrides"])
            self.assertTrue(plan["includes_live_config_overrides"])
            self.assertIn("--allow-live-submit-config", plan["command"])
            self.assertIn("--allow-real-funds-canary-config", plan["command"])

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

    def test_main_run_fails_closed_when_gate_env_vars_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            original = dict(os.environ)
            try:
                for key in self.module.REQUIRED_GATE_ENV_VARS:
                    os.environ.pop(key, None)
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
                with self.assertRaisesRegex(SystemExit, "missing required gate env vars"):
                    self.module.main()
            finally:
                self.module.parse_args = original_parse_args
                os.environ.clear()
                os.environ.update(original)

    def test_main_run_rejects_armed_without_explicit_live_override_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            package, env_file = self.package_fixture(tmp)
            original = dict(os.environ)
            try:
                for key in self.module.REQUIRED_GATE_ENV_VARS:
                    os.environ[key] = "1"
                original_parse_args = self.module.parse_args
                self.module.parse_args = lambda: self.module.argparse.Namespace(
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
                    run=True,
                )
                with self.assertRaisesRegex(
                    SystemExit,
                    "requires --include-live-config-overrides before execution",
                ):
                    self.module.main()
            finally:
                self.module.parse_args = original_parse_args
                os.environ.clear()
                os.environ.update(original)


if __name__ == "__main__":
    unittest.main()
