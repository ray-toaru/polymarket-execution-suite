from __future__ import annotations

import re
from collections.abc import Iterator

from validate_contracts_support import (
    API_SRC,
    CONTROL,
    CORE_SRC,
    EXPECTED_202_PATHS,
    FORBIDDEN_PUBLIC_TOKENS,
    PY_MODEL_BY_SCHEMA,
    SQL,
    fail,
    import_control_models,
    rust_handler_body,
    rust_routes,
    rust_source_text,
)
from validate_contracts_executor import (
    operation_request_ref,
    operation_response_ref,
    schema_property_names,
    schema_required_names,
)


def iter_json_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key)
            yield from iter_json_strings(nested)
        return
    if isinstance(value, list):
        for nested in value:
            yield from iter_json_strings(nested)


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


def validate_critical_contract_shapes(spec: dict) -> None:
    expected_refs = {
        ("/v1/submissions", "post", "request"): "#/components/schemas/SubmitRequest",
        ("/v1/submissions", "post", "202"): "#/components/schemas/SubmitReceipt",
        ("/v1/admin/kill-switch", "post", "request"): "#/components/schemas/KillSwitchRequest",
        ("/v1/admin/kill-switch", "post", "202"): "#/components/schemas/KillSwitchReceipt",
        ("/v1/admin/cancel-order", "post", "request"): "#/components/schemas/CancelOrderRequest",
        ("/v1/admin/cancel-order", "post", "202"): "#/components/schemas/CancelReceipt",
        ("/v1/admin/reconcile", "post", "request"): "#/components/schemas/ReconcileRequest",
        ("/v1/admin/reconcile", "post", "202"): "#/components/schemas/ReconcileReport",
    }
    for (path, method, kind), expected_ref in expected_refs.items():
        actual_ref = operation_request_ref(spec, path, method) if kind == "request" else operation_response_ref(spec, path, method, kind)
        if actual_ref != expected_ref:
            fail(f"critical contract {method.upper()} {path} {kind} must reference {expected_ref}, got {actual_ref}")

    exact_required = {
        "SubmitRequest": {"execution_id", "plan_hash", "idempotency_key", "mode"},
        "SubmitReceipt": {"execution_id", "receipt_id", "status", "executor_version", "contract_version"},
        "KillSwitchRequest": {"scope", "enabled", "reason"},
        "KillSwitchReceipt": {"scope", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"},
        "CancelOrderRequest": {"account_id", "order_id", "reason"},
        "CancelReceipt": {"cancel_id", "order_id", "state"},
        "ReconcileRequest": {"account_id", "execution_id", "reason"},
        "ReconcileReport": {"reconcile_id", "status", "checked_orders", "findings"},
    }
    exact_props = {
        "SubmitRequest": {"execution_id", "plan_hash", "idempotency_key", "mode"},
        "SubmitReceipt": {"execution_id", "receipt_id", "status", "executor_version", "contract_version"},
        "KillSwitchRequest": {"scope", "account_id", "enabled", "reason"},
        "KillSwitchReceipt": {"scope", "account_id", "enabled", "changed_at", "effective_at", "state_version", "persisted", "reason"},
        "CancelOrderRequest": {"account_id", "execution_id", "order_id", "reason"},
        "CancelReceipt": {"cancel_id", "order_id", "state"},
        "ReconcileRequest": {"account_id", "execution_id", "order_id", "reason", "remote_observation"},
        "ReconcileReport": {"reconcile_id", "status", "checked_orders", "findings"},
    }
    for schema_name, expected in exact_required.items():
        actual = schema_required_names(spec, schema_name)
        if actual != expected:
            fail(f"critical contract schema {schema_name} required fields changed: expected {sorted(expected)} got {sorted(actual)}")
    for schema_name, expected in exact_props.items():
        actual = schema_property_names(spec, schema_name)
        if actual != expected:
            fail(f"critical contract schema {schema_name} properties changed: expected {sorted(expected)} got {sorted(actual)}")


def validate_no_public_forbidden_tokens(spec: dict) -> None:
    public_tokens = set(iter_json_strings(spec))
    for token in FORBIDDEN_PUBLIC_TOKENS:
        if token in public_tokens:
            fail(f"forbidden token in public OpenAPI: {token}")
    for py in (CONTROL / "src").rglob("*.py"):
        text = py.read_text()
        for token in FORBIDDEN_PUBLIC_TOKENS:
            if token in text:
                fail(f"forbidden token {token} in control package {py.relative_to(CONTROL.parent)}")


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
    if re.search(r"idempotency_key\s+TEXT\s+PRIMARY\s+KEY", sql):
        fail("idempotency_key must not be a global primary key")
    table_match = re.search(
        r"CREATE TABLE IF NOT EXISTS idempotency_records\s*\((?P<body>.*?)\);\s*",
        sql,
        re.DOTALL,
    )
    if not table_match:
        fail("SQL missing idempotency_records table")
    body = table_match.group("body")
    required_column_patterns = {
        "request_fingerprint TEXT NOT NULL": r"\brequest_fingerprint\s+TEXT\s+NOT\s+NULL\b",
        "submit_attempt INTEGER NOT NULL CHECK (submit_attempt >= 1)": r"\bsubmit_attempt\s+INTEGER\s+NOT\s+NULL\s+CHECK\s*\(\s*submit_attempt\s*>=\s*1\s*\)",
        "UNIQUE(account_id, execution_id, idempotency_key)": r"UNIQUE\s*\(\s*account_id\s*,\s*execution_id\s*,\s*idempotency_key\s*\)",
        "UNIQUE(account_id, execution_id, submit_attempt)": r"UNIQUE\s*\(\s*account_id\s*,\s*execution_id\s*,\s*submit_attempt\s*\)",
    }
    for label, pattern in required_column_patterns.items():
        if not re.search(pattern, body, re.DOTALL):
            fail(f"SQL missing idempotency invariant: {label}")


def validate_rust_deny_unknown_fields() -> None:
    file_structs = {
        API_SRC / "model.rs": [
            "DecisionRequest",
            "CompilePlanRequest",
            "SubmitPlanRequest",
            "CancelOrderRequest",
            "ReconcileOrderLocalRequest",
        ],
        CORE_SRC / "domain/intent.rs": ["TradeIntent", "NormalizedIntent"],
        CORE_SRC / "domain/plan/ops.rs": ["KillSwitchRequest", "ReconcileRequest"],
    }
    for path, struct_names in file_structs.items():
        text = path.read_text()
        for struct_name in struct_names:
            pattern = rf"#\[serde\(deny_unknown_fields\)\]\s*pub struct {struct_name}"
            if not re.search(pattern, text):
                fail(f"Rust DTO {struct_name} missing #[serde(deny_unknown_fields)] in {path.relative_to(CONTROL.parent)}")
