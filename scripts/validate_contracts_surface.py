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
