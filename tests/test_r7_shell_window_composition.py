from __future__ import annotations

import unittest

from greia_launcher.composition import (
    development_shell_window_backend,
    provisional_installed_shell_window_backend,
)
from greia_launcher.shell_window import NoopShellWindowController
from greia_launcher.shell_window_legacy_x import LegacyXShellWindowController


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


if __name__ == "__main__":
    unittest.main()
