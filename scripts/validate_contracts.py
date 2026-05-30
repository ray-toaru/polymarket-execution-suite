#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import json
import re

import yaml

from validate_contracts_governance import (
    validate_canary_candidate_market_prep_boundary,
    validate_controlled_canary_release_decision_governance,
    validate_current_docs_and_release_governance,
    validate_current_evidence_manifest_guard,
    validate_current_hermes_client_surface,
    validate_single_host_deployment_governance,
    validate_v28_production_live_candidate_guard,
)
from validate_contracts_support import (
    API_E2E_TEST,
    API_POSTGRES_E2E_TEST,
    API_SRC,
    CONTROL,
    CORE_SRC,
    EXECUTOR,
    EXPECTED_202_PATHS,
    FORBIDDEN_PUBLIC_TOKENS,
    GATEWAY_SRC,
    LIVE_SUBMIT_GUARD,
    OPENAPI,
    POSTGRES_RS,
    PY_MODEL_BY_SCHEMA,
    ROOT,
    ROOT_CARGO_TOML,
    SDK_ADAPTER_RS,
    SDK_ADAPTER_SRC,
    SDK_ADAPTER_TOML,
    SDK_SPIKE_RS,
    SDK_SPIKE_TOML,
    SERVICE_RS,
    SERVICE_SRC,
    SERVICE_TOML,
    SQL,
    STORE_RS,
    STORE_SRC,
    fail,
    import_control_models,
    rust_file_with_modules_text,
    rust_handler_body,
    rust_routes,
    rust_source_text,
)


def validate_paths_and_statuses(spec: dict) -> None:
    openapi_paths = set(spec["paths"].keys())
    routes = rust_routes()
    missing = openapi_paths - routes
    extra = routes - openapi_paths
    if missing:
        fail(f"Rust routes missing OpenAPI paths: {sorted(missing)}")
    if extra:
        fail(f"Rust routes not present in OpenAPI: {sorted(extra)}")
    for path, handler in EXPECTED_202_PATHS.items():
        statuses = set(spec["paths"][path][next(iter(spec["paths"][path]))]["responses"].keys())
        if "202" not in statuses:
            fail(f"OpenAPI path {path} does not declare 202")
        body = rust_handler_body(handler)
        if "StatusCode::ACCEPTED" not in body:
            fail(f"handler {handler} does not visibly return StatusCode::ACCEPTED")


def validate_no_public_forbidden_tokens() -> None:
    public_text = OPENAPI.read_text() + "\n" + (CONTROL / "src").read_text() if False else OPENAPI.read_text()
    for token in FORBIDDEN_PUBLIC_TOKENS:
        if token in public_text:
            fail(f"forbidden token in public OpenAPI: {token}")
    for py in (CONTROL / "src").rglob("*.py"):
        text = py.read_text()
        for token in FORBIDDEN_PUBLIC_TOKENS:
            if token in text:
                fail(f"forbidden token {token} in control package {py.relative_to(ROOT)}")


def validate_additional_properties(spec: dict) -> None:
    for name, schema in spec["components"]["schemas"].items():
        if schema.get("type") == "object" and name != "HealthReport":
            if schema.get("additionalProperties") is not False:
                fail(f"schema {name} must set additionalProperties: false")
        if name == "HealthReport" and schema.get("additionalProperties") is not False:
            fail("HealthReport must set additionalProperties: false at top level")


def validate_python_field_parity(spec: dict) -> None:
    models = import_control_models()
    for schema_name, model_name in PY_MODEL_BY_SCHEMA.items():
        schema = spec["components"]["schemas"][schema_name]
        props = set(schema.get("properties", {}).keys())
        py_model = getattr(models, model_name)
        py_fields = set(py_model.model_fields.keys())
        if props != py_fields:
            fail(f"Python model {model_name} fields {sorted(py_fields)} != OpenAPI {schema_name} fields {sorted(props)}")


