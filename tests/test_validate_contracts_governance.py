from __future__ import annotations

import json
from types import SimpleNamespace
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_governance as module
from validate_contracts_support import ContractValidationError


class ValidateContractsGovernanceTests(unittest.TestCase):
    def test_validate_absent_tokens_rejects_forbidden_token(self) -> None:
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_absent_tokens("safe text with raw_signature=", "deployment template", ["raw_signature="])
        self.assertIn("deployment template contains forbidden token: raw_signature=", str(ctx.exception))

    def test_require_existing_paths_reports_missing_relative_path(self) -> None:
        missing = ROOT / "does-not-exist-governance-test.json"
        with self.assertRaises(ContractValidationError) as ctx:
            module.require_existing_paths([missing], "governance fixture")
        self.assertIn("governance fixture missing: does-not-exist-governance-test.json", str(ctx.exception))

    def test_validate_current_hermes_client_surface_uses_structural_client_and_model_checks(self) -> None:
        class GoodClient:
            def record_sign_only_lifecycle_event(self, record, *, correlation_id=None) -> "SignOnlyLifecycleRecord":
                return None

            def list_sign_only_lifecycle_events(
                self, execution_id, *, limit=None, before_event_id=None, correlation_id=None
            ) -> list["SignOnlyLifecycleRecord"]:
                return []

            def list_execution_lifecycle_events(
                self, execution_id, *, limit=None, before_event_id=None, correlation_id=None
            ) -> list["ExecutionLifecycleEvent"]:
                return []

            def list_admin_audit_events(
                self,
                *,
                limit=None,
                before_audit_id=None,
                operation=None,
                principal_subject=None,
                result=None,
                audit_correlation_id=None,
                correlation_id=None,
            ) -> list["AdminAuditEvent"]:
                return []

            def cancel_order(self, account_id, order_id, reason, *, execution_id=None, correlation_id=None) -> "CancelReceipt":
                return None

            def reconcile(self, account_id, reason, execution_id=None, *, correlation_id=None) -> "ReconcileReport":
                return None

            def reconcile_order_local(
                self, account_id, order_id, remote_observation, reason, *, correlation_id=None
            ) -> "ReconcileOrderLocalResponse":
                return None

            def _headers(self, *, admin=False, correlation_id=None):
                headers = {}
                if correlation_id:
                    headers["X-Correlation-Id"] = correlation_id
                return headers

        class FakeField:
            def __init__(self, annotation) -> None:
                self.annotation = annotation

        class GoodSignOnlyLifecycleRecord:
            model_fields = {
                "execution_id": FakeField(str),
                "client_event_id": FakeField(str | None),
                "signed_order_ref": FakeField(str | None),
                "no_remote_side_effect": FakeField(bool),
            }

            @staticmethod
            def model_validate(payload):
                raise ValueError("sign-only lifecycle records must not contain remote side effects")

        fake_models = SimpleNamespace(
            SignOnlyLifecycleRecord=GoodSignOnlyLifecycleRecord,
            RedactedPayloadEnvelope=SimpleNamespace(
                model_fields={
                    "correlation_id": FakeField(str | None),
                    "redacted_fields": FakeField(list[str]),
                    "body": FakeField(dict),
                }
            ),
            ExecutionLifecycleEvent=SimpleNamespace(
                model_fields={
                    "execution_id": FakeField(str),
                    "payload": FakeField("RedactedPayloadEnvelope"),
                }
            ),
            AdminAuditEvent=SimpleNamespace(
                model_fields={
                    "principal_subject": FakeField(str),
                    "result": FakeField(str),
                    "correlation_id": FakeField(str | None),
                }
            ),
            OrderLifecycleDivergence=SimpleNamespace(model_fields={}),
            ReconcileOrderLocalResponse=SimpleNamespace(model_fields={}),
        )

        with (
            mock.patch.object(module, "import_control_client", return_value=SimpleNamespace(ExecutorClient=GoodClient)),
            mock.patch.object(module, "import_control_models", return_value=fake_models),
        ):
            module.validate_current_hermes_client_surface()

    def test_validate_current_hermes_client_surface_rejects_missing_structural_contract(self) -> None:
        class BadClient:
            def list_admin_audit_events(self, *, correlation_id=None) -> list["AdminAuditEvent"]:
                return []

            def _headers(self, *, admin=False, correlation_id=None):
                return {}

        fake_models = SimpleNamespace(
            SignOnlyLifecycleRecord=SimpleNamespace(model_fields={}),
            RedactedPayloadEnvelope=SimpleNamespace(model_fields={}),
            ExecutionLifecycleEvent=SimpleNamespace(model_fields={"payload": SimpleNamespace(annotation="RedactedPayloadEnvelope")}),
            AdminAuditEvent=SimpleNamespace(model_fields={}),
            OrderLifecycleDivergence=SimpleNamespace(model_fields={}),
            ReconcileOrderLocalResponse=SimpleNamespace(model_fields={}),
        )

        with (
            mock.patch.object(module, "import_control_client", return_value=SimpleNamespace(ExecutorClient=BadClient)),
            mock.patch.object(module, "import_control_models", return_value=fake_models),
        ):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_current_hermes_client_surface()
        self.assertIn("record_sign_only_lifecycle_event", str(ctx.exception))

    def test_validate_current_evidence_manifest_guard_uses_structural_module_checks(self) -> None:
        fake_guard = SimpleNamespace(
            REQUIRED_SECTIONS=[
                "local_static_validation",
                "rust_workspace_validation",
                "postgres_validation",
                "sdk_adapter_validation",
                "credentialed_non_trading_validation",
            ],
            VALID_STATUSES={"pending", "pass", "fail", "skipped", "not_run"},
            TEST_LOG_RULES={"x": {"min_passed": 1}},
            JSON_LOG_RULES={"y": {"status": "pass"}},
            validate=lambda *args, **kwargs: 0,
            validate_test_log_semantics=lambda *args, **kwargs: None,
            validate_json_log_semantics=lambda *args, **kwargs: None,
        )
        fake_writer = SimpleNamespace(
            TEST_LOG_RULES={"x": {"min_passed": 1}},
            JSON_LOG_RULES={"y": {"status": "pass"}},
            SECTIONS={
                "local_static_validation": [],
                "runtime_worker_status_validation": [],
                "real_funds_canary_store_truth_cli_validation": [],
            },
            CURRENT_DIR=ROOT / "polymarket-execution-engine" / "evidence" / "current",
            OUT=ROOT / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json",
            build_section=lambda *args, **kwargs: {},
        )
        fake_docs = SimpleNamespace(
            CURRENT_MANIFEST=ROOT / "polymarket-execution-engine" / "evidence" / "current" / "manifest.json",
            RELEASE_MANIFEST=ROOT / "polymarket-execution-engine" / "release" / "manifest.json",
            PACKAGE_SCRIPT=ROOT / "scripts" / "package_release.py",
            ARTIFACT_CHECK=ROOT / "scripts" / "check_release_artifact.py",
            RELEASE_POLICY=ROOT / "scripts" / "release_policy.py",
            validate_root_docs=lambda failures: None,
            validate_evidence_layout=lambda failures: None,
            validate_release_binding=lambda failures: None,
            validate_current_manifest=lambda failures: None,
            validate_execution_docs_and_gates=lambda failures: None,
            validate_agents_guidance=lambda failures: None,
        )

        def fake_import(name: str, path: Path):
            if path.name == "check_current_evidence_manifest.py":
                return fake_guard
            if path.name == "write_current_evidence_manifest.py":
                return fake_writer
            if path.name == "check_docs_evidence_governance.py":
                return fake_docs
            raise AssertionError(path)

        with mock.patch.object(module, "import_module_from_path", side_effect=fake_import):
            module.validate_current_evidence_manifest_guard()

    def test_validate_current_docs_and_release_governance_uses_structural_guard_checks(self) -> None:
        fake_docs = SimpleNamespace(
            PACKAGE_SCRIPT=ROOT / "scripts" / "package_release.py",
            ARTIFACT_CHECK=ROOT / "scripts" / "check_release_artifact.py",
            RELEASE_POLICY=ROOT / "scripts" / "release_policy.py",
            validate_root_docs=lambda failures: None,
            validate_evidence_layout=lambda failures: None,
            validate_release_binding=lambda failures: None,
            validate_current_manifest=lambda failures: None,
            validate_execution_docs_and_gates=lambda failures: None,
            validate_agents_guidance=lambda failures: None,
            validate_packaging_scripts=lambda failures: None,
        )

        original_release = (ROOT / "polymarket-execution-engine" / "release" / "manifest.json").read_text()
        try:
            with mock.patch.object(module, "import_module_from_path", return_value=fake_docs):
                module.validate_current_docs_and_release_governance()
        finally:
            (ROOT / "polymarket-execution-engine" / "release" / "manifest.json").write_text(original_release)

    def test_validate_v28_production_live_candidate_guard_uses_structural_module_checks(self) -> None:
        fake_guard = SimpleNamespace(
            ROOT=ROOT,
            TARGET_VERSION="0.28.0",
            HEX64=SimpleNamespace(pattern=r"^[0-9a-f]{64}$"),
            REQUIRED_CANDIDATE_TERMS=[
                "production-live-candidate",
                "validated_release=false",
                "production_ready=false",
                "live_trading_ready=false",
                "operator approval",
                "runtime state healthy",
                "kill switch open",
                "no geoblock",
                "idempotency reservation",
                "rollback",
                "incident",
                "alert",
                "custody",
            ],
            __doc__="Audit v0.28 production-live-candidate readiness.",
            read_text=lambda path: "",
            load_json=lambda path: {},
            component_matrix_versions=lambda text: {},
            require_contains=lambda blockers, label, text, token: None,
            require_false=lambda blockers, data, key, label: None,
            evaluate=lambda root=None, target_version="0.28.0": {},
            main=lambda argv=None: 0,
        )

        with mock.patch.object(module, "import_module_from_path", return_value=fake_guard):
            module.validate_v28_production_live_candidate_guard()

    def test_validate_controlled_canary_release_decision_governance_uses_structural_module_checks(self) -> None:
        template = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.release-decision.template.json"
        example = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.release-decision.example.json"
        invalid = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.release-decision.invalid-partial.fixture.json"
        invalid_mismatched = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.release-decision.invalid-mismatched.fixture.json"
        external_template = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.external-references.template.json"
        external_example = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.external-references.example.json"
        external_invalid = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.external-references.invalid-sensitive.fixture.json"
        runtime_truth_template = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.runtime-truth.template.json"
        runtime_truth_invalid_partial = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.runtime-truth.invalid-partial.fixture.json"
        runtime_truth_invalid_sensitive = ROOT / "polymarket-execution-engine" / "config" / "controlled-canary.runtime-truth.invalid-sensitive.fixture.json"
        validator = ROOT / "polymarket-execution-engine" / "validation" / "validate_controlled_canary_release_decision.py"
        external_validator = ROOT / "polymarket-execution-engine" / "validation" / "validate_controlled_canary_external_references.py"
        runtime_truth_validator = ROOT / "polymarket-execution-engine" / "validation" / "validate_controlled_canary_runtime_truth.py"
        review_script = ROOT / "polymarket-execution-engine" / "validation" / "prepare_real_funds_canary_review.py"
        review_drill = ROOT / "polymarket-execution-engine" / "validation" / "run_real_funds_canary_review_package_drill.py"
        readiness_doc = ROOT / "polymarket-execution-engine" / "docs" / "REAL_FUNDS_CANARY_OPERATIONS_READINESS.md"
        rehearsal = ROOT / "polymarket-execution-engine" / "validation" / "run_real_funds_canary_blocked_rehearsal_package.py"

        template_data = json.loads(template.read_text())
        example_data = json.loads(example.read_text())
        invalid_data = json.loads(invalid.read_text())
        invalid_mismatched_data = json.loads(invalid_mismatched.read_text())
        external_example_data = json.loads(external_example.read_text())
        runtime_truth_template_data = json.loads(runtime_truth_template.read_text())
        review_drill_text = review_drill.read_text()
        self.assertIn(
            'DRILL_CREDENTIALED_SDK_RUN_ID = "local-current-gates-review-package-drill"',
            review_drill_text,
        )
        self.assertEqual(review_drill_text.count('"--credentialed-sdk-run-id"'), 3)
        for drill_name in [
            "run_single_host_canary_candidate_drill.py",
            "run_single_host_go_candidate_drill.py",
        ]:
            drill_text = (review_drill.parent / drill_name).read_text()
            self.assertIn(
                'DRILL_CREDENTIALED_SDK_RUN_ID = "local-current-gates-20260523"',
                drill_text,
            )
            self.assertIn('"--credentialed-sdk-run-id"', drill_text)

        validator_module = SimpleNamespace(
            TEMPLATE=template,
            EXAMPLE=example,
            INVALID_PARTIAL=invalid,
            INVALID_MISMATCHED=invalid_mismatched,
            EXPECTED_RUN_IDS={
                "root_ci_run_id": "26268697168",
                "hermes_ci_run_id": "26267887116",
                "execution_engine_ci_run_id": "26268276210",
                "credentialed_sdk_run_id": "local-current-gates-20260523",
            },
            ALLOWED_TOP_LEVEL_FIELDS={"reviewed_release_decision_present", "real_funds_canary_authorized"},
            AUTHORIZATION_FLAGS=["real_funds_canary_authorized"],
            validate_shape=lambda *args, **kwargs: [],
            main=lambda: 0,
        )
        review_module = SimpleNamespace(
            DEFAULT_RELEASE_DECISION=template,
            DEFAULT_EXTERNAL_REFERENCES=external_template,
            DEFAULT_ROOT_CI_RUN_ID="26268697168",
            DEFAULT_HERMES_CI_RUN_ID="26267887116",
            DEFAULT_EXECUTION_ENGINE_CI_RUN_ID="26268276210",
            resolve_input_path=lambda path: path,
            require_sha256=lambda value, label: value,
            validate_candidate_market_json=lambda *args, **kwargs: None,
            main=lambda: 0,
        )
        drill_module = SimpleNamespace(
            SCRIPT=review_script,
            DECISION_VALIDATOR=validator,
            EXTERNAL_REFERENCES_VALIDATOR=external_validator,
            BLOCKED_REHEARSAL=rehearsal,
            EXTERNAL_REFERENCES_EXAMPLE=external_example,
            EXTERNAL_REFERENCES_TEMPLATE=external_template,
            DOC=readiness_doc,
            EXAMPLE_REVIEW_ARTIFACT_SHA256="c0c22c91541d48c508a588b06a2fa5d7051bc6c8e29df626de67a59cc96c24e6",
            MANIFEST_WRITER=ROOT / "polymarket-execution-engine" / "validation" / "write_current_evidence_manifest.py",
            main=lambda: 0,
        )
        external_module = SimpleNamespace(
            TEMPLATE=external_template,
            EXAMPLE=external_example,
            INVALID_SENSITIVE=external_invalid,
            EXPECTED_ARTIFACT_SHA256="b" * 64,
            EXPECTED_RUN_IDS={
                "root_ci_run_id": "26268697168",
                "credentialed_sdk_run_id": "local-current-gates-20260523",
            },
            REQUIRED_FIELDS={"runbooks": ["rollback_runbook_ref", "incident_runbook_ref", "canary_retry_policy_ref"]},
            FORBIDDEN_VALUE_FRAGMENTS=("fixture-sensitive-value-must-not-be-logged",),
            FORBIDDEN_KEYS={"SignedOrderEnvelope"},
            validate_shape=lambda *args, **kwargs: [],
            placeholder_paths=lambda *args, **kwargs: [],
            has_placeholder=lambda *args, **kwargs: False,
            main=lambda: 0,
        )
        runtime_truth_module = SimpleNamespace(
            validate_shape=lambda *args, **kwargs: [],
            placeholder_paths=lambda *args, **kwargs: [],
            has_placeholder=lambda *args, **kwargs: False,
            main=lambda: 0,
        )

        path_map = {
            validator.name: validator_module,
            external_validator.name: external_module,
            runtime_truth_validator.name: runtime_truth_module,
            review_script.name: review_module,
            review_drill.name: drill_module,
        }

        def fake_import(name: str, path: Path):
            module_obj = path_map.get(path.name)
            if module_obj is None:
                raise AssertionError(path)
            return module_obj

        with mock.patch.object(module, "import_module_from_path", side_effect=fake_import):
            module.validate_controlled_canary_release_decision_governance()

    def test_validate_single_host_deployment_governance_uses_structural_module_checks(self) -> None:
        deploy = ROOT / "polymarket-execution-engine" / "deploy" / "single-host"
        manifest_writer = ROOT / "polymarket-execution-engine" / "validation" / "write_current_evidence_manifest.py"
        deployment_validator = ROOT / "polymarket-execution-engine" / "validation" / "run_single_host_deployment_drill.py"
        candidate_validator = ROOT / "polymarket-execution-engine" / "validation" / "run_single_host_canary_candidate_drill.py"
        go_candidate_validator = ROOT / "polymarket-execution-engine" / "validation" / "run_single_host_go_candidate_drill.py"

        deployment_module = SimpleNamespace(
            DEPLOY=deploy,
            README=deploy / "README.md",
            API_ENV=deploy / "env/pmx-api.env.example",
            CANARY_ENV=deploy / "env/pmx-real-funds-canary.env.example",
            API_SERVICE=deploy / "systemd/pmx-api.service",
            CANARY_SERVICE=deploy / "systemd/pmx-real-funds-canary@.service",
            PREFLIGHT=deploy / "bin/pmx-single-host-preflight.sh",
            ROLLBACK=deploy / "bin/pmx-single-host-rollback.sh",
            CANARY_PACKAGE_PREFLIGHT=deploy / "bin/pmx-single-host-canary-package-preflight.sh",
            MANIFEST_WRITER=manifest_writer,
            FAIL_CLOSED_FLAGS=["PMX_ALLOW_REAL_FUNDS_CANARY=0"],
            FORBIDDEN_VALUE_FRAGMENTS=["PMX_PRODUCTION_DEPLOYMENT_ENABLED=1"],
            run_api_bind_smoke=lambda failures: True,
            read=lambda path: "",
            main=lambda: 0,
        )
        candidate_module = SimpleNamespace(
            CANARY_SERVICE=deploy / "systemd/pmx-real-funds-canary@.service",
            MANIFEST_WRITER=manifest_writer,
            main=lambda: 0,
        )
        go_candidate_module = SimpleNamespace(
            MANIFEST_WRITER=manifest_writer,
            main=lambda: 0,
        )
        writer_module = SimpleNamespace(
            SECTIONS={
                "single_host_deployment_validation": ["69-single-host-deployment-drill.log"],
                "single_host_canary_candidate_validation": ["70-single-host-canary-candidate-drill.log"],
                "single_host_go_candidate_validation": ["71-single-host-go-candidate-drill.log"],
            }
        )
        path_map = {
            deployment_validator.name: deployment_module,
            candidate_validator.name: candidate_module,
            go_candidate_validator.name: go_candidate_module,
            manifest_writer.name: writer_module,
        }

        def fake_import(name: str, path: Path):
            module_obj = path_map.get(path.name)
            if module_obj is None:
                raise AssertionError(path)
            return module_obj

        with mock.patch.object(module, "import_module_from_path", side_effect=fake_import):
            module.validate_single_host_deployment_governance()

    def test_validate_canary_candidate_market_prep_boundary_uses_structural_module_checks(self) -> None:
        prep_script = ROOT / "polymarket-execution-engine" / "validation" / "prepare_canary_candidate_market.py"

        class FakeCandidate:
            def __init__(self, **kwargs) -> None:
                self.kwargs = kwargs

            def to_engine_json(self) -> dict[str, object]:
                return {
                    "side": "BUY",
                    "order_type": "GTC",
                    "post_only": True,
                    "human_review_ref": "https://example.invalid/review/123",
                    "exchange_rule_snapshot": {
                        "order_mode": "post_only_limit",
                        "order_type": "GTC",
                        "side": "BUY",
                        "target_size_semantics": "outcome_shares",
                        "evidence_ref": "https://example.invalid/rules/123",
                    },
                }

        fake_module = SimpleNamespace(
            __doc__=(
                "Prepare a reviewed canary market candidate from public read-only APIs.\n\n"
                "The output shape matches the execution engine RealFundsCanaryMarketCandidate."
            ),
            ROOT=ROOT / "polymarket-execution-engine",
            INTEGRATION_ROOT=ROOT,
            DEFAULT_GAMMA_URL="https://gamma-api.polymarket.com",
            DEFAULT_CLOB_URL="https://clob.polymarket.com",
            FETCH_RETRY_ATTEMPTS=3,
            Candidate=FakeCandidate,
            parse_args=lambda: None,
            fetch_json=lambda *args, **kwargs: {},
            fetch_json_or_error=lambda *args, **kwargs: {},
            post_only_buy_limit_price=lambda *args, **kwargs: None,
            candidate_from_market=lambda *args, **kwargs: None,
            load_market_by_slug=lambda *args, **kwargs: {},
            scan=lambda *args, **kwargs: ({}, {}),
            main=lambda: 0,
        )

        def fake_import(name: str, path: Path):
            if path != prep_script:
                raise AssertionError(path)
            return fake_module

        with mock.patch.object(module, "import_module_from_path", side_effect=fake_import):
            module.validate_canary_candidate_market_prep_boundary()

    def test_validate_canary_candidate_market_prep_boundary_rejects_missing_scan_audit_tokens(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/validation/prepare_canary_candidate_market.py"):
                return """
\"\"\"Prepare a reviewed canary market candidate from public read-only APIs.

The output shape matches the execution engine RealFundsCanaryMarketCandidate.
\"\"\"

from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal

ROOT = Path(".")
INTEGRATION_ROOT = Path(".")
DEFAULT_GAMMA_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_URL = "https://clob.polymarket.com"
FETCH_RETRY_ATTEMPTS = 3

@dataclass(frozen=True)
class Candidate:
    market_id: str
    token_id: str
    outcome: str
    market_slug: str
    active: bool
    accepting_orders: bool
    closed: bool
    archived: bool
    best_ask: Decimal
    limit_price: Decimal
    ask_size: Decimal
    target_size: Decimal
    spread_bps: int
    min_order_size: Decimal
    min_tick_size: Decimal
    liquidity_score: int
    source_market_hash: str
    book_snapshot_timestamp: str
    human_review_ref: str
    exchange_rule_evidence_ref: str
    exchange_rule_valid_for_minutes: int

    def to_engine_json(self):
        return {
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "human_review_ref": self.human_review_ref,
            "exchange_rule_snapshot": {
                "order_mode": "post_only_limit",
                "order_type": "GTC",
                "side": "BUY",
                "target_size_semantics": "outcome_shares",
                "evidence_ref": self.exchange_rule_evidence_ref,
            },
        }

def parse_args():
    \"\"\"candidate-market.json public read-only Polymarket APIs.\"\"\"
    return None

def fetch_json(*args, **kwargs):
    urllib.request.Request("https://example.invalid")
    urllib.request.urlopen("https://example.invalid")
    FETCH_RETRY_ATTEMPTS

def fetch_json_or_error(*args, **kwargs):
    try:
        return fetch_json(base_url, path, query, timeout_seconds)
    except Exception as exc:
        audit.setdefault("fetch_errors", []).append(
            {"path": path, "query": query, "error": f"{type(exc).__name__}: {exc}"}
        )
        raise CandidateError(failure_message, audit) from exc

def post_only_buy_limit_price(*args, **kwargs):
    ask_ticks = (best_ask_price / min_tick_size).to_integral_value(rounding=ROUND_FLOOR)
    upper = ask_ticks * min_tick_size
    upper -= min_tick_size
    improved_bid = ((best_bid_price / min_tick_size).to_integral_value(rounding=ROUND_FLOOR) + 1) * min_tick_size
    if improved_bid < best_ask_price and improved_bid <= upper:
        return improved_bid
    if bid_grid > 0 and bid_grid < best_ask_price and bid_grid <= upper:
        return bid_grid
    return upper

def candidate_from_market(*args, **kwargs):
    \"/book\"
    \"/spread\"
    post_only_buy_limit_price()
    raise RuntimeError("selected market spread is unavailable")

def load_market_by_slug(args, slug, requested_outcome):
    fetch_json(args.gamma_url, "/markets", {"slug": slug}, args.timeout_seconds)
    fetch_json(args.gamma_url, "/events", {"slug": slug}, args.timeout_seconds)
    return {}

def scan(args):
    return {}, {}

def main():
    return 0
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_canary_candidate_market_prep_boundary()
        self.assertIn("canary candidate market prep scan", str(ctx.exception))

    def test_validate_canary_candidate_market_prep_boundary_rejects_forbidden_surface_token(self) -> None:
        original_read_text = Path.read_text

        def fake_read_text(path_self: Path, *args, **kwargs) -> str:
            path = str(path_self)
            if path.endswith("polymarket-execution-engine/validation/prepare_canary_candidate_market.py"):
                return """
\"\"\"Prepare a reviewed canary market candidate from public read-only APIs.

The output shape matches the execution engine RealFundsCanaryMarketCandidate.
\"\"\"

from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal
import urllib.request

ROOT = Path(".")
INTEGRATION_ROOT = Path(".")
DEFAULT_GAMMA_URL = "https://gamma-api.polymarket.com"
DEFAULT_CLOB_URL = "https://clob.polymarket.com"
FETCH_RETRY_ATTEMPTS = 3

@dataclass(frozen=True)
class Candidate:
    market_id: str
    token_id: str
    outcome: str
    market_slug: str
    active: bool
    accepting_orders: bool
    closed: bool
    archived: bool
    best_ask: Decimal
    limit_price: Decimal
    ask_size: Decimal
    target_size: Decimal
    spread_bps: int
    min_order_size: Decimal
    min_tick_size: Decimal
    liquidity_score: int
    source_market_hash: str
    book_snapshot_timestamp: str
    human_review_ref: str
    exchange_rule_evidence_ref: str
    exchange_rule_valid_for_minutes: int

    def to_engine_json(self):
        return {
            "side": "BUY",
            "order_type": "GTC",
            "post_only": True,
            "human_review_ref": self.human_review_ref,
            "exchange_rule_snapshot": {
                "order_mode": "post_only_limit",
                "order_type": "GTC",
                "side": "BUY",
                "target_size_semantics": "outcome_shares",
                "evidence_ref": self.exchange_rule_evidence_ref,
            },
        }

def parse_args():
    \"\"\"candidate-market.json public read-only Polymarket APIs.\"\"\"
    return None

def fetch_json(*args, **kwargs):
    urllib.request.Request("https://example.invalid")
    urllib.request.urlopen("https://example.invalid")
    FETCH_RETRY_ATTEMPTS

def fetch_json_or_error(*args, **kwargs):
    try:
        return fetch_json(base_url, path, query, timeout_seconds)
    except Exception as exc:
        audit.setdefault("fetch_errors", []).append(
            {"path": path, "query": query, "error": f"{type(exc).__name__}: {exc}"}
        )
        raise CandidateError(failure_message, audit) from exc

def post_only_buy_limit_price(*args, **kwargs):
    ask_ticks = (best_ask_price / min_tick_size).to_integral_value(rounding=ROUND_FLOOR)
    upper = ask_ticks * min_tick_size
    upper -= min_tick_size
    improved_bid = ((best_bid_price / min_tick_size).to_integral_value(rounding=ROUND_FLOOR) + 1) * min_tick_size
    if improved_bid < best_ask_price and improved_bid <= upper:
        return improved_bid
    if bid_grid > 0 and bid_grid < best_ask_price and bid_grid <= upper:
        return bid_grid
    return upper

def candidate_from_market(*args, **kwargs):
    \"/book\"
    \"/spread\"
    post_only_buy_limit_price()
    raise RuntimeError("selected market spread is unavailable")

def load_market_by_slug(args, slug, requested_outcome):
    fetch_json(args.gamma_url, "/markets", {"slug": slug}, args.timeout_seconds)
    fetch_json(args.gamma_url, "/events", {"slug": slug}, args.timeout_seconds)
    return {}

def scan(args):
    \"PMX_ALLOW_LIVE_SUBMIT=1\"
    return {}, {
        "rejections": {"post_only_price_unavailable": 0},
        "remote_side_effects": False,
        "authorized_for_live": False,
    }

def main():
    print({
        "candidate_market": str(args.output),
        "remote_side_effects": False,
        "authorized_for_live": False,
    })
    return 0
"""
            return original_read_text(path_self, *args, **kwargs)

        with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=fake_read_text):
            with self.assertRaises(ContractValidationError) as ctx:
                module.validate_canary_candidate_market_prep_boundary()
        self.assertIn("canary candidate market prep script public/safe surface contains forbidden token", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
