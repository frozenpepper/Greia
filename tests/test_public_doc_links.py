"""Relative links in the public entry documents must resolve.

These are the first pages a new contributor reads. A broken link there is
the cheapest kind of documentation rot to catch, so the check stays narrow:
only Markdown links in the entry documents, only repository-relative targets.
"""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]

ENTRY_DOCUMENTS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "NOTICE.md",
    "docs/DOCUMENTATION.md",
    "docs/archive/README.md",
)

# [text](target) — the target stops at whitespace or the closing parenthesis.
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _relative_targets(text: str) -> list[str]:
    targets = []
    for target in _LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


class PublicDocumentLinkTests(unittest.TestCase):
    def test_relative_links_in_entry_documents_resolve(self) -> None:
        for document in ENTRY_DOCUMENTS:
            path = ROOT / document
            with self.subTest(document=document):
                self.assertTrue(path.is_file(), f"{document} is missing")
                for target in _relative_targets(path.read_text(encoding="utf-8")):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(
                        resolved.exists(),
                        f"{document} links to missing {target}",
                    )


if __name__ == "__main__":
    unittest.main()