def validate_sql_idempotency() -> None:
    sql = SQL.read_text()
    if "idempotency_key TEXT PRIMARY KEY" in sql:
        fail("idempotency_key must not be a global primary key")
    required = [
        "UNIQUE(account_id, execution_id, idempotency_key)",
        "request_fingerprint TEXT NOT NULL",
        "submit_attempt INTEGER NOT NULL CHECK (submit_attempt >= 1)",
    ]
    for needle in required:
        if needle not in sql:
            fail(f"SQL missing idempotency invariant: {needle}")


def validate_rust_deny_unknown_fields() -> None:
    text = rust_source_text(API_SRC) + "\n" + rust_source_text(CORE_SRC)
    for struct_name in [
        "TradeIntent", "NormalizedIntent", "DecisionRequest", "CompilePlanRequest",
        "SubmitPlanRequest", "CancelOrderRequest", "KillSwitchRequest", "ReconcileRequest",
        "ReconcileOrderLocalRequest",
    ]:
        pattern = rf"#\[serde\(deny_unknown_fields\)\]\s*pub struct {struct_name}"
        if not re.search(pattern, text):
            fail(f"Rust DTO {struct_name} missing #[serde(deny_unknown_fields)]")



def validate_v04_source_landings() -> None:
    if not API_E2E_TEST.exists():
        fail("missing HTTP/auth/fake E2E integration test source")
    test_text = rust_file_with_modules_text(API_E2E_TEST)
    for needle in ["http_auth_and_fake_e2e_smoke", "StatusCode::UNAUTHORIZED", "StatusCode::FORBIDDEN", "StatusCode::ACCEPTED"]:
        if needle not in test_text:
            fail(f"HTTP/auth/fake E2E test missing expected assertion token: {needle}")
    store_text = rust_source_text(STORE_SRC)
    for needle in ["pub struct AdvisoryLockKey", "pub fn advisory_lock_key"]:
        if needle not in store_text:
            fail(f"pmx-store missing advisory lock helper evidence: {needle}")
    if not POSTGRES_RS.exists():
        fail("missing PostgreSQL repository adapter source")
    postgres_text = rust_source_text(STORE_SRC)
    for needle in [
        "pub struct PostgresStore",
        "impl IdempotencyStore for PostgresStore",
        "pg_advisory_xact_lock",
        "same_request_replay_is_persisted",
        "fingerprint_mismatch_is_conflict",
        "reservation_double_spend_is_prevented_concurrently",
        "remote_unknown_is_persisted_conservatively",
    ]:
        if needle not in postgres_text:
            fail(f"PostgreSQL adapter missing expected repository proof token: {needle}")


def validate_v07_source_landings() -> None:
    gateway_text = rust_source_text(GATEWAY_SRC)
    for needle in [
        "pub trait SignerProvider",
        "pub struct DisabledSignerProvider",
        "pub struct DeterministicTestSignerProvider",
        "signer_provider_defaults_are_production_conservative",
        "fake_gateway_surfaces_remote_unknown_without_local_success",
    ]:
        if needle not in gateway_text:
            fail(f"v0.7 gateway landing missing token: {needle}")
    e2e_text = rust_file_with_modules_text(API_E2E_TEST)
    for needle in [
        "full_scaffold_path_compile_submit_cancel_and_reconcile",
        "/v1/plans/compile",
        "/v1/submissions",
        "/v1/admin/cancel-order",
        "/v1/admin/reconcile",
    ]:
        if needle not in e2e_text:
            fail(f"v0.7 API E2E landing missing token: {needle}")
    sdk_text = SDK_SPIKE_RS.read_text()
    for needle in [
        "OFFICIAL_SDK_REPOSITORY",
        "PINNED_OFFICIAL_SDK_VERSION",
        "LIVE_SUBMIT_FEATURE_NAME",
        "allow_live_submit: false",
        "require_explicit_runtime_kill_switch_open: true",
        "sdk_client_type_marker",
    ]:
        if needle not in sdk_text:
            fail(f"v0.7 SDK spike landing missing token: {needle}")

