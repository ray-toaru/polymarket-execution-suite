from __future__ import annotations

import json
import re

from validate_contracts_support import (
    CONTROL,
    CORE_SRC,
    EXECUTOR,
    EXCLUDED_PREFIXES,
    OPENAPI,
    ROOT,
    SDK_ADAPTER_SRC,
    fail,
    rust_source_text,
)


def require_existing_paths(paths: list, label: str) -> None:
    for path in paths:
        if not path.exists():
            fail(f"{label} missing: {path.relative_to(ROOT)}")


def validate_absent_tokens(text: str, label: str, tokens: list[str]) -> None:
    for token in tokens:
        if token in text:
            fail(f"{label} contains forbidden token: {token}")


def validate_current_hermes_client_surface() -> None:
    client_text = (CONTROL / "src/hermes_polymarket_executor_adapter/client.py").read_text()
    model_text = (CONTROL / "src/hermes_polymarket_executor_adapter/models.py").read_text()
    for needle in [
        "record_sign_only_lifecycle_event",
        "list_sign_only_lifecycle_events",
        "list_execution_lifecycle_events",
        "list_admin_audit_events",
        "reconcile_order_local",
        "ReconcileOrderLocalResponse",
        "principal_subject: str | None = None",
        "result: str | None = None",
        "execution_id: str | None = None",
        "X-Correlation-Id",
    ]:
        if needle not in client_text:
            fail(f"Hermes current client surface missing token: {needle}")
    for needle in [
        "class SignOnlyLifecycleRecord",
        "client_event_id",
        "class RedactedPayloadEnvelope",
        "payload: RedactedPayloadEnvelope",
        "class ExecutionLifecycleEvent",
        "class AdminAuditEvent",
        "class OrderLifecycleDivergence",
        "class ReconcileOrderLocalResponse",
        "sign-only lifecycle records must not contain remote side effects",
    ]:
        if needle not in model_text:
            fail(f"Hermes current model surface missing token: {needle}")


def validate_current_evidence_manifest_guard() -> None:
    manifest = EXECUTOR / "validation/templates/evidence_manifest.template.json"
    current_manifest = EXECUTOR / "evidence/current/manifest.json"
    guard = EXECUTOR / "validation/check_current_evidence_manifest.py"
    governance_guard = EXECUTOR / "validation/check_docs_evidence_governance.py"
    writer = EXECUTOR / "validation/write_current_evidence_manifest.py"
    if not manifest.exists():
        fail("current evidence manifest template missing from validation/templates")
    if not guard.exists():
        fail("current evidence manifest guard missing")
    if not governance_guard.exists():
        fail("current docs/evidence governance guard missing")
    if not writer.exists():
        fail("current evidence manifest writer missing")
    data = json.loads(manifest.read_text())
    expected_version = (ROOT / "VERSION").read_text().strip()
    if data.get("version") != expected_version:
        fail(f"current evidence manifest template must use version {expected_version}")
    if data.get("canonical_evidence_dir") != "polymarket-execution-engine/evidence/current":
        fail("current evidence manifest template must point to evidence/current")
    if not current_manifest.exists():
        fail("current evidence manifest missing")
    if data.get("release_decision", {}).get("validated_release") is not False:
        fail("current evidence template must not mark validated_release=true")
    for section in [
        "rust_workspace_validation",
        "postgres_validation",
        "sdk_adapter_validation",
        "credentialed_non_trading_validation",
    ]:
        if data.get(section, {}).get("status") != "pending":
            fail(f"current evidence template {section} must stay pending")
    guard_text = guard.read_text()
    for needle in [
        "validated_release=true",
        "non-pass evidence sections",
        "artifact_kind=validated_release",
        "artifact.sha256",
    ]:
        if needle not in guard_text:
            fail(f"current evidence guard missing token: {needle}")
    governance_text = governance_guard.read_text()
    for needle in [
        "docs/evidence governance guard passed",
        "canonical evidence manifest",
        "archive-excluded-from-release-package",
    ]:
        if needle not in governance_text:
            fail(f"current docs/evidence governance guard missing token: {needle}")
    writer_text = writer.read_text()
    for needle in [
        "canonical_evidence_dir",
        "artifact",
        "sha256",
        "generated_from_gate_logs",
        "runtime_worker_status_validation",
    ]:
        if needle not in writer_text:
            fail(f"current evidence manifest writer missing token: {needle}")


