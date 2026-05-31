from __future__ import annotations

import re
import tomllib

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


def validate_required_groups(groups: dict[str, tuple[str, list[str]]]) -> None:
    for label, (text, needles) in groups.items():
        require_tokens(text, label, needles)


def rust_module_names(text: str, prefix: str = "mod") -> set[str]:
    pattern = rf"(?m)^\s*{re.escape(prefix)}\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;"
    return set(re.findall(pattern, text))


def rust_pub_use_targets(text: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*pub\s+use\s+([a-zA-Z_][a-zA-Z0-9_]*)::", text))


def rust_async_fn_names(text: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*pub(?:\([^)]*\))?\s+async\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)", text))


def rust_struct_field_names(text: str, struct_name: str) -> set[str]:
    pattern = rf"(?s)struct\s+{re.escape(struct_name)}[^\{{]*\{{(.*?)\n\}}"
    match = re.search(pattern, text)
    if not match:
        fail(f"missing Rust struct: {struct_name}")
    body = match.group(1)
    return set(
        re.findall(
            r"(?m)^\s*(?:pub\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*:",
            body,
        )
    )


def ensure_match_arms(text: str, label: str, fn_name: str, required_arms: list[str]) -> None:
    marker = f"async fn {fn_name}"
    start = text.find(marker)
    if start == -1:
        fail(f"{label} missing async fn: {fn_name}")
    next_match = re.search(r"\n\s*(?:pub(?:\([^)]*\))?\s+)?async fn ", text[start + len(marker) :])
    end = len(text) if not next_match else start + len(marker) + next_match.start()
    body = text[start:end]
    for arm in required_arms:
        if arm not in body:
            fail(f"{label} missing token: {arm}")


def rust_trait_method_signatures(text: str, trait_name: str) -> set[str]:
    pattern = rf"(?s)trait\s+{re.escape(trait_name)}[^\{{]*\{{(.*?)\n\}}"
    match = re.search(pattern, text)
    if not match:
        fail(f"missing Rust trait: {trait_name}")
    body = match.group(1)
    return set(
        re.findall(
            r"(?m)^\s*async\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            body,
        )
    )


def cargo_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except FileNotFoundError:
        fail(f"missing Cargo/TOML file: {path.relative_to(ROOT)}")


