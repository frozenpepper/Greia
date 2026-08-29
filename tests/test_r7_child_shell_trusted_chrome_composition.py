from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.child_shell import ProfileVisualActivitySupervisor
from greia_launcher.trusted_chrome_supervisor import TrustedChromeActivitySupervisor
from greia_launcher.trusted_presentation import TrustedGreiaLauncherPresentation


ROOT = Path(__file__).resolve().parents[1]
CHILD_SHELL = ROOT / "src" / "greia_launcher" / "child_shell.py"
X_SESSION = ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os" / "greia-x-session"


class ChildShellTrustedChromeCompositionTests(unittest.TestCase):
    def test_profile_supervisor_extends_trusted_chrome_lifecycle(self) -> None:
        self.assertTrue(issubclass(ProfileVisualActivitySupervisor, TrustedChromeActivitySupervisor))

    def test_installed_child_shell_composes_platform_chrome_factory(self) -> None:
        source = CHILD_SHELL.read_text(encoding="utf-8")
        self.assertIn("provisional_installed_system_chrome", source)
        self.assertIn("system_chrome_coordinator=self._system_chrome_coordinator()", source)
        self.assertNotIn("draw_system_chrome_overlay", source)
        self.assertNotIn("is_home_clicked", source)

    def test_x_session_fallback_is_also_trusted(self) -> None:
        self.assertTrue(issubclass(TrustedGreiaLauncherPresentation, object))
        source = X_SESSION.read_text(encoding="utf-8")
        self.assertIn("greia_launcher.trusted_presentation", source)
        self.assertNotIn("-m greia_launcher.presentation\n", source)


if __name__ == "__main__":
    unittest.main()
