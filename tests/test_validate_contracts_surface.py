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
    def test_split_top_level_csv_respects_nested_parentheses(self) -> None:
        parts = module.split_top_level_csv(
            "account_id TEXT NOT NULL, submit_attempt INTEGER NOT NULL CHECK ( submit_attempt >= 1 ), UNIQUE ( account_id, execution_id, submit_attempt )"
        )
        self.assertEqual(
            parts,
            [
                "account_id TEXT NOT NULL",
                "submit_attempt INTEGER NOT NULL CHECK ( submit_attempt >= 1 )",
                "UNIQUE ( account_id, execution_id, submit_attempt )",
            ],
        )

    def test_rust_struct_has_deny_unknown_fields_accepts_pub_crate_struct(self) -> None:
        text = """
        #[derive(Debug)]
        #[serde(deny_unknown_fields)]
        pub(crate) struct SampleRequest {
            pub field: String,
        }
        """
        self.assertTrue(module.rust_struct_has_deny_unknown_fields(text, "SampleRequest"))

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

    def test_validate_sql_idempotency_parses_table_constraints_structurally(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS idempotency_records (
            idempotency_record_id BIGSERIAL PRIMARY KEY,
            account_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            submit_attempt INTEGER NOT NULL CHECK ( submit_attempt >= 1 ),
            request_fingerprint TEXT NOT NULL,
            UNIQUE ( account_id, execution_id, idempotency_key ),
            UNIQUE ( account_id, execution_id, submit_attempt )
        );
        """
        with mock.patch.object(module, "SQL", mock.Mock(read_text=mock.Mock(return_value=sql))):
            module.validate_sql_idempotency()

    def test_validate_sql_idempotency_rejects_global_primary_key(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS idempotency_records (
            idempotency_key TEXT PRIMARY KEY
        );
        """
        with mock.patch.object(module, "SQL", mock.Mock(read_text=mock.Mock(return_value=sql))):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_sql_idempotency()
        self.assertIn("idempotency_key must not be a global primary key", str(ctx.exception))

    def test_validate_paths_and_statuses_scans_all_operations_for_202(self) -> None:
        spec = {
            "paths": {
                "/v1/submissions": {
                    "get": {"responses": {"200": {}}},
                    "post": {"responses": {"202": {}}},
                }
            }
        }
        with (
            mock.patch.object(module, "rust_routes", return_value={"/v1/submissions"}),
            mock.patch.object(module, "rust_handler_body", return_value="StatusCode::ACCEPTED"),
            mock.patch.object(module, "EXPECTED_202_PATHS", {"/v1/submissions": "submit_plan"}),
        ):
            module.validate_paths_and_statuses(spec)


if __name__ == "__main__":
    unittest.main()
