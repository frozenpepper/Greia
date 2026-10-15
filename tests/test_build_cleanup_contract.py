from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SAFE_CLEANUP = ROOT / "build/lib/safe-cleanup.sh"
BUILDERS = ("build/build-image.sh", "build/build-installer-image.sh")


def _cleanup_function(relative: str) -> str:
    text = (ROOT / relative).read_text(encoding="utf-8")
    start = text.index("cleanup() {")
    return text[start:text.index("trap cleanup EXIT", start)]


def _safe_cleanup_exit() -> str:
    text = SAFE_CLEANUP.read_text(encoding="utf-8")
    start = text.index("safe_cleanup_exit() {")
    return text[start:text.index("\n}\n", start)]


class BuildCleanupContractTests(unittest.TestCase):
    """Cleanup is an EXIT trap: returning non-zero from it does not reliably
    fail an otherwise successful process, so both builders delegate to the
    shared ``safe_cleanup_exit`` which ends in ``exit``."""

    def test_builders_capture_status_first_and_delegate_to_shared_exit(self) -> None:
        for relative in BUILDERS:
            with self.subTest(builder=relative):
                cleanup = _cleanup_function(relative)
                self.assertIn("local original_status=$?", cleanup)
                self.assertLess(
                    cleanup.index("local original_status=$?"),
                    cleanup.index("trap - EXIT INT TERM"),
                )
                self.assertIn("cleanup_failed=1", cleanup)
                self.assertIn(
                    'safe_cleanup_exit "$original_status" "$cleanup_failed"',
                    cleanup,
                )

    def test_successful_build_cannot_hide_cleanup_failure(self) -> None:
        body = _safe_cleanup_exit()
        self.assertIn("if (( cleanup_failed != 0 )); then", body)
        self.assertIn("if (( final_status == 0 )); then", body)
        self.assertIn("final_status=1", body)
        self.assertIn('exit "$final_status"', body)

    def test_original_build_failure_remains_authoritative(self) -> None:
        body = _safe_cleanup_exit()
        # The final status starts as the original one and is only replaced
        # when that was success, so a build failure is never overwritten.
        self.assertIn('local final_status="$original_status"', body)
        self.assertLess(
            body.index("if (( final_status == 0 )); then"),
            body.index('exit "$final_status"'),
        )
        code = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("return", code)


if __name__ == "__main__":
    unittest.main()