def validate_current_docs_and_release_governance() -> None:
    release = json.loads((EXECUTOR / "release/manifest.json").read_text())
    expected_archive_prefixes = {
        "docs/archive",
        "external_reviews",
        "validation/archive",
        "polymarket-execution-engine/validation/archive",
        "polymarket-execution-engine/evidence/archive",
        "polymarket-execution-engine/docs/archive",
    }
    if not expected_archive_prefixes.issubset(EXCLUDED_PREFIXES):
        fail("release policy missing expected archive exclusion prefixes")
    canonical = release.get("canonical_evidence", {})
    if canonical.get("manifest_path") != "polymarket-execution-engine/evidence/current/manifest.json":
        fail("release manifest must bind canonical evidence manifest")
    if canonical.get("historical_evidence_policy") != "archive-excluded-from-release-package":
        fail("release manifest must state archive-excluded-from-release-package")
    stale_root = []
    historical_root = []
    for path in ROOT.glob("*.md"):
        if path.name.startswith("V0_") or path.name.startswith("VALIDATION_V0_"):
            stale_root.append(path.name)
        first_line = path.read_text(errors="replace").splitlines()[:1]
        if first_line and re.search(r"\bHistorical v0\.", first_line[0], re.IGNORECASE):
            historical_root.append(path.name)
    if stale_root:
        fail("stale versioned root docs remain outside docs/archive: " + ", ".join(sorted(stale_root)))
    if historical_root:
        fail("historical version root docs remain outside docs/archive: " + ", ".join(sorted(historical_root)))
    active_versioned_engine_docs = [path.name for path in (EXECUTOR / "docs").glob("V0_*.md")]
    if active_versioned_engine_docs:
        fail(
            "stale execution-engine versioned docs remain outside docs/archive: "
            + ", ".join(sorted(active_versioned_engine_docs))
        )
    active_old_gates = [path.name for path in (EXECUTOR / "validation").glob("run_v0_*_gates.sh")]
    if active_old_gates:
        fail("stale gate scripts remain outside validation/archive: " + ", ".join(sorted(active_old_gates)))
    if not (EXECUTOR / "validation/run_current_gates.sh").exists():
        fail("run_current_gates.sh missing")
    if (EXECUTOR / "evidence/v0.23").exists():
        fail("evidence/v0.23 must not exist; template belongs in validation/templates")
    todo_artifacts = [path.relative_to(ROOT).as_posix() for path in (EXECUTOR / "validation").rglob("*todo*")]
    if todo_artifacts:
        fail("validation TODO artifacts remain: " + ", ".join(sorted(todo_artifacts)))


