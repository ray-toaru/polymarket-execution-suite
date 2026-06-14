import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = (
    ROOT
    / "polymarket-execution-engine"
    / "validation"
    / "check_docs_evidence_governance.py"
)


def load_guard():
    spec = importlib.util.spec_from_file_location("docs_evidence_guard", GUARD)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DocsEvidenceStatusBindingTests(unittest.TestCase):
    def test_rejects_documented_pass_when_current_manifest_is_skipped(self):
        guard = load_guard()
        manifest = {"postgres_validation": {"status": "skipped"}}
        docs = {
            "IMPLEMENTATION_STATUS.md": (
                "Current manifest gate statuses:\n"
                "- `postgres_validation=pass`\n"
            )
        }

        failures = guard.current_status_binding_failures(
            manifest,
            docs,
            sections=("postgres_validation",),
        )

        self.assertEqual(
            failures,
            [
                "IMPLEMENTATION_STATUS.md current status for "
                "postgres_validation is pass, manifest is skipped"
            ],
        )

    def test_accepts_matching_current_status_and_ignores_historical_pass(self):
        guard = load_guard()
        manifest = {"postgres_validation": {"status": "skipped"}}
        docs = {
            "RELEASE_DECISION.md": (
                "Current manifest gate statuses:\n"
                "- `postgres_validation=skipped`\n"
                "Historical evidence: postgres_validation passed on 2026-05-23.\n"
            )
        }

        self.assertEqual(
            guard.current_status_binding_failures(
                manifest,
                docs,
                sections=("postgres_validation",),
            ),
            [],
        )

    def test_requires_each_current_document_to_bind_all_gate_statuses(self):
        guard = load_guard()
        manifest = {"postgres_validation": {"status": "skipped"}}
        docs = {"RELEASE_DECISION.md": "No current status marker.\n"}

        self.assertEqual(
            guard.current_status_binding_failures(
                manifest,
                docs,
                sections=("postgres_validation",),
            ),
            [
                "RELEASE_DECISION.md missing current status binding for "
                "postgres_validation"
            ],
        )


if __name__ == "__main__":
    unittest.main()
