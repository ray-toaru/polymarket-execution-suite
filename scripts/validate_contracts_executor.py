from __future__ import annotations

import re

from validate_contracts_support import (
    API_E2E_TEST,
    API_POSTGRES_E2E_TEST,
    API_SRC,
    CORE_SRC,
    EXECUTOR,
    GATEWAY_SRC,
    LIVE_SUBMIT_GUARD,
    OPENAPI,
    POSTGRES_RS,
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
    STORE_SRC,
    fail,
    rust_file_with_modules_text,
    rust_source_text,
)


def openapi_operation(spec: dict, path: str, method: str) -> dict:
    try:
        return spec["paths"][path][method]
    except KeyError as exc:
        fail(f"OpenAPI missing {method.upper()} {path}: {exc}")


def operation_parameter_names(operation: dict) -> set[str]:
    return {param["name"] for param in operation.get("parameters", [])}


def schema_property_names(spec: dict, schema_name: str) -> set[str]:
    try:
        schema = spec["components"]["schemas"][schema_name]
    except KeyError as exc:
        fail(f"OpenAPI missing schema {schema_name}: {exc}")
    return set(schema.get("properties", {}).keys())


def schema_required_names(spec: dict, schema_name: str) -> set[str]:
    try:
        schema = spec["components"]["schemas"][schema_name]
    except KeyError as exc:
        fail(f"OpenAPI missing schema {schema_name}: {exc}")
    return set(schema.get("required", []))


def operation_request_ref(spec: dict, path: str, method: str) -> str | None:
    return (
        openapi_operation(spec, path, method)
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref")
    )


