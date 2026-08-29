from __future__ import annotations

import ast
import unittest
from pathlib import Path

from greia_platform.activity_backend_policy import (
    BackendFindingSeverity,
    scan_python_activity_backend_policy,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "activities" / "r7_noncooperative_chrome"


def _fixture_names() -> set[str]:
    """AST-walk the fixture and return every Name / Attribute tail used.

    This is the strict source invariant: a comment or docstring that happens
    to contain a forbidden token must not be reported as a real reference.
    """
    source = (FIXTURE / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


class R7NonCooperativeChromeFixtureTests(unittest.TestCase):
    def test_fixture_has_no_activity_owned_escape_or_chrome_path(self) -> None:
        source = (FIXTURE / "main.py").read_text(encoding="utf-8")
        self.assertIn("mark_activity_ready", source)
        names = _fixture_names()
        for forbidden in (
            "activity_stop_requested",
            "draw_system_chrome_overlay",
            "is_home_clicked",
        ):
            self.assertNotIn(
                forbidden,
                names,
                f"fixture must not reference {forbidden} as a real symbol",
            )
        # Pygame input keys are real Name lookups; they show up in the AST
        # walk above if the fixture references them.
        self.assertNotIn("K_ESCAPE", names)
        self.assertNotIn("QUIT", names)

    def test_fixture_is_backend_independent(self) -> None:
        findings = scan_python_activity_backend_policy(FIXTURE)
        blockers = [
            item for item in findings if item.severity is BackendFindingSeverity.BLOCKER
        ]
        self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