def validate_v08_dependency_and_sdk_policy() -> None:
    cargo_text = ROOT_CARGO_TOML.read_text()
    for needle in [
        'edition = "2024"',
        'rust-version = "1.88"',
        f'version = "{(ROOT / "VERSION").read_text().strip()}"',
        'tokio = { version = "1.52.3"',
        'serde = { version = "1.0.228"',
    ]:
        if needle not in cargo_text:
            fail(f"v0.13 Cargo baseline missing token: {needle}")

    sdk_text = SDK_SPIKE_RS.read_text()
    sdk_toml = SDK_SPIKE_TOML.read_text()
    for needle in [
        'PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1"',
        'read_only_ok_smoke',
        'default_read_only_client',
        'polymarket_client_sdk_v2::clob::Client::new',
        'client.server_time()',
    ]:
        if needle not in sdk_text:
            fail(f"v0.11 SDK read-only smoke missing token: {needle}")

    if 'use std::time::Duration;' in sdk_text and '#[cfg(feature = "sdk-typecheck")]\n    use std::time::Duration;' not in sdk_text:
        fail("Duration import must be cfg-gated to avoid no-feature warning")

    if 'polymarket_client_sdk_v2 = { version = "=0.6.0-canary.1"' not in sdk_toml:
        fail("official SDK dependency must remain explicitly pinned in spike")

    for doc in [
        ROOT / "DEPENDENCY_POLICY.md",
        EXECUTOR / "docs/SDK_FIRST_ADAPTER_PLAN.md",
        EXECUTOR / "rust-toolchain.toml",
        ROOT / ".github/dependabot.yml",
        ROOT / ".github/workflows/ci.yml",
    ]:
        if not doc.exists():
            fail(f"v0.11 missing dependency/CI artifact: {doc.relative_to(ROOT)}")



def validate_v09_official_adapter_boundary() -> None:
    if not SDK_ADAPTER_RS.exists():
        fail("missing official SDK adapter boundary crate source")
    if not SDK_ADAPTER_TOML.exists():
        fail("missing official SDK adapter boundary Cargo.toml")
    adapter_text = rust_source_text(SDK_ADAPTER_SRC)
    adapter_toml = SDK_ADAPTER_TOML.read_text()
    required_tokens = [
        "OfficialSdkAdapterConfig",
        "AdapterCredentialSnapshot",
        "SignOnlyDryRunRequest",
        "SignOnlyDryRunReceipt",
        "validate_authenticated_non_trading_smoke",
        "validate_sign_only_dry_run",
        "validate_live_submit_preconditions",
        "PMX_RUN_AUTHENTICATED_NON_TRADING_SMOKE",
        "PMX_ALLOW_SIGN_ONLY_DRY_RUN",
        "PMX_ALLOW_LIVE_SUBMIT",
        "posted: bool",
    ]
    for needle in required_tokens:
        if needle not in adapter_text:
            fail(f"v0.11 official adapter boundary missing token: {needle}")
    if 'polymarket_client_sdk_v2 = { version = "=0.6.0-canary.1"' not in adapter_toml:
        fail("official adapter must pin the official SDK canary explicitly")
    if not re.search(r'(?m)^live-submit\s*=\s*\[', adapter_toml):
        fail("official adapter must expose an explicit live-submit feature gate")
    live_canary = SDK_ADAPTER_SRC / "sdk_runtime/live_canary.rs"
    gateway_bridge = SDK_ADAPTER_SRC / "sdk_runtime/gateway.rs"
    adapter_boundary_text = adapter_text
    for allowed_post_order_file in [live_canary, gateway_bridge]:
        if allowed_post_order_file.exists():
            adapter_boundary_text = adapter_boundary_text.replace(allowed_post_order_file.read_text(), "")
    if 'post_order(' in adapter_boundary_text or 'post_orders(' in adapter_text:
        fail("official adapter boundary must not call post_order/post_orders outside guarded canary/gateway bridge paths")
    if gateway_bridge.exists():
        gateway_text = gateway_bridge.read_text()
        for needle in [
            "allow_live_submit",
            "OfficialSdkGateway",
            "official-sdk-signed:",
            "signed_payload_ref",
            "SignedOrderEnvelope",
            "redact_sensitive_text",
        ]:
            if needle not in gateway_text:
                fail(f"official SDK gateway bridge missing boundary token: {needle}")
    if 'allow_live_submit: false' not in adapter_text:
        fail("official adapter default must keep live submit disabled")
    for doc in [
        EXECUTOR / "docs/AUTHENTICATED_NON_TRADING_SMOKE.md",
        EXECUTOR / "docs/SIGN_ONLY_DRY_RUN.md",
        EXECUTOR / "docs/OFFICIAL_SDK_ADAPTER_BOUNDARY.md",
        ROOT / "NO_LOCAL_ACTIONS_REMAINING.md",
        EXECUTOR / "validation/run_current_gates.sh",
    ]:
        if not doc.exists():
            fail(f"v0.11 missing continuation artifact: {doc.relative_to(ROOT)}")


