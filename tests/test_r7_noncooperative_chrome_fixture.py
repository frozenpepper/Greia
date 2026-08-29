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


def _python_symbols(source: str) -> set[str]:
    """Return executable/imported Python symbols, excluding comments/docstrings."""

    tree = ast.parse(source)
    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            symbols.add(node.id)
        elif isinstance(node, ast.Attribute):
            symbols.add(node.attr)
        elif isinstance(node, ast.alias):
            symbols.add(node.asname or node.name.rsplit(".", 1)[-1])
    return symbols


class R7NonCooperativeChromeFixtureTests(unittest.TestCase):
    def test_fixture_has_no_activity_owned_escape_or_chrome_path(self) -> None:
        source = (FIXTURE / "main.py").read_text(encoding="utf-8")
        symbols = _python_symbols(source)
        self.assertIn("mark_activity_ready", symbols)
        for forbidden in (
            "activity_stop_requested",
            "draw_system_chrome_overlay",
            "is_home_clicked",
            "K_ESCAPE",
            "QUIT",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, symbols)

    def test_fixture_is_backend_independent(self) -> None:
        findings = scan_python_activity_backend_policy(FIXTURE)
        blockers = [
            item for item in findings if item.severity is BackendFindingSeverity.BLOCKER
        ]
        self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
