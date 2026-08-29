from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.child_shell import ProfileVisualActivitySupervisor
from greia_launcher.trusted_chrome_supervisor import TrustedChromeActivitySupervisor


ROOT = Path(__file__).resolve().parents[1]
CHILD_SHELL = ROOT / "src" / "greia_launcher" / "child_shell.py"


class ChildShellTrustedChromeCompositionTests(unittest.TestCase):
    def test_profile_supervisor_extends_trusted_chrome_lifecycle(self) -> None:
        self.assertTrue(issubclass(ProfileVisualActivitySupervisor, TrustedChromeActivitySupervisor))

    def test_installed_child_shell_composes_platform_chrome_factory(self) -> None:
        source = CHILD_SHELL.read_text(encoding="utf-8")
        self.assertIn("provisional_installed_system_chrome", source)
        self.assertIn("system_chrome_coordinator=self._system_chrome_coordinator()", source)
        self.assertNotIn("draw_system_chrome_overlay", source)
        self.assertNotIn("is_home_clicked", source)


if __name__ == "__main__":
    unittest.main()
