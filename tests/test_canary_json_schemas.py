import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
ENGINE_CONFIG = ROOT / "polymarket-execution-engine" / "config"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text())


class CanaryJsonSchemaTests(unittest.TestCase):
    def test_approval_request_schema_validates_generated_request(self):
        module = load_module(ROOT / "scripts" / "prepare_operator_approval_request.py", "prepare_operator_approval_request")
        schema = load_json(ENGINE_CONFIG / "real-funds-canary.approval-request.schema.json")
        request = module.build_request(
            account_id="acct-canary",
            condition_id="condition-1",
            active_profile_ref="local-profile://acct_b",
            operator_identity_ref="operator://primary",
            approval_ticket_ref="ticket://approval",
            candidate_market_file=ROOT / "README.md",
            runtime_truth_file=ROOT / "VERSION",
            runtime_gate_snapshot={
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
            runtime_gate_evidence_refs={
                "kill_switch_open": "pg://runtime/kill-switch",
                "runtime_worker_healthy": "pg://runtime/runtime-worker",
                "geoblock_allowed": "pg://runtime/geoblock",
                "repository_reservation_exists": "pg://runtime/reservation",
                "idempotency_key_written": "pg://runtime/idempotency",
                "reconcile_worker_healthy": "pg://runtime/reconcile",
                "cancel_only_fallback_ready": "pg://runtime/cancel-only-fallback",
                "balance_allowance_checked": "pg://runtime/allowance",
            },
            sidecar={
                "artifact_sha256": "a" * 64,
                "workspace_manifest_sha256": "b" * 64,
                "archived_manifest_sha256": "c" * 64,
                "evidence_manifest_sha256": "c" * 64,
            },
            candidate_limits={
                "target_size": "5",
                "limit_price": "0.02",
                "estimated_order_notional_usd": "0.1",
            },
            max_order_notional=module.Decimal("0.2"),
            max_daily_notional=module.Decimal("0.2"),
            root_ci_run_id="1",
            hermes_ci_run_id="2",
            execution_engine_ci_run_id="3",
            credentialed_sdk_run_id="local",
            valid_for_minutes=15,
        )
        jsonschema.validate(request, schema)

    def test_dual_control_review_schema_validates_template_output(self):
        request = {
            "status": "operator_approval_request_not_authorization",
            "scope": "REAL_FUNDS_CANARY",
            "execution_style": "GTC_LIMIT_POST_ONLY_CANCEL",
            "live_submit_authorized": False,
            "remote_side_effects_authorized": False,
            "secrets_included": False,
            "active_profile_ref": "local-profile://acct_b",
            "approval_hash": "a" * 64,
            "artifact_sha256": "b" * 64,
            "workspace_manifest_sha256": "c" * 64,
            "archived_manifest_sha256": "d" * 64,
            "evidence_manifest_sha256": "d" * 64,
            "market_candidate_sha256": "e" * 64,
            "runtime_truth_sha256": "f" * 64,
            "expires_at": "2099-01-01T00:00:00Z",
            "risk_limits": {
                "max_order_notional_usd": "0.2",
                "max_daily_notional_usd": "0.2",
                "candidate_target_size": "5",
                "candidate_limit_price": "0.02",
                "candidate_estimated_order_notional_usd": "0.1",
            },
        }
        module = load_module(ROOT / "scripts" / "prepare_dual_control_review_template.py", "prepare_dual_control_review_template")
        schema = load_json(ENGINE_CONFIG / "controlled-canary.dual-control-review.schema.json")
        template = module.build_template(request, approval_request_sha256="9" * 64)
        jsonschema.validate(template, schema)

    def test_release_decision_schema_validates_template_and_example(self):
        schema = load_json(ENGINE_CONFIG / "controlled-canary.release-decision.schema.json")
        template = load_json(ENGINE_CONFIG / "controlled-canary.release-decision.template.json")
        example = load_json(ENGINE_CONFIG / "controlled-canary.release-decision.example.json")
        jsonschema.validate(template, schema)
        jsonschema.validate(example, schema)


if __name__ == "__main__":
    unittest.main()