def validate_controlled_canary_release_decision_governance() -> None:
    template = EXECUTOR / "config/controlled-canary.release-decision.template.json"
    example = EXECUTOR / "config/controlled-canary.release-decision.example.json"
    invalid = EXECUTOR / "config/controlled-canary.release-decision.invalid-partial.fixture.json"
    invalid_mismatched = EXECUTOR / "config/controlled-canary.release-decision.invalid-mismatched.fixture.json"
    validator = EXECUTOR / "validation/validate_controlled_canary_release_decision.py"
    review_script = EXECUTOR / "validation/prepare_real_funds_canary_review.py"
    review_drill = EXECUTOR / "validation/run_real_funds_canary_review_package_drill.py"
    readiness_doc = EXECUTOR / "docs/REAL_FUNDS_CANARY_OPERATIONS_READINESS.md"
    external_template = EXECUTOR / "config/controlled-canary.external-references.template.json"
    external_example = EXECUTOR / "config/controlled-canary.external-references.example.json"
    external_invalid = EXECUTOR / "config/controlled-canary.external-references.invalid-sensitive.fixture.json"
    external_validator = EXECUTOR / "validation/validate_controlled_canary_external_references.py"
    runtime_truth_template = EXECUTOR / "config/controlled-canary.runtime-truth.template.json"
    runtime_truth_invalid_partial = EXECUTOR / "config/controlled-canary.runtime-truth.invalid-partial.fixture.json"
    runtime_truth_invalid_sensitive = EXECUTOR / "config/controlled-canary.runtime-truth.invalid-sensitive.fixture.json"
    runtime_truth_validator = EXECUTOR / "validation/validate_controlled_canary_runtime_truth.py"
    require_existing_paths(
        [template, example, invalid, invalid_mismatched, validator],
        "controlled canary release-decision governance file",
    )
    require_existing_paths(
        [external_template, external_example, external_invalid, external_validator],
        "controlled canary external-reference governance file",
    )
    require_existing_paths(
        [
        runtime_truth_template,
        runtime_truth_invalid_partial,
        runtime_truth_invalid_sensitive,
        runtime_truth_validator,
        ],
        "controlled canary runtime-truth governance file",
    )
    template_data = json.loads(template.read_text())
    example_data = json.loads(example.read_text())
    invalid_data = json.loads(invalid.read_text())
    invalid_mismatched_data = json.loads(invalid_mismatched.read_text())
    external_example_data = json.loads(external_example.read_text())
    runtime_truth_template_data = json.loads(runtime_truth_template.read_text())
    if template_data.get("decision") != "no_go":
        fail("controlled canary release-decision template must default to no_go")
    for flag in [
        "live_submit_authorized",
        "live_cancel_authorized",
        "production_deployment_authorized",
        "real_funds_canary_authorized",
        "remote_side_effects_authorized",
        "allow_real_funds_canary",
    ]:
        if template_data.get(flag) is not False:
            fail(f"controlled canary release-decision template must keep {flag}=false")
        if example_data.get(flag) is not False:
            fail(f"controlled canary release-decision example must keep {flag}=false")
    if example_data.get("artifact_sha256") != "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb":
        fail("controlled canary release-decision example must bind illustrative current-release artifact SHA-256")
    if example_data.get("market_candidate_sha256") != "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd":
        fail("controlled canary release-decision example must bind illustrative current-release market candidate SHA-256")
    if invalid_data.get("decision") != "go" or invalid_data.get("live_submit_authorized") is not True:
        fail("controlled canary invalid partial fixture must exercise rejected go/live-submit path")
    if invalid_mismatched_data.get("artifact_sha256") == example_data.get("artifact_sha256"):
        fail("controlled canary invalid mismatched fixture must use a mismatched artifact hash")
    validator_text = validator.read_text()
    for needle in [
        "invalid partial fixture must be rejected",
        "invalid mismatched fixture must be rejected",
        "go decision missing external references",
        "go decision is expired",
        "artifact hash does not match",
        "market candidate hash does not match",
        "live_submit_authorized",
        "real_funds_canary_authorized",
        "reviewed_release_decision_present",
    ]:
        if needle not in validator_text:
            fail(f"controlled canary release-decision validator missing token: {needle}")
    review_text = review_script.read_text()
    if "release-decision.json" not in review_text or "DEFAULT_RELEASE_DECISION" not in review_text:
        fail("real-funds canary review package must include release-decision.json")
    if "external-references.json" not in review_text or "DEFAULT_EXTERNAL_REFERENCES" not in review_text:
        fail("real-funds canary review package must include external-references.json")
    for needle in [
        "--external-references-file",
        "--artifact-sha256",
        "--evidence-manifest-sha256",
        "release sidecar binds the final zip hash",
        "external_references_placeholders_remaining",
        "validate_external_references_shape",
    ]:
        if needle not in review_text:
            fail(f"real-funds canary review package missing external-reference candidate support token: {needle}")
    for needle in [
        "DEFAULT_ROOT_CI_RUN_ID",
        "DEFAULT_HERMES_CI_RUN_ID",
        "DEFAULT_EXECUTION_ENGINE_CI_RUN_ID",
        "DEFAULT_CREDENTIALED_SDK_RUN_ID",
    ]:
        if needle not in review_text:
            fail(f"real-funds canary review package must bind GitHub evidence run id token: {needle}")
    drill_text = review_drill.read_text()
    for needle in [
        "validate_controlled_canary_release_decision.py",
        "validate_controlled_canary_external_references.py",
        "credentialed_sdk_run_id",
    ]:
        if needle not in drill_text:
            fail(f"real-funds canary review package drill missing token: {needle}")
    for needle in [
        "run_real_funds_canary_blocked_rehearsal_package.py",
        "blocked real-funds canary rehearsal package failed",
    ]:
        if needle not in drill_text:
            fail(f"real-funds canary review package drill missing blocked rehearsal token: {needle}")
    for needle in ["--file", "--allow-placeholders", "must reject unresolved placeholders", "review-with-concrete-references"]:
        if needle not in drill_text:
            fail(f"real-funds canary review package drill missing external-reference candidate token: {needle}")
    external_text = external_validator.read_text()
    for needle in [
        "argparse",
        "placeholder_paths",
        "--allow-placeholders",
        "Validate an operator-supplied external reference candidate",
        "invalid sensitive fixture must be rejected",
        "forbidden sensitive reference key",
        "fixture-sensitive-value-must-not-be-logged",
        "rollback_runbook_ref",
        "incident_runbook_ref",
        "canary_retry_policy_ref",
        "references_only_no_secret_values",
    ]:
        if needle not in external_text:
            fail(f"controlled canary external-reference validator missing token: {needle}")
    if external_example_data.get("artifact_sha256") != example_data.get("artifact_sha256"):
        fail("controlled canary external-reference example must bind the same artifact hash as the release-decision example")
    if external_example_data.get("evidence_manifest_sha256") != example_data.get("evidence_manifest_sha256"):
        fail("controlled canary external-reference example must bind the same evidence manifest hash as the release-decision example")
    if runtime_truth_template_data.get("schema_version") != 1:
        fail("controlled canary runtime-truth template must use schema_version=1")
    if runtime_truth_template_data.get("references_only_no_secret_values") is not True:
        fail("controlled canary runtime-truth template must be references-only")
    for flag in [
        "live_submit_allowed",
        "live_cancel_allowed",
        "real_funds_canary_authorized",
        "remote_side_effects",
        "production_ready_claimed",
    ]:
        if runtime_truth_template_data.get(flag) is not False:
            fail(f"controlled canary runtime-truth template must keep {flag}=false")
    runtime_truth_dependencies = runtime_truth_template_data.get("dependencies")
    if not isinstance(runtime_truth_dependencies, list):
        fail("controlled canary runtime-truth template dependencies must be a list")
        runtime_truth_dependencies = []
    dependency_names = {item.get("name") for item in runtime_truth_dependencies if isinstance(item, dict)}
    for name in ["kill_switch", "live_submit_gate", "idempotency_lease", "order_cancel_reconciliation"]:
        if name not in dependency_names:
            fail(f"controlled canary runtime-truth template missing dependency: {name}")
    for item in runtime_truth_dependencies:
        if not isinstance(item, dict):
            fail("controlled canary runtime-truth template dependencies must be objects")
            continue
        if item.get("status") != "durable_runtime_truth":
            fail(f"controlled canary runtime-truth template dependency {item.get('name')} must require durable_runtime_truth")
        evidence_ref = item.get("evidence_ref")
        if not isinstance(evidence_ref, str) or "REPLACE_WITH" not in evidence_ref:
            fail(f"controlled canary runtime-truth template dependency {item.get('name')} must use placeholder evidence_ref")
    runtime_truth_validator_text = runtime_truth_validator.read_text()
    for needle in [
        "Validate an operator-supplied runtime truth candidate",
        "--allow-placeholders",
        "runtime truth missing durable dependencies",
        "invalid partial fixture must be rejected",
        "invalid sensitive fixture must be rejected",
        "forbidden sensitive runtime-truth key",
        "references_only_no_secret_values",
    ]:
        if needle not in runtime_truth_validator_text:
            fail(f"controlled canary runtime-truth validator missing token: {needle}")
    gate_text = (EXECUTOR / "validation/run_current_gates_impl.sh").read_text()
    if "73-controlled-canary-runtime-truth.log" not in gate_text:
        fail("current gates must emit controlled canary runtime-truth validator log")
    store_truth_cli_preflight_text = (EXECUTOR / "validation/run_real_funds_canary_store_truth_cli_preflight.py").read_text()
    for needle in [
        "--runtime-truth-output",
        "--artifact-sha256",
        "--workspace-manifest-sha256",
        "--archived-manifest-sha256",
        "runtime_truth_document",
        "references_only_no_secret_values",
        "pg://canary-runtime-truth",
    ]:
        if needle not in store_truth_cli_preflight_text:
            fail(f"store truth CLI preflight missing runtime-truth output token: {needle}")
    controlled_pipeline_text = (ROOT / "scripts/run_controlled_canary_pipeline.py").read_text()
    for needle in [
        "validate_controlled_canary_runtime_truth.py",
        "runtime truth validator failed",
        "runtime truth artifact binding mismatch",
        "expected_artifact_sha256",
        "expected_workspace_manifest_sha256",
        "expected_archived_manifest_sha256",
    ]:
        if needle not in controlled_pipeline_text:
            fail(f"controlled canary pipeline missing runtime-truth binding token: {needle}")
    readiness_text = readiness_doc.read_text()
    rehearsal = EXECUTOR / "validation/run_real_funds_canary_blocked_rehearsal_package.py"
    if not rehearsal.exists():
        fail("real-funds canary blocked rehearsal package script missing")
    rehearsal_text = rehearsal.read_text()
    for needle in [
        "blocked_real_funds_canary_armed_no_go",
        "--armed",
        "--allow-live-submit-config",
        "--allow-real-funds-canary-config",
        "real-funds canary not allowed by release decision",
        "release_decision_gate",
        "remote_side_effects",
        "raw_signed_order_exposed",
        "--output-dir",
        "blocked-rehearsal.report.json",
        "--artifact-sha256",
        "--evidence-manifest-sha256",
        "--market-file",
    ]:
        if needle not in rehearsal_text:
            fail(f"blocked real-funds canary rehearsal script missing token: {needle}")
    for needle in [
        "default no-go",
        "external-references.json",
        "release-decision.json",
        "controlled-canary.runtime-truth.template.json",
        "real_funds_canary_authorized=false",
        "--external-references-file",
        "REPLACE_WITH_*",
        "run_real_funds_canary_blocked_rehearsal_package.py",
    ]:
        if needle not in readiness_text:
            fail(f"real-funds canary operations readiness doc missing token: {needle}")
    for needle in ["prepare_canary_candidate_market.py", "candidate-market.audit.json", "read-only public API candidate"]:
        if needle not in readiness_text:
            fail(f"real-funds canary operations readiness doc missing candidate-prep token: {needle}")
    for needle in ["prepare_canary_candidate_market.py", "candidate-market.audit.json"]:
        if needle not in review_text:
            fail(f"real-funds canary review package missing candidate-prep token: {needle}")


