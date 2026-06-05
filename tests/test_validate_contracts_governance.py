from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
