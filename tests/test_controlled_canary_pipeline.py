import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_controlled_canary_pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("run_controlled_canary_pipeline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ControlledCanaryPipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()

    def candidate(self, **overrides):
        data = {
            "market_id": "condition-1",
            "token_id": "123",
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
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "dependencies": [
                        {"name": name, "status": "durable_runtime_truth", "evidence_ref": f"pg://{name}"}
                        for name in [
                            "kill_switch",
                            "live_submit_gate",
                            "idempotency_lease",
                            "order_cancel_reconciliation",
                        ]
                    ],
                }
            )
        )
        report = self.pipeline.validate_runtime_truth_file(path)
        self.assertTrue(report["ready_for_armed_stage"])

    def test_reviewed_go_decision_requires_single_attempt_scope(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "release-decision.json"
        path.write_text(json.dumps({"decision": "go", "status": "reviewed_go"}))
        with self.assertRaisesRegex(SystemExit, "single_attempt"):
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
            ROOT / "dist" / "polymarket-execution-suite-v0.26.0.zip",
        )
        self.assertEqual(stage["status"], "pass")
        self.assertFalse(stage["remote_side_effects"])
        self.assertTrue((package / "closeout.json").exists())


if __name__ == "__main__":
    unittest.main()
