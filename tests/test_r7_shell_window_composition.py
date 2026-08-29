from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.composition import (
    development_shell_window_backend,
    provisional_installed_shell_window_backend,
)
from greia_launcher.shell_window import NoopShellWindowController
from greia_launcher.shell_window_legacy_x import LegacyXShellWindowController


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_MAIN = ROOT / "src" / "greia_launcher" / "main.py"
LEGACY_X_WINDOW = ROOT / "src" / "greia_launcher" / "shell_window_legacy_x.py"


class ShellWindowCompositionBoundaryTests(unittest.TestCase):
    def test_installed_and_development_paths_compose_explicit_backends(self) -> None:
        self.assertIsInstance(
            provisional_installed_shell_window_backend(),
            LegacyXShellWindowController,
        )
        self.assertIsInstance(
            development_shell_window_backend(),
            NoopShellWindowController,
        )

    def test_generic_launcher_contains_no_direct_x11_focus_mechanics(self) -> None:
        source = LAUNCHER_MAIN.read_text(encoding="utf-8")
        self.assertNotIn("_set_x11_input_focus", source)
        self.assertNotIn("XSetInputFocus", source)
        self.assertNotIn("XOpenDisplay", source)
        self.assertNotIn("SDL_VIDEODRIVER", source)
        self.assertIn(
            "self._shell_window_backend.after_window_created(pygame)",
            source,
        )

    def test_legacy_x_controller_does_not_choose_backend_from_environment(self) -> None:
        source = LEGACY_X_WINDOW.read_text(encoding="utf-8")
        self.assertNotIn("SDL_VIDEODRIVER", source)
        self.assertNotIn("os.environ", source)


if __name__ == "__main__":
    unittest.main()
