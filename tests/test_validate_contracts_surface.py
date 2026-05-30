from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_surface as module


class ValidateContractsSurfaceTests(unittest.TestCase):
    def test_iter_json_strings_walks_nested_values_and_keys(self) -> None:
        payload = {"a": ["x", {"b": "y"}], "c": {"d": 1}}
        self.assertEqual(set(module.iter_json_strings(payload)), {"a", "x", "b", "y", "c", "d"})

    def test_validate_no_public_forbidden_tokens_uses_structural_spec_scan(self) -> None:
        spec = {
            "components": {
                "schemas": {
                    "Example": {
                        "type": "object",
                        "properties": {"danger": {"type": "string", "description": "signed_payload"}},
                    }
                }
            }
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_no_public_forbidden_tokens(spec)
        self.assertIn("forbidden token in public OpenAPI: signed_payload", str(ctx.exception))

    def test_validate_no_public_forbidden_tokens_scans_control_sources(self) -> None:
        fake_file = mock.Mock()
        fake_file.read_text.return_value = "private_key"
        fake_file.relative_to.return_value = Path("hermes-polymarket-executor-adapter/src/fake.py")
        fake_src = mock.Mock()
        fake_src.rglob.return_value = [fake_file]
        fake_control = mock.Mock()
        fake_control.__truediv__ = mock.Mock(return_value=fake_src)
        fake_control.parent = ROOT
        with mock.patch.object(module, "CONTROL", fake_control):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_no_public_forbidden_tokens({"openapi": "clean"})
        self.assertIn("forbidden token private_key in control package", str(ctx.exception))

    def test_validate_rust_deny_unknown_fields_targets_specific_files(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/model.rs"):
                return "#[serde(deny_unknown_fields)]\npub struct DecisionRequest\n#[serde(deny_unknown_fields)]\npub struct CompilePlanRequest\n#[serde(deny_unknown_fields)]\npub struct SubmitPlanRequest\n#[serde(deny_unknown_fields)]\npub struct CancelOrderRequest\n"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_rust_deny_unknown_fields()
        self.assertIn("ReconcileOrderLocalRequest", str(ctx.exception))

    def test_validate_critical_contract_shapes_checks_refs_and_schema_shape(self) -> None:
        spec = {
            "paths": {
                "/v1/submissions": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitRequest"}}}},
                        "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitReceipt"}}}}},
                    }
                },
                "/v1/admin/kill-switch": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchRequest"}}}},
                        "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchReceipt"}}}}},
                    }
                },
                "/v1/admin/cancel-order": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelOrderRequest"}}}},
                        "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelReceipt"}}}}},
                    }
                },
                "/v1/admin/reconcile": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileRequest"}}}},
                        "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileReport"}}}}},
                    }
                },
            },
            "components": {
                "schemas": {
                    "SubmitRequest": {"properties": {k: {} for k in ["execution_id", "plan_hash", "idempotency_key", "mode"]}, "required": ["execution_id", "plan_hash", "idempotency_key", "mode"]},
                    "SubmitReceipt": {"properties": {k: {} for k in ["execution_id", "receipt_id", "status", "executor_version", "contract_version"]}, "required": ["execution_id", "receipt_id", "status", "executor_version", "contract_version"]},
                    "KillSwitchRequest": {"properties": {k: {} for k in ["scope", "account_id", "enabled", "reason"]}, "required": ["scope", "enabled", "reason"]},
                    "KillSwitchReceipt": {"properties": {k: {} for k in ["scope", "account_id", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"]}, "required": ["scope", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"]},
                    "CancelOrderRequest": {"properties": {k: {} for k in ["account_id", "execution_id", "order_id", "reason"]}, "required": ["account_id", "order_id", "reason"]},
                    "CancelReceipt": {"properties": {k: {} for k in ["cancel_id", "order_id", "state"]}, "required": ["cancel_id", "order_id", "state"]},
                    "ReconcileRequest": {"properties": {k: {} for k in ["account_id", "execution_id", "order_id", "reason", "remote_observation"]}, "required": ["account_id", "execution_id", "reason"]},
                    "ReconcileReport": {"properties": {k: {} for k in ["reconcile_id", "status", "checked_orders", "findings"]}, "required": ["reconcile_id", "status", "checked_orders", "findings"]},
                }
            },
        }
        module.validate_critical_contract_shapes(spec)

    def test_validate_critical_contract_shapes_rejects_schema_drift(self) -> None:
        spec = {
            "paths": {
                "/v1/submissions": {
                    "post": {
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitRequest"}}}},
                        "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitReceipt"}}}}},
                    }
                },
                "/v1/admin/kill-switch": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchRequest"}}}}, "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchReceipt"}}}}}}},
                "/v1/admin/cancel-order": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelOrderRequest"}}}}, "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelReceipt"}}}}}}},
                "/v1/admin/reconcile": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileRequest"}}}}, "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileReport"}}}}}}},
            },
            "components": {
                "schemas": {
                    "SubmitRequest": {"properties": {k: {} for k in ["execution_id", "plan_hash", "idempotency_key", "mode", "extra"]}, "required": ["execution_id", "plan_hash", "idempotency_key", "mode"]},
                    "SubmitReceipt": {"properties": {k: {} for k in ["execution_id", "receipt_id", "status", "executor_version", "contract_version"]}, "required": ["execution_id", "receipt_id", "status", "executor_version", "contract_version"]},
                    "KillSwitchRequest": {"properties": {k: {} for k in ["scope", "account_id", "enabled", "reason"]}, "required": ["scope", "enabled", "reason"]},
                    "KillSwitchReceipt": {"properties": {k: {} for k in ["scope", "account_id", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"]}, "required": ["scope", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"]},
                    "CancelOrderRequest": {"properties": {k: {} for k in ["account_id", "execution_id", "order_id", "reason"]}, "required": ["account_id", "order_id", "reason"]},
                    "CancelReceipt": {"properties": {k: {} for k in ["cancel_id", "order_id", "state"]}, "required": ["cancel_id", "order_id", "state"]},
                    "ReconcileRequest": {"properties": {k: {} for k in ["account_id", "execution_id", "order_id", "reason", "remote_observation"]}, "required": ["account_id", "execution_id", "reason"]},
                    "ReconcileReport": {"properties": {k: {} for k in ["reconcile_id", "status", "checked_orders", "findings"]}, "required": ["reconcile_id", "status", "checked_orders", "findings"]},
                }
            },
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_critical_contract_shapes(spec)
        self.assertIn("SubmitRequest", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
