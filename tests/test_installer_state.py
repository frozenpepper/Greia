from __future__ import annotations

import unittest
import threading
from pathlib import Path
from unittest import mock

from greia_installer.engine import InstallResult
from greia_installer.main import InstallerApplication, InstallerPage


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeRect:
    def __init__(self, inside: bool = True):
        self.inside = inside

    def collidepoint(self, position):
        return self.inside


class FakeMouse:
    def __init__(self, *, pressed: bool, position=(10, 10)):
        self.pressed = pressed
        self.position = position

    def get_pressed(self, *, num_buttons=3):
        return (self.pressed, False, False)

    def get_pos(self):
        return self.position


class FakePygame:
    def __init__(self, mouse: FakeMouse):
        self.mouse = mouse


class InstallerStateTests(unittest.TestCase):
    def make_app(self) -> InstallerApplication:
        return InstallerApplication(
            root=PROJECT_ROOT,
            payload=Path("/tmp/not-used.squashfs"),
            payload_digest=None,
            windowed=True,
            demo=True,
        )

    def test_demo_starts_safe_without_touchpad_tapping(self) -> None:
        app = self.make_app()
        self.assertEqual(app.state.page, InstallerPage.WELCOME)
        self.assertFalse(app.state.settings.touchpad_tap)
        self.assertEqual(app.state.target.path, Path("/dev/sda"))
        self.assertIn("1024x600", app.available_resolutions)

    def test_hold_is_cancelled_when_pointer_leaves_button(self) -> None:
        app = self.make_app()
        app.state.page = InstallerPage.CONFIRM
        rect = FakeRect(inside=False)
        app._buttons["install"] = rect
        app._hold_started = 10.0
        with mock.patch.object(app, "_start_installation") as start:
            app._update_install_hold(FakePygame(FakeMouse(pressed=True)))
        self.assertIsNone(app._hold_started)
        start.assert_not_called()

    def test_terminal_worker_event_releases_worker_for_safe_retry(self) -> None:
        app = self.make_app()
        app._worker = threading.Thread(target=lambda: None)
        app._events.put(RuntimeError("copy failed"))
        app._drain_worker_events()
        self.assertEqual(app.state.page, InstallerPage.ERROR)
        self.assertIsNone(app._worker)
        app._back()
        self.assertEqual(app.state.page, InstallerPage.CONFIRM)

    def test_success_event_preserves_recovery_code_for_completion_page(self) -> None:
        app = self.make_app()
        app._worker = threading.Thread(target=lambda: None)
        result = InstallResult("pip-recovery", "ABCDEFGHJKLMNPQRSTUV")
        app._events.put(result)
        app._drain_worker_events()
        self.assertEqual(app.state.page, InstallerPage.COMPLETE)
        self.assertEqual(app.state.result, result)
        self.assertIsNone(app._worker)

    def test_uninterrupted_hold_starts_installation_without_waiting_for_release(self) -> None:
        app = self.make_app()
        app.state.page = InstallerPage.CONFIRM
        app._buttons["install"] = FakeRect(inside=True)
        app._hold_started = 10.0
        with mock.patch("greia_installer.main.time.monotonic", return_value=12.1):
            with mock.patch.object(app, "_start_installation") as start:
                app._update_install_hold(FakePygame(FakeMouse(pressed=True)))
        self.assertIsNone(app._hold_started)
        start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