def validate_v12_service_layer() -> None:
    if not SERVICE_RS.exists():
        fail("missing pmx-service crate source")
    if not SERVICE_TOML.exists():
        fail("missing pmx-service Cargo.toml")
    service_text = rust_source_text(SERVICE_SRC)
    api_text = rust_source_text(API_SRC)
    root_toml = ROOT_CARGO_TOML.read_text()
    for needle in [
        '"crates/pmx-service"',
        'name = "pmx-service"',
        'pub struct ExecutorService',
        'pub trait RuntimeStateProvider',
        'pub enum SubmitOutcome',
        'IdempotencyAction::InProgress',
        'verify_decision_binding',
        'DecisionByIdRequest',
        'CompilePlanByIdCommand',
        'evaluate_decision_by_id',
        'compile_plan_by_id',
        'ApprovalHashInput',
        'approval_receipt_hash',
        'approval_hash does not match canonical approval receipt',
        'service_id_bound_flow_persists_and_blocks_submit',
        'service_flow_persists_and_blocks_submit',
        'service_rejects_object_graph_mismatch',
        'service_rejects_tampered_approval_hash',
    ]:
        combined = root_toml + "\n" + SERVICE_TOML.read_text() + "\n" + service_text
        if needle not in combined:
            fail(f"service layer contract missing token: {needle}")
    blocked_submit = (SERVICE_SRC / "submit/blocked.rs").read_text()
    for needle in [
        '"SUBMIT_BLOCKED_BEFORE_REMOTE"',
        '"no_remote_side_effect": true',
        '"reservation_written": false',
    ]:
        if needle not in blocked_submit:
            fail(f"blocked submit path missing non-live boundary token: {needle}")
    if "save_order_reservation" in blocked_submit:
        fail("blocked submit path must not persist reservations")
    for needle in [
        'pub enum ServiceBackend',
        'ServiceBackend::InMemory',
        'ServiceBackend::Postgres',
        'try_postgres_app',
        'service.normalize(',
        'service.capture_snapshot(',
        'service.evaluate_decision_by_id(',
        'service.compile_plan_by_id(',
        'service.submit_plan(',
        'SubmitOutcome::Accepted',
    ]:
        if needle not in api_text:
            fail(f"API handler not wired through pmx-service: {needle}")
    if 'pub fn fake_snapshot' in api_text:
        fail("pmx-api must not keep fake_snapshot helper after pmx-service extraction")

    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")
    if not API_POSTGRES_E2E_TEST.exists():
        fail("missing HTTP PostgreSQL E2E test source")
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    for needle in [
        'http_postgres_backed_e2e_smoke',
        'http_postgres_rejects_cross_object_graph_and_bad_plan_hash',
        'PMX_TEST_DATABASE_URL',
        'try_postgres_app',
        '"database"], "postgres"',
        'StatusCode::ACCEPTED',
        'StatusCode::OK',
    ]:
        if needle not in pg_test_text:
            fail(f"PostgreSQL API E2E missing token: {needle}")



