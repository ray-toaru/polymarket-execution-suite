import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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

    def test_rejects_current_source_wording_with_fixed_commit_pins(self):
        guard = load_guard()
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            scripts = tmp / "scripts"
            scripts.mkdir()
            (scripts / "active_docs.py").write_text(
                "ACTIVE_DOCS = ['DOC_STATUS.md']\n"
            )
            (tmp / "DOC_STATUS.md").write_text(
                "Current source is aligned with a review:\n"
                "- integration root: "
                "081f8240610189455d08a981ef309de02bdc61e3\n"
            )

            import sys
            sys.modules.pop("active_docs", None)
            with mock.patch.object(guard, "INTEGRATION_MODE", True):
                sys.path.insert(0, str(scripts))
                try:
                    failures = guard.active_source_pin_drift_failures(tmp)
                finally:
                    sys.path.remove(str(scripts))
                    sys.modules.pop("active_docs", None)

        self.assertEqual(
            failures,
            [
                "DOC_STATUS.md:1 uses current-source wording with fixed commit pins; "
                "use reviewed-packet or generated snapshot wording"
            ],
        )

    def test_allows_reviewed_packet_source_binding_with_fixed_commit_pins(self):
        guard = load_guard()
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            scripts = tmp / "scripts"
            scripts.mkdir()
            (scripts / "active_docs.py").write_text(
                "ACTIVE_DOCS = ['DOC_STATUS.md']\n"
            )
            (tmp / "DOC_STATUS.md").write_text(
                "Reviewed packet source binding:\n"
                "- integration root: "
                "081f8240610189455d08a981ef309de02bdc61e3\n"
            )

            import sys
            sys.modules.pop("active_docs", None)
            with mock.patch.object(guard, "INTEGRATION_MODE", True):
                sys.path.insert(0, str(scripts))
                try:
                    failures = guard.active_source_pin_drift_failures(tmp)
                finally:
                    sys.path.remove(str(scripts))
                    sys.modules.pop("active_docs", None)

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
