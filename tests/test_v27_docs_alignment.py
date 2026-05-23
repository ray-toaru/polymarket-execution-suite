from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


class V027DocsAlignmentTests(unittest.TestCase):
    def test_execution_engine_roadmap_reflects_v027_current_state(self):
        text = read("polymarket-execution-engine/docs/ROADMAP.md")
        self.assertIn("v0.27 development status", text)
        self.assertIn("Already landed for v0.27", text)
        self.assertIn("Remaining before v0.27 release", text)
        self.assertNotIn("Add a local-only real-funds canary CLI", text)
        self.assertNotIn("Add SDK read-only automatic market selection", text)

    def test_adapter_docs_reflect_executor_adapter_v027_state(self):
        readme = read("hermes-polymarket-executor-adapter/README.md")
        roadmap = read("hermes-polymarket-executor-adapter/docs/ROADMAP.md")
        progress = read("hermes-polymarket-executor-adapter/docs/PROGRESS.md")
        combined = "\n".join([readme, roadmap, progress])
        self.assertIn("v0.27 development status", readme)
        self.assertIn("Hermes executor adapter", combined)
        self.assertIn("no signing, no direct CLOB, no executor database credentials", combined)
        self.assertNotIn("## v0.2\n", roadmap)
        self.assertNotIn("Hermes plugin/tool registration", progress)


if __name__ == "__main__":
    unittest.main()
