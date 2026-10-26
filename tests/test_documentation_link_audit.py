"""Pure source tests for Greia's read-only Markdown link audit."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from audit_greia_documentation import is_historical, markdown_files, scan


class DocumentationLinkAuditTests(unittest.TestCase):
    def test_scans_living_and_historical_without_mutating_anything(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text(
                "# A\n[guide](docs/user/README.md)\n", encoding="utf-8")
            user = root / "docs/user"
            user.mkdir(parents=True)
            (user / "README.md").write_text(
                "# Welcome\n[broken](missing.md)\n"
                "```markdown\n[not a link](never.md)\n```\n"
                "[external](https://example.com/file.md)\n",
                encoding="utf-8",
            )
            archive = root / "docs/archive/reviews"
            archive.mkdir(parents=True)
            (archive / "old.md").write_text(
                "# Old\n[old attachment](gone.png)\n", encoding="utf-8")
            before = [(path, path.read_bytes()) for path in markdown_files(root)]
            count, errors = scan(root)
            self.assertEqual(count, 3)
            self.assertEqual(len(errors), 2, errors)
            self.assertEqual([(x.historical, x.destination) for x in errors],
                             [(True, "gone.png"), (False, "missing.md")])
            self.assertEqual(before, [(path, path.read_bytes())
                                      for path in markdown_files(root)])

    def test_dated_test_procedures_are_historical_not_routing_docs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            live = root / "docs/testing/LOCAL_AGENT_START_HERE.md"
            dated = root / "docs/testing/2026-10-26_AB_STAGE_RETRY.md"
            dated.parent.mkdir(parents=True)
            live.write_text("# Current\n", encoding="utf-8")
            dated.write_text("# Historical\n", encoding="utf-8")
            self.assertFalse(is_historical(live, root))
            self.assertTrue(is_historical(dated, root))


if __name__ == "__main__":
    unittest.main()
