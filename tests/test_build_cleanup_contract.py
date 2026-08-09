from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildCleanupContractTests(unittest.TestCase):
    def test_successful_build_cannot_hide_cleanup_failure(self) -> None:
        for relative in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            cleanup_start = text.index("cleanup() {")
            trap_start = text.index("trap cleanup EXIT", cleanup_start)
            cleanup = text[cleanup_start:trap_start]
            self.assertIn("if (( cleanup_failed != 0 )); then", cleanup)
            self.assertIn("if (( original_status == 0 )); then", cleanup)
            self.assertIn("return 1", cleanup)
            self.assertIn('return "$original_status"', cleanup)

    def test_original_build_failure_remains_authoritative(self) -> None:
        for relative in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            cleanup = text[text.index("cleanup() {"):text.index("trap cleanup EXIT")]
            self.assertLess(
                cleanup.index("if (( original_status == 0 )); then"),
                cleanup.rindex('return "$original_status"'),
            )


if __name__ == "__main__":
    unittest.main()