def validate_v15_admin_audit_and_runtime_provider() -> None:
    service_text = rust_source_text(SERVICE_SRC)
    store_text = rust_source_text(STORE_SRC)
    postgres_text = rust_source_text(STORE_SRC)
    api_text = rust_source_text(API_SRC)
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    for needle in [
        "pub struct AdminAuditEvent",
        "pub trait AdminAuditStore",
        "impl AdminAuditStore for InMemoryStore",
        "admin_audit: Vec<AdminAuditEvent>",
    ]:
        if needle not in store_text:
            fail(f"store admin audit missing token: {needle}")
    for needle in [
        "impl AdminAuditStore for PostgresStore",
        "INSERT INTO admin_audit_events",
        "postgres_records_admin_audit_event",
    ]:
        if needle not in postgres_text:
            fail(f"postgres admin audit missing token: {needle}")
    for needle in [
        "pub struct StaticRuntimeStateProvider",
        "record_admin_audit_event",
        "static_runtime_provider_can_reach_ready_plan_but_submit_still_blocks",
    ]:
        if needle not in service_text:
            fail(f"service runtime/audit missing token: {needle}")
    for needle in [
        "record_admin_audit",
        "AdminAuditEvent",
        "pmx_service_server_authoritative_id_bound_admin_audit",
        "operation: &'static str",
    ]:
        if needle not in api_text:
            fail(f"API admin audit missing token: {needle}")
    for needle in [
        "http_postgres_admin_routes_record_audit_events",
        "admin_audit_events",
        "KillSwitch",
        "CancelOrder",
    ]:
        if needle not in pg_test_text:
            fail(f"PostgreSQL API audit E2E missing token: {needle}")
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")



def validate_v16_postgres_runtime_provider() -> None:
    service_text = rust_source_text(SERVICE_SRC)
    store_text = rust_source_text(STORE_SRC)
    postgres_text = rust_source_text(STORE_SRC)
    api_text = rust_source_text(API_SRC)
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    spike_text = SDK_SPIKE_RS.read_text()
    for needle in [
        "pub struct ExecutionLifecycleEvent",
        "pub trait ExecutionLifecycleStore",
        "impl ExecutionLifecycleStore for InMemoryStore",
        "pub struct RuntimeStateQuery",
        "pub trait RuntimeStateStore",
        "impl RuntimeStateStore for InMemoryStore",
        "set_runtime_state_for_test",
    ]:
        if needle not in store_text:
            fail(f"v0.16 store runtime state missing token: {needle}")
    for needle in [
        "impl ExecutionLifecycleStore for PostgresStore",
        "execution_lifecycle_events",
        "postgres_records_execution_lifecycle_event",
        "impl RuntimeStateStore for PostgresStore",
        "runtime_accounts",
        "collateral_profiles",
        "worker_health",
        "postgres_loads_runtime_state_from_runtime_tables",
    ]:
        if needle not in postgres_text:
            fail(f"v0.16 postgres runtime state missing token: {needle}")
    for needle in [
        "async fn capture_runtime_state",
        "pub struct StoreBackedRuntimeStateProvider",
        "StoreBackedRuntimeStateProvider::new",
        "store_backed_runtime_provider_uses_store_state",
        "SUBMIT_BLOCKED_BEFORE_REMOTE",
    ]:
        if needle not in service_text:
            fail(f"v0.16 service runtime provider missing token: {needle}")
    for needle in [
        "StoreBackedRuntimeStateProvider<PostgresStore>",
        "StoreBackedRuntimeStateProvider::new(store.clone())",
    ]:
        if needle not in api_text:
            fail(f"v0.16 API postgres runtime provider missing token: {needle}")
    for needle in [
        "http_postgres_runtime_rows_can_reach_ready_plan_but_submit_still_blocks",
        "seed_allow_runtime",
        "REJECTED%",
        "execution_lifecycle_events",
    ]:
        if needle not in pg_test_text:
            fail(f"v0.16 PostgreSQL runtime/audit E2E missing token: {needle}")
    if "read-only smoke must not depend on signer credentials" in spike_text:
        fail("SDK spike read-only smoke must not fail just because credentials are exported")
    for doc in [
        EXECUTOR / "docs/POSTGRES_RUNTIME_PROVIDER.md",
        EXECUTOR / "docs/ADMIN_AUDIT_FAILURE_PATHS.md",
        EXECUTOR / "validation/run_current_gates.sh",
        EXECUTOR / "docs/VALIDATION_PARTITIONING.md",
        EXECUTOR / "docs/RELEASE_HYGIENE_CLEAN_SNAPSHOT.md",
    ]:
        if not doc.exists():
            fail(f"v0.18 missing continuation artifact: {doc.relative_to(ROOT)}")


