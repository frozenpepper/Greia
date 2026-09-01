from __future__ import annotations

import unittest

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.composition import (
    development_shell_window_backend,
    provisional_installed_shell_window_backend,
)
from greia_launcher.presentation import GreiaLauncherPresentation
from greia_launcher.shell_window import NoopShellWindowController
from greia_launcher.shell_window_legacy_x import LegacyXShellWindowController


class _FakeDisplay:
    def __init__(self, window_id: int = 4242) -> None:
        self.window_id = window_id

    def get_wm_info(self):
        return {"window": self.window_id}


class _FakePygame:
    def __init__(self, window_id: int = 4242) -> None:
        self.display = _FakeDisplay(window_id)


class _RecordingFocusBridge:
    def __init__(self) -> None:
        self.windows: list[int] = []

    def focus_window(self, window_id: int) -> bool:
        self.windows.append(window_id)
        return True


class _RecordingShellWindowController:
    def __init__(self) -> None:
        self.returned: list[object] = []

    def after_activity_return(self, pygame: object) -> bool:
        self.returned.append(pygame)
        return True


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

    def test_noop_backend_accepts_both_bounded_lifecycle_hooks(self) -> None:
        backend = NoopShellWindowController()
        token = object()
        self.assertTrue(backend.after_window_created(token))
        self.assertTrue(backend.after_activity_return(token))

    def test_legacy_x_repairs_current_shell_focus_at_creation_and_return(self) -> None:
        bridge = _RecordingFocusBridge()
        backend = LegacyXShellWindowController(focus_bridge=bridge)
        pygame = _FakePygame(window_id=9123)

        self.assertTrue(backend.after_window_created(pygame))
        self.assertTrue(backend.after_activity_return(pygame))
        self.assertEqual(bridge.windows, [9123, 9123])

    def test_production_child_shell_restores_focus_after_launch_lifecycle(self) -> None:
        shell = object.__new__(GreiaChildShell)
        backend = _RecordingShellWindowController()
        shell._shell_window_backend = backend
        pygame = object()
        launch_calls: list[tuple[object, object]] = []

        original = GreiaLauncherPresentation._launch_selected

        def fake_launch(instance: object, pygame_arg: object) -> None:
            launch_calls.append((instance, pygame_arg))

        GreiaLauncherPresentation._launch_selected = fake_launch
        try:
            GreiaChildShell._launch_selected(shell, pygame)
        finally:
            GreiaLauncherPresentation._launch_selected = original

        self.assertEqual(launch_calls, [(shell, pygame)])
        self.assertEqual(backend.returned, [pygame])


if __name__ == "__main__":
    unittest.main()