def validate_v04_source_landings() -> None:
    if not API_E2E_TEST.exists():
        fail("missing HTTP/auth/fake E2E integration test source")
    smoke_text = (API_E2E_TEST.parent / "http_and_fake_e2e/smoke.rs").read_text()
    for fn_name in ["http_auth_and_fake_e2e_smoke"]:
        if fn_name not in smoke_text:
            fail(f"HTTP/auth fake E2E smoke missing token: {fn_name}")
    for status in ["StatusCode::UNAUTHORIZED", "StatusCode::FORBIDDEN", "StatusCode::ACCEPTED"]:
        if status not in smoke_text:
            fail(f"HTTP/auth fake E2E smoke missing token: {status}")
    advisory_text = (STORE_SRC / "model/advisory.rs").read_text()
    if not re.search(r"pub\s+struct\s+AdvisoryLockKey\b", advisory_text):
        fail("pmx-store advisory lock model missing token: pub struct AdvisoryLockKey")
    if not re.search(r"pub\s+fn\s+advisory_lock_key\s*\(", advisory_text):
        fail("pmx-store advisory lock model missing token: pub fn advisory_lock_key")
    for needle in ["const FNV_OFFSET", "const FNV_PRIME", "i64::from_ne_bytes(hash.to_ne_bytes())"]:
        if needle not in advisory_text:
            fail(f"pmx-store advisory lock model missing token: {needle}")
    postgres_text = (STORE_SRC / "postgres.rs").read_text()
    if not re.search(r"pub\s+struct\s+PostgresStore\b", postgres_text):
        fail("pmx-store postgres adapter missing token: pub struct PostgresStore")
    if "tokio_postgres::connect(&self.database_url, NoTls)" not in postgres_text:
        fail("pmx-store postgres adapter missing token: tokio_postgres::connect(&self.database_url, NoTls)")
    if not POSTGRES_RS.exists():
        fail("missing PostgreSQL repository adapter source")
    idempotency_adapter = (STORE_SRC / "postgres_idempotency.rs").read_text()
    if "impl IdempotencyStore for PostgresStore" not in idempotency_adapter:
        fail("postgres idempotency adapter missing token: impl IdempotencyStore for PostgresStore")
    ensure_match_arms(
        idempotency_adapter.replace("async fn finish_submit_attempt", "\nasync fn finish_submit_attempt"),
        "postgres idempotency adapter",
        "begin_submit_attempt",
        ["begin::begin_submit_attempt(", "request_fingerprint"],
    )
    ensure_match_arms(
        idempotency_adapter.replace("async fn finish_submit_attempt", "\nasync fn finish_submit_attempt"),
        "postgres idempotency adapter",
        "finish_submit_attempt",
        ["finish::finish_submit_attempt(self, attempt).await"],
    )
    begin_text = (STORE_SRC / "postgres_idempotency/begin.rs").read_text()
    for needle in ["SELECT pg_advisory_xact_lock($1)", 'status == "PROCEEDING"', "IdempotencyAction::InProgress", "IdempotencyAction::Proceed"]:
        if needle not in begin_text:
            fail(f"postgres idempotency begin path missing token: {needle}")
    idempotency_tests = (STORE_SRC / "postgres_tests/idempotency.rs").read_text()
    for test_name in ["same_request_replay_is_persisted", "fingerprint_mismatch_is_conflict"]:
        if test_name not in idempotency_tests:
            fail(f"postgres idempotency tests missing token: {test_name}")
    reservation_tests = (STORE_SRC / "postgres_tests/receipt_reservation.rs").read_text()
    for test_name in ["reservation_double_spend_is_prevented_concurrently", "remote_unknown_is_persisted_conservatively"]:
        if test_name not in reservation_tests:
            fail(f"postgres receipt/reservation tests missing token: {test_name}")