def validate_canary_candidate_market_prep_boundary() -> None:
    prep_script = ROOT / "scripts/prepare_canary_candidate_market.py"
    if not prep_script.exists():
        fail("root canary candidate market prep script missing")
    text = prep_script.read_text()
    for needle in [
        "candidate-market.json",
        "public read-only",
        "urllib.request",
        "remote_side_effects",
        "authorized_for_live",
        "False",
        "/markets",
        "/book",
        "/spread",
        "max_order_notional_usd",
        "target_size",
        "estimated_order_notional_usd",
        "exchange_rule_snapshot",
        "post_only_buy_limit_price",
        "post_only_price_unavailable",
        "limit_price",
        "max_spread_bps",
        "RealFundsCanaryMarketCandidate",
        "--human-review-ref",
        "--market-url",
        "--outcome",
        "human_review_ref",
        "order_type",
    ]:
        if needle not in text:
            fail(f"canary candidate market prep script missing boundary token: {needle}")
    validate_absent_tokens(text, "canary candidate market prep script", [
        "post_order",
        "post_orders",
        "private_key",
        "clob_secret",
        "api_secret",
        "POLYMARKET_PRIVATE_KEY",
        "PMX_ALLOW_LIVE_SUBMIT=1",
        "PMX_ALLOW_REAL_FUNDS_CANARY=1",
    ])
    live_canary = (SDK_ADAPTER_SRC / "sdk_runtime/live_canary.rs").read_text()
    validate_absent_tokens(live_canary, "execution-engine live canary runtime", [
        "simplified_markets",
        "sampling_markets",
        "sampling_simplified_markets",
        ".market_order(",
    ])
    for needle in [
        "limit_order()",
        "size(size)",
        "SdkOrderType::GTC",
        ".post_only(true)",
        "cancel_order",
        '"cancel_confirmed"',
    ]:
        if needle not in live_canary:
            fail(f"execution-engine live canary runtime missing size-driven order token: {needle}")
    canary_cli = (SDK_ADAPTER_SRC / "bin/pmx-real-funds-canary.rs").read_text()
    for needle in ["append_stage_history", "stage_history_path", ".stages.jsonl"]:
        if needle not in canary_cli:
            fail(f"execution-engine real-funds canary CLI missing stage-history token: {needle}")
    real_funds_gate = (SDK_ADAPTER_SRC / "gates/real_funds.rs").read_text()
    for needle in [
        "candidate_notional_usd",
        "target_notional_lte",
        "target_size",
        "exchange_rule_snapshot_valid",
        "post_only_limit_terms_valid",
    ]:
        if needle not in real_funds_gate:
            fail(f"execution-engine real-funds gate missing size/notional derivation token: {needle}")
    active_texts = {
        "README.md": (ROOT / "README.md").read_text(),
        "IMPLEMENTATION_STATUS.md": (ROOT / "IMPLEMENTATION_STATUS.md").read_text(),
        "REAL_FUNDS_CANARY.md": (EXECUTOR / "docs/REAL_FUNDS_CANARY.md").read_text(),
        "REAL_FUNDS_CANARY_CLOSEOUT.md": (EXECUTOR / "docs/REAL_FUNDS_CANARY_CLOSEOUT.md").read_text(),
        "REAL_FUNDS_CANARY_SEMANTICS_AUDIT.md": (
            EXECUTOR / "docs/REAL_FUNDS_CANARY_SEMANTICS_AUDIT.md"
        ).read_text(),
    }
    for path, doc_text in active_texts.items():
        if "FOK limit-fill" in doc_text or "FOK_LIMIT_FILL" in doc_text:
            fail(f"active canary docs must not describe the current canary as FOK limit-fill: {path}")
    closeout_script = ROOT / "scripts/prepare_canary_closeout.py"
    if not closeout_script.exists():
        fail("canary closeout script missing")
    closeout_text = closeout_script.read_text()
    for needle in [
        "GTC_LIMIT_POST_ONLY_CANCEL",
        "notional_rule",
        "limit_price * size",
        "post-canary-report.json.stages.jsonl",
        "stage_history_has_cancel_confirmed",
        "operator-recovery.json",
        "operator-incident-recovery.json",
        "operator_reviewed_closed_no_retry",
        "operator_reviewed_no_remote_order_found_no_retry",
        "account-open-orders-readback.json",
        "account-trade-history-readback.json",
        "no_retry_authorized",
        "incident_recovered_no_remote_order_found",
        "incident_recovery_no_matching_open_orders",
        "stage_history_summary",
        "operator_recovery_summary",
        "stage_history_operator_required_recovered",
        "stage_history_remote_order_matches_report",
        "order_remote_status_canceled",
        "trade_query_zero_matching_trades",
        "account_activity_zero_open_positions",
        "not a formal exchange/account statement export",
    ]:
        if needle not in closeout_text:
            fail(f"canary closeout script missing evidence/semantics token: {needle}")


