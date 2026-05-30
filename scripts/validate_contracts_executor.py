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


def require_tokens(text: str, label: str, tokens: list[str]) -> None:
    for token in tokens:
        if token not in text:
            fail(f"{label} missing token: {token}")


def require_file_tokens(path, label: str, tokens: list[str]) -> None:
    if not path.exists():
        fail(f"missing {label} source: {path.relative_to(ROOT)}")
    require_tokens(path.read_text(), label, tokens)


def validate_absent_tokens(text: str, label: str, tokens: list[str]) -> None:
    for token in tokens:
        if token in text:
            fail(f"{label} contains forbidden token: {token}")


def source_tree_text_without_paths(root, excluded_paths: list) -> str:
    text = rust_source_text(root)
    for excluded in excluded_paths:
        if excluded.exists():
            text = text.replace(excluded.read_text(), "")
    return text


def validate_v04_source_landings() -> None:
    if not API_E2E_TEST.exists():
        fail("missing HTTP/auth/fake E2E integration test source")
    require_file_tokens(
        API_E2E_TEST.parent / "http_and_fake_e2e/smoke.rs",
        "HTTP/auth fake E2E smoke",
        ["http_auth_and_fake_e2e_smoke", "StatusCode::UNAUTHORIZED", "StatusCode::FORBIDDEN", "StatusCode::ACCEPTED"],
    )
    require_file_tokens(
        STORE_SRC / "model/advisory.rs",
        "pmx-store advisory lock model",
        ["pub struct AdvisoryLockKey", "pub fn advisory_lock_key", "const FNV_OFFSET", "const FNV_PRIME", "i64::from_ne_bytes(hash.to_ne_bytes())"],
    )
    require_file_tokens(
        STORE_SRC / "postgres.rs",
        "pmx-store postgres adapter",
        ["pub struct PostgresStore", "tokio_postgres::connect(&self.database_url, NoTls)"],
    )
    if not POSTGRES_RS.exists():
        fail("missing PostgreSQL repository adapter source")
    require_file_tokens(
        STORE_SRC / "postgres_idempotency.rs",
        "postgres idempotency adapter",
        ["impl IdempotencyStore for PostgresStore", "begin::begin_submit_attempt(", "finish::finish_submit_attempt(self, attempt).await"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_idempotency/begin.rs",
        "postgres idempotency begin path",
        ["SELECT pg_advisory_xact_lock($1)", 'status == "PROCEEDING"', "IdempotencyAction::InProgress", "IdempotencyAction::Proceed"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_tests/idempotency.rs",
        "postgres idempotency tests",
        ["same_request_replay_is_persisted", "fingerprint_mismatch_is_conflict"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_tests/receipt_reservation.rs",
        "postgres receipt/reservation tests",
        ["reservation_double_spend_is_prevented_concurrently", "remote_unknown_is_persisted_conservatively"],
    )


def validate_v07_source_landings() -> None:
    require_file_tokens(
        GATEWAY_SRC / "traits.rs",
        "gateway traits",
        ["pub trait SignerProvider", "pub trait ClobGateway", "pub trait RemoteReconcileReader", "async fn post_order(&self, order: &SignedOrderEnvelope)"],
    )
    require_file_tokens(
        GATEWAY_SRC / "signer.rs",
        "gateway signer provider",
        ["pub struct DeterministicTestSignerProvider", "pub struct DeterministicTestSigner", "pub struct SignerProviderConfig", "allow_local_private_key_material: false", "require_remote_signer_in_production: true"],
    )
    require_file_tokens(
        GATEWAY_SRC / "tests/signer.rs",
        "gateway signer tests",
        ["disabled_signer_provider_refuses_to_materialize_signer", "signer_provider_defaults_are_production_conservative"],
    )
    require_file_tokens(
        GATEWAY_SRC / "tests/post_cancel.rs",
        "gateway post/cancel tests",
        ["deterministic_signer_provider_posts_reads_and_cancels", "fake_gateway_surfaces_remote_unknown_without_local_success"],
    )
    require_file_tokens(
        API_E2E_TEST.parent / "http_and_fake_e2e/scaffold.rs",
        "HTTP scaffold E2E",
        ["full_scaffold_path_compile_submit_cancel_and_reconcile", "compile_blocked_plan", "verify_submit_and_sign_only", "verify_non_live_admin_paths", "verify_public_queries"],
    )
    require_file_tokens(
        API_E2E_TEST.parent / "http_and_fake_e2e/scaffold/admin_paths.rs",
        "HTTP scaffold admin paths",
        ["/v1/admin/cancel-order", "/v1/admin/reconcile", "/v1/admin/reconcile-order-local", "StatusCode::ACCEPTED", "StatusCode::NOT_FOUND"],
    )
    require_file_tokens(
        API_E2E_TEST.parent / "http_and_fake_e2e/scaffold/submit_sign_only.rs",
        "HTTP scaffold submit/sign-only",
        ["/v1/submissions", "/v1/sign-only/standard-constructions", "/v1/sign-only/lifecycle-events", '"mode": "BLOCKED_DRY_RUN"', "StatusCode::BAD_REQUEST"],
    )
    require_file_tokens(
        SDK_SPIKE_RS,
        "official SDK spike",
        ["OFFICIAL_SDK_REPOSITORY", "PINNED_OFFICIAL_SDK_VERSION", "LIVE_SUBMIT_FEATURE_NAME", "allow_live_submit: false", "require_explicit_runtime_kill_switch_open: true", "sdk_client_type_marker"],
    )


def validate_v08_dependency_and_sdk_policy() -> None:
    require_file_tokens(
        ROOT_CARGO_TOML,
        "root Cargo baseline",
        [
            'edition = "2024"',
            'rust-version = "1.88"',
            f'version = "{(ROOT / "VERSION").read_text().strip()}"',
            'tokio = { version = "1.52.3"',
            'serde = { version = "1.0.228"',
        ],
    )
    require_file_tokens(
        EXECUTOR / "rust-toolchain.toml",
        "executor rust toolchain",
        ['channel = "1.88.0"', 'components = ["rustfmt", "clippy"]', 'profile = "minimal"'],
    )
    require_file_tokens(
        SDK_SPIKE_TOML,
        "official SDK spike Cargo",
        ['name = "pmx-official-sdk-spike"', 'rust-version = "1.88"', 'sdk-typecheck = ["dep:polymarket_client_sdk_v2"]', 'live-submit = ["sdk-typecheck"]', 'polymarket_client_sdk_v2 = { version = "=0.6.0-canary.1"'],
    )
    require_file_tokens(
        SDK_SPIKE_RS,
        "official SDK spike",
        ['PINNED_OFFICIAL_SDK_VERSION: &str = "=0.6.0-canary.1"', 'read_only_ok_smoke', 'default_read_only_client', 'polymarket_client_sdk_v2::clob::Client::new', 'client.server_time()'],
    )
    sdk_text = SDK_SPIKE_RS.read_text()
    sdk_toml = SDK_SPIKE_TOML.read_text()
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
    adapter_toml = SDK_ADAPTER_TOML.read_text()
    require_file_tokens(
        SDK_ADAPTER_RS,
        "official SDK adapter root",
        ["Official Polymarket SDK adapter boundary", "sign-only dry-runs require explicit opt-in", "live submit requires the explicit `live-submit` feature", "pub use gates::*", "run_sign_only_dry_run", "validate_active_profile_env_for_canary"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "model/config.rs",
        "official SDK adapter config",
        ["pub struct OfficialSdkAdapterConfig", "allow_sign_only_dry_run: false", "allow_live_submit: false", "allow_real_funds_canary: false", "pub struct OfficialSdkStandardSignOnlyProfile"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "gates/smoke.rs",
        "official SDK smoke gates",
        ["validate_authenticated_non_trading_smoke", "validate_sign_only_dry_run", "ENV_RUN_AUTHENTICATED_SMOKE", "ENV_ALLOW_SIGN_ONLY_DRY_RUN", "ENV_ALLOW_LIVE_SUBMIT"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "sdk_runtime/sign_only/dry_run.rs",
        "official SDK sign-only dry run",
        ["SignOnlyDryRunReceipt", "validate_sign_only_dry_run(config, &credentials)?", "signed_order_ref = format!(", "posted: false"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "tests/feature_gated.rs",
        "official SDK feature-gated tests",
        ["authenticated_non_trading_smoke_executes_when_enabled", "sign_only_dry_run_executes_when_enabled", "env_helpers_trim_values_and_accept_case_insensitive_true", "assert!(!receipt.posted);"],
    )
    if 'polymarket_client_sdk_v2 = { version = "=0.6.0-canary.1"' not in adapter_toml:
        fail("official adapter must pin the official SDK canary explicitly")
    if not re.search(r'(?m)^live-submit\s*=\s*\[', adapter_toml):
        fail("official adapter must expose an explicit live-submit feature gate")
    live_canary = SDK_ADAPTER_SRC / "sdk_runtime/live_canary.rs"
    gateway_bridge = SDK_ADAPTER_SRC / "sdk_runtime/gateway.rs"
    adapter_boundary_text = source_tree_text_without_paths(SDK_ADAPTER_SRC, [live_canary, gateway_bridge])
    validate_absent_tokens(
        adapter_boundary_text,
        "official adapter boundary",
        ["post_order(", "post_orders("],
    )
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
    if 'allow_live_submit: false' not in rust_source_text(SDK_ADAPTER_SRC):
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
    api_text = rust_source_text(API_SRC)
    if not SERVICE_RS.exists():
        fail("missing pmx-service crate source")
    if not SERVICE_TOML.exists():
        fail("missing pmx-service Cargo.toml")
    backend_text = (API_SRC / "backend.rs").read_text()
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
    require_file_tokens(
        SERVICE_TOML,
        "pmx-service Cargo",
        ['name = "pmx-service"'],
    )
    require_file_tokens(
        SERVICE_RS,
        "pmx-service crate root",
        ["mod binding;", "mod plan_flow;", "mod submit;", "pub use binding::*;", "pub use submit::*;"],
    )
    require_file_tokens(
        SERVICE_SRC / "binding/hash_inputs.rs",
        "service binding hash inputs",
        ["pub(crate) struct PlanHashInput<'a>", "approval_id: &'a str", "approval_hash: &'a HashValue", "executor_version: &'a str", "contract_version: &'a str", "pub(crate) struct ApprovalHashInput<'a>", "bound_snapshot_hash: &'a HashValue"],
    )
    require_file_tokens(
        SERVICE_SRC / "submit/blocked.rs",
        "blocked submit path",
        ['"SUBMIT_BLOCKED_BEFORE_REMOTE"', '"no_remote_side_effect": true', '"reservation_written": false', "finish_submit_attempt(pmx_store::FinishSubmitAttempt"],
    )
    blocked_submit = (SERVICE_SRC / "submit/blocked.rs").read_text()
    validate_absent_tokens(blocked_submit, "blocked submit path", ["save_order_reservation"])
    require_file_tokens(
        SERVICE_SRC / "service_tests/flow.rs",
        "service flow tests",
        ["service_flow_persists_and_blocks_submit", "service_id_bound_flow_persists_and_blocks_submit", "service_rejects_object_graph_mismatch", "service_rejects_tampered_approval_hash"],
    )
    require_file_tokens(
        API_SRC / "routes/bootstrap.rs",
        "API bootstrap routes",
        ['.route("/v1/plans/compile", post(flow::compile_plan))', '.route("/v1/submissions", post(flow::submit_plan))', '"/v1/admin/cancel-order"', '"/v1/admin/reconcile"', "pub async fn try_postgres_app(", "AppState::postgres(store)"],
    )
    for needle in [
        "pub enum ServiceBackend",
        "InMemory(ExecutorService<InMemoryStore>)",
        "Postgres(ExecutorService<PostgresStore, StoreBackedRuntimeStateProvider<PostgresStore>>)",
    ]:
        if needle not in backend_text:
            fail(f"pmx-api backend structure missing token: {needle}")
    validate_absent_tokens(api_text, "pmx-api", ["pub fn fake_snapshot"])
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
    require_file_tokens(
        STORE_SRC / "model/audit.rs",
        "store admin audit model",
        ["pub struct AdminAuditEvent", "pub trait AdminAuditStore", "pub struct AdminAuditQuery", "pub correlation_id: Option<String>"],
    )
    require_file_tokens(
        STORE_SRC / "memory/audit.rs",
        "in-memory admin audit store",
        ["impl AdminAuditStore for InMemoryStore", "sanitize_admin_audit_event", "state.admin_audit.push(stored)", "correlation_id"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_audit/admin.rs",
        "postgres admin audit store",
        ["impl AdminAuditStore for PostgresStore", "INSERT INTO admin_audit_events", "FROM admin_audit_events", "AND ($6::text IS NULL OR correlation_id = $6)"],
    )
    require_file_tokens(
        SERVICE_SRC / "service/audit.rs",
        "service admin audit bridge",
        ["AdminAuditStore", "pub async fn record_admin_audit_event", "self.store.record_admin_audit_event(&event).await?", "pub async fn list_admin_audit_events"],
    )
    require_file_tokens(
        API_SRC / "backend/audit.rs",
        "API admin audit backend",
        ["record_admin_audit_event", "list_admin_audit_events", "Self::InMemory(service) => service.record_admin_audit_event(event).await", "Self::Postgres(service) => service.list_admin_audit_events(query).await"],
    )
    require_file_tokens(
        API_SRC / "routes/admin/audit.rs",
        "API admin audit routes",
        ["pub(crate) async fn list_admin_audit_events", "AdminAuditQuery", "correlation_id: query.correlation_id", "StatusCode::OK"],
    )
    require_file_tokens(
        API_SRC / "support/audit.rs",
        "API admin audit support",
        ["pub(crate) async fn record_admin_audit", "operation: &'static str", "record_admin_audit_event(AdminAuditEvent", "principal_subject: principal.subject.clone()"],
    )
    require_file_tokens(
        API_SRC / "routes/health.rs",
        "API health route",
        ['"service_layer": "pmx_service_server_authoritative_id_bound_admin_audit"'],
    )
    for needle in ["http_postgres_admin_routes_record_audit_events", "admin_audit_events", "KillSwitch", "CancelOrder"]:
        if needle not in pg_test_text:
            fail(f"PostgreSQL API audit E2E missing token: {needle}")
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("missing current gate runner")


def validate_v16_postgres_runtime_provider(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    backend_text = (API_SRC / "backend.rs").read_text()
    health_text = (API_SRC / "routes/health.rs").read_text()
    pg_test_text = rust_file_with_modules_text(API_POSTGRES_E2E_TEST)
    spike_text = SDK_SPIKE_RS.read_text()
    runtime_worker_ref = operation_response_ref(spec, "/v1/runtime/workers", "get", "200")
    if runtime_worker_ref != "#/components/schemas/RuntimeWorkerStatusReport":
        fail("v0.16 runtime workers response must reference RuntimeWorkerStatusReport")
    require_file_tokens(
        STORE_SRC / "model/runtime.rs",
        "store runtime model",
        ["pub struct RuntimeStateQuery", "pub trait RuntimeStateStore", "pub struct RuntimeWorkerStatusReport", "pub trait RuntimeWorkerStatusStore"],
    )
    require_file_tokens(
        STORE_SRC / "memory/runtime/state.rs",
        "in-memory runtime state store",
        ["impl RuntimeStateStore for InMemoryStore", "apply_runtime_worker_observations", "worker_status_from_heartbeats", "global_kill_switch"],
    )
    require_file_tokens(
        STORE_SRC / "memory/runtime/support.rs",
        "in-memory runtime support",
        ["pub fn set_runtime_state_for_test(", "query.state_scope_key()", "runtime_observation_is_fresh", "observations_for_account"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_runtime.rs",
        "postgres runtime state store",
        ["impl RuntimeStateStore for PostgresStore", "IsolationLevel::RepeatableRead", "account_collateral::load_account_state", "worker_rows::load_worker_rows", "apply_runtime_worker_observations", "impl RuntimeControlStore for PostgresStore"],
    )
    require_file_tokens(
        STORE_SRC / "postgres_worker/status.rs",
        "postgres runtime worker status store",
        ["impl RuntimeWorkerStatusStore for PostgresStore", "FROM worker_health", "FROM runtime_worker_observations", "RuntimeWorkerStatusReport"],
    )
    require_file_tokens(
        SERVICE_SRC / "runtime_state/store_backed.rs",
        "service store-backed runtime provider",
        ["pub struct StoreBackedRuntimeStateProvider<S>", "pub fn new(store: S) -> Self", "async fn capture_runtime_state", "load_runtime_state(&query)", "fail_closed_runtime_state(query.required_capabilities)"],
    )
    require_file_tokens(
        SERVICE_SRC / "service_tests/flow.rs",
        "service runtime provider flow tests",
        ["static_runtime_provider_can_reach_ready_plan_but_submit_still_blocks", "assert_eq!(plan.status, PlanStatus::Ready);", "SubmitMode::BlockedDryRun", "SubmitStatus::Blocked"],
    )
    require_file_tokens(
        API_SRC / "backend/runtime.rs",
        "API runtime backend",
        ["list_runtime_worker_status", "set_account_kill_switch", "set_global_kill_switch", ".store()", ".set_account_kill_switch(account_id, enabled, reason)", ".set_global_kill_switch(enabled, reason)"],
    )
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
    validate_absent_tokens(
        spike_text,
        "SDK spike read-only smoke",
        ["read-only smoke must not depend on signer credentials"],
    )
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
    validate_absent_tokens(migration, "v0.20 migration", ["CREATE TABLE IF NOT EXISTS plan_summaries"])
    validate_absent_tokens(postgres, "v0.20 PostgresStore", ["INSERT INTO plan_summaries", '"plan_summaries"'])
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


def validate_store_and_backend_structure() -> None:
    store_lib = (STORE_SRC / "lib.rs").read_text()
    postgres_rs = (STORE_SRC / "postgres.rs").read_text()
    service_lib = (SERVICE_SRC / "lib.rs").read_text()
    api_backend_audit = (API_SRC / "backend/audit.rs").read_text()
    api_backend_sign_only = (API_SRC / "backend/sign_only.rs").read_text()
    api_backend_runtime = (API_SRC / "backend/runtime.rs").read_text()

    require_tokens(
        store_lib,
        "pmx-store module boundary",
        [
            "pub mod postgres;",
            "mod postgres_audit;",
            "mod postgres_execution;",
            "mod postgres_idempotency;",
            "mod postgres_runtime;",
            "mod postgres_sign_only;",
            "mod postgres_worker;",
            "pub use postgres::PostgresStore;",
        ],
    )
    require_tokens(
        postgres_rs,
        "PostgresStore structure",
        [
            "pub struct PostgresStore",
            "database_url: String",
            "pub async fn connect",
            'simple_query("SELECT 1")',
            "pub async fn apply_schema",
            "pub async fn applied_schema_migrations",
            "pub(crate) async fn client",
            "tokio_postgres::connect(&self.database_url, NoTls)",
            'client.batch_execute("ROLLBACK")',
        ],
    )
    require_tokens(
        service_lib,
        "pmx-service module boundary",
        [
            "mod runtime_state;",
            "mod runtime_worker;",
            "mod sign_only;",
            "mod submit;",
            "pub use runtime_state::*;",
            "pub use runtime_worker::*;",
            "pub use sign_only::*;",
            "pub use submit::*;",
        ],
    )
    require_tokens(
        api_backend_audit,
        "pmx-api audit backend bridge",
        [
            "impl ServiceBackend",
            "record_admin_audit_event",
            "list_admin_audit_events",
            "Self::InMemory(service) => service.record_admin_audit_event(event).await",
            "Self::Postgres(service) => service.record_admin_audit_event(event).await",
            "Self::InMemory(service) => service.list_admin_audit_events(query).await",
            "Self::Postgres(service) => service.list_admin_audit_events(query).await",
        ],
    )
    require_tokens(
        api_backend_sign_only,
        "pmx-api sign-only backend bridge",
        [
            "record_standard_sign_only_construction",
            "list_sign_only_lifecycle_events",
            "Self::InMemory(service) => service.record_standard_sign_only_construction(req).await",
            "Self::Postgres(service) => service.record_standard_sign_only_construction(req).await",
            "Self::InMemory(service) => service.list_sign_only_lifecycle_events(query).await",
            "Self::Postgres(service) => service.list_sign_only_lifecycle_events(query).await",
        ],
    )
    require_tokens(
        api_backend_runtime,
        "pmx-api runtime backend bridge",
        [
            "list_runtime_worker_status",
            "set_account_kill_switch",
            "set_global_kill_switch",
            "Self::InMemory(service) => service.list_runtime_worker_status(query).await",
            "Self::Postgres(service) => service.list_runtime_worker_status(query).await",
            ".store()",
            ".set_account_kill_switch(account_id, enabled, reason)",
            ".set_global_kill_switch(enabled, reason)",
        ],
    )


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
