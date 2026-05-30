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


if __name__ == "__main__":
    unittest.main()
