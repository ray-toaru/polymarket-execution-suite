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
from validate_contracts_support import ContractValidationError


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
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("before_audit_id", str(ctx.exception))

    def test_v23_requires_redacted_payload_fields(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/plan/redaction.rs"):
                return """
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RedactedPayloadEnvelope {
    pub schema_version: u32,
    pub kind: String,
    pub body: Value,
}

pub fn redacted_payload_envelope() {}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("RedactedPayloadEnvelope", str(ctx.exception))

    def test_v23_requires_redacted_payload_envelope_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/plan/redaction.rs"):
                return """
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RedactedPayloadEnvelope {
    pub schema_version: u32,
    pub kind: String,
    pub correlation_id: Option<String>,
    pub redacted_fields: Vec<String>,
    pub body: Value,
}

pub fn redacted_payload_envelope(
    kind: impl Into<String>,
    correlation_id: Option<String>,
    body: Value,
) -> Value {
    serde_json::json!({
        "kind": kind.into(),
        "correlation_id": correlation_id,
        "body": body,
    })
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current core redaction helper", str(ctx.exception))

    def test_v23_requires_runtime_worker_status_trait_method(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/model/runtime.rs"):
                return """
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeWorkerObservation {
    pub account_id: String,
    pub capability: String,
    pub worker_kind: String,
    pub status: String,
    pub should_fail_closed: bool,
    pub reason: String,
    pub observed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeWorkerHeartbeat {
    pub worker_id: String,
    pub role: String,
    pub capability: String,
    pub status: String,
    pub last_heartbeat_at: DateTime<Utc>,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuntimeWorkerStatusQuery {
    pub account_id: String,
    pub limit: usize,
    pub before_observed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeWorkerStatusReport {
    pub heartbeats: Vec<RuntimeWorkerHeartbeat>,
    pub observations: Vec<RuntimeWorkerObservation>,
}

#[async_trait]
pub trait RuntimeWorkerHealthStore: Send + Sync {
    async fn record_worker_heartbeat(&self, heartbeat: &RuntimeWorkerHeartbeat) -> Result<(), StoreError>;
}

#[async_trait]
pub trait RuntimeWorkerStatusStore: Send + Sync {}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("RuntimeWorkerStatusStore", str(ctx.exception))

    def test_v23_requires_runtime_route_signature(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/read/runtime.rs"):
                return """
use super::*;

pub(crate) async fn list_runtime_worker_status(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> ApiResult<Vec<RuntimeWorkerStatusReport>> {
    require(&headers, Operation::ReadReport)?;
    let _ = state;
    Ok((StatusCode::OK, Json(Vec::new())))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("RuntimeWorkerStatusListQuery", str(ctx.exception))

    def test_v23_requires_api_error_support_bodies(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/support/error.rs"):
                return """
use axum::{Json, http::StatusCode};
use axum::http::HeaderMap;

pub(crate) fn api_error_with_correlation(
    status: StatusCode,
    message: impl Into<String>,
    correlation_id: impl Into<String>,
) -> (StatusCode, Json<serde_json::Value>) {
    (status, Json(serde_json::json!({ "error": message.into() })))
}

pub(crate) fn correlation_id_from_headers(headers: &HeaderMap) -> String {
    let _ = headers;
    String::new()
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current API error support", str(ctx.exception))

    def test_v23_requires_reconcile_route_signature(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/admin/reconcile/local.rs"):
                return """
use super::*;

pub(crate) async fn reconcile_order_local(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> ApiResult<Vec<ReconcileOrderLocalResponse>> {
    let _ = (state, headers);
    Ok((axum::http::StatusCode::ACCEPTED, Json(Vec::new())))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("ReconcileOrderLocalRequest", str(ctx.exception))

    def test_v23_requires_cancel_route_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/admin/cancel.rs"):
                return """
use super::*;

pub(crate) async fn record_cancel_order_non_live(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(req): Json<CancelOrderRequest>,
) -> ApiResult<CancelReceipt> {
    let _ = (state, headers, req);
    Ok((StatusCode::ACCEPTED, Json(CancelReceipt {
        cancel_id: "cancel-1".into(),
        order_id: "order-1".into(),
        state: CancelState::ReconcileRequired,
    })))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current API cancel route", str(ctx.exception))

    def test_v23_requires_lifecycle_read_route_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/read/lifecycle.rs"):
                return """
use super::*;

pub(crate) async fn list_sign_only_lifecycle_events(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(execution_id): Path<String>,
    Query(query): Query<EventListQuery>,
) -> ApiResult<Vec<SignOnlyLifecycleRecord>> {
    let _ = (state, headers, execution_id, query);
    Ok((StatusCode::OK, Json(Vec::new())))
}

pub(crate) async fn list_execution_lifecycle_events(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(execution_id): Path<String>,
    Query(query): Query<EventListQuery>,
) -> ApiResult<Vec<ExecutionLifecycleEvent>> {
    let _ = (state, headers, execution_id, query);
    Ok((StatusCode::OK, Json(Vec::new())))
}

pub(crate) async fn list_order_lifecycle_events(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(order_id): Path<String>,
    Query(query): Query<EventListQuery>,
) -> ApiResult<Vec<OrderLifecycleEventRecord>> {
    let _ = (state, headers, order_id, query);
    Ok((StatusCode::OK, Json(Vec::new())))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current API lifecycle read route", str(ctx.exception))

    def test_v23_requires_service_sign_only_lifecycle_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/sign_only/lifecycle.rs"):
                return """
use super::*;

pub async fn record_sign_only_lifecycle_event<S>(
    store: &S,
    mut record: SignOnlyLifecycleRecord,
) -> Result<SignOnlyLifecycleRecord, ServiceError>
where
    S: SignOnlyLifecycleStore + Send + Sync,
{
    let _ = (store, record);
    Err(ServiceError::Invariant("wrong path".into()))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current service sign-only lifecycle helper", str(ctx.exception))

    def test_v23_requires_service_order_lifecycle_divergence_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/order_lifecycle/divergence.rs"):
                return """
use super::*;

pub async fn reconcile_order_lifecycle_divergence<S>(
    store: &S,
    order_id: &str,
    account_id: Option<&str>,
    remote_observation: RemoteOrderObservation,
    reason: &str,
    correlation_id: Option<String>,
) -> Result<Option<(OrderLifecycleDivergence, Option<OrderLifecycleRecord>)>, ServiceError>
where
    S: OrderLifecycleStore + Send + Sync,
{
    let _ = (store, order_id, account_id, remote_observation, reason, correlation_id);
    Ok(None)
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current service order lifecycle divergence helper", str(ctx.exception))

    def test_v23_requires_store_sign_only_replay_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/helpers/lifecycle.rs"):
                return """
use super::*;

pub(crate) fn sign_only_lifecycle_record_is_replay(
    existing: &[SignOnlyLifecycleRecord],
    record: &SignOnlyLifecycleRecord,
) -> Result<bool, StoreError> {
    let _ = (existing, record);
    Ok(false)
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current store sign-only replay helper", str(ctx.exception))

    def test_v23_requires_store_runtime_ttl_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/helpers/runtime/freshness.rs"):
                return """
use super::*;

pub fn runtime_observation_ttl_seconds() -> i64 {
    DEFAULT_RUNTIME_OBSERVATION_TTL_SECONDS
}

pub(crate) fn runtime_observation_is_fresh(observation: &RuntimeWorkerObservation) -> bool {
    let _ = observation;
    true
}

pub(crate) fn runtime_worker_heartbeat_is_fresh(heartbeat: &RuntimeWorkerHeartbeat) -> bool {
    let _ = heartbeat;
    true
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current store runtime freshness helper", str(ctx.exception))

    def test_v23_requires_postgres_sign_only_write_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_sign_only/write.rs"):
                return """
use super::*;

pub(super) async fn record_sign_only_lifecycle_event(
    store: &PostgresStore,
    record: &SignOnlyLifecycleRecord,
) -> Result<(), StoreError> {
    let _ = (store, record);
    Ok(())
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current postgres sign-only write path", str(ctx.exception))

    def test_v23_requires_postgres_worker_status_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_worker/status.rs"):
                return """
use async_trait::async_trait;

use crate::postgres::PostgresStore;
use crate::{RuntimeWorkerStatusQuery, RuntimeWorkerStatusReport, RuntimeWorkerStatusStore, StoreError};

#[async_trait]
impl RuntimeWorkerStatusStore for PostgresStore {
    async fn list_runtime_worker_status(
        &self,
        query: &RuntimeWorkerStatusQuery,
    ) -> Result<RuntimeWorkerStatusReport, StoreError> {
        let _ = query;
        unimplemented!()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current postgres worker status path", str(ctx.exception))

    def test_v23_requires_postgres_map_db_error_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_support/error.rs"):
                return """
use super::*;

pub(crate) fn map_db_error(err: tokio_postgres::Error) -> StoreError {
    StoreError::DatabaseUnavailable(err.to_string())
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current postgres map_db_error path", str(ctx.exception))

    def test_v23_requires_postgres_order_lifecycle_write_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_order_lifecycle/write.rs"):
                return """
use crate::postgres::PostgresStore;
use crate::{OrderLifecycleEventRecord, OrderLifecycleRecord, StoreError};

pub(super) async fn record_order_lifecycle_event(
    store: &PostgresStore,
    event: &OrderLifecycleEventRecord,
) -> Result<OrderLifecycleRecord, StoreError> {
    let _ = (store, event);
    unimplemented!()
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current postgres order lifecycle write path", str(ctx.exception))

    def test_v23_requires_postgres_admin_audit_list_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_audit/admin.rs"):
                return """
use async_trait::async_trait;

use crate::postgres::PostgresStore;
use crate::{AdminAuditEvent, AdminAuditQuery, AdminAuditStore, StoreError};

#[async_trait]
impl AdminAuditStore for PostgresStore {
    async fn record_admin_audit_event(&self, event: &AdminAuditEvent) -> Result<(), StoreError> {
        let _ = event;
        Ok(())
    }

    async fn list_admin_audit_events(
        &self,
        query: &AdminAuditQuery,
    ) -> Result<Vec<AdminAuditEvent>, StoreError> {
        let _ = query;
        unimplemented!()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current postgres admin audit list path", str(ctx.exception))

    def test_v23_requires_runtime_worker_status_route_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/read/runtime.rs"):
                return """
use super::*;

pub(crate) async fn list_runtime_worker_status(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(query): Query<RuntimeWorkerStatusListQuery>,
) -> ApiResult<RuntimeWorkerStatusReport> {
    let _ = (state, headers, query);
    unimplemented!()
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current runtime worker status route", str(ctx.exception))

    def test_v23_requires_api_support_admin_audit_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/support/audit.rs"):
                return """
use axum::{Json, http::StatusCode};
use pmx_authz::Principal;

use crate::backend::AppState;

pub(crate) async fn record_admin_audit(
    state: &AppState,
    principal: &Principal,
    operation: &'static str,
    request_fingerprint: Option<String>,
    correlation_id: Option<String>,
    result: impl Into<String>,
) -> Result<(), (StatusCode, Json<serde_json::Value>)> {
    let _ = (state, principal, operation, request_fingerprint, correlation_id, result);
    Ok(())
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current API support admin audit helper", str(ctx.exception))

    def test_v23_requires_reconcile_local_route_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/admin/reconcile/local.rs"):
                return """
use axum::{Json, extract::State, http::HeaderMap};

use crate::backend::AppState;
use crate::model::{ReconcileOrderLocalRequest, ReconcileOrderLocalResponse};
use crate::support::ApiResult;

pub(crate) async fn reconcile_order_local(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(req): Json<ReconcileOrderLocalRequest>,
) -> ApiResult<ReconcileOrderLocalResponse> {
    let _ = (state, headers, req);
    unimplemented!()
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current reconcile local route", str(ctx.exception))

    def test_v23_requires_runtime_policy_worker_handling(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-policy/src/runtime.rs"):
                return """
use pmx_core::{
    BlockReason, CollateralProfileStatus, GeoblockStatus, RuntimeStateSummary, WorkerStatus,
};

pub(crate) fn collect_runtime_reasons(state: &RuntimeStateSummary, reasons: &mut Vec<BlockReason>) {
    let _ = (state, reasons);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current runtime policy worker handling", str(ctx.exception))

    def test_v23_requires_lifecycle_gate_source_text_helper(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("validation/check_current_lifecycle_api.py"):
                return """
#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from current_gate_chain import ACTIVE_GATE_IMPLEMENTATION, CURRENT_GATES

ROOT = Path(__file__).resolve().parents[1]
GATE = CURRENT_GATES
ACTIVE_GATE = ACTIVE_GATE_IMPLEMENTATION
VERSION_GUARD = ROOT.parent / "scripts" / "check_version_consistency.py"
HERMES_CLIENT = ROOT.parent / "hermes-polymarket-executor-adapter" / "src" / "hermes_polymarket_executor_adapter" / "client.py"
HERMES_MODELS = ROOT.parent / "hermes-polymarket-executor-adapter" / "src" / "hermes_polymarket_executor_adapter" / "models.py"
REQUIRED = {ACTIVE_GATE: ["current gates completed"]}
FORBIDDEN = {}

def source_text(path: Path) -> str:
    return path.read_text()

def main() -> int:
    failures: list[str] = []
    for path, needles in REQUIRED.items():
        if not path.exists() and path in {VERSION_GUARD, HERMES_CLIENT, HERMES_MODELS}:
            continue
        text = source_text(path)
        for needle in needles:
            if needle not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {needle}")
    for path, needles in FORBIDDEN.items():
        text = source_text(path)
        for needle in needles:
            if needle in text:
                failures.append(f"{path.relative_to(ROOT)} contains forbidden token {needle}")
    print("current lifecycle/query static guard passed")
    return 0
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current lifecycle gate guard", str(ctx.exception))

    def test_v23_requires_runtime_status_gate_helpers(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("validation/check_runtime_worker_status_query.py"):
                return """
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from current_gate_chain import ACTIVE_GATE_IMPLEMENTATION, CURRENT_GATES

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "crates" / "pmx-api" / "src"
GATES = CURRENT_GATES
ACTIVE_GATES = ACTIVE_GATE_IMPLEMENTATION
REQUIRED = {ACTIVE_GATES: ["42-runtime-worker-status-query.log"], API: ["/v1/runtime/workers"]}

def env_enabled(name: str) -> bool:
    return bool(os.environ.get(name))

def source_text(path: Path) -> str:
    return path.read_text()

def main() -> int:
    failures: list[str] = []
    for path, needles in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing artifact: {path.relative_to(ROOT)}")
            continue
        text = source_text(path)
        for needle in needles:
            if needle not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {needle}")
    if env_enabled("PMX_ALLOW_LIVE_SUBMIT"):
        failures.append("PMX_ALLOW_LIVE_SUBMIT=1 is not allowed during runtime status query guard")
    if env_enabled("PMX_ALLOW_LIVE_CANCEL"):
        failures.append("PMX_ALLOW_LIVE_CANCEL=1 is not allowed during runtime status query guard")
    result = {
        "status": "fail" if failures else "pass",
        "route": "/v1/runtime/workers",
        "live_submit_env_enabled": env_enabled("PMX_ALLOW_LIVE_SUBMIT"),
        "live_cancel_env_enabled": env_enabled("PMX_ALLOW_LIVE_CANCEL"),
        "remote_trading_side_effect": "not_executed",
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if failures else 0
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("runtime status query guard", str(ctx.exception))

    def test_v19_requires_live_submit_guard_module_bindings(self) -> None:
        class GuardModule:
            ALLOWED_GATEWAY_POST_ORDER_FILE = Path("sdk_runtime/gateway.rs")
            ALLOWED_POST_ORDER_FILE = Path("sdk_runtime/live_canary.rs")
            ALLOWED_SERVICE_POST_ORDER_FILE = Path("submit/live.rs")
            PUBLIC_CONTRACT = Path("openapi/executor.v1.yaml")
            FORBIDDEN_PUBLIC_TERMS = ["SignedOrderEnvelope"]
            REQUIRED_CANARY_TOKENS = []
            REQUIRED_IDEMPOTENCY_TOKENS = []

            @staticmethod
            def strip_rust_comments(text: str) -> str:
                return text

            @staticmethod
            def validate_allowed_call_sites(**kwargs):
                return []

            @staticmethod
            def validate_required_tokens(**kwargs):
                return []

            @staticmethod
            def validate_idempotency_guard_tokens():
                return []

            @staticmethod
            def validate_canary_guard_tokens(raw_adapter_text: str):
                return []

            @staticmethod
            def validate_service_live_submit_tokens():
                return []

            @staticmethod
            def main() -> int:
                return 0

        with mock.patch.object(module, "import_module_from_path", return_value=GuardModule):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard({})
        self.assertIn("live-submit static guard missing forbidden public terms", str(ctx.exception))

    def test_v21_requires_sign_only_transition_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "plan_hash",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
            "properties": {
                "heartbeats": {"type": "array"},
                "observations": {"type": "array"},
            },
        }
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/lifecycle/sign_only.rs"):
                return """
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::{AccountId, CoreError, ExecutionId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignOnlyLifecycleState {
    Planned,
    ReservationPrepared,
    SigningRequested,
    SignedDryRun,
    Failed,
    Abandoned,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignOnlyLifecycleEventKind {
    PrepareReservation,
    RequestSigning,
    SignedWithoutPost,
    SigningFailed,
    Abandon,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SignOnlyLifecycleRecord {
    pub execution_id: ExecutionId,
    pub account_id: AccountId,
    pub state: SignOnlyLifecycleState,
    pub event: SignOnlyLifecycleEventKind,
    pub client_event_id: Option<String>,
    pub signed_order_ref: Option<String>,
    pub no_remote_side_effect: bool,
    pub event_id: Option<i64>,
    pub created_at: Option<DateTime<Utc>>,
}
pub fn sign_only_lifecycle_records_equivalent(left: &SignOnlyLifecycleRecord, right: &SignOnlyLifecycleRecord) -> bool {
    left.execution_id == right.execution_id
}
pub fn transition_sign_only_lifecycle(from: SignOnlyLifecycleState, event: SignOnlyLifecycleEventKind) -> Result<SignOnlyLifecycleState, CoreError> {
    let _ = (from, event);
    Err(CoreError::InvalidSignOnlyTransition { from: SignOnlyLifecycleState::Planned, event: SignOnlyLifecycleEventKind::Abandon })
}
pub fn sign_only_lifecycle_has_remote_side_effect(record: &SignOnlyLifecycleRecord) -> bool { !record.no_remote_side_effect }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 sign-only lifecycle equivalence", str(ctx.exception))

    def test_v21_requires_runtime_worker_store_write_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/health/action.rs"):
                return """
use serde::{Deserialize, Serialize};

use super::RuntimeSignal;
use crate::{HealthLevel, RuntimeWorkerKind};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeWorkerAction {
    pub kind: RuntimeWorkerKind,
    pub capability: String,
    pub should_fail_closed: bool,
    pub should_update_runtime_store: bool,
    pub reason: String,
}

pub fn worker_actions_from_runtime_signals(signals: &[RuntimeSignal]) -> Vec<RuntimeWorkerAction> {
    let _ = signals;
    Vec::new()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RuntimeWorkerStoreWrite {
    pub account_id: String,
    pub capability: String,
    pub worker_kind: RuntimeWorkerKind,
    pub status: HealthLevel,
    pub should_fail_closed: bool,
    pub reason: String,
}

pub fn runtime_worker_store_writes(
    account_id: impl Into<String>,
    signals: &[RuntimeSignal],
) -> Vec<RuntimeWorkerStoreWrite> {
    let _ = (account_id, signals);
    Vec::new()
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 runtime worker action model", str(ctx.exception))

    def test_v21_requires_sign_only_receipt_lifecycle_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/lifecycle.rs"):
                return """
use crate::{OfficialSdkAdapterError, SignOnlyDryRunReceipt};
use pmx_core::{SignOnlyLifecycleRecord};

pub fn sign_only_lifecycle_records_from_receipt(
    receipt: &SignOnlyDryRunReceipt,
) -> Result<Vec<SignOnlyLifecycleRecord>, OfficialSdkAdapterError> {
    let _ = receipt;
    Ok(vec![])
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 sign-only lifecycle adapter", str(ctx.exception))

    def test_v21_requires_sign_only_lifecycle_test_bodies(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/tests/sign_only.rs"):
                return """
use super::*;

#[test]
fn standard_sign_only_construction_emits_only_digest_ref_and_lifecycle() {
    assert!(true);
}

#[test]
fn sign_only_lifecycle_records_are_persistable_and_non_mutating() {
    assert!(true);
}

#[test]
fn sign_only_lifecycle_rejects_posted_receipt() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 sign-only lifecycle tests", str(ctx.exception))

    def test_v21_requires_runtime_worker_test_bodies(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/runtime_tests/breakdown_loop/capabilities/groups.rs"):
                return """
use super::super::super::*;

#[test]
fn worker_actions_mark_stale_runtime_inputs_as_fail_closed_updates() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 runtime worker tests", str(ctx.exception))

    def test_v21_requires_sign_only_remote_side_effect_helper_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"] = {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                                }
                            }
                        }
                    }
                }
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["components"]["schemas"]["StandardSignOnlyConstructionRequest"] = {
            "type": "object",
            "required": ["execution_id", "account_id", "plan_hash", "no_remote_side_effect"],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
                "signed_order_ref": {"type": "string"},
                "signed_order_digest": {"type": "string"},
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
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
            "properties": {
                "execution_id": {"type": "string"},
                "account_id": {"type": "string"},
                "state": {"type": "string"},
                "event": {"type": "string"},
                "client_event_id": {"type": "string"},
                "signed_order_ref": {"type": "string"},
                "no_remote_side_effect": {"type": "boolean"},
            },
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/lifecycle/sign_only.rs"):
                return """
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::{AccountId, CoreError, ExecutionId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignOnlyLifecycleState {
    Planned,
    ReservationPrepared,
    SigningRequested,
    SignedDryRun,
    Failed,
    Abandoned,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignOnlyLifecycleEventKind {
    PrepareReservation,
    RequestSigning,
    SignedWithoutPost,
    SigningFailed,
    Abandon,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SignOnlyLifecycleRecord {
    pub execution_id: ExecutionId,
    pub account_id: AccountId,
    pub state: SignOnlyLifecycleState,
    pub event: SignOnlyLifecycleEventKind,
    pub client_event_id: Option<String>,
    pub signed_order_ref: Option<String>,
    pub no_remote_side_effect: bool,
    pub event_id: Option<i64>,
    pub created_at: Option<DateTime<Utc>>,
}

pub fn sign_only_lifecycle_records_equivalent(
    left: &SignOnlyLifecycleRecord,
    right: &SignOnlyLifecycleRecord,
) -> bool {
    left.execution_id == right.execution_id
        && left.account_id == right.account_id
        && left.state == right.state
        && left.event == right.event
        && left.client_event_id == right.client_event_id
        && left.signed_order_ref == right.signed_order_ref
        && left.no_remote_side_effect == right.no_remote_side_effect
}

pub fn transition_sign_only_lifecycle(
    from: SignOnlyLifecycleState,
    event: SignOnlyLifecycleEventKind,
) -> Result<SignOnlyLifecycleState, CoreError> {
    let next = match (&from, &event) {
        (SignOnlyLifecycleState::Planned, SignOnlyLifecycleEventKind::PrepareReservation) => SignOnlyLifecycleState::ReservationPrepared,
        (SignOnlyLifecycleState::ReservationPrepared, SignOnlyLifecycleEventKind::RequestSigning) => SignOnlyLifecycleState::SigningRequested,
        (SignOnlyLifecycleState::SigningRequested, SignOnlyLifecycleEventKind::SignedWithoutPost) => SignOnlyLifecycleState::SignedDryRun,
        (SignOnlyLifecycleState::SigningRequested, SignOnlyLifecycleEventKind::SigningFailed)
        | (SignOnlyLifecycleState::ReservationPrepared, SignOnlyLifecycleEventKind::SigningFailed) => SignOnlyLifecycleState::Failed,
        (SignOnlyLifecycleState::Planned, SignOnlyLifecycleEventKind::Abandon)
        | (SignOnlyLifecycleState::ReservationPrepared, SignOnlyLifecycleEventKind::Abandon)
        | (SignOnlyLifecycleState::SigningRequested, SignOnlyLifecycleEventKind::Abandon) => SignOnlyLifecycleState::Abandoned,
        _ => return Err(CoreError::InvalidSignOnlyTransition { from, event }),
    };
    Ok(next)
}

pub fn sign_only_lifecycle_has_remote_side_effect(record: &SignOnlyLifecycleRecord) -> bool {
    record.no_remote_side_effect
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("v0.21 sign-only lifecycle core", str(ctx.exception))

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
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_v12_service_layer(spec)
        self.assertIn("/v1/plans/compile request", str(ctx.exception))

    def test_v08_requires_toolchain_pin(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/rust-toolchain.toml"):
                return '[toolchain]\nchannel = "stable"\ncomponents = ["rustfmt", "clippy"]\nprofile = "minimal"\n'
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("executor rust toolchain", str(ctx.exception))

    def test_v08_requires_sdk_spike_manifest_feature_wiring(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-spike/Cargo.toml"):
                return """
[package]
name = "pmx-official-sdk-spike"
version = "0.0.0"
edition = "2024"
rust-version = "1.88"

[features]
default = []
sdk-typecheck = ["dep:polymarket_client_sdk_v2"]
live-submit = []

[dependencies]
polymarket_client_sdk_v2 = { version = "=0.6.0-canary.1", optional = true }

[workspace]
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("official SDK spike Cargo must keep live-submit gated by sdk-typecheck", str(ctx.exception))

    def test_v08_requires_sdk_spike_default_config_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-spike/src/lib.rs"):
                return """
use serde::{Deserialize, Serialize};

pub const OFFICIAL_SDK_REPOSITORY: &str = "https://github.com/Polymarket/rs-clob-client-v2";
pub const OFFICIAL_SDK_CRATE: &str = "polymarket_client_sdk_v2";
pub const PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1";
pub const LIVE_SUBMIT_FEATURE_NAME: &str = "live-submit";
pub const CLOB_PRODUCTION_HOST: &str = "https://clob.polymarket.com";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub use_ws: bool,
    pub use_heartbeats: bool,
    pub allow_live_submit: bool,
    pub require_explicit_runtime_kill_switch_open: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.to_string(),
            use_ws: true,
            use_heartbeats: true,
            allow_live_submit: true,
            require_explicit_runtime_kill_switch_open: true,
        }
    }
}

#[cfg(feature = "sdk-typecheck")]
pub fn sdk_client_type_marker() -> &'static str {
    std::any::type_name::<polymarket_client_sdk_v2::clob::Client>()
}

#[cfg(test)]
mod tests {
    #[cfg(feature = "sdk-typecheck")]
    use std::time::Duration;
    #[cfg(feature = "sdk-typecheck")]
    use tokio::time;
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("official SDK spike", str(ctx.exception))

    def test_v08_requires_sdk_spike_cfg_gated_test_imports(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-spike/src/lib.rs"):
                return """
use serde::{Deserialize, Serialize};

pub const OFFICIAL_SDK_REPOSITORY: &str = "https://github.com/Polymarket/rs-clob-client-v2";
pub const OFFICIAL_SDK_CRATE: &str = "polymarket_client_sdk_v2";
pub const PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1";
pub const LIVE_SUBMIT_FEATURE_NAME: &str = "live-submit";
pub const CLOB_PRODUCTION_HOST: &str = "https://clob.polymarket.com";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub use_ws: bool,
    pub use_heartbeats: bool,
    pub allow_live_submit: bool,
    pub require_explicit_runtime_kill_switch_open: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.to_string(),
            use_ws: true,
            use_heartbeats: true,
            allow_live_submit: false,
            require_explicit_runtime_kill_switch_open: true,
        }
    }
}

#[cfg(feature = "sdk-typecheck")]
pub fn sdk_client_type_marker() -> &'static str {
    std::any::type_name::<polymarket_client_sdk_v2::clob::Client>()
}

#[cfg(test)]
mod tests {
    use super::*;
    use polymarket_client_sdk_v2::Result as SdkResult;
    use std::time::Duration;
    #[cfg(feature = "sdk-typecheck")]
    use tokio::time;

    #[cfg(feature = "sdk-typecheck")]
    fn default_read_only_client() -> SdkResult<polymarket_client_sdk_v2::clob::Client> {
        polymarket_client_sdk_v2::clob::Client::new(
            CLOB_PRODUCTION_HOST,
            polymarket_client_sdk_v2::clob::Config::default(),
        )
    }

    #[test]
    fn live_submit_is_disabled_by_default() {
        let cfg = OfficialSdkAdapterConfig::default();
        assert!(!cfg.allow_live_submit);
        assert_eq!(cfg.clob_host, CLOB_PRODUCTION_HOST);
        assert!(cfg.require_explicit_runtime_kill_switch_open);
    }

    #[cfg(feature = "sdk-typecheck")]
    #[tokio::test]
    async fn read_only_ok_smoke() -> anyhow::Result<()> {
        let client = default_read_only_client()?;
        let status = time::timeout(Duration::from_secs(10), client.ok())
            .await
            .map_err(|_| anyhow::anyhow!("SDK read-only smoke timeout"))??;
        assert_eq!(status.to_uppercase(), "OK");
        let _ = time::timeout(Duration::from_secs(10), client.server_time())
            .await
            .map_err(|_| anyhow::anyhow!("SDK read-only smoke server time timeout"))??;
        Ok(())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("official SDK spike", str(ctx.exception))

    def test_v08_requires_dependency_policy_doc_tokens(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("DEPENDENCY_POLICY.md"):
                return """
# Dependency and environment policy

Official SDK crate: polymarket_client_sdk_v2
Official SDK version: =0.6.0-canary.1

- Official SDK dependencies stay isolated in adapter crates.
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("dependency policy doc", str(ctx.exception))

    def test_v08_requires_dependency_policy_bullet_lines(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("DEPENDENCY_POLICY.md"):
                return """
# Dependency and environment policy — v0.28

## Current baseline

```text
Official SDK crate: polymarket_client_sdk_v2
Official SDK version: =0.6.0-canary.1
```

## Policy

Official SDK dependencies stay isolated in adapter crates.
Core, policy, store, service, and public API crates must not depend directly on the official SDK.
The official SDK remains exactly pinned until a newer version is separately reviewed and validated.
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("missing policy line", str(ctx.exception))

    def test_v08_requires_root_cargo_workspace_version_alignment(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/Cargo.toml"):
                return """
[workspace]
members = ["crates/pmx-core"]
resolver = "2"

[workspace.package]
edition = "2024"
license = "Apache-2.0"
version = "0.27.9"
rust-version = "1.88"

[workspace.dependencies]
serde = { version = "1.0.228", features = ["derive"] }
tokio = { version = "1.52.3", features = ["macros"] }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("workspace.package.version aligned with VERSION", str(ctx.exception))

    def test_v08_requires_sdk_plan_tokens_under_expected_sections(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/docs/SDK_FIRST_ADAPTER_PLAN.md"):
                return """
# Official SDK-first Adapter Plan

## Current state

```text
v0.7: official SDK spike + read-only smoke evidence
```

## Promotion sequence

```text
1. SDK spike typecheck/read-only smoke: done
2. official adapter crate fmt/check/clippy/test: done
```

## Notes

```text
8. live-submit denied-path tests
9. manual live-submit readiness review
- no SDK dependency in core/policy/store
- no live submit without feature + env + config + runtime gates
```
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("SDK first adapter plan doc", str(ctx.exception))

    def test_v07_requires_scaffold_admin_paths_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/tests/http_and_fake_e2e/scaffold/admin_paths.rs"):
                return """
use super::super::*;

pub(super) async fn verify_non_live_admin_paths(app: axum::Router, execution_id: &str) {
    let _ = (app, execution_id);
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("HTTP scaffold admin paths", str(ctx.exception))

    def test_v07_requires_scaffold_submit_sign_only_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/tests/http_and_fake_e2e/scaffold/submit_sign_only.rs"):
                return """
use super::super::*;

pub(super) async fn verify_submit_and_sign_only(
    app: axum::Router,
    execution_id: &str,
    plan_hash: &str,
) {
    let _ = (app, execution_id, plan_hash);
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("HTTP scaffold submit/sign-only", str(ctx.exception))

    def test_v07_requires_signer_provider_default_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/signer.rs"):
                return """
use crate::{GatewayError, PlanOrder, Signer, SignerProvider};
use async_trait::async_trait;
use pmx_core::{AccountId, InternalOrderId, SignedOrderEnvelope};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SignerBackendKind {
    Disabled,
    DeterministicTest,
    OfficialSdkLocal,
    OfficialSdkRemoteKms,
    OfficialSdkExternal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SignerProviderConfig {
    pub backend: SignerBackendKind,
    pub allow_local_private_key_material: bool,
    pub require_remote_signer_in_production: bool,
}

impl Default for SignerProviderConfig {
    fn default() -> Self {
        Self {
            backend: SignerBackendKind::Disabled,
            allow_local_private_key_material: true,
            require_remote_signer_in_production: true,
        }
    }
}

#[derive(Default)]
pub struct DeterministicTestSignerProvider;

#[async_trait]
impl SignerProvider for DeterministicTestSignerProvider {
    async fn signer_for_account(
        &self,
        _account_id: &AccountId,
    ) -> Result<Arc<dyn Signer>, GatewayError> {
        Ok(Arc::new(DeterministicTestSigner))
    }
}

pub struct DeterministicTestSigner;

#[async_trait]
impl Signer for DeterministicTestSigner {
    async fn sign_order(&self, order: &PlanOrder) -> Result<SignedOrderEnvelope, GatewayError> {
        Ok(SignedOrderEnvelope {
            internal_order_id: InternalOrderId(format!("test-order-{}", order.execution_id)),
            account_id: order.account_id.clone(),
            signer_fingerprint: format!(
                "deterministic-test-signer:{}:{}",
                order.side, order.time_in_force
            ),
            signed_payload_ref: "test-only-no-real-signature".into(),
        })
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway signer provider", str(ctx.exception))

    def test_v07_requires_deterministic_signer_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/signer.rs"):
                return """
use crate::{GatewayError, PlanOrder, Signer, SignerProvider};
use async_trait::async_trait;
use pmx_core::{AccountId, InternalOrderId, SignedOrderEnvelope};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SignerBackendKind {
    Disabled,
    DeterministicTest,
    OfficialSdkLocal,
    OfficialSdkRemoteKms,
    OfficialSdkExternal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SignerProviderConfig {
    pub backend: SignerBackendKind,
    pub allow_local_private_key_material: bool,
    pub require_remote_signer_in_production: bool,
}

impl Default for SignerProviderConfig {
    fn default() -> Self {
        Self {
            backend: SignerBackendKind::Disabled,
            allow_local_private_key_material: false,
            require_remote_signer_in_production: true,
        }
    }
}

#[derive(Default)]
pub struct DeterministicTestSignerProvider;

#[async_trait]
impl SignerProvider for DeterministicTestSignerProvider {
    async fn signer_for_account(
        &self,
        _account_id: &AccountId,
    ) -> Result<Arc<dyn Signer>, GatewayError> {
        Ok(Arc::new(DeterministicTestSigner))
    }
}

pub struct DeterministicTestSigner;

#[async_trait]
impl Signer for DeterministicTestSigner {
    async fn sign_order(&self, order: &PlanOrder) -> Result<SignedOrderEnvelope, GatewayError> {
        let _ = order;
        Err(GatewayError::SigningUnavailable)
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway signer provider", str(ctx.exception))

    def test_v07_requires_gateway_state_machine_test_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/tests/post_cancel.rs"):
                return """
use super::*;

#[tokio::test]
async fn deterministic_signer_provider_posts_reads_and_cancels() {
    let provider = DeterministicTestSignerProvider;
    let gateway = FakeGateway::new();
    let account = pmx_core::AccountId("acct-gateway-test".into());
    let signer = provider.signer_for_account(&account).await.expect("test signer");
    let signed = signer.sign_order(&sample_order()).await.expect("signed");
    let ack = gateway.post_order(&signed).await.expect("posted");
    let read = gateway.get_order(&account, &ack.remote_order_id).await.expect("read").expect("remote order");
    assert_eq!(read.state, "OPEN");
    assert_eq!(gateway.get_open_orders(&account).await.expect("open").len(), 1);
    let cancel = gateway.cancel_order(&account, &ack.remote_order_id).await.expect("cancel");
    assert_eq!(cancel, pmx_core::CancelState::RemoteAccepted);
    assert!(gateway.get_open_orders(&account).await.expect("open").is_empty());
}

#[tokio::test]
async fn fake_gateway_cancel_maps_to_order_lifecycle_state_machine() {
    assert!(true);
}

#[tokio::test]
async fn fake_gateway_surfaces_remote_unknown_without_local_success() {
    let gateway = FakeGateway::new().with_post_failure(FakeGatewayFailure::RemoteUnknown(
        "timeout after signing".into(),
    ));
    let signed = DeterministicTestSigner.sign_order(&sample_order()).await.expect("signed");
    let err = gateway.post_order(&signed).await.expect_err("remote unknown");
    assert_eq!(err, GatewayError::RemoteUnknown("timeout after signing".into()));
}

#[tokio::test]
async fn fake_gateway_is_account_scoped() {
    let gateway = FakeGateway::new();
    let account_a = pmx_core::AccountId("acct-a".into());
    let account_b = pmx_core::AccountId("acct-b".into());
    let signer = DeterministicTestSigner;
    let mut order = sample_order();
    order.account_id = account_a.clone();
    let signed = signer.sign_order(&order).await.expect("signed");
    let ack = gateway.post_order(&signed).await.expect("posted");
    assert!(gateway.get_order(&account_b, &ack.remote_order_id).await.expect("read").is_none());
    assert!(gateway.get_open_orders(&account_b).await.expect("open").is_empty());
    assert_eq!(gateway.cancel_order(&account_b, &ack.remote_order_id).await.expect("cancel foreign"), pmx_core::CancelState::ReconcileRequired);
    assert_eq!(gateway.get_open_orders(&account_a).await.expect("open account a").len(), 1);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway post/cancel tests", str(ctx.exception))

    def test_v07_requires_gateway_account_scope_test_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/tests/post_cancel.rs"):
                return """
use super::*;

#[tokio::test]
async fn deterministic_signer_provider_posts_reads_and_cancels() {
    let provider = DeterministicTestSignerProvider;
    let gateway = FakeGateway::new();
    let account = pmx_core::AccountId("acct-gateway-test".into());
    let signer = provider.signer_for_account(&account).await.expect("test signer");
    let signed = signer.sign_order(&sample_order()).await.expect("signed");
    let ack = gateway.post_order(&signed).await.expect("posted");
    let read = gateway.get_order(&account, &ack.remote_order_id).await.expect("read").expect("remote order");
    assert_eq!(read.state, "OPEN");
    assert_eq!(gateway.get_open_orders(&account).await.expect("open").len(), 1);
    let cancel = gateway.cancel_order(&account, &ack.remote_order_id).await.expect("cancel");
    assert_eq!(cancel, pmx_core::CancelState::RemoteAccepted);
    assert!(gateway.get_open_orders(&account).await.expect("open").is_empty());
}

#[tokio::test]
async fn fake_gateway_cancel_maps_to_order_lifecycle_state_machine() {
    let provider = DeterministicTestSignerProvider;
    let gateway = FakeGateway::new();
    let account = pmx_core::AccountId("acct-gateway-test".into());
    let signer = provider.signer_for_account(&account).await.expect("test signer");
    let signed = signer.sign_order(&sample_order()).await.expect("signed");
    let mut state = OrderLifecycleState::Planned;
    state = transition_order_state(state, OrderEventKind::Signed).expect("signed transition");
    state = transition_order_state(state, OrderEventKind::PostRequested).expect("post requested transition");
    let ack = gateway.post_order(&signed).await.expect("posted");
    state = transition_order_state(state, OrderEventKind::RemotePosted).expect("remote posted transition");
    let cancel = gateway.cancel_order(&account, &ack.remote_order_id).await.expect("cancel");
    assert_eq!(cancel, pmx_core::CancelState::RemoteAccepted);
    state = transition_order_state(state, OrderEventKind::CancelRequested).expect("cancel requested transition");
    state = transition_order_state(state, OrderEventKind::CancelRemoteAccepted).expect("cancel accepted transition");
    assert_eq!(state, OrderLifecycleState::CancelRemoteAccepted);
}

#[tokio::test]
async fn fake_gateway_surfaces_remote_unknown_without_local_success() {
    let gateway = FakeGateway::new().with_post_failure(FakeGatewayFailure::RemoteUnknown(
        "timeout after signing".into(),
    ));
    let signed = DeterministicTestSigner.sign_order(&sample_order()).await.expect("signed");
    let err = gateway.post_order(&signed).await.expect_err("remote unknown");
    assert_eq!(err, GatewayError::RemoteUnknown("timeout after signing".into()));
}

#[tokio::test]
async fn fake_gateway_is_account_scoped() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway post/cancel tests", str(ctx.exception))

    def test_v08_requires_dependabot_weekly_root_updates(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith(".github/dependabot.yml"):
                return """
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 5
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("dependabot github-actions update schedule must stay weekly", str(ctx.exception))

    def test_v08_requires_integration_static_contract_step_names(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith(".github/workflows/ci.yml"):
                return """
name: ci
jobs:
  adapter-required-ci:
    uses: ray-toaru/hermes-polymarket-executor-adapter/.github/workflows/ci.yml@caec425b172e126365b2f521f70ac82badc60e70
  engine-required-ci:
    uses: ray-toaru/polymarket-execution-engine/.github/workflows/ci.yml@edc1b62b531b84a3297f254a48b8e17e01610f84
  engine-rust-locked:
    runs-on: ubuntu-latest
  integration-python-compat:
    runs-on: ubuntu-latest
  integration-static:
    runs-on: ubuntu-latest
    steps:
      - name: Validate root and API contracts
      - name: Run integration Python tests
      - name: Run adapter tests
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v08_dependency_and_sdk_policy()
        self.assertIn("root CI workflow integration-static job missing step", str(ctx.exception))

    def test_v04_requires_postgres_receipt_reservation_tests(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_tests/receipt_reservation.rs"):
                return "remote_unknown_is_persisted_conservatively"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("remote_unknown_is_persisted_conservatively", str(ctx.exception))

    def test_v04_requires_http_auth_fake_e2e_smoke_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/tests/http_and_fake_e2e/smoke.rs"):
                return """
use super::*;

#[tokio::test]
async fn http_auth_and_fake_e2e_smoke() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("HTTP/auth fake E2E smoke", str(ctx.exception))

    def test_v04_requires_remote_unknown_receipt_test_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_tests/receipt_reservation.rs"):
                return """
use super::*;

#[tokio::test]
async fn remote_unknown_is_persisted_conservatively() {
    assert!(true);
}

#[tokio::test]
async fn reservation_double_spend_is_prevented_concurrently() {
    let Some(store) = test_store().await else {
        return;
    };
    let account = unique("acct");
    let execution = unique("exec");
    let reservation = OrderReservation {
        reservation_id: unique("reservation"),
        account_id: AccountId(account.clone()),
        execution_id: ExecutionId(execution.clone()),
        internal_order_id: None,
        quantity_bound: QuantityBound::WorstCaseQuoteNotional(DecimalString("10".into())),
        state: ReservationState::Active,
    };
    let a = store.clone();
    let b = store.clone();
    let r1 = reservation.clone();
    let r2 = reservation;
    let (_left, _right) = tokio::join!(
        async move { a.save_order_reservation(&r1).await },
        async move { b.save_order_reservation(&r2).await }
    );
    let client = store.client().await.expect("test postgres client");
    let count: i64 = client
        .query_one(
            "SELECT COUNT(*) FROM order_reservations WHERE account_id = $1 AND execution_id = $2",
            &[&account, &execution],
        )
        .await
        .expect("query reservations")
        .get(0);
    assert_eq!(count, 1);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("postgres receipt/reservation tests", str(ctx.exception))

    def test_v04_requires_advisory_lock_key_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/model/advisory.rs"):
                return """
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct AdvisoryLockKey(pub i64);

pub fn advisory_lock_key(namespace: &str, account_id: &str, resource_key: &str) -> AdvisoryLockKey {
    let _ = (namespace, account_id, resource_key);
    AdvisoryLockKey(0)
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("pmx-store advisory lock model", str(ctx.exception))

    def test_v04_requires_postgres_connect_and_client_bodies(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return """
use crate::StoreError;
use tokio_postgres::{Client, NoTls};

#[derive(Debug, Clone)]
pub struct PostgresStore {
    database_url: String,
}

impl PostgresStore {
    pub fn new(database_url: impl Into<String>) -> Self {
        Self {
            database_url: database_url.into(),
        }
    }

    pub async fn connect(database_url: impl Into<String>) -> Result<Self, StoreError> {
        let store = Self::new(database_url);
        Ok(store)
    }

    pub async fn apply_schema(&self) -> Result<(), StoreError> {
        let _ = self;
        Ok(())
    }

    pub async fn applied_schema_migrations(&self) -> Result<Vec<(String, String)>, StoreError> {
        let _ = self;
        Ok(Vec::new())
    }

    pub(crate) async fn client(&self) -> Result<Client, StoreError> {
        let _ = (&self.database_url, NoTls);
        unimplemented!()
    }

    pub(crate) async fn rollback(client: &Client) {
        let _ = client;
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("pmx-store postgres adapter", str(ctx.exception))

    def test_v04_requires_idempotency_replay_test_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_tests/idempotency.rs"):
                return """
use super::*;

#[tokio::test]
async fn same_request_replay_is_persisted() {
    assert!(true);
}

#[tokio::test]
async fn fingerprint_mismatch_is_conflict() {
    let Some(store) = test_store().await else {
        return;
    };
    let account = unique("acct");
    let execution = unique("exec");
    seed_execution_plan(&store, &account, &execution).await;
    store
        .begin_submit_attempt(&account, &execution, "idem-1", "req-1")
        .await
        .expect("begin idempotency");
    let conflict = store
        .begin_submit_attempt(&account, &execution, "idem-1", "req-2")
        .await
        .expect("conflict result");
    assert_eq!(conflict, IdempotencyAction::Conflict);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("postgres idempotency tests", str(ctx.exception))

    def test_v04_requires_idempotency_begin_path_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_idempotency/begin.rs"):
                return """
use crate::postgres::PostgresStore;
use crate::postgres_support::map_db_error;
use crate::{IdempotencyAction, StoreError, advisory_lock_key};

pub(super) async fn begin_submit_attempt(
    store: &PostgresStore,
    account_id: &str,
    execution_id: &str,
    idempotency_key: &str,
    request_fingerprint: &str,
) -> Result<IdempotencyAction, StoreError> {
    let _ = (store, account_id, execution_id, idempotency_key, request_fingerprint);
    Ok(IdempotencyAction::Conflict)
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("postgres idempotency begin path", str(ctx.exception))

    def test_v04_requires_idempotency_impl_method_bodies(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_idempotency.rs"):
                return """
use async_trait::async_trait;

use crate::postgres::PostgresStore;
use crate::{FinishSubmitAttempt, IdempotencyAction, IdempotencyStore, StoreError};

#[async_trait]
impl IdempotencyStore for PostgresStore {
    async fn begin_submit_attempt(
        &self,
        account_id: &str,
        execution_id: &str,
        idempotency_key: &str,
        request_fingerprint: &str,
    ) -> Result<IdempotencyAction, StoreError> {
        let _ = (self, account_id, execution_id, idempotency_key, request_fingerprint);
        Ok(IdempotencyAction::Conflict)
    }

    async fn finish_submit_attempt(
        &self,
        attempt: FinishSubmitAttempt<'_>,
    ) -> Result<(), StoreError> {
        let _ = (self, attempt);
        Ok(())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v04_source_landings()
        self.assertIn("postgres idempotency adapter", str(ctx.exception))

    def test_v07_requires_gateway_traits_file_tokens(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/traits.rs"):
                return "pub trait SignerProvider\npub trait ClobGateway\npub trait RemoteReconcileReader"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("SignerProvider", str(ctx.exception))

    def test_v07_requires_gateway_trait_signature_bindings(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/traits.rs"):
                return """
use crate::{
    GatewayError, PlanOrder, PostOrderAck, RemoteOrder, RemoteReconcileReadReport,
    RemoteReconcileReadRequest,
};
use async_trait::async_trait;
use pmx_core::{AccountId, CancelState, RemoteOrderId, SignedOrderEnvelope};
use std::sync::Arc;

#[async_trait]
pub trait Signer: Send + Sync {
    async fn sign_order(&self, order: &PlanOrder) -> Result<SignedOrderEnvelope, GatewayError>;
}

#[async_trait]
pub trait ClobGateway: Send + Sync {
    async fn post_order(&self, order: &SignedOrderEnvelope) -> Result<PostOrderAck, GatewayError>;
    async fn cancel_order(
        &self,
        account_id: &AccountId,
        remote_order_id: &RemoteOrderId,
    ) -> Result<RemoteOrder, GatewayError>;
    async fn get_order(
        &self,
        account_id: &AccountId,
        remote_order_id: &RemoteOrderId,
    ) -> Result<Option<RemoteOrder>, GatewayError>;
    async fn get_open_orders(
        &self,
        account_id: &AccountId,
    ) -> Result<Vec<RemoteOrder>, GatewayError>;
}

#[async_trait]
pub trait RemoteReconcileReader: Send + Sync {
    async fn read_remote_order_observations(
        &self,
        request: &RemoteReconcileReadRequest,
    ) -> Result<RemoteReconcileReadReport, GatewayError>;
}

#[async_trait]
pub trait SignerProvider: Send + Sync {
    async fn signer_for_account(
        &self,
        account_id: &AccountId,
    ) -> Result<Arc<dyn Signer>, GatewayError>;
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway traits", str(ctx.exception))

    def test_v07_requires_sdk_spike_live_submit_default_test_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-spike/src/lib.rs"):
                return """
use serde::{Deserialize, Serialize};

pub const OFFICIAL_SDK_REPOSITORY: &str = "https://github.com/Polymarket/rs-clob-client-v2";
pub const OFFICIAL_SDK_CRATE: &str = "polymarket_client_sdk_v2";
pub const PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1";
pub const LIVE_SUBMIT_FEATURE_NAME: &str = "live-submit";
pub const CLOB_PRODUCTION_HOST: &str = "https://clob.polymarket.com";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub use_ws: bool,
    pub use_heartbeats: bool,
    pub allow_live_submit: bool,
    pub require_explicit_runtime_kill_switch_open: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.to_string(),
            use_ws: true,
            use_heartbeats: true,
            allow_live_submit: false,
            require_explicit_runtime_kill_switch_open: true,
        }
    }
}

#[cfg(feature = "sdk-typecheck")]
pub fn sdk_client_type_marker() -> &'static str {
    std::any::type_name::<polymarket_client_sdk_v2::clob::Client>()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(feature = "sdk-typecheck")]
    use polymarket_client_sdk_v2::Result as SdkResult;
    #[cfg(feature = "sdk-typecheck")]
    use std::time::Duration;
    #[cfg(feature = "sdk-typecheck")]
    use tokio::time;

    #[cfg(feature = "sdk-typecheck")]
    fn default_read_only_client() -> SdkResult<polymarket_client_sdk_v2::clob::Client> {
        polymarket_client_sdk_v2::clob::Client::new(
            CLOB_PRODUCTION_HOST,
            polymarket_client_sdk_v2::clob::Config::default(),
        )
    }

    #[test]
    fn live_submit_is_disabled_by_default() {
        let cfg = OfficialSdkAdapterConfig::default();
        assert!(cfg.allow_live_submit);
    }

    #[cfg(feature = "sdk-typecheck")]
    #[tokio::test]
    async fn read_only_ok_smoke() -> anyhow::Result<()> {
        let client = default_read_only_client()?;
        let status = time::timeout(Duration::from_secs(10), client.ok())
            .await
            .map_err(|_| anyhow::anyhow!("SDK read-only smoke timeout"))??;
        assert_eq!(status.to_uppercase(), "OK");
        let _ = time::timeout(Duration::from_secs(10), client.server_time())
            .await
            .map_err(|_| anyhow::anyhow!("SDK read-only smoke server time timeout"))??;
        Ok(())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("official SDK spike", str(ctx.exception))

    def test_v07_requires_gateway_post_cancel_test_bodies(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-gateway/src/tests/post_cancel.rs"):
                return """
use super::*;

#[tokio::test]
async fn deterministic_signer_provider_posts_reads_and_cancels() {
    assert!(true);
}

#[tokio::test]
async fn fake_gateway_cancel_maps_to_order_lifecycle_state_machine() {
    assert!(true);
}

#[tokio::test]
async fn fake_gateway_surfaces_remote_unknown_without_local_success() {
    let gateway = FakeGateway::new().with_post_failure(FakeGatewayFailure::RemoteUnknown(
        "timeout after signing".into(),
    ));
    let signed = DeterministicTestSigner
        .sign_order(&sample_order())
        .await
        .expect("signed");
    let err = gateway.post_order(&signed).await.expect_err("remote unknown");
    assert_eq!(
        err,
        GatewayError::RemoteUnknown("timeout after signing".into())
    );
}

#[tokio::test]
async fn fake_gateway_is_account_scoped() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("gateway post/cancel tests", str(ctx.exception))

    def test_v07_requires_http_scaffold_flow_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/tests/http_and_fake_e2e/scaffold.rs"):
                return """
use super::*;

#[path = "scaffold/admin_paths.rs"]
mod admin_paths;

#[path = "scaffold/compile_plan.rs"]
mod compile_plan;

#[path = "scaffold/public_queries.rs"]
mod public_queries;

#[path = "scaffold/submit_sign_only.rs"]
mod submit_sign_only;

#[tokio::test]
async fn full_scaffold_path_compile_submit_cancel_and_reconcile() {
    let _guard = env_lock().await;
    let store = pmx_store::InMemoryStore::default();
    let app = pmx_api::try_in_memory_app_with_store(store.clone()).expect("in-memory app");
    let (execution_id, plan_hash) = compile_plan::compile_blocked_plan(app.clone()).await;
    submit_sign_only::verify_submit_and_sign_only(app.clone(), &execution_id, &plan_hash).await;
    public_queries::verify_public_queries(app, &execution_id).await;
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("HTTP scaffold E2E", str(ctx.exception))

    def test_v07_requires_sdk_spike_read_only_smoke_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-spike/src/lib.rs"):
                return """
use serde::{Deserialize, Serialize};

pub const OFFICIAL_SDK_REPOSITORY: &str = "https://github.com/Polymarket/rs-clob-client-v2";
pub const OFFICIAL_SDK_CRATE: &str = "polymarket_client_sdk_v2";
pub const PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1";
pub const LIVE_SUBMIT_FEATURE_NAME: &str = "live-submit";
pub const CLOB_PRODUCTION_HOST: &str = "https://clob.polymarket.com";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub use_ws: bool,
    pub use_heartbeats: bool,
    pub allow_live_submit: bool,
    pub require_explicit_runtime_kill_switch_open: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.to_string(),
            use_ws: true,
            use_heartbeats: true,
            allow_live_submit: false,
            require_explicit_runtime_kill_switch_open: true,
        }
    }
}

#[cfg(feature = "sdk-typecheck")]
pub fn sdk_client_type_marker() -> &'static str {
    std::any::type_name::<polymarket_client_sdk_v2::clob::Client>()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(feature = "sdk-typecheck")]
    use polymarket_client_sdk_v2::Result as SdkResult;
    #[cfg(feature = "sdk-typecheck")]
    use std::time::Duration;
    #[cfg(feature = "sdk-typecheck")]
    use tokio::time;

    #[cfg(feature = "sdk-typecheck")]
    fn default_read_only_client() -> SdkResult<polymarket_client_sdk_v2::clob::Client> {
        polymarket_client_sdk_v2::clob::Client::new(
            CLOB_PRODUCTION_HOST,
            polymarket_client_sdk_v2::clob::Config::default(),
        )
    }

    #[test]
    fn live_submit_is_disabled_by_default() {
        let cfg = OfficialSdkAdapterConfig::default();
        assert!(!cfg.allow_live_submit);
        assert_eq!(cfg.clob_host, CLOB_PRODUCTION_HOST);
        assert!(cfg.require_explicit_runtime_kill_switch_open);
    }

    #[cfg(feature = "sdk-typecheck")]
    #[tokio::test]
    async fn read_only_ok_smoke() -> anyhow::Result<()> {
        Ok(())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v07_source_landings()
        self.assertIn("official SDK spike", str(ctx.exception))

    def test_v16_requires_runtime_worker_schema_ref(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/runtime/workers"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Wrong"
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("RuntimeWorkerStatusReport", str(ctx.exception))

    def test_v12_requires_service_binding_hash_inputs(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/binding/hash_inputs.rs"):
                return "pub(crate) struct PlanHashInput<'a>\napproval_id: &'a str\napproval_hash: &'a HashValue\nexecutor_version: &'a str"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("PlanHashInput", str(ctx.exception))

    def test_v12_requires_service_backend_variants(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/backend.rs"):
                return """
#[derive(Clone)]
pub enum ServiceBackend {
    InMemory(ExecutorService<InMemoryStore>),
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("ServiceBackend variants", str(ctx.exception))

    def test_v12_requires_blocked_submit_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/submit/blocked.rs"):
                return """
use super::*;

pub struct BlockedSubmitRequest<'a> {
    pub plan: &'a pmx_core::ExecutionPlanSummary,
}

pub async fn blocked_submit_outcome<S>(
    store: &S,
    req: BlockedSubmitRequest<'_>,
) -> Result<SubmitOutcome, ServiceError>
where
    S: ExecutionStore + IdempotencyStore + ExecutionLifecycleStore + Send + Sync,
{
    let _ = (store, req);
    Err(ServiceError::Conflict("nope".into()))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("blocked submit path", str(ctx.exception))

    def test_v12_requires_flow_test_bodies(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/service_tests/flow.rs"):
                return """
use super::*;

#[tokio::test]
async fn service_flow_persists_and_blocks_submit() { assert!(true); }

#[tokio::test]
async fn service_id_bound_flow_persists_and_blocks_submit() { assert!(true); }

#[tokio::test]
async fn service_rejects_object_graph_mismatch() { assert!(true); }

#[tokio::test]
async fn service_rejects_tampered_approval_hash() { assert!(true); }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("service flow tests", str(ctx.exception))

    def test_v12_requires_try_postgres_app_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/src/routes/bootstrap.rs"):
                return """
use super::*;
use axum::routing::{get, post};

fn router_with_state(state: AppState) -> Router {
    Router::new()
        .route("/v1/health", get(health))
        .route("/v1/plans/compile", post(flow::compile_plan))
        .route("/v1/submissions", post(flow::submit_plan))
        .route("/v1/admin/cancel-order", post(admin::record_cancel_order_non_live))
        .route("/v1/admin/reconcile", post(admin::record_reconcile_non_live))
        .with_state(state)
}

pub async fn try_postgres_app(
    database_url: impl Into<String>,
    apply_schema: bool,
) -> Result<Router, String> {
    let _ = (database_url.into(), apply_schema);
    Ok(router_with_state(AppState::default()))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("API bootstrap routes", str(ctx.exception))

    def test_v12_requires_postgres_e2e_main_bodies(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-api/tests/http_postgres_e2e/smoke.rs"):
                return """
use super::*;

#[tokio::test]
async fn http_postgres_backed_e2e_smoke() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v12_service_layer(spec)
        self.assertIn("PostgreSQL API E2E", str(ctx.exception))

    def test_v09_requires_feature_gated_adapter_tests(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/tests/feature_gated.rs"):
                return "authenticated_non_trading_smoke_executes_when_enabled\nsign_only_dry_run_executes_when_enabled"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v09_official_adapter_boundary()
        self.assertIn("official SDK feature-gated tests", str(ctx.exception))

    def test_v09_requires_structured_adapter_config_fields(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/model/config.rs"):
                return """
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub allow_read_only_smoke: bool,
    pub allow_authenticated_non_trading_smoke: bool,
    pub allow_sign_only_dry_run: bool,
    pub allow_live_submit: bool,
    pub allow_real_funds_canary: bool,
    pub require_kill_switch_open_for_live_submit: bool,
    pub require_reconcile_worker_for_live_submit: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: String::new(),
            allow_read_only_smoke: true,
            allow_authenticated_non_trading_smoke: false,
            allow_sign_only_dry_run: false,
            allow_live_submit: false,
            allow_real_funds_canary: false,
            require_kill_switch_open_for_live_submit: true,
            require_reconcile_worker_for_live_submit: true,
        }
    }
}

pub struct OfficialSdkStandardSignOnlyProfile {
    pub clob_host: String,
    pub collateral_symbol: String,
    pub signing_protocol: String,
    pub uses_deposit_wallet_order_path: bool,
    pub supports_builder_attribution: bool,
    pub supports_fee_metadata: bool,
    pub exposes_raw_signed_order: bool,
    pub may_post_order: bool,
    pub may_cancel_order: bool,
}
impl Default for OfficialSdkStandardSignOnlyProfile {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.into(),
            collateral_symbol: CLOB_V2_COLLATERAL_SYMBOL.into(),
            signing_protocol: CLOB_V2_SIGNING_PROTOCOL.into(),
            uses_deposit_wallet_order_path: true,
            supports_builder_attribution: true,
            supports_fee_metadata: true,
            exposes_raw_signed_order: false,
            may_post_order: false,
            may_cancel_order: false,
        }
    }
}
may_post_order: false
may_cancel_order: false
exposes_raw_signed_order: false
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v09_official_adapter_boundary()
        self.assertIn("OfficialSdkAdapterConfig fields", str(ctx.exception))

    def test_v09_requires_structured_standard_profile_default_semantics(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/model/config.rs"):
                return """
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OfficialSdkAdapterConfig {
    pub clob_host: String,
    pub allow_read_only_smoke: bool,
    pub allow_authenticated_non_trading_smoke: bool,
    pub allow_sign_only_dry_run: bool,
    pub allow_live_submit: bool,
    pub allow_real_funds_canary: bool,
    pub require_kill_switch_open_for_live_submit: bool,
    pub require_repository_reservation_for_live_submit: bool,
    pub require_reconcile_worker_for_live_submit: bool,
}

impl Default for OfficialSdkAdapterConfig {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.to_string(),
            allow_read_only_smoke: true,
            allow_authenticated_non_trading_smoke: false,
            allow_sign_only_dry_run: false,
            allow_live_submit: false,
            allow_real_funds_canary: false,
            require_kill_switch_open_for_live_submit: true,
            require_repository_reservation_for_live_submit: true,
            require_reconcile_worker_for_live_submit: true,
        }
    }
}

pub struct OfficialSdkStandardSignOnlyProfile {
    pub clob_host: String,
    pub collateral_symbol: String,
    pub signing_protocol: String,
    pub uses_deposit_wallet_order_path: bool,
    pub supports_builder_attribution: bool,
    pub supports_fee_metadata: bool,
    pub exposes_raw_signed_order: bool,
    pub may_post_order: bool,
    pub may_cancel_order: bool,
}

impl Default for OfficialSdkStandardSignOnlyProfile {
    fn default() -> Self {
        Self {
            clob_host: CLOB_PRODUCTION_HOST.into(),
            collateral_symbol: CLOB_V2_COLLATERAL_SYMBOL.into(),
            signing_protocol: CLOB_V2_SIGNING_PROTOCOL.into(),
            uses_deposit_wallet_order_path: true,
            supports_builder_attribution: true,
            supports_fee_metadata: true,
            exposes_raw_signed_order: true,
            may_post_order: false,
            may_cancel_order: false,
        }
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v09_official_adapter_boundary()
        self.assertIn("standard sign-only profile default", str(ctx.exception))

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
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("API admin audit support", str(ctx.exception))

    def test_v15_requires_backend_audit_async_method(self) -> None:
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
            if path.endswith("crates/pmx-api/src/backend/audit.rs"):
                return """
use pmx_service::ServiceError;
use pmx_store::{AdminAuditEvent, AdminAuditQuery};

impl ServiceBackend {
    pub(crate) async fn record_admin_audit_event(
        &self,
        event: AdminAuditEvent,
    ) -> Result<(), ServiceError> {
        match self {
            Self::InMemory(service) => service.record_admin_audit_event(event).await,
            Self::Postgres(service) => service.record_admin_audit_event(event).await,
        }
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("API admin audit backend", str(ctx.exception))

    def test_v15_requires_in_memory_audit_store_impl_methods(self) -> None:
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
            if path.endswith("crates/pmx-store/src/memory/audit.rs"):
                return """
use async_trait::async_trait;

#[async_trait]
impl AdminAuditStore for InMemoryStore {
    async fn record_admin_audit_event(&self, event: &AdminAuditEvent) -> Result<(), StoreError> {
        let stored = sanitize_admin_audit_event(event.clone());
        state.admin_audit.push(stored);
        Ok(())
    }

    async fn list_admin_audit_events(&self, _query: &AdminAuditQuery) -> Result<Vec<AdminAuditEvent>, StoreError> {
        Ok(Vec::new())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("in-memory admin audit store", str(ctx.exception))

    def test_v15_requires_postgres_audit_query_body_filters(self) -> None:
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
            if path.endswith("crates/pmx-store/src/postgres_audit/admin.rs"):
                return """
use async_trait::async_trait;

#[async_trait]
impl AdminAuditStore for PostgresStore {
    async fn record_admin_audit_event(&self, event: &AdminAuditEvent) -> Result<(), StoreError> {
        let client = self.client().await?;
        client.execute("INSERT INTO admin_audit_events", &[&event.correlation_id]).await.map_err(map_db_error)?;
        Ok(())
    }

    async fn list_admin_audit_events(&self, query: &AdminAuditQuery) -> Result<Vec<AdminAuditEvent>, StoreError> {
        let _ = query.bounded_limit();
        let rows = client.query("SELECT * FROM admin_audit_events", &[]).await.map_err(map_db_error)?;
        let _ = rows;
        Ok(Vec::new())
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("postgres admin audit store", str(ctx.exception))

    def test_v15_requires_health_body(self) -> None:
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
            if path.endswith("crates/pmx-api/src/routes/health.rs"):
                return """
use super::*;

pub(super) async fn health(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> ApiResult<serde_json::Value> {
    let _ = (state, headers);
    Ok((StatusCode::OK, Json(serde_json::json!({"status": "NOT_READY"}))))
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("API health route", str(ctx.exception))

    def test_v15_requires_postgres_admin_audit_e2e_body(self) -> None:
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
            if path.endswith("crates/pmx-api/tests/http_postgres_e2e/admin_audit.rs"):
                return """
use super::*;

#[tokio::test]
async fn http_postgres_admin_routes_record_audit_events() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("PostgreSQL API audit E2E", str(ctx.exception))

    def test_v16_requires_store_backed_runtime_provider_tokens(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/runtime_state/store_backed.rs"):
                return """
use super::*;

pub struct StoreBackedRuntimeStateProvider<S> {
    store: S,
    required_capabilities: Vec<String>,
}

impl<S> StoreBackedRuntimeStateProvider<S> {
    pub fn new(store: S) -> Self {
        Self { store, required_capabilities: Vec::new() }
    }

    pub fn with_required_capabilities(store: S, required_capabilities: Vec<String>) -> Self {
        Self { store, required_capabilities }
    }

    pub async fn load_canary_runtime_truth(
        &self,
        query: &pmx_store::CanaryRuntimeTruthQuery,
    ) -> Result<pmx_store::CanaryRuntimeTruthBindings, ServiceError>
    where
        S: pmx_store::CanaryRuntimeTruthStore,
    {
        self.store.load_canary_runtime_truth(query).await.map_err(ServiceError::Store)
    }
}

#[async_trait]
impl<S> RuntimeStateProvider for StoreBackedRuntimeStateProvider<S>
where
    S: RuntimeStateStore + Clone + Send + Sync + 'static,
{
    async fn capture_runtime_state(
        &self,
        normalized_intent: &NormalizedIntent,
    ) -> RuntimeStateSummary {
        let _ = normalized_intent;
        RuntimeStateSummary::default()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("service store-backed runtime provider", str(ctx.exception))

    def test_v16_requires_runtime_support_helper(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/memory/runtime/support.rs"):
                return """
impl InMemoryStore {
    pub fn set_runtime_state_for_test(
        &self,
        account_id: &str,
        condition_id: &str,
        collateral_profile_id: Option<&str>,
        runtime_state: RuntimeStateSummary,
    ) {
        let _ = (account_id, condition_id, collateral_profile_id, runtime_state);
    }

    pub(crate) fn observations_for_account(
        &self,
        account_id: &str,
    ) -> Vec<RuntimeWorkerObservation> {
        let _ = account_id;
        Vec::new()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("in-memory runtime support", str(ctx.exception))

    def test_v16_requires_postgres_runtime_state_impl_methods(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/postgres_runtime.rs"):
                return """
use async_trait::async_trait;

#[async_trait]
impl RuntimeStateStore for PostgresStore {
    async fn load_runtime_state(
        &self,
        query: &RuntimeStateQuery,
    ) -> Result<RuntimeStateSummary, StoreError> {
        let _ = query;
        Ok(RuntimeStateSummary::default())
    }
}

#[async_trait]
impl RuntimeControlStore for PostgresStore {
    async fn set_account_kill_switch(
        &self,
        account_id: &pmx_core::AccountId,
        enabled: bool,
        reason: &str,
    ) -> Result<KillSwitchStateChange, StoreError> {
        let _ = (account_id, enabled, reason);
        Ok(KillSwitchStateChange {
            scope: KillSwitchScope::Global,
            account_id: None,
            enabled: false,
            state_version: 1,
            effective_at: Utc::now(),
        })
    }

    async fn set_global_kill_switch(
        &self,
        enabled: bool,
        reason: &str,
    ) -> Result<KillSwitchStateChange, StoreError> {
        let _ = (enabled, reason);
        Ok(KillSwitchStateChange {
            scope: KillSwitchScope::Global,
            account_id: None,
            enabled: false,
            state_version: 1,
            effective_at: Utc::now(),
        })
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("postgres runtime state store", str(ctx.exception))

    def test_v16_requires_store_backed_capture_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/runtime_state/store_backed.rs"):
                return """
use super::*;

pub struct StoreBackedRuntimeStateProvider<S> {
    store: S,
    required_capabilities: Vec<String>,
}

impl<S> StoreBackedRuntimeStateProvider<S> {
    pub fn new(store: S) -> Self {
        Self { store, required_capabilities: Vec::new() }
    }

    pub fn with_required_capabilities(store: S, required_capabilities: Vec<String>) -> Self {
        Self { store, required_capabilities }
    }

    pub async fn load_canary_runtime_truth(
        &self,
        query: &pmx_store::CanaryRuntimeTruthQuery,
    ) -> Result<pmx_store::CanaryRuntimeTruthBindings, ServiceError>
    where
        S: pmx_store::CanaryRuntimeTruthStore,
    {
        self.store.load_canary_runtime_truth(query).await.map_err(ServiceError::Store)
    }
}

#[async_trait]
impl<S> RuntimeStateProvider for StoreBackedRuntimeStateProvider<S>
where
    S: RuntimeStateStore + Clone + Send + Sync + 'static,
{
    async fn capture_runtime_state(
        &self,
        normalized_intent: &NormalizedIntent,
    ) -> RuntimeStateSummary {
        let _ = normalized_intent;
        RuntimeStateSummary::default()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v16_postgres_runtime_provider(spec)
        self.assertIn("service store-backed runtime provider", str(ctx.exception))

    def test_v16_requires_store_backed_canary_truth_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-service/src/runtime_state/store_backed.rs"):
                return """
use super::*;

pub struct StoreBackedRuntimeStateProvider<S> {
    store: S,
    required_capabilities: Vec<String>,
}

impl<S> StoreBackedRuntimeStateProvider<S> {
    pub fn new(store: S) -> Self {
        Self { store, required_capabilities: Vec::new() }
    }

    pub fn with_required_capabilities(store: S, required_capabilities: Vec<String>) -> Self {
        Self { store, required_capabilities }
    }

    pub async fn load_canary_runtime_truth(
        &self,
        query: &pmx_store::CanaryRuntimeTruthQuery,
    ) -> Result<pmx_store::CanaryRuntimeTruthBindings, ServiceError>
    where
        S: pmx_store::CanaryRuntimeTruthStore,
    {
        let _ = query;
        Err(ServiceError::Invariant("wrong path".into()))
    }
}

#[async_trait]
impl<S> RuntimeStateProvider for StoreBackedRuntimeStateProvider<S>
where
    S: RuntimeStateStore + Clone + Send + Sync + 'static,
{
    async fn capture_runtime_state(
        &self,
        normalized_intent: &NormalizedIntent,
    ) -> RuntimeStateSummary {
        let _ = normalized_intent;
        RuntimeStateSummary::default()
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
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
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_v15_admin_audit_and_runtime_provider(spec)
        self.assertIn("v0.15 admin audit query must expose", str(ctx.exception))

    def test_validate_required_groups_reports_label(self) -> None:
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_required_groups({"demo group": ("only-one-token", ["missing-token"])})
        self.assertIn("demo group missing token: missing-token", str(ctx.exception))

    def test_v19_rejects_forbidden_public_contract_tokens_structurally(self) -> None:
        spec = self._minimal_v23_spec()
        spec["components"]["schemas"]["Leak"] = {"type": "object", "properties": {"danger": {"description": "signed_payload"}}}
        with self.assertRaises(ContractValidationError) as ctx:
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
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("ExecutionPlanSummary", str(ctx.exception))

    def test_v20_requires_plan_summaries_drop_statement(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/migrations/0001_initial.sql"):
                return """
CREATE TABLE IF NOT EXISTS execution_plans (
    execution_id TEXT PRIMARY KEY,
    plan_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    summary_json JSONB NOT NULL
);
-- plan_summaries intentionally removed. Use execution_plans.summary_json as canonical plan summary storage.
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("drop legacy plan_summaries table", str(ctx.exception))

    def test_v20_requires_summary_json_canonicalization_note(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/migrations/0001_initial.sql"):
                return """
DROP TABLE IF EXISTS plan_summaries;
CREATE TABLE IF NOT EXISTS execution_plans (
    execution_id TEXT PRIMARY KEY,
    plan_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    summary_json JSONB NOT NULL
);
-- legacy plan table removed
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("summary_json as canonical storage", str(ctx.exception))

    def test_v20_requires_mapping_validation_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/mapping/validation.rs"):
                return """
use crate::OfficialSdkAdapterError;
use pmx_core::{validate_limit_price_decimal_string, validate_positive_decimal_string};

pub(super) fn validate_token_id(raw: &str) -> Result<(), OfficialSdkAdapterError> {
    Ok(())
}

pub(super) fn validate_limit_price_for_sdk(raw: &str) -> Result<(), OfficialSdkAdapterError> {
    validate_limit_price_decimal_string(raw).map_err(|_| {
        OfficialSdkAdapterError::InvalidInput(format!(
            "invalid limit_price for official SDK order builder: {raw}"
        ))
    })
}

pub(super) fn validate_positive_quantity_for_sdk(
    raw: &str,
    field: &str,
) -> Result<(), OfficialSdkAdapterError> {
    validate_positive_decimal_string(raw).map_err(|_| {
        OfficialSdkAdapterError::InvalidInput(format!(
            "invalid {field} for official SDK order builder: {raw}"
        ))
    })
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 SDK mapping validation", str(ctx.exception))

    def test_v19_requires_redacted_constant(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/model/constants.rs"):
                return 'pub const OTHER: &str = "x";\n'
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("REDACTED", str(ctx.exception))

    def test_v19_requires_normalization_signature_and_kind_coverage(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/liveness/error_normalization.rs"):
                return """
use crate::{OfficialSdkErrorCategory, OfficialSdkNormalizedError};
use polymarket_client_sdk_v2::error::{Error as SdkError, Kind as SdkErrorKind};

pub fn normalize_sdk_error(error: SdkError) -> OfficialSdkNormalizedError {
    match error.kind() {
        SdkErrorKind::Validation => OfficialSdkNormalizedError {
            category: OfficialSdkErrorCategory::ValidationFailed,
            retryable: false,
            message: String::new(),
            http_status: None,
            geoblock_country: None,
            geoblock_region: None,
        },
        SdkErrorKind::Status => OfficialSdkNormalizedError {
            category: OfficialSdkErrorCategory::RemoteRejected,
            retryable: false,
            message: String::new(),
            http_status: None,
            geoblock_country: None,
            geoblock_region: None,
        },
        _ => OfficialSdkNormalizedError {
            category: OfficialSdkErrorCategory::Internal,
            retryable: true,
            message: String::new(),
            http_status: None,
            geoblock_country: None,
            geoblock_region: None,
        },
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("OfficialSdkNormalizedError", str(ctx.exception))

    def test_v19_requires_gateway_error_redaction_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/redaction.rs"):
                return """
use crate::{OfficialSdkErrorCategory, OfficialSdkNormalizedError};
use pmx_gateway::GatewayError;

pub fn gateway_error_from_normalized_sdk_error(
    normalized: &OfficialSdkNormalizedError,
) -> GatewayError {
    match normalized.category {
        OfficialSdkErrorCategory::AuthenticationFailed => GatewayError::AuthenticationFailed,
        _ => GatewayError::RemoteUnknown(normalized.message.clone()),
    }
}

pub fn redact_sensitive_text(input: &str) -> String {
    input.to_string()
}

pub fn redact_normalized_error(error: &OfficialSdkNormalizedError) -> OfficialSdkNormalizedError {
    error.clone()
}

fn looks_like_hex_private_key(_token: &str) -> bool { false }
fn redact_assignment_value(input: &str, _key: &str) -> String { input.to_string() }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("v0.19 adapter redaction", str(ctx.exception))

    def test_v19_requires_redact_sensitive_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/redaction.rs"):
                return """
use crate::{OfficialSdkErrorCategory, OfficialSdkNormalizedError};
use pmx_gateway::GatewayError;

pub fn gateway_error_from_normalized_sdk_error(
    normalized: &OfficialSdkNormalizedError,
) -> GatewayError {
    match normalized.category {
        OfficialSdkErrorCategory::AuthenticationFailed => GatewayError::AuthenticationFailed,
        OfficialSdkErrorCategory::ValidationFailed | OfficialSdkErrorCategory::RemoteRejected => GatewayError::RemoteRejected(redact_sensitive_text(&normalized.message)),
        _ => GatewayError::RemoteUnknown(redact_sensitive_text(&normalized.message)),
    }
}

pub fn redact_sensitive_text(input: &str) -> String {
    input.to_string()
}

pub fn redact_normalized_error(error: &OfficialSdkNormalizedError) -> OfficialSdkNormalizedError {
    error.clone()
}

fn looks_like_hex_private_key(_token: &str) -> bool { false }
fn redact_assignment_value(input: &str, _key: &str) -> String { input.to_string() }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("v0.19 adapter redaction", str(ctx.exception))

    def test_v19_requires_redact_normalized_error_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/redaction.rs"):
                return """
use crate::{OfficialSdkErrorCategory, OfficialSdkNormalizedError, REDACTED};
use pmx_gateway::GatewayError;

pub fn gateway_error_from_normalized_sdk_error(
    normalized: &OfficialSdkNormalizedError,
) -> GatewayError {
    match normalized.category {
        OfficialSdkErrorCategory::AuthenticationFailed => GatewayError::AuthenticationFailed,
        OfficialSdkErrorCategory::ValidationFailed | OfficialSdkErrorCategory::RemoteRejected => GatewayError::RemoteRejected(redact_sensitive_text(&normalized.message)),
        _ => GatewayError::RemoteUnknown(redact_sensitive_text(&normalized.message)),
    }
}

fn redact_assignment_value(input: &str, key: &str) -> String {
    let marker = format!("{key}=");
    let mut out = String::with_capacity(input.len());
    out.push_str(&marker);
    out.push_str(REDACTED);
    out.push_str(input);
    out
}

pub fn redact_sensitive_text(input: &str) -> String {
    let env_redacted = redact_known_env_values(input);
    env_redacted
        .split_whitespace()
        .map(|token| {
            if looks_like_hex_private_key(token) {
                "0x[REDACTED]".to_string()
            } else {
                token.to_string()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn redact_normalized_error(error: &OfficialSdkNormalizedError) -> OfficialSdkNormalizedError {
    error.clone()
}

fn looks_like_hex_private_key(_token: &str) -> bool { false }
fn redact_known_env_values(input: &str) -> String { input.to_string() }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("v0.19 adapter redaction", str(ctx.exception))

    def test_v19_requires_redact_assignment_value_body(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/redaction.rs"):
                return """
use crate::{OfficialSdkErrorCategory, OfficialSdkNormalizedError, REDACTED};
use pmx_gateway::GatewayError;

pub fn gateway_error_from_normalized_sdk_error(
    normalized: &OfficialSdkNormalizedError,
) -> GatewayError {
    match normalized.category {
        OfficialSdkErrorCategory::AuthenticationFailed => GatewayError::AuthenticationFailed,
        OfficialSdkErrorCategory::ValidationFailed | OfficialSdkErrorCategory::RemoteRejected => GatewayError::RemoteRejected(redact_sensitive_text(&normalized.message)),
        _ => GatewayError::RemoteUnknown(redact_sensitive_text(&normalized.message)),
    }
}

fn redact_assignment_value(input: &str, key: &str) -> String {
    let marker = format!("{key}=");
    let mut out = String::with_capacity(input.len());
    out.push_str(&marker);
    out.push_str(REDACTED);
    out.push_str(input);
    out
}

pub fn redact_sensitive_text(input: &str) -> String {
    let env_redacted = redact_known_env_values(input);
    env_redacted
        .split_whitespace()
        .map(|token| {
            if looks_like_hex_private_key(token) {
                "0x[REDACTED]".to_string()
            } else {
                token.to_string()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn redact_normalized_error(error: &OfficialSdkNormalizedError) -> OfficialSdkNormalizedError {
    let mut redacted = error.clone();
    redacted.message = redact_sensitive_text(&redacted.message);
    redacted
}

fn looks_like_hex_private_key(_token: &str) -> bool { false }
fn redact_known_env_values(input: &str) -> String { input.to_string() }
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("v0.19 adapter redaction", str(ctx.exception))

    def test_v19_requires_redaction_test_bodies(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/tests/liveness_errors.rs"):
                return """
use super::*;

#[test]
fn redacts_named_secret_assignments() {
    assert!(true);
}

#[test]
fn redacts_private_key_like_hex_tokens() {
    assert!(true);
}

#[test]
fn gateway_error_conversion_redacts_sensitive_message() {
    assert!(true);
}

#[test]
fn normalized_error_redaction_covers_remote_unknown_messages() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v19_redaction_and_live_guard(self._minimal_v23_spec())
        self.assertIn("v0.19 adapter redaction tests", str(ctx.exception))

    def test_v20_requires_reconcile_backlog_remote_unknown_field(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/health/signal/model.rs"):
                return """
pub enum RuntimeSignal {
    ReconcileBacklog {
        count: u32,
    },
    Geoblock {
        status: GeoblockStatus,
    },
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("remote_unknown_orders", str(ctx.exception))

    def test_v20_requires_runtime_breakdown_signature(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/health/signal/breakdown.rs"):
                return """
use super::RuntimeSignal;
use crate::RuntimeHealthBreakdown;

pub fn runtime_breakdown_from_signals(signals: &[RuntimeSignal]) -> Vec<RuntimeHealthBreakdown> {
    let _ = signals;
    Vec::new()
}
RuntimeSignal::Geoblock
RuntimeSignal::ReconcileBacklog
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("RuntimeHealthBreakdown", str(ctx.exception))

    def test_v20_requires_runtime_breakdown_body_mappings(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/health/signal/breakdown.rs"):
                return """
use super::RuntimeSignal;
use crate::RuntimeHealthBreakdown;

pub fn runtime_breakdown_from_signals(
    account_id: impl Into<String>,
    signals: &[RuntimeSignal],
) -> RuntimeHealthBreakdown {
    let _ = signals;
    RuntimeHealthBreakdown {
        account_id: account_id.into(),
        account_capabilities: Vec::new(),
        market_capabilities: Vec::new(),
        asset_capabilities: Vec::new(),
        worker_capabilities: Vec::new(),
    }
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 runtime breakdown", str(ctx.exception))

    def test_v20_requires_order_lifecycle_reconcile_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/lifecycle/order.rs"):
                return """
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderLifecycleState {
    CancelRequested,
    RemoteUnknown,
    PartialRemoteUnknown,
    Failed,
}

pub fn cancel_state_from_lifecycle(state: &OrderLifecycleState) -> crate::CancelState {
    match state {
        OrderLifecycleState::CancelRequested => crate::CancelState::Requested,
        OrderLifecycleState::Failed => crate::CancelState::NotCanceled,
        _ => crate::CancelState::ReconcileRequired,
    }
}

pub fn lifecycle_requires_reconcile(state: &OrderLifecycleState) -> bool {
    let _ = state;
    false
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 core order lifecycle", str(ctx.exception))

    def test_v20_requires_remote_unknown_liveness_test_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        spec.setdefault("components", {}).setdefault("schemas", {})["CompilePlanRequest"] = {
            "type": "object",
            "properties": {},
        }
        spec["components"]["schemas"]["ExecutionPlanSummary"] = {
            "type": "object",
            "properties": {},
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/tests/liveness_errors.rs"):
                return """
use super::*;

#[test]
fn normalized_error_redaction_covers_remote_unknown_messages() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 SDK liveness tests", str(ctx.exception))

    def test_v20_requires_runtime_blocking_test_body(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        spec.setdefault("components", {}).setdefault("schemas", {})["CompilePlanRequest"] = {
            "type": "object",
            "properties": {},
        }
        spec["components"]["schemas"]["ExecutionPlanSummary"] = {
            "type": "object",
            "properties": {},
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-runtime/src/runtime_tests/breakdown_loop/capabilities/blocking.rs"):
                return """
use super::super::super::*;

#[test]
fn geoblock_unknown_and_reconcile_backlog_block_submit() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 runtime evaluation tests", str(ctx.exception))

    def test_v20_requires_plan_storage_guard_structure(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        spec.setdefault("components", {}).setdefault("schemas", {})["CompilePlanRequest"] = {
            "type": "object",
            "properties": {},
        }
        spec["components"]["schemas"]["ExecutionPlanSummary"] = {
            "type": "object",
            "properties": {},
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("validation/check_plan_storage.py"):
                return """
#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "0001_initial.sql"
POSTGRES_ENTRYPOINT = ROOT / "crates" / "pmx-store" / "src" / "postgres.rs"
POSTGRES_EXECUTION = ROOT / "crates" / "pmx-store" / "src" / "postgres_execution"

def read_postgres_store_sources() -> str:
    paths = [POSTGRES_ENTRYPOINT]
    paths.extend([])
    return "\\n".join(path.read_text() for path in paths)

def main() -> int:
    failures: list[str] = []
    migration = MIGRATION.read_text()
    postgres = read_postgres_store_sources()
    if "DROP TABLE IF EXISTS plan_summaries" not in migration:
        failures.append("migration must explicitly remove legacy plan_summaries")
    if "CREATE TABLE IF NOT EXISTS plan_summaries" in migration:
        failures.append("migration must not recreate plan_summaries")
    if "INSERT INTO plan_summaries" in postgres or '"plan_summaries"' in postgres:
        failures.append("PostgresStore must not read/write plan_summaries")
    if "INSERT INTO execution_plans" not in postgres:
        failures.append("PostgresStore must write canonical execution_plans")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("plan storage guard passed: execution_plans is canonical")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 plan storage guard", str(ctx.exception))
        self.assertIn('paths.extend(sorted(POSTGRES_EXECUTION.rglob("*.rs")))', str(ctx.exception))

    def test_v20_requires_plan_storage_documentation_tokens(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        spec.setdefault("components", {}).setdefault("schemas", {})["CompilePlanRequest"] = {
            "type": "object",
            "properties": {},
        }
        spec["components"]["schemas"]["ExecutionPlanSummary"] = {
            "type": "object",
            "properties": {},
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("docs/PLAN_STORAGE_CANONICALIZATION.md"):
                return "# Plan storage canonicalization\n\nThis document is intentionally too thin.\n"
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 plan storage documentation", str(ctx.exception))

    def test_v20_requires_plan_storage_guard_to_run_before_manifest_refresh(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/plans/compile"] = {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CompilePlanRequest"}}}},
                "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionPlanSummary"}}}}},
            }
        }
        spec.setdefault("components", {}).setdefault("schemas", {})["CompilePlanRequest"] = {
            "type": "object",
            "properties": {},
        }
        spec["components"]["schemas"]["ExecutionPlanSummary"] = {
            "type": "object",
            "properties": {},
        }
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("validation/run_current_gates_impl.sh"):
                return """
python validation/check_live_submit_guard.py 2>&1 | tee "${EVIDENCE_DIR}/19-live-submit-static-guard.log"
python validation/check_sign_only_lifecycle.py 2>&1 | tee "${EVIDENCE_DIR}/20-sign-only-lifecycle-guard.log"
python validation/check_runtime_worker_models.py 2>&1 | tee "${EVIDENCE_DIR}/21-runtime-worker-model-guard.log"
python validation/write_current_evidence_manifest.py "${EVIDENCE_DIR}" >/dev/null
python validation/check_plan_storage.py 2>&1 | tee "${EVIDENCE_DIR}/18-plan-storage-guard.log"
python validation/check_current_evidence_manifest.py 2>&1 | tee "${EVIDENCE_DIR}/23-current-evidence-manifest-guard.log"
ARTIFACT_PATH="$(python "${INTEGRATION_ROOT}/scripts/package_release.py" "${VERSION}" --output-dir "${INTEGRATION_ROOT}/dist")"
python "${INTEGRATION_ROOT}/scripts/check_release_artifact.py" "${ARTIFACT_PATH}" "$(cat "${INTEGRATION_ROOT}/VERSION")"
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v20_plan_storage_and_packaging(spec)
        self.assertIn("v0.20 current gates implementation", str(ctx.exception))
        self.assertIn("missing ordered token", str(ctx.exception))

    def test_v23_requires_sign_only_equivalence_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-core/src/domain/lifecycle/sign_only.rs"):
                return """
use super::*;

pub struct SignOnlyLifecycleRecord {
    pub execution_id: String,
    pub account_id: String,
    pub state: String,
    pub event: String,
    pub client_event_id: Option<String>,
    pub signed_order_ref: Option<String>,
    pub no_remote_side_effect: bool,
    pub event_id: Option<i64>,
    pub created_at: Option<String>,
}

pub fn sign_only_lifecycle_records_equivalent(
    left: &SignOnlyLifecycleRecord,
    right: &SignOnlyLifecycleRecord,
) -> bool {
    left.execution_id == right.execution_id
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current sign-only replay equivalence helper", str(ctx.exception))

    def test_v23_requires_memory_runtime_worker_test_body(self) -> None:
        spec = self._minimal_v23_spec()
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/memory_tests/runtime_worker_health.rs"):
                return """
use super::*;

#[test]
async fn in_memory_worker_heartbeat_informs_runtime_state() {
    assert!(true);
}
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v23_lifecycle_query_and_hardening(spec)
        self.assertIn("current in-memory runtime worker tests", str(ctx.exception))

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
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("SignOnlyLifecycleRecord", str(ctx.exception))

    def test_v21_requires_lifecycle_adapter_function(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"]["get"]["responses"] = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                        }
                    }
                }
            }
        }
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/lifecycle.rs"):
                return """
use crate::{OfficialSdkAdapterError, SignOnlyDryRunReceipt};

pub fn some_other_helper(
    _receipt: &SignOnlyDryRunReceipt,
) -> Result<(), OfficialSdkAdapterError> {
    Ok(())
}
transition_sign_only_lifecycle
no_remote_side_effect: true
sign-only receipt unexpectedly indicates remote posting
signed_order_ref: Some(receipt.signed_order_ref.clone())
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("sign-only lifecycle adapter", str(ctx.exception))

    def test_v21_requires_lifecycle_adapter_signature(self) -> None:
        spec = self._minimal_v23_spec()
        spec["paths"]["/v1/sign-only/lifecycle-events"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"}
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/standard-constructions"] = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/StandardSignOnlyConstructionRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/StandardSignOnlyConstructionReceipt"
                                }
                            }
                        }
                    }
                },
            }
        }
        spec["paths"]["/v1/sign-only/lifecycle-events/{execution_id}"]["get"]["responses"] = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SignOnlyLifecycleRecord"},
                        }
                    }
                }
            }
        }
        spec["components"]["schemas"]["SignOnlyLifecycleRecord"] = {
            "type": "object",
            "required": [
                "execution_id",
                "account_id",
                "state",
                "event",
                "signed_order_ref",
                "no_remote_side_effect",
            ],
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
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("adapters/pmx-official-sdk-adapter/src/lifecycle.rs"):
                return """
use crate::{OfficialSdkAdapterError, SignOnlyDryRunReceipt};

pub fn sign_only_lifecycle_records_from_receipt(
    receipt: SignOnlyDryRunReceipt,
) -> Result<SignOnlyLifecycleRecord, OfficialSdkAdapterError> {
    let _ = receipt;
    Err(OfficialSdkAdapterError::validation("bad"))
}
transition_sign_only_lifecycle
no_remote_side_effect: true
sign-only receipt unexpectedly indicates remote posting
signed_order_ref: Some(receipt.signed_order_ref.clone())
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_v21_sign_only_and_runtime_models(spec)
        self.assertIn("OfficialSdkAdapterError", str(ctx.exception))

    def test_store_and_backend_structure_rejects_missing_postgres_export(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/lib.rs"):
                return (
                    "mod helpers;\nmod memory;\nmod model;\n"
                    "mod postgres_audit;\nmod postgres_execution;\nmod postgres_idempotency;\n"
                    "mod postgres_runtime;\nmod postgres_sign_only;\nmod postgres_worker;\n"
                )
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return (
                    "pub struct PostgresStore { database_url: String }\n"
                    "impl PostgresStore {\n"
                    "pub fn new(database_url: impl Into<String>) -> Self { Self { database_url: database_url.into() } }\n"
                    "pub async fn connect(database_url: impl Into<String>) -> Result<Self, StoreError> {\n"
                    "let store = Self::new(database_url);\n"
                    "let client = store.client().await?;\n"
                    "client.simple_query(\"SELECT 1\").await?;\n"
                    "Ok(store)\n"
                    "}\n"
                    "pub async fn apply_schema(&self) -> Result<(), StoreError> { Ok(()) }\n"
                    "pub async fn applied_schema_migrations(&self) -> Result<Vec<(String, String)>, StoreError> { Ok(Vec::new()) }\n"
                    "pub(crate) async fn client(&self) -> Result<Client, StoreError> {\n"
                    "tokio_postgres::connect(&self.database_url, NoTls).await?;\n"
                    "unimplemented!()\n"
                    "}\n"
                    "pub(crate) async fn rollback(client: &Client) { client.batch_execute(\"ROLLBACK\").await; }\n"
                    "}\n"
                )
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
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_store_and_backend_structure()
        self.assertIn("pmx-store module boundary missing token: pub mod postgres;", str(ctx.exception))

    def test_store_and_backend_structure_uses_backend_match_arm_structure(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/lib.rs"):
                return (
                    "mod helpers;\nmod memory;\nmod model;\npub mod postgres;\n"
                    "mod postgres_audit;\nmod postgres_execution;\nmod postgres_idempotency;\n"
                    "mod postgres_runtime;\nmod postgres_sign_only;\nmod postgres_worker;\n"
                    "pub use postgres::PostgresStore;\n"
                )
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return (
                    "pub struct PostgresStore { database_url: String }\n"
                    "impl PostgresStore {\n"
                    "pub fn new(database_url: impl Into<String>) -> Self { Self { database_url: database_url.into() } }\n"
                    "pub async fn connect(database_url: impl Into<String>) -> Result<Self, StoreError> {\n"
                    "let store = Self::new(database_url);\n"
                    "let client = store.client().await?;\n"
                    "client.simple_query(\"SELECT 1\").await?;\n"
                    "Ok(store)\n"
                    "}\n"
                    "pub async fn apply_schema(&self) -> Result<(), StoreError> { Ok(()) }\n"
                    "pub async fn applied_schema_migrations(&self) -> Result<Vec<(String, String)>, StoreError> { Ok(Vec::new()) }\n"
                    "pub(crate) async fn client(&self) -> Result<Client, StoreError> {\n"
                    "tokio_postgres::connect(&self.database_url, NoTls).await?;\n"
                    "unimplemented!()\n"
                    "}\n"
                    "pub(crate) async fn rollback(client: &Client) { client.batch_execute(\"ROLLBACK\").await; }\n"
                    "}\n"
                )
            if path.endswith("crates/pmx-service/src/lib.rs"):
                return (
                    "mod runtime_state;\nmod runtime_worker;\nmod sign_only;\nmod submit;\n"
                    "pub use runtime_state::*;\npub use runtime_worker::*;\npub use sign_only::*;\npub use submit::*;\n"
                )
            if path.endswith("crates/pmx-api/src/backend/audit.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_admin_audit_event(&self, event: AdminAuditEvent) -> Result<(), ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_admin_audit_event(event).await,\n"
                    "Self::Postgres(service) => service.record_admin_audit_event(event).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn list_admin_audit_events(&self, query: AdminAuditQuery) -> Result<Vec<AdminAuditEvent>, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_admin_audit_events(query).await,\n"
                    "Self::Postgres(service) => service.list_admin_audit_events(query).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/sign_only.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_standard_sign_only_construction(&self, req: StandardSignOnlyConstructionRequest) -> Result<StandardSignOnlyConstructionReceipt, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "Self::Postgres(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn list_sign_only_lifecycle_events(&self, query: SignOnlyLifecycleQuery) -> Result<Vec<SignOnlyLifecycleRecord>, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "Self::Postgres(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/runtime.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn list_runtime_worker_status(&self, query: RuntimeWorkerStatusQuery) -> Result<RuntimeWorkerStatusReport, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_runtime_worker_status(query).await,\n"
                    "Self::Postgres(service) => service.list_runtime_worker_status(query).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn set_account_kill_switch(&self, account_id: &pmx_core::AccountId, enabled: bool, reason: &str) -> Result<KillSwitchStateChange, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.store().set_account_kill_switch(account_id, enabled, reason).await,\n"
                    "Self::Postgres(service) => service.store().set_account_kill_switch(account_id, enabled, reason).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn set_global_kill_switch(&self, enabled: bool, reason: &str) -> Result<KillSwitchStateChange, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.store().set_global_kill_switch(enabled, reason).await,\n"
                    "Self::Postgres(service) => service.store().set_global_kill_switch(enabled, reason).await,\n"
                    "}\n}\n}\n"
                )
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            module.validate_store_and_backend_structure()

    def test_store_and_backend_structure_requires_runtime_backend_async_methods(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/lib.rs"):
                return (
                    "mod helpers;\nmod memory;\nmod model;\npub mod postgres;\n"
                    "mod postgres_audit;\nmod postgres_execution;\nmod postgres_idempotency;\n"
                    "mod postgres_runtime;\nmod postgres_sign_only;\nmod postgres_worker;\n"
                    "pub use postgres::PostgresStore;\n"
                )
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return (
                    "pub struct PostgresStore { database_url: String }\n"
                    "impl PostgresStore {\n"
                    "pub fn new(database_url: impl Into<String>) -> Self { Self { database_url: database_url.into() } }\n"
                    "pub async fn connect(database_url: impl Into<String>) -> Result<Self, StoreError> {\n"
                    "let store = Self::new(database_url);\n"
                    "let client = store.client().await?;\n"
                    "client.simple_query(\"SELECT 1\").await?;\n"
                    "Ok(store)\n"
                    "}\n"
                    "pub async fn apply_schema(&self) -> Result<(), StoreError> { Ok(()) }\n"
                    "pub async fn applied_schema_migrations(&self) -> Result<Vec<(String, String)>, StoreError> { Ok(Vec::new()) }\n"
                    "pub(crate) async fn client(&self) -> Result<Client, StoreError> {\n"
                    "tokio_postgres::connect(&self.database_url, NoTls).await?;\n"
                    "unimplemented!()\n"
                    "}\n"
                    "pub(crate) async fn rollback(client: &Client) { client.batch_execute(\"ROLLBACK\").await; }\n"
                    "}\n"
                )
            if path.endswith("crates/pmx-service/src/lib.rs"):
                return (
                    "mod runtime_state;\nmod runtime_worker;\nmod sign_only;\nmod submit;\n"
                    "pub use runtime_state::*;\npub use runtime_worker::*;\npub use sign_only::*;\npub use submit::*;\n"
                )
            if path.endswith("crates/pmx-api/src/backend/audit.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_admin_audit_event(&self, event: AdminAuditEvent) -> Result<(), ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_admin_audit_event(event).await,\n"
                    "Self::Postgres(service) => service.record_admin_audit_event(event).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn list_admin_audit_events(&self, query: AdminAuditQuery) -> Result<Vec<AdminAuditEvent>, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_admin_audit_events(query).await,\n"
                    "Self::Postgres(service) => service.list_admin_audit_events(query).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/sign_only.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_standard_sign_only_construction(&self, req: StandardSignOnlyConstructionRequest) -> Result<StandardSignOnlyConstructionReceipt, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "Self::Postgres(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn list_sign_only_lifecycle_events(&self, query: SignOnlyLifecycleQuery) -> Result<Vec<SignOnlyLifecycleRecord>, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "Self::Postgres(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/runtime.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn list_runtime_worker_status(&self, query: RuntimeWorkerStatusQuery) -> Result<RuntimeWorkerStatusReport, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_runtime_worker_status(query).await,\n"
                    "Self::Postgres(service) => service.list_runtime_worker_status(query).await,\n"
                    "}\n}\n"
                )
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_store_and_backend_structure()
        self.assertIn("runtime backend bridge missing ServiceBackend impl methods", str(ctx.exception))

    def test_store_and_backend_structure_requires_audit_backend_impl_methods(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("crates/pmx-store/src/lib.rs"):
                return (
                    "mod helpers;\nmod memory;\nmod model;\npub mod postgres;\n"
                    "mod postgres_audit;\nmod postgres_execution;\nmod postgres_idempotency;\n"
                    "mod postgres_runtime;\nmod postgres_sign_only;\nmod postgres_worker;\n"
                    "pub use postgres::PostgresStore;\n"
                )
            if path.endswith("crates/pmx-store/src/postgres.rs"):
                return (
                    "pub struct PostgresStore { database_url: String }\n"
                    "impl PostgresStore {\n"
                    "pub fn new(database_url: impl Into<String>) -> Self { Self { database_url: database_url.into() } }\n"
                    "pub async fn connect(database_url: impl Into<String>) -> Result<Self, StoreError> {\n"
                    "let store = Self::new(database_url);\n"
                    "let client = store.client().await?;\n"
                    "client.simple_query(\"SELECT 1\").await?;\n"
                    "Ok(store)\n"
                    "}\n"
                    "pub async fn apply_schema(&self) -> Result<(), StoreError> { Ok(()) }\n"
                    "pub async fn applied_schema_migrations(&self) -> Result<Vec<(String, String)>, StoreError> { Ok(Vec::new()) }\n"
                    "pub(crate) async fn client(&self) -> Result<Client, StoreError> {\n"
                    "tokio_postgres::connect(&self.database_url, NoTls).await?;\n"
                    "unimplemented!()\n"
                    "}\n"
                    "pub(crate) async fn rollback(client: &Client) { client.batch_execute(\"ROLLBACK\").await; }\n"
                    "}\n"
                )
            if path.endswith("crates/pmx-service/src/lib.rs"):
                return (
                    "mod runtime_state;\nmod runtime_worker;\nmod sign_only;\nmod submit;\n"
                    "pub use runtime_state::*;\npub use runtime_worker::*;\npub use sign_only::*;\npub use submit::*;\n"
                )
            if path.endswith("crates/pmx-api/src/backend/audit.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_admin_audit_event(&self, event: AdminAuditEvent) -> Result<(), ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_admin_audit_event(event).await,\n"
                    "Self::Postgres(service) => service.record_admin_audit_event(event).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/sign_only.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn record_standard_sign_only_construction(&self, req: StandardSignOnlyConstructionRequest) -> Result<StandardSignOnlyConstructionReceipt, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "Self::Postgres(service) => service.record_standard_sign_only_construction(req).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn list_sign_only_lifecycle_events(&self, query: SignOnlyLifecycleQuery) -> Result<Vec<SignOnlyLifecycleRecord>, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "Self::Postgres(service) => service.list_sign_only_lifecycle_events(query).await,\n"
                    "}\n}\n}\n"
                )
            if path.endswith("crates/pmx-api/src/backend/runtime.rs"):
                return (
                    "impl ServiceBackend {\n"
                    "pub(crate) async fn list_runtime_worker_status(&self, query: RuntimeWorkerStatusQuery) -> Result<RuntimeWorkerStatusReport, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.list_runtime_worker_status(query).await,\n"
                    "Self::Postgres(service) => service.list_runtime_worker_status(query).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn set_account_kill_switch(&self, account_id: &pmx_core::AccountId, enabled: bool, reason: &str) -> Result<KillSwitchStateChange, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.store().set_account_kill_switch(account_id, enabled, reason).await,\n"
                    "Self::Postgres(service) => service.store().set_account_kill_switch(account_id, enabled, reason).await,\n"
                    "}\n}\n"
                    "pub(crate) async fn set_global_kill_switch(&self, enabled: bool, reason: &str) -> Result<KillSwitchStateChange, ServiceError> {\n"
                    "match self {\n"
                    "Self::InMemory(service) => service.store().set_global_kill_switch(enabled, reason).await,\n"
                    "Self::Postgres(service) => service.store().set_global_kill_switch(enabled, reason).await,\n"
                    "}\n}\n}\n"
                )
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_store_and_backend_structure()
        self.assertIn("audit backend bridge missing ServiceBackend impl methods", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