def validate_v07_source_landings() -> None:
    traits_text = (GATEWAY_SRC / "traits.rs").read_text()
    for trait_name in ["SignerProvider", "ClobGateway", "RemoteReconcileReader"]:
        if f"trait {trait_name}" not in traits_text:
            fail(f"gateway traits missing token: pub trait {trait_name}")
    try:
        signer_provider_methods = rust_trait_method_signatures(traits_text, "SignerProvider")
        clob_gateway_methods = rust_trait_method_signatures(traits_text, "ClobGateway")
        reconcile_reader_methods = rust_trait_method_signatures(traits_text, "RemoteReconcileReader")
    except SystemExit as exc:
        fail(f"gateway traits malformed: {exc}")
    if signer_provider_methods != {"signer_for_account"}:
        fail(f"gateway traits missing token: pub trait SignerProvider")
    if not {"post_order", "cancel_order", "get_order", "get_open_orders"}.issubset(clob_gateway_methods):
        fail("gateway traits missing token: async fn post_order(&self, order: &SignedOrderEnvelope)")
    if reconcile_reader_methods != {"read_remote_order_observations"}:
        fail("gateway traits missing token: pub trait RemoteReconcileReader")
    signer_text = (GATEWAY_SRC / "signer.rs").read_text()
    for needle in [
        "pub struct DeterministicTestSignerProvider",
        "pub struct DeterministicTestSigner",
        "pub struct SignerProviderConfig",
        "allow_local_private_key_material: false",
        "require_remote_signer_in_production: true",
    ]:
        if needle not in signer_text:
            fail(f"gateway signer provider missing token: {needle}")
    signer_tests = (GATEWAY_SRC / "tests/signer.rs").read_text()
    for test_name in ["disabled_signer_provider_refuses_to_materialize_signer", "signer_provider_defaults_are_production_conservative"]:
        if test_name not in signer_tests:
            fail(f"gateway signer tests missing token: {test_name}")
    post_cancel_tests = (GATEWAY_SRC / "tests/post_cancel.rs").read_text()
    for test_name in ["deterministic_signer_provider_posts_reads_and_cancels", "fake_gateway_surfaces_remote_unknown_without_local_success"]:
        if test_name not in post_cancel_tests:
            fail(f"gateway post/cancel tests missing token: {test_name}")
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
    adapter_toml = cargo_toml(SDK_ADAPTER_TOML)
    adapter_text = SDK_ADAPTER_RS.read_text()
    for needle in [
        "Official Polymarket SDK adapter boundary",
        "sign-only dry-runs require explicit opt-in",
        "live submit requires the explicit `live-submit` feature",
        "pub use gates::*",
    ]:
        if needle not in adapter_text:
            fail(f"official SDK adapter root missing token: {needle}")
    adapter_modules = rust_module_names(adapter_text, "mod")
    for module_name in ["gates", "lifecycle", "liveness", "mapping", "model", "redaction", "sdk_runtime", "standard_sign_only"]:
        if module_name not in adapter_modules:
            fail(f"official SDK adapter root missing token: mod {module_name};")
    if "gates" not in rust_pub_use_targets(adapter_text):
        fail("official SDK adapter root missing token: pub use gates::*")
    feature_names = set(adapter_toml.get("features", {}).keys())
    for feature_name in ["sdk-typecheck", "authenticated-smoke", "sign-only-dry-run", "live-submit"]:
        if feature_name not in feature_names:
            fail(f"official adapter must expose feature: {feature_name}")
    sdk_dep = adapter_toml.get("dependencies", {}).get("polymarket_client_sdk_v2", {})
    if sdk_dep.get("version") != "=0.6.0-canary.1":
        fail("official adapter must pin the official SDK canary explicitly")
    bins = {entry.get("name"): entry for entry in adapter_toml.get("bin", [])}
    if bins.get("pmx-real-funds-canary", {}).get("required-features") != ["live-submit"]:
        fail("official adapter must gate pmx-real-funds-canary behind live-submit")
    config_text = (SDK_ADAPTER_SRC / "model/config.rs").read_text()
    for needle in [
        "pub struct OfficialSdkAdapterConfig",
        "allow_sign_only_dry_run: false",
        "allow_live_submit: false",
        "allow_real_funds_canary: false",
        "pub struct OfficialSdkStandardSignOnlyProfile",
    ]:
        if needle not in config_text:
            fail(f"official SDK adapter config missing token: {needle}")
    smoke_text = (SDK_ADAPTER_SRC / "gates/smoke.rs").read_text()
    for fn_name in ["validate_authenticated_non_trading_smoke", "validate_sign_only_dry_run"]:
        if fn_name not in smoke_text:
            fail(f"official SDK smoke gates missing token: {fn_name}")
    for env_name in ["ENV_RUN_AUTHENTICATED_SMOKE", "ENV_ALLOW_SIGN_ONLY_DRY_RUN", "ENV_ALLOW_LIVE_SUBMIT"]:
        if env_name not in smoke_text:
            fail(f"official SDK smoke gates missing token: {env_name}")
    sign_only_text = (SDK_ADAPTER_SRC / "sdk_runtime/sign_only/dry_run.rs").read_text()
    for needle in ["SignOnlyDryRunReceipt", "validate_sign_only_dry_run(config, &credentials)?", "signed_order_ref = format!(", "posted: false"]:
        if needle not in sign_only_text:
            fail(f"official SDK sign-only dry run missing token: {needle}")
    feature_tests = (SDK_ADAPTER_SRC / "tests/feature_gated.rs").read_text()
    for test_name in [
        "authenticated_non_trading_smoke_executes_when_enabled",
        "sign_only_dry_run_executes_when_enabled",
        "env_helpers_trim_values_and_accept_case_insensitive_true",
        "assert!(!receipt.posted);",
    ]:
        if test_name not in feature_tests:
            fail(f"official SDK feature-gated tests missing token: {test_name}")
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
    service_root_text = SERVICE_RS.read_text()
    module_names = rust_module_names(service_root_text)
    if not {"binding", "plan_flow", "submit"}.issubset(module_names):
        fail("pmx-service crate root missing required modules")
    pub_use_targets = rust_pub_use_targets(service_root_text)
    if not {"binding", "submit"}.issubset(pub_use_targets):
        fail("pmx-service crate root missing required pub use re-exports")
    hash_inputs_text = (SERVICE_SRC / "binding/hash_inputs.rs").read_text()
    try:
        plan_hash_fields = rust_struct_field_names(hash_inputs_text, "PlanHashInput")
        approval_hash_fields = rust_struct_field_names(hash_inputs_text, "ApprovalHashInput")
    except SystemExit as exc:
        fail(f"service binding hash inputs malformed: {exc}")
    if not {
        "approval_id",
        "approval_hash",
        "executor_version",
        "contract_version",
    }.issubset(plan_hash_fields):
        fail("service binding hash inputs missing required PlanHashInput fields")
    if "bound_snapshot_hash" not in approval_hash_fields:
        fail("service binding hash inputs missing required ApprovalHashInput fields")
    require_tokens(
        hash_inputs_text,
        "service binding hash inputs",
        ["impl<'a> From<&'a ApprovalReceipt> for ApprovalHashInput<'a>", "impl<'a> From<&'a ExecutionPlanSummary> for PlanHashInput<'a>"],
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
    bootstrap_text = (API_SRC / "routes/bootstrap.rs").read_text()
    route_paths = set(re.findall(r'\.route\(\s*"([^"]+)"', bootstrap_text))
    if not {
        "/v1/plans/compile",
        "/v1/submissions",
        "/v1/admin/cancel-order",
        "/v1/admin/reconcile",
    }.issubset(route_paths):
        fail("API bootstrap routes missing required paths")
    require_tokens(
        bootstrap_text,
        "API bootstrap routes",
        ["pub async fn try_postgres_app(", "AppState::postgres(store)"],
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
    audit_model_text = (STORE_SRC / "model/audit.rs").read_text()
    try:
        audit_event_fields = rust_struct_field_names(audit_model_text, "AdminAuditEvent")
        audit_query_fields = rust_struct_field_names(audit_model_text, "AdminAuditQuery")
        audit_store_methods = rust_trait_method_signatures(audit_model_text, "AdminAuditStore")
    except SystemExit as exc:
        fail(f"store admin audit model malformed: {exc}")
    if "correlation_id" not in audit_event_fields or "correlation_id" not in audit_query_fields:
        fail("store admin audit model missing correlation_id fields")
    if audit_store_methods != {"record_admin_audit_event", "list_admin_audit_events"}:
        fail("store admin audit model missing AdminAuditStore methods")
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
    runtime_model_text = (STORE_SRC / "model/runtime.rs").read_text()
    try:
        runtime_state_query_fields = rust_struct_field_names(runtime_model_text, "RuntimeStateQuery")
        runtime_worker_status_report_fields = rust_struct_field_names(
            runtime_model_text, "RuntimeWorkerStatusReport"
        )
        runtime_state_methods = rust_trait_method_signatures(runtime_model_text, "RuntimeStateStore")
        runtime_worker_methods = rust_trait_method_signatures(
            runtime_model_text, "RuntimeWorkerStatusStore"
        )
        runtime_control_methods = rust_trait_method_signatures(
            runtime_model_text, "RuntimeControlStore"
        )
    except SystemExit as exc:
        fail(f"store runtime model malformed: {exc}")
    if not {"account_id", "condition_id", "collateral_profile_id", "required_capabilities"}.issubset(
        runtime_state_query_fields
    ):
        fail("store runtime model missing RuntimeStateQuery fields")
    if runtime_worker_status_report_fields != {"heartbeats", "observations"}:
        fail("store runtime model missing RuntimeWorkerStatusReport fields")
    if runtime_state_methods != {"load_runtime_state"}:
        fail("store runtime model missing RuntimeStateStore methods")
    if runtime_worker_methods != {"list_runtime_worker_status"}:
        fail("store runtime model missing RuntimeWorkerStatusStore methods")
    if runtime_control_methods != {"set_account_kill_switch", "set_global_kill_switch"}:
        fail("store runtime model missing RuntimeControlStore methods")
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
    require_file_tokens(
        SDK_ADAPTER_SRC / "redaction.rs",
        "v0.19 adapter redaction",
        ["pub fn redact_sensitive_text", "pub fn redact_normalized_error", "gateway_error_from_normalized_sdk_error", "looks_like_hex_private_key", "redact_assignment_value"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "model/constants.rs",
        "v0.19 adapter constants",
        ['pub const REDACTED: &str = "[REDACTED]";'],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "liveness/error_normalization.rs",
        "v0.19 liveness error normalization",
        ["pub fn normalize_sdk_error", "OfficialSdkErrorCategory::RemoteRejected", "OfficialSdkErrorCategory::WebSocketFailed", "OfficialSdkErrorCategory::AuthenticationFailed"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "tests/liveness_errors.rs",
        "v0.19 adapter redaction tests",
        ["gateway_error_conversion_redacts_sensitive_message", "normalized_error_redaction_covers_remote_unknown_messages", "redacts_private_key_like_hex_tokens", "redacts_named_secret_assignments"],
    )
    if not LIVE_SUBMIT_GUARD.exists():
        fail("missing v0.19 live-submit static guard")
    guard_text = LIVE_SUBMIT_GUARD.read_text()
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
    require_file_tokens(
        SDK_ADAPTER_SRC / "mapping/validation.rs",
        "v0.20 SDK mapping validation",
        ["validate_token_id", "validate_limit_price_for_sdk", "validate_positive_quantity_for_sdk"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "tests/liveness_errors.rs",
        "v0.20 SDK liveness tests",
        ["normalized_error_redaction_covers_remote_unknown_messages"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/health/signal/model.rs",
        "v0.20 runtime signal model",
        ["pub enum RuntimeSignal", "ReconcileBacklog", "remote_unknown_orders: u32"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/health/signal/breakdown.rs",
        "v0.20 runtime breakdown",
        ["pub fn runtime_breakdown_from_signals", "RuntimeSignal::Geoblock", "RuntimeSignal::ReconcileBacklog"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/runtime_tests/breakdown_loop/capabilities/blocking.rs",
        "v0.20 runtime evaluation tests",
        ["geoblock_unknown_and_reconcile_backlog_block_submit"],
    )
    require_file_tokens(
        CORE_SRC / "domain/lifecycle/order.rs",
        "v0.20 core order lifecycle",
        ["cancel_state_from_lifecycle", "lifecycle_requires_reconcile", "OrderLifecycleState::RemoteUnknown", "OrderLifecycleState::PartialRemoteUnknown"],
    )
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
    require_file_tokens(
        CORE_SRC / "domain/lifecycle/sign_only.rs",
        "v0.21 sign-only lifecycle core",
        ["pub enum SignOnlyLifecycleState", "transition_sign_only_lifecycle", "sign_only_lifecycle_has_remote_side_effect", "pub client_event_id: Option<String>"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "lifecycle.rs",
        "v0.21 sign-only lifecycle adapter",
        ["sign_only_lifecycle_records_from_receipt", "no_remote_side_effect: true", "sign-only receipt unexpectedly indicates remote posting", "signed_order_ref: Some(receipt.signed_order_ref.clone())"],
    )
    require_file_tokens(
        SDK_ADAPTER_SRC / "tests/sign_only.rs",
        "v0.21 sign-only lifecycle tests",
        ["sign_only_lifecycle_records_are_persistable_and_non_mutating", "sign_only_lifecycle_rejects_posted_receipt", "standard_sign_only_construction_emits_only_digest_ref_and_lifecycle"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/health/action.rs",
        "v0.21 runtime worker action model",
        ["pub struct RuntimeWorkerAction", "worker_actions_from_runtime_signals", "should_fail_closed: health.blocks_submit()", "pub struct RuntimeWorkerStoreWrite"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/health/worker.rs",
        "v0.21 runtime worker kinds",
        ["pub enum RuntimeWorkerKind"],
    )
    require_file_tokens(
        EXECUTOR / "crates/pmx-runtime/src/runtime_tests/breakdown_loop/capabilities/groups.rs",
        "v0.21 runtime worker tests",
        ["worker_actions_mark_stale_runtime_inputs_as_fail_closed_updates"],
    )
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
    store_private_modules = rust_module_names(store_lib, "mod")
    for module_name in [
        "postgres_audit",
        "postgres_execution",
        "postgres_idempotency",
        "postgres_runtime",
        "postgres_sign_only",
        "postgres_worker",
    ]:
        if module_name not in store_private_modules:
            fail(f"pmx-store module boundary missing token: mod {module_name};")
    if "postgres" not in rust_module_names(store_lib, "pub mod"):
        fail("pmx-store module boundary missing token: pub mod postgres;")
    if "postgres" not in rust_pub_use_targets(store_lib) or "PostgresStore" not in store_lib:
        fail("pmx-store module boundary missing token: pub use postgres::PostgresStore;")

    postgres_async_fns = rust_async_fn_names(postgres_rs)
    for fn_name in ["connect", "apply_schema", "applied_schema_migrations"]:
        if fn_name not in postgres_async_fns:
            fail(f"PostgresStore structure missing token: pub async fn {fn_name}")
    if not re.search(r"pub\s+struct\s+PostgresStore\b", postgres_rs):
        fail("PostgresStore structure missing token: pub struct PostgresStore")
    if "database_url: String" not in postgres_rs:
        fail("PostgresStore structure missing token: database_url: String")
    if "pub(crate) async fn client" not in postgres_rs:
        fail("PostgresStore structure missing token: pub(crate) async fn client")
    for needle in [
        'simple_query("SELECT 1")',
        "tokio_postgres::connect(&self.database_url, NoTls)",
        'client.batch_execute("ROLLBACK")',
    ]:
        if needle not in postgres_rs:
            fail(f"PostgresStore structure missing token: {needle}")

    service_modules = rust_module_names(service_lib, "mod")
    for module_name in ["runtime_state", "runtime_worker", "sign_only", "submit"]:
        if module_name not in service_modules:
            fail(f"pmx-service module boundary missing token: mod {module_name};")
    service_reexports = rust_pub_use_targets(service_lib)
    for module_name in ["runtime_state", "runtime_worker", "sign_only", "submit"]:
        if module_name not in service_reexports:
            fail(f"pmx-service module boundary missing token: pub use {module_name}::*;")

    ensure_match_arms(
        api_backend_audit,
        "pmx-api audit backend bridge",
        "record_admin_audit_event",
        [
            "Self::InMemory(service) => service.record_admin_audit_event(event).await",
            "Self::Postgres(service) => service.record_admin_audit_event(event).await",
        ],
    )
    ensure_match_arms(
        api_backend_audit,
        "pmx-api audit backend bridge",
        "list_admin_audit_events",
        [
            "Self::InMemory(service) => service.list_admin_audit_events(query).await",
            "Self::Postgres(service) => service.list_admin_audit_events(query).await",
        ],
    )

    ensure_match_arms(
        api_backend_sign_only,
        "pmx-api sign-only backend bridge",
        "record_standard_sign_only_construction",
        [
            "Self::InMemory(service) => service.record_standard_sign_only_construction(req).await",
            "Self::Postgres(service) => service.record_standard_sign_only_construction(req).await",
        ],
    )
    ensure_match_arms(
        api_backend_sign_only,
        "pmx-api sign-only backend bridge",
        "list_sign_only_lifecycle_events",
        [
            "Self::InMemory(service) => service.list_sign_only_lifecycle_events(query).await",
            "Self::Postgres(service) => service.list_sign_only_lifecycle_events(query).await",
        ],
    )

    ensure_match_arms(
        api_backend_runtime,
        "pmx-api runtime backend bridge",
        "list_runtime_worker_status",
        [
            "Self::InMemory(service) => service.list_runtime_worker_status(query).await",
            "Self::Postgres(service) => service.list_runtime_worker_status(query).await",
        ],
    )
    ensure_match_arms(
        api_backend_runtime,
        "pmx-api runtime backend bridge",
        "set_account_kill_switch",
        [
            ".store()",
            ".set_account_kill_switch(account_id, enabled, reason)",
            "Self::InMemory(service)",
            "Self::Postgres(service)",
        ],
    )
    ensure_match_arms(
        api_backend_runtime,
        "pmx-api runtime backend bridge",
        "set_global_kill_switch",
        [
            ".store()",
            ".set_global_kill_switch(enabled, reason)",
            "Self::InMemory(service)",
            "Self::Postgres(service)",
        ],
    )


def validate_v23_lifecycle_query_and_hardening(spec: dict | None = None) -> None:
    if spec is None:
        import yaml

        spec = yaml.safe_load(OPENAPI.read_text())
    core = rust_source_text(CORE_SRC)
    store = rust_source_text(STORE_SRC)
    postgres = rust_source_text(STORE_SRC)
    service = rust_source_text(SERVICE_SRC)
    policy = (EXECUTOR / "crates/pmx-policy/src/lib.rs").read_text()
    sql = SQL.read_text()
    gate = (EXECUTOR / "validation/run_current_gates_impl.sh").read_text()
    api_runtime_read = (API_SRC / "routes/read/runtime.rs").read_text()
    api_reconcile_local = (API_SRC / "routes/admin/reconcile/local.rs").read_text()
    api_support_error = (API_SRC / "support/error.rs").read_text()
    api_support_audit = (API_SRC / "support/audit.rs").read_text()
    api_cancel_route = (API_SRC / "routes/admin/cancel.rs").read_text()
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
        "api runtime read route": (api_runtime_read, ["pub(crate) async fn list_runtime_worker_status", "Query(query): Query<RuntimeWorkerStatusListQuery>", "list_runtime_worker_status(RuntimeWorkerStatusQuery", "StatusCode::OK"]),
        "api reconcile local route": (api_reconcile_local, ["pub(crate) async fn reconcile_order_local", "api_error_with_correlation", "record_admin_audit(", "ReconcileOrderLocalResponse", "no_remote_side_effect: true"]),
        "api support error": (api_support_error, ["correlation_id_from_headers", "api_error_with_correlation"]),
        "api support audit": (api_support_audit, ["pub(crate) async fn record_admin_audit", "operation: &'static str", "AdminAuditEvent"]),
        "api cancel route": (api_cancel_route, ["redacted_payload_envelope", "payload: redacted_payload_envelope(", "CancelReceipt"]),
        "gate": (gate, ["run_current_gates.sh", "check_current_lifecycle_api.py", "check_version_consistency.py", "check_docs_evidence_governance.py", "write_current_evidence_manifest.py", "check_runtime_worker_status_query.py", "42-runtime-worker-status-query.log", "evidence/current"]),
    }
    validate_required_groups(required_by_file)
    if core.count("pub client_event_id: Option<String>") != 1:
        fail("current SignOnlyLifecycleRecord must have exactly one client_event_id field")
    if store.count("pub observed_at: Option<DateTime<Utc>>") != 1:
        fail("current RuntimeWorkerObservation must have exactly one observed_at field")
    openapi_text = OPENAPI.read_text()
    if "SignedOrderEnvelope" in openapi_text or "signed_payload" in openapi_text:
        fail("current public OpenAPI must not expose signed payload internals")
