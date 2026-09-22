from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MakefileHygieneTests(unittest.TestCase):
    def test_clean_bytecode_stays_inside_source_owned_python_trees(self) -> None:
        makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "PYTHON_SOURCE_ROOTS := src tests tools activities",
            makefile,
        )

        start = makefile.index("clean-bytecode:")
        end = makefile.index("\ntest:", start)
        clean_block = makefile[start:end]

        # Keep cleanup directly scoped to source-owned Python trees. Avoid a
        # shell loop entirely so Make/shell variable escaping cannot silently
        # redirect cleanup away from the intended roots.
        self.assertNotIn("for root in", clean_block)
        self.assertNotIn("$root", clean_block)
        self.assertIn(
            "find $(PYTHON_SOURCE_ROOTS) -type d -name __pycache__",
            clean_block,
        )
        self.assertIn(
            'find $(PYTHON_SOURCE_ROOTS) -type f -name "*.py[co]" -delete',
            clean_block,
        )

        # Build/evidence/cache roots such as tmp/ and out/ may legitimately be
        # root-owned after privileged release work. Repository verification
        # must not recursively traverse arbitrary ignored state.
        self.assertNotIn("find . -type", clean_block)

        # Root-level Python bytecode is still cleaned without recursively
        # descending into unrelated ignored directories.
        self.assertIn("find . -maxdepth 1 -type d -name __pycache__", clean_block)
        self.assertIn('find . -maxdepth 1 -type f -name "*.py[co]" -delete', clean_block)


    def test_source_footprint_ignores_ignored_build_evidence_in_git_checkouts(self) -> None:
        script = (PROJECT_ROOT / "build/footprint-source.sh").read_text(encoding="utf-8")
        self.assertIn('git -C "$root" rev-parse --is-inside-work-tree', script)
        self.assertIn('["git", "-C", str(root), "ls-files", "-z"]', script)
        self.assertIn("tracked source files", script)
        self.assertNotIn('echo "Source archive-relevant footprint:"\ndu -sh "$root"', script)


if __name__ == "__main__":
    unittest.main()