def validate_v19_redaction_and_live_guard() -> None:
    adapter_text = rust_source_text(SDK_ADAPTER_SRC)
    for needle in [
        "pub const REDACTED",
        "redact_sensitive_text",
        "redact_normalized_error",
        "gateway_error_conversion_redacts_sensitive_message",
        "read_only_smoke_ignores_ambient_credentials_but_must_remain_unauthenticated",
    ]:
        if needle not in adapter_text:
            fail(f"v0.19 adapter redaction/read-only update missing token: {needle}")
    if not LIVE_SUBMIT_GUARD.exists():
        fail("missing v0.19 live-submit static guard")
    guard_text = LIVE_SUBMIT_GUARD.read_text()
    for needle in ["post_order", "post_orders", "public OpenAPI", "live-submit static guard passed"]:
        if needle not in guard_text:
            fail(f"v0.19 live-submit static guard missing token: {needle}")
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")
    for doc in [
        EXECUTOR / "docs/SIGNED_PAYLOAD_REDACTION.md",
        EXECUTOR / "docs/LIVE_SUBMIT_STATIC_GUARD.md",
    ]:
        if not doc.exists():
            fail(f"v0.19 missing safety doc: {doc.relative_to(ROOT)}")


def validate_v20_plan_storage_and_packaging() -> None:
    migration = (EXECUTOR / "migrations/0001_initial.sql").read_text()
    postgres = (EXECUTOR / "crates/pmx-store/src/postgres.rs").read_text()
    adapter = rust_source_text(SDK_ADAPTER_SRC)
    runtime = rust_source_text(EXECUTOR / "crates/pmx-runtime/src")
    core = rust_source_text(CORE_SRC)

    for needle in [
        "DROP TABLE IF EXISTS plan_summaries",
        "execution_plans.summary_json as canonical plan summary storage",
    ]:
        if needle not in migration:
            fail(f"v0.20 migration plan storage missing token: {needle}")
    if "CREATE TABLE IF NOT EXISTS plan_summaries" in migration:
        fail("v0.20 migration must not recreate plan_summaries")
    if "INSERT INTO plan_summaries" in postgres or '"plan_summaries"' in postgres:
        fail("v0.20 PostgresStore must not read/write plan_summaries")
    for needle in [
        "validate_token_id",
        "validate_limit_price_for_sdk",
        "plan_mapping_rejects_placeholder_token_id",
        "normalized_error_redaction_covers_remote_unknown_messages",
    ]:
        if needle not in adapter:
            fail(f"v0.20 SDK adapter coverage missing token: {needle}")
    for needle in [
        "pub enum RuntimeSignal",
        "runtime_breakdown_from_signals",
        "geoblock_unknown_and_reconcile_backlog_block_submit",
    ]:
        if needle not in runtime:
            fail(f"v0.20 runtime linkage missing token: {needle}")
    for needle in [
        "cancel_state_from_lifecycle",
        "lifecycle_requires_reconcile",
        "remote_unknown_states_require_reconcile",
    ]:
        if needle not in core:
            fail(f"v0.20 cancel/reconcile linkage missing token: {needle}")
    for doc in [
        ROOT / "scripts/package_release.py",
        ROOT / "scripts/check_release_artifact.py",
        EXECUTOR / "validation/check_plan_storage.py",
        EXECUTOR / "validation/run_current_gates.sh",
        EXECUTOR / "docs/PLAN_STORAGE_CANONICALIZATION.md",
        EXECUTOR / "docs/DOC_STATUS.md",
    ]:
        if not doc.exists():
            fail(f"v0.20 missing artifact: {doc.relative_to(ROOT)}")