def validate_single_host_deployment_governance() -> None:
    deploy = EXECUTOR / "deploy/single-host"
    required = [
        deploy / "README.md",
        deploy / "env/pmx-api.env.example",
        deploy / "env/pmx-real-funds-canary.env.example",
        deploy / "systemd/pmx-api.service",
        deploy / "systemd/pmx-real-funds-canary@.service",
        deploy / "bin/pmx-single-host-preflight.sh",
        deploy / "bin/pmx-single-host-rollback.sh",
        deploy / "bin/pmx-single-host-canary-package-preflight.sh",
        EXECUTOR / "validation/run_single_host_deployment_drill.py",
        EXECUTOR / "validation/run_single_host_canary_candidate_drill.py",
        EXECUTOR / "validation/run_single_host_go_candidate_drill.py",
    ]
    for path in required:
        if not path.exists():
            fail(f"single-host deployment governance file missing: {path.relative_to(ROOT)}")
    readme = (deploy / "README.md").read_text()
    canary_service = (deploy / "systemd/pmx-real-funds-canary@.service").read_text()
    validator = (EXECUTOR / "validation/run_single_host_deployment_drill.py").read_text()
    candidate_validator = (EXECUTOR / "validation/run_single_host_canary_candidate_drill.py").read_text()
    go_candidate_validator = (EXECUTOR / "validation/run_single_host_go_candidate_drill.py").read_text()
    package_preflight = (deploy / "bin/pmx-single-host-canary-package-preflight.sh").read_text()
    gate_impl = (EXECUTOR / "validation/run_current_gates_impl.sh").read_text()
    writer = (EXECUTOR / "validation/write_current_evidence_manifest.py").read_text()
    combined_templates = "\n".join(
        path.read_text()
        for path in required
        if path.exists()
        and "deploy/single-host" in path.as_posix()
        and path.name != "pmx-single-host-canary-package-preflight.sh"
    )
    for needle in [
        "single-host limited deployment",
        "not production-ready evidence",
        "PMX_LIVE_SUBMIT_ENABLED=0",
        "PMX_ALLOW_REAL_FUNDS_CANARY=0",
        "long-running HTTP listener",
        "non-live API smoke",
        "pass://polymarket-execution-engine/controlled-canary",
        "reviewed `go` release decision",
    ]:
        if needle not in readme:
            fail(f"single-host deployment README missing token: {needle}")
    if "--dry-run" not in canary_service:
        fail("single-host canary service must run dry-run mode")
    validate_absent_tokens(
        canary_service,
        "single-host canary service",
        ["--armed", "--allow-live-submit-config", "--allow-real-funds-canary-config"],
    )
    for needle in [
        "single_host_deployment_validation",
        "69-single-host-deployment-drill.log",
        "live_submit_allowed",
        "production_deployment_allowed",
        "secrets_included",
        "api_bind_smoke",
        "run_api_bind_smoke",
        "PMX_PRODUCTION_DEPLOYMENT_ENABLED=1",
    ]:
        if needle not in validator:
            fail(f"single-host deployment validator missing token: {needle}")
    if "69-single-host-deployment-drill.log" not in gate_impl:
        fail("current gates must emit single-host deployment drill log")
    if "70-single-host-canary-candidate-drill.log" not in gate_impl:
        fail("current gates must emit single-host canary candidate drill log")
    if "71-single-host-go-candidate-drill.log" not in gate_impl:
        fail("current gates must emit single-host go candidate drill log")
    if '"single_host_deployment_validation"' not in writer or "69-single-host-deployment-drill.log" not in writer:
        fail("current evidence manifest writer must include single-host deployment validation")
    if '"single_host_canary_candidate_validation"' not in writer or "70-single-host-canary-candidate-drill.log" not in writer:
        fail("current evidence manifest writer must include single-host canary candidate validation")
    if '"single_host_go_candidate_validation"' not in writer or "71-single-host-go-candidate-drill.log" not in writer:
        fail("current evidence manifest writer must include single-host go candidate validation")
    for needle in [
        "candidate_package_generated",
        "release_decision",
        "no_go",
        "PMX_EXECUTION_ENGINE_ROOT",
        "single_host_canary_candidate_validation",
        "70-single-host-canary-candidate-drill.log",
    ]:
        if needle not in candidate_validator:
            fail(f"single-host canary candidate validator missing token: {needle}")
    for needle in [
        "validate_controlled_canary_external_references.py",
        "single-host canary package preflight only accepts no_go release decisions",
        "candidate-market.json",
        "market_candidate_sha256",
        "target_size",
        "release decision must keep",
        "single-host canary package preflight passed",
    ]:
        if needle not in package_preflight:
            fail(f"single-host canary package preflight missing token: {needle}")
    for needle in [
        "temporary_go_candidate_generated",
        "go_candidate_committed",
        "candidate_go_not_committed",
        "missing_release_decision_blocks_armed",
        "--release-decision-file is required with --armed",
        "FORBIDDEN_GO_DECISION_GLOBS",
        "single_host_go_candidate_validation",
        "71-single-host-go-candidate-drill.log",
    ]:
        if needle not in go_candidate_validator:
            fail(f"single-host go candidate validator missing token: {needle}")
    validate_absent_tokens(combined_templates, "single-host deployment files", [
        "-----BEGIN",
        "clob_secret=",
        "raw_signature=",
        "raw_signed_payload=",
        "signed_order_envelope=",
        "PMX_ALLOW_LIVE_SUBMIT=1",
        "PMX_ALLOW_LIVE_CANCEL=1",
        "PMX_ALLOW_REAL_FUNDS_CANARY=1",
        "PMX_PRODUCTION_DEPLOYMENT_ENABLED=1",
    ])


