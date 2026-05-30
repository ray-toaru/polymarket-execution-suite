from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_executor as module


class ValidateContractsExecutorTests(unittest.TestCase):
    def _minimal_v23_spec(self) -> dict:
        return {
            "paths": {
                "/v1/sign-only/lifecycle-events": {},
                "/v1/sign-only/lifecycle-events/{execution_id}": {
                    "get": {"parameters": [{"name": "before_event_id"}]}
                },
                "/v1/lifecycle/executions/{execution_id}/events": {
                    "get": {"parameters": [{"name": "before_event_id"}]}
                },
                "/v1/runtime/workers": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/RuntimeWorkerStatusReport"}
                                    }
                                }
                            }
                        }
                    }
                },
                "/v1/admin/audit-events": {"get": {"parameters": [{"name": "before_audit_id"}]}},
                "/v1/admin/reconcile-order-local": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ReconcileOrderLocalRequest"}
                                }
                            }
                        },
                        "responses": {
                            "202": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ReconcileOrderLocalResponse"}
                                    }
                                }
                            }
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "RuntimeWorkerStatusReport": {"type": "object"},
                    "ReconcileOrderLocalRequest": {"type": "object"},
                    "ReconcileOrderLocalResponse": {"type": "object"},
                    "SignOnlyLifecycleRecord": {"type": "object", "properties": {"client_event_id": {"type": "string"}}},
                }
            },
        }

    def test_v23_requires_structural_before_audit_id(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/admin/audit-events"]["get"]["parameters"] = []
        rust_text = "\n".join(
            [
                "pub client_event_id: Option<String>",
                "pub observed_at: Option<DateTime<Utc>>",
                "correlation_id_from_headers",
                "api_error_with_correlation",
                "redacted_payload_envelope",
                "principal_subject: query.principal_subject",
                "result: query.result",
                "reconcile_order_local",
                "ReconcileOrderLocalResponse",
                "list_runtime_worker_status",
                "/v1/runtime/workers",
                "candidate.client_event_id.as_deref()",
                "record.event_id = None",
                "record.created_at = None",
                "record_standard_sign_only_construction",
                "account_id does not match request",
                "OrderLifecycleRecord",
                "OrderLifecycleStore",
                "record_order_lifecycle_event",
                "in_memory_order_lifecycle_records_cancel_requested",
                "RuntimeWorkerHeartbeat",
                "RuntimeWorkerHealthStore",
                "RuntimeWorkerStatusReport",
                "RuntimeWorkerStatusStore",
                "list_runtime_worker_status",
                "record_worker_heartbeat",
                "in_memory_worker_heartbeat_informs_runtime_state",
                "principal_subject: Option<String>",
                "result: Option<String>",
                "sign_only_lifecycle_record_is_replay",
                "client_event_id reused with different event payload",
                "PMX_RUNTIME_OBSERVATION_TTL_SECONDS",
                "runtime_observation_ttl_seconds",
                "execution_id={}",
                "pub struct RedactedPayloadEnvelope",
                "redacted_payload_envelope",
                "redacted_fields",
                "WorkerDegraded",
                "pub struct SignOnlyLifecycleRecord",
                "left.client_event_id == right.client_event_id",
                "impl OrderLifecycleStore for PostgresStore",
                "postgres_records_order_lifecycle_event",
                "impl RuntimeWorkerHealthStore for PostgresStore",
                "impl RuntimeWorkerStatusStore for PostgresStore",
                "postgres_records_worker_heartbeat",
                "postgres_lists_runtime_worker_status",
                "principal_subject = $4",
                "result = $5",
                "pg_advisory_xact_lock",
                "runtime_observation_ttl_seconds",
                "FOREIGN_KEY_VIOLATION",
                "CHECK_VIOLATION",
            ]
        )

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("executor.v1.yaml"):
                return "openapi-no-private-signed-fields"
            if path.endswith("lib.rs"):
                return "WorkerStatus::Degraded => reasons.push(BlockReason::WorkerDegraded)\ndegraded_worker_blocks_pre_live"
            if path.endswith("0001_initial.sql"):
                return "\n".join(
                    [
                        "CREATE TABLE IF NOT EXISTS orders",
                        "CREATE TABLE IF NOT EXISTS order_events",
                        "idx_order_events_order_created",
                        "client_event_id TEXT",
                        "uq_sign_only_lifecycle_client_event",
                        "WHERE client_event_id IS NOT NULL",
                        "ADD COLUMN IF NOT EXISTS client_event_id",
                        "ADD COLUMN IF NOT EXISTS observed_at",
                        "ADD COLUMN IF NOT EXISTS correlation_id",
                    ]
                )
            if path.endswith("run_current_gates_impl.sh"):
                return "\n".join(
                    [
                        "run_current_gates.sh",
                        "check_current_lifecycle_api.py",
                        "check_version_consistency.py",
                        "check_docs_evidence_governance.py",
                        "write_current_evidence_manifest.py",
                        "check_runtime_worker_status_query.py",
                        "42-runtime-worker-status-query.log",
                        "evidence/current",
                    ]
                )
            return ""

        with mock.patch.object(module, "rust_source_text", return_value=rust_text), mock.patch(
            "pathlib.Path.read_text", autospec=True, side_effect=fake_read_text
        ):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("before_audit_id", str(ctx.exception))

    def test_v12_requires_compile_request_ref(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}}
            }
        }
        spec["paths"]["/v1/submissions"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SubmitReceipt"}}}}},
            }
        }
        spec["paths"]["/v1/admin/cancel-order"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelOrderRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CancelReceipt"}}}}},
            }
        }
        spec["paths"]["/v1/admin/reconcile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReconcileReport"}}}}},
            }
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v12_service_layer(spec)
        self.assertIn("/v1/plans/compile request", str(ctx.exception))

    def test_v04_requires_postgres_receipt_reservation_tests(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_tests/receipt_reservation.rs"):
                return "remote_unknown_is_persisted_conservatively"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("postgres receipt/reservation tests", str(ctx.exception))

    def test_v07_requires_gateway_traits_file_tokens(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/traits.rs"):
                return "pub trait SignerProvider\npub trait ClobGateway\npub trait RemoteReconcileReader"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway traits", str(ctx.exception))

    def test_v16_requires_runtime_worker_schema_ref(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/runtime/workers"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Wrong"
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("RuntimeWorkerStatusReport", str(ctx.exception))

    def test_v09_requires_feature_gated_adapter_tests(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/tests/feature_gated.rs"):
                return "authenticated_non_trading_smoke_executes_when_enabled\nsign_only_dry_run_executes_when_enabled"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v09_official_adapter_boundary()
        self.assertIn("official SDK feature-gated tests", str(ctx.exception))

    def test_v15_requires_api_admin_audit_support_tokens(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/admin/audit-events"]["get"]["parameters"] = [
            {"name": "before_audit_id"},
            {"name": "operation"},
            {"name": "principal_subject"},
            {"name": "result"},
            {"name": "correlation_id"},
        ]
        spec["paths"]["/v1/admin/audit-events"]["get"]["responses"] = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {"type": "array", "items": {"$ref": "#/components/schemas/AdminAuditEvent"}}
                    }
                }
            }
        }
        spec["paths"]["/v1/admin/kill-switch"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchReceipt"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/support/audit.rs"):
                return "pub(crate) async fn record_admin_audit\nprincipal_subject: principal.subject.clone()"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("API admin audit support", str(ctx.exception))

    def test_v16_requires_store_backed_runtime_provider_tokens(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/runtime_state/store_backed.rs"):
                return "pub struct StoreBackedRuntimeStateProvider<S>\npub fn new(store: S) -> Self\nasync fn capture_runtime_state"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("service store-backed runtime provider", str(ctx.exception))

    def test_v15_requires_admin_audit_query_filters(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/admin/audit-events"]["get"]["parameters"] = [{"name": "before_audit_id"}]
        spec["paths"]["/v1/admin/audit-events"]["get"]["responses"] = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {"type": "array", "items": {"$ref": "#/components/schemas/AdminAuditEvent"}}
                    }
                }
            }
        }
        spec["paths"]["/v1/admin/kill-switch"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/KillSwitchReceipt"}}}}},
            }
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("v0.15 admin audit query must expose", str(ctx.exception))

    def test_v19_rejects_forbidden_public_contract_tokens_structurally(self) -> None:
        spec = self._minimal_v23_spec()
        spec["components"]["schemas"]["Leak"] = {"type": "object", "properties": {"danger": {"description": "signed_payload"}}}
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v19_redaction_and_live_guard(spec)
        self.assertIn("signed_payload", str(ctx.exception))

    def test_v20_requires_compile_response_binding(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Wrong"}}}}},
            }
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("ExecutionPlanSummary", str(ctx.exception))

    def test_v21_requires_lifecycle_record_binding(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Wrong"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}}}}},
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"}}}},
                "responses": {"202": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"}}}}},
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"]["get"]["responses"] = {
            "200": {"content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}}}}}
        }
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "state", "event", "signed_order_ref", "no_remote_side_effect"],
            "properties": {
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionReceipt"] = {
            "type": "object",
            "properties": {
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
                "lifecycle_records": {"type": "array"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        spec["components"]["schemas"]["RuntimeWorkerStatusReport"] = {
            "type": "object",
            "properties": {"heartbeats": {"type": "array"}, "observations": {"type": "array"}},
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("SignOnlyLifecycleRecord", str(ctx.exception))

    def test_store_and_backend_structure_rejects_missing_postgres_export(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/lib.rs"):
                return "mod helpers;\nmod memory;\nmod model;\n"
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return "pub struct PostgresStore\ndatabase_url: String\npub async fn connect\nsimple_query(\"SELECT 1\")\npub async fn apply_schema\npub async fn applied_schema_migrations\npub(crate) async fn client\ntokio_postgres::connect(&self.database_url, NoTls)\nclient.batch_execute(\"ROLLBACK\")"
            if path.endswith("crates/pmx-service/src/lib.rs"):
                return "mod runtime_state;\nmod runtime_worker;\nmod sign_only;\nmod submit;\npub use runtime_state::*;\npub use runtime_worker::*;\npub use sign_only::*;\npub use submit::*;"
            if path.endswith("crates/pmx-api/src/backend/audit.rs"):
                return "impl ServiceBackend\nrecord_admin_audit_event\nlist_admin_audit_events\nSelf::InMemory(service) => service.record_admin_audit_event(event).await\nSelf::Postgres(service) => service.record_admin_audit_event(event).await\nSelf::InMemory(service) => service.list_admin_audit_events(query).await\nSelf::Postgres(service) => service.list_admin_audit_events(query).await"
            if path.endswith("crates/pmx-api/src/backend/sign_only.rs"):
                return "record_standard_sign_only_construction\nlist_sign_only_lifecycle_events\nSelf::InMemory(service) => service.record_standard_sign_only_construction(req).await\nSelf::Postgres(service) => service.record_standard_sign_only_construction(req).await\nSelf::InMemory(service) => service.list_sign_only_lifecycle_events(query).await\nSelf::Postgres(service) => service.list_sign_only_lifecycle_events(query).await"
            if path.endswith("crates/pmx-api/src/backend/runtime.rs"):
                return "list_runtime_worker_status\nset_account_kill_switch\nset_global_kill_switch\nSelf::InMemory(service) => service.list_runtime_worker_status(query).await\nSelf::Postgres(service) => service.list_runtime_worker_status(query).await\n.store()\n.set_account_kill_switch(account_id, enabled, reason)\n.set_global_kill_switch(enabled, reason)"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_store_and_backend_structure()
        self.assertIn("pmx-store module boundary missing token: pub mod postgres;", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