def validate_v21_sign_only_and_runtime_models() -> None:
    core = rust_source_text(CORE_SRC)
    adapter = rust_source_text(SDK_ADAPTER_SRC)
    runtime = rust_source_text(EXECUTOR / "crates/pmx-runtime/src")
    for needle in [
        "pub enum SignOnlyLifecycleState",
        "transition_sign_only_lifecycle",
        "sign_only_lifecycle_has_remote_side_effect",
    ]:
        if needle not in core:
            fail(f"v0.21 sign-only lifecycle core missing token: {needle}")
    for needle in [
        "sign_only_lifecycle_records_from_receipt",
        "sign_only_lifecycle_records_are_persistable_and_non_mutating",
        "sign_only_lifecycle_rejects_posted_receipt",
    ]:
        if needle not in adapter:
            fail(f"v0.21 sign-only lifecycle adapter missing token: {needle}")
    for needle in [
        "pub enum RuntimeWorkerKind",
        "pub struct RuntimeWorkerAction",
        "worker_actions_from_runtime_signals",
        "worker_actions_mark_stale_runtime_inputs_as_fail_closed_updates",
    ]:
        if needle not in runtime:
            fail(f"v0.21 runtime worker model missing token: {needle}")
    for doc in [
        EXECUTOR / "validation/check_sign_only_lifecycle.py",
        EXECUTOR / "validation/check_runtime_worker_models.py",
        EXECUTOR / "validation/run_current_gates.sh",
        EXECUTOR / "docs/SIGN_ONLY_LIFECYCLE_PERSISTENCE.md",
        EXECUTOR / "docs/RUNTIME_WORKER_MODEL.md",
        EXECUTOR / "docs/DOC_STATUS.md",
    ]:
        if not doc.exists():
            fail(f"v0.21 missing artifact: {doc.relative_to(ROOT)}")

