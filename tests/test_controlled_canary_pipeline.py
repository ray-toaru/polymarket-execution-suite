import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_controlled_canary_pipeline.py"
CLOSEOUT_SCRIPT = ROOT / "scripts" / "prepare_canary_closeout.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("run_controlled_canary_pipeline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_closeout_module():
    spec = importlib.util.spec_from_file_location("prepare_canary_closeout", CLOSEOUT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ControlledCanaryPipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.closeout = load_closeout_module()

    def candidate(self, **overrides):
        data = {
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
        }
        data.update(overrides)
        return data

    def write_candidate(self, data):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "candidate-market.json"
        path.write_text(json.dumps(data))
        self.addCleanup(tmp.cleanup)
        return path

    def runtime_truth(self, **overrides):
        data = {
            "schema_version": 1,
            "status": "reviewed_runtime_truth_candidate",
            "source_release": f"v{(ROOT / 'polymarket-execution-engine' / 'Cargo.toml').read_text().split('version = \"')[1].split('\"')[0]}",
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
        }
        data.update(overrides)
        return data

    def test_supplied_candidate_requires_dynamic_exchange_rule_snapshot(self):
        candidate = self.candidate()
        candidate.pop("exchange_rule_snapshot")
        with self.assertRaisesRegex(SystemExit, "exchange_rule_snapshot"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_rejects_release_invariant_size_without_rule_support(self):
        candidate = self.candidate(target_size="5")
        candidate["exchange_rule_snapshot"]["min_share_size"] = "6"
        with self.assertRaisesRegex(SystemExit, "min_share_size"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_requires_bound_notional(self):
        candidate = self.candidate(estimated_order_notional_usd="0.2")
        with self.assertRaisesRegex(SystemExit, "estimated_order_notional_usd"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_rejects_notional_above_cap(self):
        candidate = self.candidate(limit_price="0.50", best_ask="0.60", estimated_order_notional_usd="2.5")
        with self.assertRaisesRegex(SystemExit, "exceeds max_order_notional_usd"):
            self.pipeline.validate_candidate_file(
                self.write_candidate(candidate),
                max_order_notional_usd=self.pipeline.Decimal("1.00"),
            )

    def test_supplied_candidate_requires_outcome(self):
        candidate = self.candidate()
        candidate.pop("outcome")
        with self.assertRaisesRegex(SystemExit, "candidate outcome is required"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_rejects_price_out_of_bounds(self):
        candidate = self.candidate(best_ask="1.20", limit_price="1.10", estimated_order_notional_usd="5.5")
        with self.assertRaisesRegex(SystemExit, "price bounds"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_rejects_spread_over_cap(self):
        candidate = self.candidate(spread_bps=101)
        with self.assertRaisesRegex(SystemExit, "spread_bps exceeds max_spread_bps"):
            self.pipeline.validate_candidate_file(
                self.write_candidate(candidate),
                max_spread_bps=100,
            )

    def test_supplied_candidate_rejects_future_captured_at(self):
        candidate = self.candidate()
        candidate["exchange_rule_snapshot"]["captured_at"] = "2099-01-01T00:00:00+00:00"
        candidate["exchange_rule_snapshot"]["expires_at"] = "2099-01-02T00:00:00+00:00"
        with self.assertRaisesRegex(SystemExit, "captured_at must not be in the future"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_supplied_candidate_rejects_expires_at_before_captured_at(self):
        candidate = self.candidate()
        candidate["exchange_rule_snapshot"]["captured_at"] = "2026-05-23T01:00:00+00:00"
        candidate["exchange_rule_snapshot"]["expires_at"] = "2026-05-23T00:00:00+00:00"
        with self.assertRaisesRegex(SystemExit, "expires_at must be after captured_at"):
            self.pipeline.validate_candidate_file(self.write_candidate(candidate))

    def test_stage_plan_is_no_go_by_default_and_blocks_live_phases(self):
        plan = self.pipeline.build_stage_plan(
            reviewed_go=False,
            closeout_package_dir=None,
            runtime_truth_ready=False,
        )
        names = [stage["stage"] for stage in plan]
        self.assertEqual(
            names,
            [
                "candidate",
                "no_go_review",
                "blocked_rehearsal",
                "reviewed_go_decision",
                "armed_post_cancel",
                "readback",
                "closeout",
            ],
        )
        blocked = {stage["stage"]: stage["status"] for stage in plan}
        self.assertEqual(blocked["reviewed_go_decision"], "blocked")
        self.assertEqual(blocked["armed_post_cancel"], "blocked")
        self.assertEqual(blocked["readback"], "blocked")
        self.assertEqual(blocked["closeout"], "blocked")

    def test_reviewed_go_without_runtime_truth_still_blocks_armed_phase(self):
        plan = self.pipeline.build_stage_plan(
            reviewed_go=True,
            closeout_package_dir=None,
            runtime_truth_ready=False,
        )
        by_stage = {stage["stage"]: stage for stage in plan}
        self.assertEqual(by_stage["reviewed_go_decision"]["status"], "provided")
        self.assertEqual(by_stage["armed_post_cancel"]["status"], "blocked_runtime_truth_missing")
        self.assertFalse(by_stage["armed_post_cancel"]["remote_side_effects"])
        self.assertEqual(by_stage["readback"]["status"], "blocked")

    def test_reviewed_go_with_runtime_truth_emits_operator_runbook_without_auto_side_effects(self):
        runbook = self.pipeline.build_operator_runbook(
            reviewed_go=True,
            runtime_truth_ready=True,
            reviewed_go_decision={"path": "dist/fresh/release-decision.json", "sha256": "a" * 64},
        )
        self.assertEqual(runbook["status"], "operator_runnable_not_auto_executed")
        self.assertFalse(runbook["auto_execute"])
        self.assertTrue(runbook["requires_fresh_reviewed_go"])
        self.assertTrue(runbook["requires_runtime_truth"])
        self.assertTrue(runbook["requires_closeout"])
        self.assertEqual(
            [step["stage"] for step in runbook["steps"]],
            [
                "preflight",
                "armed_post_cancel",
                "readback_order",
                "readback_trades",
                "readback_account_activity",
                "closeout",
                "mark_consumed",
            ],
        )
        self.assertTrue(all(step["remote_side_effects"] is False for step in runbook["steps"] if step["stage"] != "armed_post_cancel"))

    def test_report_exposes_runtime_truth_dependencies(self):
        dependencies = self.pipeline.runtime_truth_dependencies()
        names = {item["name"] for item in dependencies}
        self.assertTrue(
            {
                "kill_switch",
                "live_submit_gate",
                "idempotency_lease",
                "order_cancel_reconciliation",
            }.issubset(names)
        )
        self.assertTrue(all(item["required_before_live"] for item in dependencies))

    def test_runtime_truth_file_must_cover_all_required_dependencies(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "runtime-truth.json"
        path.write_text(json.dumps({"schema_version": 1, "dependencies": []}))
        with self.assertRaisesRegex(SystemExit, "runtime truth missing"):
            self.pipeline.validate_runtime_truth_file(path)

    def test_runtime_truth_file_accepts_durable_ready_dependencies(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "runtime-truth.json"
        path.write_text(json.dumps(self.runtime_truth()))
        report = self.pipeline.validate_runtime_truth_file(path)
        self.assertTrue(report["ready_for_armed_stage"])
        self.assertEqual(report["artifact_sha256"], "a" * 64)

    def test_runtime_truth_file_must_bind_current_release_hashes(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "runtime-truth.json"
        path.write_text(json.dumps(self.runtime_truth()))
        with self.assertRaisesRegex(SystemExit, "artifact binding mismatch"):
            self.pipeline.validate_runtime_truth_file(
                path,
                expected_artifact_sha256="0" * 64,
                expected_workspace_manifest_sha256="b" * 64,
                expected_archived_manifest_sha256="c" * 64,
            )

    def test_runtime_truth_file_uses_engine_validator(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "runtime-truth.json"
        doc = self.runtime_truth(live_submit_allowed=True)
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(SystemExit, "runtime truth validator failed"):
            self.pipeline.validate_runtime_truth_file(path)

    def test_reviewed_go_decision_requires_single_attempt_scope(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "release-decision.json"
        path.write_text(json.dumps({"decision": "go", "status": "reviewed_go"}))
        with self.assertRaisesRegex(SystemExit, "single_attempt"):
            self.pipeline.validate_reviewed_go_decision_file(path)

    def test_reviewed_go_decision_rejects_consumed_package_directory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        package = Path(tmp.name)
        path = package / "release-decision.json"
        path.write_text(
            json.dumps(
                {
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
                }
            )
        )
        (package / "approval-consumed-20260523T000000Z.json").write_text("{}")
        with self.assertRaisesRegex(SystemExit, "already consumed"):
            self.pipeline.validate_reviewed_go_decision_file(path)

    def test_reviewed_go_decision_rejects_closed_package_directory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        package = Path(tmp.name)
        path = package / "release-decision.json"
        path.write_text(
            json.dumps(
                {
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
                }
            )
        )
        (package / "closeout.json").write_text("{}")
        with self.assertRaisesRegex(SystemExit, "already closed"):
            self.pipeline.validate_reviewed_go_decision_file(path)

    def test_closeout_package_stage_runs_read_only_closeout(self):
        package = ROOT / "dist" / "unit-closeout-fixture"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        (package / "post-canary-report.json.stages.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "status": "post_accepted",
                            "stage": "post_accepted",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": False,
                            "remote_side_effects": True,
                            "operator_required": False,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                    json.dumps(
                        {
                            "status": "cancel_confirmed",
                            "stage": "cancel_confirmed",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": True,
                            "remote_side_effects": True,
                            "operator_required": False,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                ]
            )
            + "\n"
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        stage = self.pipeline.run_closeout_stage(
            package,
            ROOT / "dist" / "polymarket-execution-suite-v0.28.0.zip",
        )
        self.assertEqual(stage["status"], "pass")
        self.assertFalse(stage["remote_side_effects"])
        self.assertTrue((package / "closeout.json").exists())
        closeout = json.loads((package / "closeout.json").read_text())
        self.assertEqual(stage["stage_history_sha256"], closeout["stage_history_summary"]["sha256"])
        self.assertEqual(stage["stage_history_stage_count"], 2)
        self.assertEqual(closeout["stage_history_summary"]["stage_count"], 2)
        self.assertEqual(closeout["stage_history_summary"]["remote_order_ids"], ["order-1"])

    def test_closeout_package_stage_requires_stage_history(self):
        package = ROOT / "dist" / "unit-closeout-no-stage-history"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        with self.assertRaisesRegex(SystemExit, "stage history"):
            self.pipeline.run_closeout_stage(
                package,
                ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
            )

    def test_closeout_default_release_zip_follows_workspace_version(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(
            self.closeout.DEFAULT_RELEASE_ZIP.name,
            f"polymarket-execution-suite-v{version}.zip",
        )

    def test_closeout_requires_cancel_confirmed_stage_for_successful_order_closeout(self):
        package = ROOT / "dist" / "unit-closeout-missing-cancel-confirmed"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        (package / "post-canary-report.json.stages.jsonl").write_text(
            json.dumps(
                {
                    "status": "post_accepted",
                    "stage": "post_accepted",
                    "remote_order_id": "order-1",
                    "posted": True,
                    "cancelled": False,
                    "remote_side_effects": True,
                    "operator_required": False,
                    "raw_signed_order_exposed": False,
                }
            )
            + "\n"
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        with self.assertRaisesRegex(SystemExit, "stage_history_has_cancel_confirmed"):
            self.closeout.build_closeout(
                package,
                ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
            )

    def test_closeout_package_stage_rejects_operator_required_history(self):
        package = ROOT / "dist" / "unit-closeout-operator-required-history"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        (package / "post-canary-report.json.stages.jsonl").write_text(
            json.dumps(
                {
                    "status": "operator_required",
                    "stage": "cancel_unknown",
                    "remote_order_id": "order-1",
                    "posted": True,
                    "cancelled": False,
                    "remote_side_effects": True,
                    "operator_required": True,
                    "raw_signed_order_exposed": False,
                }
            )
            + "\n"
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        with self.assertRaisesRegex(SystemExit, "operator_required"):
            self.pipeline.run_closeout_stage(
                package,
                ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
            )

    def test_closeout_package_stage_accepts_bound_operator_recovery_evidence(self):
        package = ROOT / "dist" / "unit-closeout-operator-recovered-history"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage_history = package / "post-canary-report.json.stages.jsonl"
        stage_history.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "status": "post_accepted",
                            "stage": "post_accepted",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": False,
                            "remote_side_effects": True,
                            "operator_required": False,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                    json.dumps(
                        {
                            "status": "operator_required",
                            "stage": "cancel_unknown",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": False,
                            "remote_side_effects": True,
                            "operator_required": True,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                ]
            )
            + "\n"
        )
        stage_history_sha = self.pipeline.sha256(stage_history)
        (package / "operator-recovery.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recovery_decision": "operator_reviewed_closed_no_retry",
                    "operator_review_ref": "ticket://recovery-review",
                    "stage_history_sha256": stage_history_sha,
                    "remote_order_id": "order-1",
                    "unresolved_operator_required": False,
                    "no_retry_authorized": True,
                    "no_second_order_placed": True,
                    "raw_signed_order_exposed": False,
                    "readback_evidence": [
                        "order-status-query.json",
                        "trade-fill-query.json",
                        "account-activity-readback.json",
                    ],
                }
            )
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        stage = self.pipeline.run_closeout_stage(
            package,
            ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
        )
        self.assertEqual(stage["status"], "pass")
        closeout = json.loads((package / "closeout.json").read_text())
        self.assertEqual(closeout["operator_recovery_summary"]["status"], "recovered")
        self.assertEqual(closeout["operator_recovery_summary"]["stage_history_sha256"], stage_history_sha)
        self.assertTrue(closeout["evidence_checks"]["stage_history_operator_required_recovered"])

    def test_closeout_package_stage_rejects_recovery_with_wrong_stage_history_hash(self):
        package = ROOT / "dist" / "unit-closeout-bad-recovery-hash"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "remote_order_readback": {"order_id": "order-1"},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        (package / "post-canary-report.json.stages.jsonl").write_text(
            json.dumps(
                {
                    "status": "operator_required",
                    "stage": "cancel_unknown",
                    "remote_order_id": "order-1",
                    "posted": True,
                    "cancelled": False,
                    "remote_side_effects": True,
                    "operator_required": True,
                    "raw_signed_order_exposed": False,
                }
            )
            + "\n"
        )
        (package / "operator-recovery.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recovery_decision": "operator_reviewed_closed_no_retry",
                    "operator_review_ref": "ticket://recovery-review",
                    "stage_history_sha256": "0" * 64,
                    "remote_order_id": "order-1",
                    "unresolved_operator_required": False,
                    "no_retry_authorized": True,
                    "no_second_order_placed": True,
                    "raw_signed_order_exposed": False,
                    "readback_evidence": [
                        "order-status-query.json",
                        "trade-fill-query.json",
                        "account-activity-readback.json",
                    ],
                }
            )
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                }
            )
        )
        with self.assertRaisesRegex(SystemExit, "operator recovery"):
            self.pipeline.run_closeout_stage(
                package,
                ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
            )

    def test_closeout_package_stage_accepts_post_unknown_incident_recovery(self):
        package = ROOT / "dist" / "unit-closeout-post-unknown-incident"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "market_candidate_sha256": self.pipeline.sha256(package / "candidate-market.json"),
                    "remote_order_readback": {"order_id": None},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage_history = package / "post-canary-report.json.stages.jsonl"
        stage_history.write_text(
            json.dumps(
                {
                    "status": "operator_required",
                    "stage": "post_unknown",
                    "remote_order_id": None,
                    "posted": False,
                    "cancelled": False,
                    "remote_side_effects": True,
                    "operator_required": True,
                    "raw_signed_order_exposed": False,
                    "error_summary": "post_order timed out",
                }
            )
            + "\n"
        )
        stage_history_sha = self.pipeline.sha256(stage_history)
        (package / "operator-incident-recovery.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recovery_decision": "operator_reviewed_no_remote_order_found_no_retry",
                    "operator_review_ref": "ticket://post-unknown-incident",
                    "stage_history_sha256": stage_history_sha,
                    "candidate_market_sha256": self.pipeline.sha256(package / "candidate-market.json"),
                    "remote_order_id": None,
                    "investigation_window": {
                        "started_at": "2026-05-23T00:00:00+00:00",
                        "ended_at": "2026-05-23T00:15:00+00:00",
                    },
                    "unresolved_operator_required": False,
                    "no_retry_authorized": True,
                    "no_second_order_placed": True,
                    "raw_signed_order_exposed": False,
                    "account_level_evidence": [
                        "account-open-orders-readback.json",
                        "account-trade-history-readback.json",
                        "account-activity-readback.json",
                    ],
                }
            )
        )
        (package / "account-open-orders-readback.json").write_text(
            json.dumps({"matching_open_orders_count": 0, "raw_signed_order_exposed": False})
        )
        (package / "account-trade-history-readback.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0", "raw_signed_order_exposed": False})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage = self.pipeline.run_closeout_stage(
            package,
            ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
        )
        self.assertEqual(stage["status"], "pass")
        closeout = json.loads((package / "closeout.json").read_text())
        self.assertEqual(closeout["decision"], "controlled_real_funds_canary_incident_closed_no_remote_order_found")
        self.assertEqual(closeout["operator_recovery_summary"]["status"], "incident_recovered_no_remote_order_found")
        self.assertTrue(closeout["evidence_checks"]["incident_recovery_no_matching_open_orders"])

    def test_closeout_package_stage_accepts_real_receipt_shape_without_synthetic_market_candidate_block(self):
        package = ROOT / "dist" / "unit-closeout-real-receipt-shape"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "remote_order_id": "order-1",
                    "posted": True,
                    "cancelled": True,
                    "remote_side_effects": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage_history = package / "post-canary-report.json.stages.jsonl"
        stage_history.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "status": "post_accepted",
                            "stage": "post_accepted",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": False,
                            "remote_side_effects": True,
                            "operator_required": False,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                    json.dumps(
                        {
                            "status": "cancel_confirmed",
                            "stage": "cancel_confirmed",
                            "remote_order_id": "order-1",
                            "posted": True,
                            "cancelled": True,
                            "remote_side_effects": True,
                            "operator_required": False,
                            "raw_signed_order_exposed": False,
                        }
                    ),
                ]
            )
            + "\n"
        )
        (package / "order-status-query.json").write_text(
            json.dumps({"remote_status": "CANCELED", "size_matched": "0"})
        )
        (package / "trade-fill-query.json").write_text(
            json.dumps({"matching_trades_count": 0, "matching_size_total": "0"})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 1,
                    "values": [{"value": "0"}],
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage = self.pipeline.run_closeout_stage(
            package,
            ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
        )
        self.assertEqual(stage["status"], "pass")
        closeout = json.loads((package / "closeout.json").read_text())
        self.assertEqual(closeout["remote_order_id"], "order-1")
        self.assertEqual(closeout["decision"], "controlled_real_funds_canary_closed")

    def test_closeout_package_stage_rejects_post_unknown_incident_recovery_with_matching_trade(self):
        package = ROOT / "dist" / "unit-closeout-post-unknown-matching-trade"
        if package.exists():
            shutil.rmtree(package)
        package.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(package, ignore_errors=True))
        candidate = self.candidate()
        (package / "candidate-market.json").write_text(json.dumps(candidate))
        (package / "post-canary-report.json").write_text(
            json.dumps(
                {
                    "market_candidate": {
                        "target_size": "5",
                        "notional_usd": "0.1",
                    },
                    "market_candidate_sha256": self.pipeline.sha256(package / "candidate-market.json"),
                    "remote_order_readback": {"order_id": None},
                    "no_second_order_placed_by_closure": True,
                    "raw_signed_order_exposed": False,
                }
            )
        )
        stage_history = package / "post-canary-report.json.stages.jsonl"
        stage_history.write_text(
            json.dumps(
                {
                    "status": "operator_required",
                    "stage": "post_unknown",
                    "remote_order_id": None,
                    "posted": False,
                    "cancelled": False,
                    "remote_side_effects": True,
                    "operator_required": True,
                    "raw_signed_order_exposed": False,
                }
            )
            + "\n"
        )
        (package / "operator-incident-recovery.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recovery_decision": "operator_reviewed_no_remote_order_found_no_retry",
                    "operator_review_ref": "ticket://post-unknown-incident",
                    "stage_history_sha256": self.pipeline.sha256(stage_history),
                    "candidate_market_sha256": self.pipeline.sha256(package / "candidate-market.json"),
                    "remote_order_id": None,
                    "investigation_window": {
                        "started_at": "2026-05-23T00:00:00+00:00",
                        "ended_at": "2026-05-23T00:15:00+00:00",
                    },
                    "unresolved_operator_required": False,
                    "no_retry_authorized": True,
                    "no_second_order_placed": True,
                    "raw_signed_order_exposed": False,
                    "account_level_evidence": [
                        "account-open-orders-readback.json",
                        "account-trade-history-readback.json",
                        "account-activity-readback.json",
                    ],
                }
            )
        )
        (package / "account-open-orders-readback.json").write_text(
            json.dumps({"matching_open_orders_count": 0, "raw_signed_order_exposed": False})
        )
        (package / "account-trade-history-readback.json").write_text(
            json.dumps({"matching_trades_count": 1, "matching_size_total": "5", "raw_signed_order_exposed": False})
        )
        (package / "account-activity-readback.json").write_text(
            json.dumps(
                {
                    "matching_activity_count": 0,
                    "matching_trade_count": 0,
                    "matching_open_position_count": 0,
                    "matching_closed_position_count": 0,
                    "matching_value_record_count": 0,
                    "values": [],
                    "raw_signed_order_exposed": False,
                }
            )
        )
        with self.assertRaisesRegex(SystemExit, "incident recovery"):
            self.pipeline.run_closeout_stage(
                package,
                ROOT / "dist" / "polymarket-execution-suite-v0.27.3.zip",
            )


if __name__ == "__main__":
    unittest.main()