def operation_response_ref(spec: dict, path: str, method: str, status: str) -> str | None:
    return (
        openapi_operation(spec, path, method)
        .get("responses", {})
        .get(status, {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref")
    )


def operation_response_array_item_ref(spec: dict, path: str, method: str, status: str) -> str | None:
    return (
        openapi_operation(spec, path, method)
        .get("responses", {})
        .get(status, {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("items", {})
        .get("$ref")
    )


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
    for needle in [
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
    ]:
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


def validate_v12_service_layer(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    if not SERVICE_RS.exists():
        fail("missing pmx-service crate source")
    if not SERVICE_TOML.exists():
        fail("missing pmx-service Cargo.toml")
    service_text = rust_source_text(SERVICE_SRC)
    api_text = rust_source_text(API_SRC)
    backend_text = (API_SRC / "backend.rs").read_text()
    root_toml = ROOT_CARGO_TOML.read_text()
    expected_openapi_refs = {
        ("/v1/plans/compile", "post", "request"): "#/components/schemas/CompilePlanRequest",
        ("/v1/plans/compile", "post", "200"): "#/components/schemas/ExecutionPlanSummary",
        ("/v1/submissions", "post", "request"): "#/components/schemas/SubmitRequest",
        ("/v1/submissions", "post", "202"): "#/components/schemas/SubmitReceipt",
        ("/v1/admin/cancel-order", "post", "request"): "#/components/schemas/CancelOrderRequest",
        ("/v1/admin/cancel-order", "post", "202"): "#/components/schemas/CancelReceipt",
        ("/v1/admin/reconcile", "post", "request"): "#/components/schemas/ReconcileRequest",
        ("/v1/admin/reconcile", "post", "202"): "#/components/schemas/ReconcileReport",
    }
    for (path, method, kind), expected_ref in expected_openapi_refs.items():
        actual_ref = operation_request_ref(spec, path, method) if kind == "request" else operation_response_ref(spec, path, method, kind)
        if actual_ref != expected_ref:
            fail(f"OpenAPI {method.upper()} {path} {kind} must reference {expected_ref}, got {actual_ref}")
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
    for needle in ['"SUBMIT_BLOCKED_BEFORE_REMOTE"', '"no_remote_side_effect": true', '"reservation_written": false']:
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
    for needle in [
        "pub enum ServiceBackend",
        "InMemory(ExecutorService<InMemoryStore>)",
        "Postgres(ExecutorService<PostgresStore, StoreBackedRuntimeStateProvider<PostgresStore>>)",
    ]:
        if needle not in backend_text:
            fail(f"pmx-api backend structure missing token: {needle}")
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


def validate_v15_admin_audit_and_runtime_provider(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    service_text = rust_source_text(SERVICE_SRC)
    store_text = rust_source_text(STORE_SRC)
    postgres_text = rust_source_text(STORE_SRC)
    api_text = rust_source_text(API_SRC)
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    audit_operation = openapi_operation(spec, "/v1/admin/audit-events", "get")
    if operation_response_array_item_ref(spec, "/v1/admin/audit-events", "get", "200") != "#/components/schemas/AdminAuditEvent":
        fail("v0.15 admin audit response must be an array of AdminAuditEvent")
    if operation_request_ref(spec, "/v1/admin/kill-switch", "post") != "#/components/schemas/KillSwitchRequest":
        fail("v0.15 kill-switch request must reference KillSwitchRequest")
    if operation_response_ref(spec, "/v1/admin/kill-switch", "post", "202") != "#/components/schemas/KillSwitchReceipt":
        fail("v0.15 kill-switch response must reference KillSwitchReceipt")
    audit_params = operation_parameter_names(audit_operation)
    for required_param in {"before_audit_id", "operation", "principal_subject", "result", "correlation_id"}:
        if required_param not in audit_params:
            fail(f"v0.15 admin audit query must expose {required_param}")
    for needle in [
        "pub struct AdminAuditEvent",
        "pub trait AdminAuditStore",
        "impl AdminAuditStore for InMemoryStore",
        "admin_audit: Vec<AdminAuditEvent>",
    ]:
        if needle not in store_text:
            fail(f"store admin audit missing token: {needle}")
    for needle in ["impl AdminAuditStore for PostgresStore", "INSERT INTO admin_audit_events", "postgres_records_admin_audit_event"]:
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
    for needle in ["http_postgres_admin_routes_record_audit_events", "admin_audit_events", "KillSwitch", "CancelOrder"]:
        if needle not in pg_test_text:
            fail(f"PostgreSQL API audit E2E missing token: {needle}")
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")


def validate_v16_postgres_runtime_provider(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    service_text = rust_source_text(SERVICE_SRC)
    store_text = rust_source_text(STORE_SRC)
    postgres_text = rust_source_text(STORE_SRC)
    api_text = rust_source_text(API_SRC)
    backend_text = (API_SRC / "backend.rs").read_text()
    health_text = (API_SRC / "routes/health.rs").read_text()
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    spike_text = SDK_SPIKE_RS.read_text()
    runtime_worker_ref = operation_response_ref(spec, "/v1/runtime/workers", "get", "200")
    if runtime_worker_ref != "#/components/schemas/RuntimeWorkerStatusReport":
        fail("v0.16 runtime workers response must reference RuntimeWorkerStatusReport")
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
    for needle in ["StoreBackedRuntimeStateProvider<PostgresStore>", "StoreBackedRuntimeStateProvider::new(store.clone())"]:
        if needle not in backend_text:
            fail(f"v0.16 API postgres runtime provider missing token: {needle}")
    for needle in ['Self::Postgres(_) => "postgres"', '"database": state.service.storage_mode()']:
        if needle not in (backend_text + "\n" + health_text):
            fail(f"v0.16 postgres health/backend structure missing token: {needle}")
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


def validate_v19_redaction_and_live_guard(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
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
    forbidden_public_tokens = {"SignedOrderEnvelope", "signed_payload", "private_key", "clob_secret", "post_order"}
    public_strings = set()
    stack = [spec]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                public_strings.add(str(key))
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str):
            public_strings.add(current)
    for token in forbidden_public_tokens:
        if token in public_strings:
            fail(f"v0.19 public contract exposes forbidden live/signed term: {token}")
    for needle in ["post_order", "post_orders", "public OpenAPI", "live-submit static guard passed"]:
        if needle not in guard_text:
            fail(f"v0.19 live-submit static guard missing token: {needle}")
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")
    for doc in [EXECUTOR / "docs/SIGNED_PAYLOAD_REDACTION.md", EXECUTOR / "docs/LIVE_SUBMIT_STATIC_GUARD.md"]:
        if not doc.exists():
            fail(f"v0.19 missing safety doc: {doc.relative_to(ROOT)}")


def validate_v20_plan_storage_and_packaging(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    migration = (EXECUTOR / "migrations/0001_initial.sql").read_text()
    postgres = (EXECUTOR / "crates/pmx-store/src/postgres.rs").read_text()
    adapter = rust_source_text(SDK_ADAPTER_SRC)
    runtime = rust_source_text(EXECUTOR / "crates/pmx-runtime/src")
    core = rust_source_text(CORE_SRC)
    compile_request_ref = operation_request_ref(spec, "/v1/plans/compile", "post")
    compile_response_ref = operation_response_ref(spec, "/v1/plans/compile", "post", "200")
    if compile_request_ref != "#/components/schemas/CompilePlanRequest":
        fail("v0.20 compile plan request must reference CompilePlanRequest")
    if compile_response_ref != "#/components/schemas/ExecutionPlanSummary":
        fail("v0.20 compile plan response must reference ExecutionPlanSummary")
    for needle in ["DROP TABLE IF EXISTS plan_summaries", "execution_plans.summary_json as canonical plan summary storage"]:
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
    for needle in ["pub enum RuntimeSignal", "runtime_breakdown_from_signals", "geoblock_unknown_and_reconcile_backlog_block_submit"]:
        if needle not in runtime:
            fail(f"v0.20 runtime linkage missing token: {needle}")
    for needle in ["cancel_state_from_lifecycle", "lifecycle_requires_reconcile", "remote_unknown_states_require_reconcile"]:
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


def validate_v21_sign_only_and_runtime_models(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    core = rust_source_text(CORE_SRC)
    adapter = rust_source_text(SDK_ADAPTER_SRC)
    runtime = rust_source_text(EXECUTOR / "crates/pmx-runtime/src")
    expected_sign_only_refs = {
        ("/v1/sign-only/lifecycle-events", "post", "request"): "#/components/schemas/SignOnlyLifecycleRecord",
        ("/v1/sign-only/lifecycle-events", "post", "202"): "#/components/schemas/SignOnlyLifecycleRecord",
        ("/v1/sign-only/standard-constructions", "post", "request"): "#/components/schemas/StandardSignOnlyConstructionRequest",
        ("/v1/sign-only/standard-constructions", "post", "202"): "#/components/schemas/StandardSignOnlyConstructionReceipt",
        ("/v1/sign-only/lifecycle-events/{execution_id}", "get", "200_items"): "#/components/schemas/SignOnlyLifecycleRecord",
    }
    for (path, method, kind), expected_ref in expected_sign_only_refs.items():
        if kind == "request":
            actual_ref = operation_request_ref(spec, path, method)
        elif kind == "200_items":
            actual_ref = operation_response_array_item_ref(spec, path, method, "200")
        else:
            actual_ref = operation_response_ref(spec, path, method, kind)
        if actual_ref != expected_ref:
            fail(f"v0.21 {method.upper()} {path} {kind} must reference {expected_ref}, got {actual_ref}")
    sign_only_required = schema_required_names(spec, "SignOnlyLifecycleRecord")
    if not {"execution_id", "account_id", "state", "event", "signed_order_ref", "no_remote_side_effect"}.issubset(sign_only_required):
        fail("v0.21 SignOnlyLifecycleRecord schema missing required lifecycle fields")
    sign_only_props = schema_property_names(spec, "SignOnlyLifecycleRecord")
    for required_prop in {"client_event_id", "signed_order_ref", "no_remote_side_effect"}:
        if required_prop not in sign_only_props:
            fail(f"v0.21 SignOnlyLifecycleRecord schema must expose {required_prop}")
    standard_req_required = schema_required_names(spec, "StandardSignOnlyConstructionRequest")
    if not {"execution_id", "account_id", "plan_hash", "no_remote_side_effect"}.issubset(standard_req_required):
        fail("v0.21 StandardSignOnlyConstructionRequest missing required binding fields")
    standard_req_props = schema_property_names(spec, "StandardSignOnlyConstructionRequest")
    for required_prop in {"signed_order_ref", "signed_order_digest", "no_remote_side_effect"}:
        if required_prop not in standard_req_props:
            fail(f"v0.21 StandardSignOnlyConstructionRequest must expose {required_prop}")
    standard_receipt_props = schema_property_names(spec, "StandardSignOnlyConstructionReceipt")
    for required_prop in {"signed_order_ref", "signed_order_digest", "lifecycle_records", "no_remote_side_effect"}:
        if required_prop not in standard_receipt_props:
            fail(f"v0.21 StandardSignOnlyConstructionReceipt must expose {required_prop}")
    runtime_worker_props = schema_property_names(spec, "RuntimeWorkerStatusReport")
    if runtime_worker_props != {"heartbeats", "observations"}:
        fail(f"v0.21 RuntimeWorkerStatusReport properties changed unexpectedly: {sorted(runtime_worker_props)}")
    for needle in ["pub enum SignOnlyLifecycleState", "transition_sign_only_lifecycle", "sign_only_lifecycle_has_remote_side_effect"]:
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


def validate_v23_lifecycle_query_and_hardening(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    api = rust_source_text(API_SRC)
    core = rust_source_text(CORE_SRC)
    store = rust_source_text(STORE_SRC)
    postgres = rust_source_text(STORE_SRC)
    service = rust_source_text(SERVICE_SRC)
    policy = (EXECUTOR / "crates/pmx-policy/src/lib.rs").read_text()
    sql = SQL.read_text()
    gate = (EXECUTOR / "validation/run_current_gates_impl.sh").read_text()
    required_paths = {
        "/v1/sign-only/lifecycle-events",
        "/v1/lifecycle/executions/{execution_id}/events",
        "/v1/runtime/workers",
        "/v1/admin/audit-events",
        "/v1/admin/reconcile-order-local",
    }
    missing_paths = required_paths - set(spec["paths"].keys())
    if missing_paths:
        fail(f"current OpenAPI missing lifecycle/runtime/admin paths: {sorted(missing_paths)}")

    sign_only_events = openapi_operation(spec, "/v1/sign-only/lifecycle-events/{execution_id}", "get")
    execution_events = openapi_operation(spec, "/v1/lifecycle/executions/{execution_id}/events", "get")
    audit_events = openapi_operation(spec, "/v1/admin/audit-events", "get")
    reconcile_local = openapi_operation(spec, "/v1/admin/reconcile-order-local", "post")
    runtime_workers = openapi_operation(spec, "/v1/runtime/workers", "get")

    if "before_event_id" not in operation_parameter_names(sign_only_events):
        fail("current OpenAPI sign-only lifecycle execution query must expose before_event_id")
    if "before_event_id" not in operation_parameter_names(execution_events):
        fail("current OpenAPI execution lifecycle query must expose before_event_id")
    if "before_audit_id" not in operation_parameter_names(audit_events):
        fail("current OpenAPI admin audit query must expose before_audit_id")

    response_ref = (
        runtime_workers.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref")
    )
    if response_ref != "#/components/schemas/RuntimeWorkerStatusReport":
        fail("current OpenAPI runtime worker response must reference RuntimeWorkerStatusReport")

    request_ref = (
        reconcile_local.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref")
    )
    if request_ref != "#/components/schemas/ReconcileOrderLocalRequest":
        fail("current OpenAPI reconcile-order-local request must reference ReconcileOrderLocalRequest")
    reconcile_response_ref = (
        reconcile_local.get("responses", {})
        .get("202", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref")
    )
    if reconcile_response_ref != "#/components/schemas/ReconcileOrderLocalResponse":
        fail("current OpenAPI reconcile-order-local response must reference ReconcileOrderLocalResponse")

    if "client_event_id" not in schema_property_names(spec, "SignOnlyLifecycleRecord"):
        fail("current OpenAPI SignOnlyLifecycleRecord must expose client_event_id")
    required_by_file = {
        "core": (core, ["pub struct RedactedPayloadEnvelope", "redacted_payload_envelope", "redacted_fields", "WorkerDegraded", "pub struct SignOnlyLifecycleRecord", "pub client_event_id: Option<String>", "left.client_event_id == right.client_event_id"]),
        "store": (store, ["OrderLifecycleRecord", "OrderLifecycleStore", "record_order_lifecycle_event", "in_memory_order_lifecycle_records_cancel_requested", "RuntimeWorkerHeartbeat", "RuntimeWorkerHealthStore", "RuntimeWorkerStatusReport", "RuntimeWorkerStatusStore", "list_runtime_worker_status", "record_worker_heartbeat", "in_memory_worker_heartbeat_informs_runtime_state", "principal_subject: Option<String>", "result: Option<String>", "sign_only_lifecycle_record_is_replay", "client_event_id reused with different event payload", "PMX_RUNTIME_OBSERVATION_TTL_SECONDS", "runtime_observation_ttl_seconds", "execution_id={}"]),
        "postgres": (postgres, ["impl OrderLifecycleStore for PostgresStore", "postgres_records_order_lifecycle_event", "impl RuntimeWorkerHealthStore for PostgresStore", "impl RuntimeWorkerStatusStore for PostgresStore", "postgres_records_worker_heartbeat", "postgres_lists_runtime_worker_status", "principal_subject = $4", "result = $5", "pg_advisory_xact_lock", "sign_only_lifecycle_record_is_replay", "runtime_observation_ttl_seconds", "FOREIGN_KEY_VIOLATION", "CHECK_VIOLATION"]),
        "sql": (sql, ["CREATE TABLE IF NOT EXISTS orders", "CREATE TABLE IF NOT EXISTS order_events", "idx_order_events_order_created", "client_event_id TEXT", "uq_sign_only_lifecycle_client_event", "WHERE client_event_id IS NOT NULL", "ADD COLUMN IF NOT EXISTS client_event_id", "ADD COLUMN IF NOT EXISTS observed_at", "ADD COLUMN IF NOT EXISTS correlation_id"]),
        "service": (service, ["candidate.client_event_id.as_deref()", "record.event_id = None", "record.created_at = None", "record_standard_sign_only_construction", "account_id does not match request"]),
        "policy": (policy, ["WorkerStatus::Degraded => reasons.push(BlockReason::WorkerDegraded)", "degraded_worker_blocks_pre_live"]),
        "api": (api, ["correlation_id_from_headers", "api_error_with_correlation", "redacted_payload_envelope", "principal_subject: query.principal_subject", "result: query.result", "reconcile_order_local", "ReconcileOrderLocalResponse", "list_runtime_worker_status", "/v1/runtime/workers"]),
        "gate": (gate, ["run_current_gates.sh", "check_current_lifecycle_api.py", "check_version_consistency.py", "check_docs_evidence_governance.py", "write_current_evidence_manifest.py", "check_runtime_worker_status_query.py", "42-runtime-worker-status-query.log", "evidence/current"]),
    }
    for label, (text, needles) in required_by_file.items():
        for needle in needles:
            if needle not in text:
                fail(f"current {label} missing token: {needle}")
    if core.count("pub client_event_id: Option<String>") != 1:
        fail("current SignOnlyLifecycleRecord must have exactly one client_event_id field")
    if store.count("pub observed_at: Option<DateTime<Utc>>") != 1:
        fail("current RuntimeWorkerObservation must have exactly one observed_at field")
    openapi_text = OPENAPI.read_text()
    if "SignedOrderEnvelope" in openapi_text or "signed_payload" in openapi_text:
        fail("current public OpenAPI must not expose signed payload internals")
