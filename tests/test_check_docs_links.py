import tempfile
import unittest
from pathlib import Path

from scripts import check_docs_links


class CheckDocsLinksTests(unittest.TestCase):
    def test_local_link_target_ignores_external_and_anchor_links(self):
        source = Path("/tmp/docs/README.md")
        self.assertIsNone(check_docs_links.local_link_target(source, "https://example.com"))
        self.assertIsNone(check_docs_links.local_link_target(source, "#section"))
        self.assertIsNone(check_docs_links.local_link_target(source, "mailto:test@example.com"))

    def test_broken_links_reports_missing_local_target(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            source = root / "README.md"
            source.write_text("[present](docs/ok.md)\n[missing](docs/missing.md)\n")
            (root / "docs").mkdir()
            (root / "docs" / "ok.md").write_text("ok\n")

            self.assertEqual(
                check_docs_links.broken_links([source], root),
                ["README.md: missing local link target docs/missing.md"],
            )

    def test_broken_links_accepts_root_relative_and_fragment_targets(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            source = root / "docs" / "README.md"
            source.parent.mkdir()
            source.write_text("[root](/README.md#top)\n[local](other.md#section)\n")
            (root / "README.md").write_text("# Top\n")
            (source.parent / "other.md").write_text("# Section\n")

            self.assertEqual(check_docs_links.broken_links([source], root), [])


if __name__ == "__main__":
    unittest.main()