def validate_v28_production_live_candidate_guard() -> None:
    guard = ROOT / "scripts/check_v28_production_live_candidate.py"
    test = ROOT / "tests/test_v28_production_live_candidate.py"
    readme = ROOT / "README.md"
    report = ROOT / "VALIDATION_REPORT.md"
    for path in [guard, test]:
        if not path.exists():
            fail(f"v0.28 production-live-candidate guard file missing: {path.relative_to(ROOT)}")
    guard_text = guard.read_text()
    for needle in [
        'TARGET_VERSION = "0.28.0"',
        "production-live-candidate",
        "--require-ready",
        "release artifact evidence sidecar missing",
        "current evidence manifest must bind final external_artifact_sidecar.sha256",
        "validated_release",
        "production_ready",
        "live_trading_ready",
        "operator approval",
        "runtime state healthy",
    ]:
        if needle not in guard_text:
            fail(f"v0.28 production-live-candidate guard missing token: {needle}")
    test_text = test.read_text()
    for needle in [
        "test_ready_tree_passes_when_candidate_boundary_is_explicit",
        "test_live_ready_claim_blocks_candidate",
        "test_missing_operator_and_runtime_terms_block_candidate",
    ]:
        if needle not in test_text:
            fail(f"v0.28 production-live-candidate tests missing token: {needle}")
    for path in [readme, report]:
        text = path.read_text()
        if "check_v28_production_live_candidate.py" not in text:
            fail(f"{path.name} must mention check_v28_production_live_candidate.py")