def validate_v23_lifecycle_query_and_hardening() -> None:
    openapi = OPENAPI.read_text()
    api = rust_source_text(API_SRC)
    core = rust_source_text(CORE_SRC)
    store = rust_source_text(STORE_SRC)
    postgres = rust_source_text(STORE_SRC)
    service = rust_source_text(SERVICE_SRC)
    policy = (EXECUTOR / "crates/pmx-policy/src/lib.rs").read_text()
    sql = SQL.read_text()
    gate = (EXECUTOR / "validation/run_current_gates_impl.sh").read_text()

    required_by_file = {
        "openapi": (openapi, [
            "/v1/sign-only/lifecycle-events",
            "/v1/lifecycle/executions/{execution_id}/events",
            "/v1/runtime/workers",
            "/v1/admin/audit-events",
            "/v1/admin/reconcile-order-local",
            "client_event_id",
            "before_event_id",
            "before_audit_id",
            "readOnly: true",
            "ReconcileOrderLocalRequest",
            "ReconcileOrderLocalResponse",
            "RuntimeWorkerStatusReport",
        ]),
        "core": (core, [
            "pub struct RedactedPayloadEnvelope",
            "redacted_payload_envelope",
            "redacted_fields",
            "WorkerDegraded",
            "pub struct SignOnlyLifecycleRecord",
            "pub client_event_id: Option<String>",
            "left.client_event_id == right.client_event_id",
        ]),
        "store": (store, [
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
        ]),
        "postgres": (postgres, [
            "impl OrderLifecycleStore for PostgresStore",
            "postgres_records_order_lifecycle_event",
            "impl RuntimeWorkerHealthStore for PostgresStore",
            "impl RuntimeWorkerStatusStore for PostgresStore",
            "postgres_records_worker_heartbeat",
            "postgres_lists_runtime_worker_status",
            "principal_subject = $4",
            "result = $5",
            "pg_advisory_xact_lock",
            "sign_only_lifecycle_record_is_replay",
            "runtime_observation_ttl_seconds",
            "FOREIGN_KEY_VIOLATION",
            "CHECK_VIOLATION",
        ]),
        "sql": (sql, [
            "CREATE TABLE IF NOT EXISTS orders",
            "CREATE TABLE IF NOT EXISTS order_events",
            "idx_order_events_order_created",
            "client_event_id TEXT",
            "uq_sign_only_lifecycle_client_event",
            "WHERE client_event_id IS NOT NULL",
            "ADD COLUMN IF NOT EXISTS client_event_id",
            "ADD COLUMN IF NOT EXISTS observed_at",
            "ADD COLUMN IF NOT EXISTS correlation_id",
        ]),
        "service": (service, [
            "candidate.client_event_id.as_deref()",
            "record.event_id = None",
            "record.created_at = None",
            "record_standard_sign_only_construction",
            "account_id does not match request",
        ]),
        "policy": (policy, [
            "WorkerStatus::Degraded => reasons.push(BlockReason::WorkerDegraded)",
            "degraded_worker_blocks_pre_live",
        ]),
        "api": (api, [
            "correlation_id_from_headers",
            "api_error_with_correlation",
            "redacted_payload_envelope",
            "principal_subject: query.principal_subject",
            "result: query.result",
            "reconcile_order_local",
            "ReconcileOrderLocalResponse",
            "list_runtime_worker_status",
            "/v1/runtime/workers",
        ]),
        "gate": (gate, [
            "run_current_gates.sh",
            "check_current_lifecycle_api.py",
            "check_version_consistency.py",
            "check_docs_evidence_governance.py",
            "write_current_evidence_manifest.py",
            "check_runtime_worker_status_query.py",
            "42-runtime-worker-status-query.log",
            "evidence/current",
        ]),
    }
    for label, (text, needles) in required_by_file.items():
        for needle in needles:
            if needle not in text:
                fail(f"current {label} missing token: {needle}")

    if core.count("pub client_event_id: Option<String>") != 1:
        fail("current SignOnlyLifecycleRecord must have exactly one client_event_id field")
    if store.count("pub observed_at: Option<DateTime<Utc>>") != 1:
        fail("current RuntimeWorkerObservation must have exactly one observed_at field")
    if "SignedOrderEnvelope" in openapi or "signed_payload" in openapi:
        fail("current public OpenAPI must not expose signed payload internals")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Validate integration contracts across OpenAPI, Rust, Hermes, SQL, and release governance."
    )
    parser.parse_args(argv)
    spec = yaml.safe_load(OPENAPI.read_text())
    validate_paths_and_statuses(spec)
    validate_no_public_forbidden_tokens()
    validate_additional_properties(spec)
    validate_python_field_parity(spec)
    validate_sql_idempotency()
    validate_rust_deny_unknown_fields()
    validate_v04_source_landings()
    validate_v07_source_landings()
    validate_v08_dependency_and_sdk_policy()
    validate_v09_official_adapter_boundary()
    validate_v12_service_layer()
    validate_v15_admin_audit_and_runtime_provider()
    validate_v16_postgres_runtime_provider()
    validate_v19_redaction_and_live_guard()
    validate_v20_plan_storage_and_packaging()
    validate_v21_sign_only_and_runtime_models()
    validate_v23_lifecycle_query_and_hardening()
    validate_current_hermes_client_surface()
    validate_current_evidence_manifest_guard()
    validate_current_docs_and_release_governance()
    validate_controlled_canary_release_decision_governance()
    validate_canary_candidate_market_prep_boundary()
    validate_single_host_deployment_governance()
    validate_v28_production_live_candidate_guard()
    print(json.dumps({"status": "ok", "paths": len(spec["paths"]), "schemas": len(spec["components"]["schemas"])}))


if __name__ == "__main__":
    main()
