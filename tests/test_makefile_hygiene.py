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

        # Build/evidence/cache roots such as tmp/ and out/ may legitimately be
        # root-owned after privileged release work. Repository verification
        # must not traverse arbitrary ignored state merely to remove bytecode.
        self.assertNotIn("find . -type", clean_block)
        self.assertIn('find "$$root" -type d -name __pycache__', clean_block)
        self.assertIn('find "$$root" -type f -name "*.py[co]" -delete', clean_block)

        # Root-level Python bytecode is still cleaned without recursively
        # descending into unrelated ignored directories.
        self.assertIn("find . -maxdepth 1 -type d -name __pycache__", clean_block)
        self.assertIn('find . -maxdepth 1 -type f -name "*.py[co]" -delete', clean_block)


if __name__ == "__main__":
    unittest.main()
