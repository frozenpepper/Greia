from __future__ import annotations

import unittest
from pathlib import Path

from greia_platform.activity_backend_policy import (
    BackendFindingSeverity,
    scan_python_activity_backend_policy,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "activities" / "r7_noncooperative_chrome"


class R7NonCooperativeChromeFixtureTests(unittest.TestCase):
    def test_fixture_has_no_activity_owned_escape_or_chrome_path(self) -> None:
        source = (FIXTURE / "main.py").read_text(encoding="utf-8")
        self.assertIn("mark_activity_ready", source)
        self.assertNotIn("activity_stop_requested", source)
        self.assertNotIn("draw_system_chrome_overlay", source)
        self.assertNotIn("is_home_clicked", source)
        self.assertNotIn("K_ESCAPE", source)
        self.assertNotIn("pygame.QUIT", source)

    def test_fixture_is_backend_independent(self) -> None:
        findings = scan_python_activity_backend_policy(FIXTURE)
        blockers = [
            item for item in findings if item.severity is BackendFindingSeverity.BLOCKER
        ]
        self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
