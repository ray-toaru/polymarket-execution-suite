from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "hermes-polymarket-executor-adapter"


class AdapterDocsAlignmentTests(unittest.TestCase):
    def test_readme_uses_current_v028_status_wording(self) -> None:
        readme = (ADAPTER / "README.md").read_text()
        self.assertIn("## Current v0.28 adapter status", readme)
        self.assertNotIn("## v0.28 development status", readme)

    def test_roadmap_drops_stale_release_wording(self) -> None:
        roadmap = (ADAPTER / "docs/ROADMAP.md").read_text()
        self.assertIn("## Current v0.28 adapter status", roadmap)
        self.assertIn("## Current v0.28 release prerequisites", roadmap)
        self.assertNotIn("v0.27 Suite Release", roadmap)

    def test_plugin_docs_match_entrypoint_enablement_and_service_url_boundary(self) -> None:
        readme = (ADAPTER / "README.md").read_text()
        plugin = (ADAPTER / "docs/HERMES_PLUGIN.md").read_text()
        architecture = (ADAPTER / "docs/ARCHITECTURE.md").read_text()
        config = (ADAPTER / "src/hermes_polymarket_executor_adapter/config.py").read_text()

        for text in (readme, plugin):
            self.assertIn("plugins.enabled", text)
            self.assertIn("hermes plugins enable", text)
            self.assertIn("PM_EXEC_SERVICE_URL", text)
            self.assertIn("required", text)

        self.assertIn('optional ExecutorClient.submit_plan(mode="BLOCKED_DRY_RUN")', architecture)
        self.assertIn("The adapter does not permit live submit mode.", architecture)
        self.assertIn('raise RuntimeError("PM_EXEC_SERVICE_URL is required")', config)

    def test_review_title_is_current(self) -> None:
        review = (ADAPTER / "docs/REVIEW.md").read_text()
        self.assertIn("# Executor Adapter Review — v0.28", review)
        self.assertNotIn("v0.3", review)


if __name__ == "__main__":
    unittest.main()
