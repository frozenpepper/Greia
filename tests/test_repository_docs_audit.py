"""Read-only Markdown documentation inventory audits."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_repository_docs import audit, maintained, targets


class DocumentationAuditTests(unittest.TestCase):
    def test_scans_links_skips_code_external_and_anchor(self):
        markdown = (
            "# title\n"
            "[working](../other.md#section)\n"
            "[external](https://example.org/a.md)\n"
            "[same](#anchor)\n"
            "```md\n"
            "[not a link](deleted.md)\n"
            "```\n"
            "![image](../image.png)\n"
        )
        self.assertEqual(
            [target for _, target, _ in targets(markdown)],
            ["../other.md", "../image.png"],
        )

    def test_maintained_scope_excludes_historical_but_keeps_live_tests(self):
        self.assertTrue(maintained(Path("docs/user/README.md")))
        self.assertTrue(maintained(Path("docs/testing/LOCAL_AGENT_START_HERE.md")))
        self.assertFalse(maintained(Path("docs/testing/2026-09-01_OLD.md")))
        self.assertFalse(maintained(Path("docs/archive/README.md")))
        self.assertFalse(maintained(Path("docs/reviews/2026-08-01.md")))

    def test_invalid_relative_paths_are_reported_without_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/guide.md").write_text(
                "[good](../README.md)\n[missing](../missing.md)\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("# good\n", encoding="utf-8")
            count, errors = audit(root)
            self.assertEqual(count, 2)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].source.as_posix(), "docs/guide.md")
            self.assertEqual(errors[0].line, 2)
            self.assertFalse((root / "missing.md").exists())


if __name__ == "__main__":
    unittest.main()
