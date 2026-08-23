from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pygame

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"

from greia_launcher.parent_panel import ParentPanelState, ParentSettingsOverlay
from greia_launcher.child_shell import GreiaChildShell
from greia_platform.hardware import HardwareSettingsStore
from greia_platform.main_credential import MainCredentialStore
from greia_platform.ssh_maintenance import (
    MockSshMaintenanceProvider,
    SshMaintenanceService,
    SshStatus,
)
from greia_platform.wifi import DemoWifiBackend


class SlowSshProvider(MockSshMaintenanceProvider):
    """Status provider whose subprocess-equivalent work takes measurable time."""

    def __init__(self, delay_seconds: float) -> None:
        super().__init__()
        self.delay_seconds = delay_seconds
        self.calls = 0

    def status(self) -> SshStatus:
        self.calls += 1
        time.sleep(self.delay_seconds)
        return super().status()


def _overlay(ssh_service) -> ParentSettingsOverlay:
    temp = tempfile.TemporaryDirectory()
    credential_store = MainCredentialStore(Path(temp.name) / "cred.json")
    credential_store.ensure_initialized()
    hardware_store = HardwareSettingsStore.load(
        REPO_ROOT / "runtime" / "hardware-settings.toml",
        Path(temp.name),
    )
    overlay = ParentSettingsOverlay(
        credential_store,
        wifi_backend=DemoWifiBackend(),
        ssh_service=ssh_service,
        hardware_store=hardware_store,
    )
    # Keep the state directory alive for as long as the overlay itself.
    overlay._test_temp_dir = temp
    return overlay


class ParentPanelTextLifecycleTests(unittest.TestCase):
    """The chord-opened panel must actually receive typed characters."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((320, 240))

    def test_entering_panel_activates_text_input_and_exit_stops_it(self) -> None:
        shell = GreiaChildShell(windowed=True)
        started: list[bool] = []
        stopped: list[bool] = []
        with mock.patch.object(
            pygame.key, "start_text_input", side_effect=lambda: started.append(True)
        ), mock.patch.object(
            pygame.key, "stop_text_input", side_effect=lambda: stopped.append(True)
        ):
            shell._enter_parent_panel(pygame)
            self.assertEqual(shell._mode, "parent_panel")
            self.assertEqual(shell._parent_panel.state, ParentPanelState.AUTH)
            self.assertTrue(
                started,
                "parent panel opened without activating text input; password typing is dead",
            )
            self.assertNotIn(
                True, stopped, "text input was stopped while opening the panel"
            )

            shell._exit_parent_panel(pygame)
            self.assertEqual(shell._mode, "profiles")
            self.assertTrue(stopped)
            self.assertEqual(shell._parent_panel.state, ParentPanelState.CLOSED)


class NonBlockingSshStatusTests(unittest.TestCase):
    def test_refresh_returns_before_slow_status_completes(self) -> None:
        provider = SlowSshProvider(0.15)
        overlay = _overlay(SshMaintenanceService(provider))
        overlay.open()

        start = time.monotonic()
        overlay.request_ssh_status_refresh(force=True)
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed,
            0.08,
            "SSH status refresh blocked the UI thread",
        )
        deadline = time.monotonic() + 2.0
        while overlay._ssh_results.empty() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(overlay.drain())
        self.assertIsNotNone(overlay.ssh_status)
        self.assertFalse(overlay.drain())

    def test_toggle_updates_cached_status_without_extra_poll(self) -> None:
        provider = MockSshMaintenanceProvider(active=False, enabled=False)
        overlay = _overlay(SshMaintenanceService(provider))
        overlay.open()
        overlay.handle_text_input("greia")

        class _PygameKeys:
            K_ESCAPE = 27
            K_BACKSPACE = 8
            K_RETURN = 13
            K_KP_ENTER = 271
            K_TAB = 9
            K_UP = 273
            K_DOWN = 274
            K_LEFT = 276
            K_RIGHT = 275
            K_SPACE = 32

        overlay.handle_key(_PygameKeys.K_RETURN, _PygameKeys)
        self.assertEqual(overlay.state, ParentPanelState.PANEL)
        overlay.handle_key(_PygameKeys.K_TAB, _PygameKeys)  # AUDIO
        overlay.handle_key(_PygameKeys.K_TAB, _PygameKeys)  # WIFI
        overlay.handle_key(_PygameKeys.K_TAB, _PygameKeys)  # SSH

        overlay.handle_key(_PygameKeys.K_SPACE, _PygameKeys)
        self.assertIsNotNone(overlay.ssh_status)
        self.assertTrue(overlay.ssh_status.active)

        overlay.handle_key(_PygameKeys.K_RETURN, _PygameKeys)
        self.assertFalse(overlay.ssh_status.active)


class MicGainReadThrottleTests(unittest.TestCase):
    def test_repeated_reads_do_not_hit_storage_every_call(self) -> None:
        provider = MockSshMaintenanceProvider()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = HardwareSettingsStore.load(
            REPO_ROOT / "runtime" / "hardware-settings.toml",
            Path(temp.name),
        )
        overlay = _overlay(SshMaintenanceService(provider))
        overlay.hardware_store = store

        original_read = store.read
        counter = {"reads": 0}

        def counting_read():
            counter["reads"] += 1
            return original_read()

        with unittest.mock.patch.object(store, "read", side_effect=counting_read):
            for _ in range(12):
                overlay._current_mic_gain()
        self.assertLessEqual(counter["reads"], 2)


class ChordRepeatGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Event draining in _enter_parent_panel requires an initialized
        # display; this class may otherwise run before any other does.
        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((320, 240))

    def test_text_rejected_while_chord_held_and_during_settle_window(self) -> None:
        shell = GreiaChildShell(windowed=True)
        shell._enter_parent_panel(pygame)

        now = shell._parent_panel_opened_monotonic + 0.05

        class HeldChord:
            is_holding = True

        original_chord = shell._parent_chord
        shell._parent_chord = HeldChord()
        try:
            self.assertFalse(shell._parent_panel_accepts_text(now))
        finally:
            shell._parent_chord = original_chord

        # Released, but still inside the settle window.
        self.assertFalse(shell._parent_panel_accepts_text(now))

        # Released and settled.
        self.assertTrue(
            shell._parent_panel_accepts_text(
                shell._parent_panel_opened_monotonic + 0.4
            )
        )
        shell._exit_parent_panel(pygame)


class TypographyRenderPipelineTests(unittest.TestCase):
    def test_get_text_uses_shared_render_with_caching(self) -> None:
        provider = MockSshMaintenanceProvider()
        overlay = _overlay(SshMaintenanceService(provider))
        typography = mock.MagicMock()
        sentinel = object()
        typography.render.return_value = sentinel

        first = overlay._get_text("🎙️ gain", __import__("greia_platform.typography", fromlist=["FontRole"]).FontRole.CONTROL, 18, (1, 2, 3), typography)
        second = overlay._get_text("🎙️ gain", __import__("greia_platform.typography", fromlist=["FontRole"]).FontRole.CONTROL, 18, (1, 2, 3), typography)

        self.assertIs(first, sentinel)
        self.assertIs(second, sentinel)
        self.assertEqual(typography.render.call_count, 1)
        typography.font.assert_not_called()


class MaskedPasswordTests(unittest.TestCase):
    def test_long_password_display_is_capped(self) -> None:
        provider = MockSshMaintenanceProvider()
        overlay = _overlay(SshMaintenanceService(provider))
        overlay.password_text = "x" * 80
        self.assertEqual(overlay._masked_password(20), "•" * 20)
        overlay.password_text = "abc"
        self.assertEqual(overlay._masked_password(20), "•••")
        overlay.password_text = ""
        self.assertEqual(overlay._masked_password(20), "")


class ModalHoverSuppressionTests(unittest.TestCase):
    """Picker hover must not invalidate while the Parent modal covers it."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def test_pointer_over_hidden_tile_does_not_invalidate_picker(self) -> None:
        from greia_launcher.child_shell import GreiaChildShell

        shell = GreiaChildShell(windowed=True)
        shell.profiles = shell.profile_store.ensure_initialized()
        screen = pygame.display.set_mode((1024, 600))
        shell._synthetic_pointer_active = True

        # Prime the picker cache with the pointer away from any target.
        shell._mode = "profiles"
        with mock.patch.object(
            pygame.mouse, "get_pos", return_value=(5, 590)
        ), mock.patch.object(pygame.mouse, "get_focused", return_value=True):
            shell._draw(screen, pygame)
        baseline_key = shell._cached_profiles_key
        self.assertIsNotNone(baseline_key)

        tile = next(
            (
                target
                for target in shell._cached_profiles_targets
                if target.action == "profile"
            ),
            None,
        )
        if tile is None:
            self.skipTest("no profile hit target available")
        center = tuple(tile.rect.center)

        # Open the modal; the pointer now sits on the hidden tile beneath it.
        shell._enter_parent_panel(pygame)
        with mock.patch.object(
            pygame.mouse, "get_pos", return_value=center
        ), mock.patch.object(pygame.mouse, "get_focused", return_value=True):
            shell._draw(screen, pygame)
        self.assertEqual(
            shell._cached_profiles_key,
            baseline_key,
            "hidden picker hover invalidated the cache under the modal",
        )

        # Sanity: in normal profiles mode the same pointer position DOES
        # invalidate (hover feedback is real there).
        shell._exit_parent_panel(pygame)
        with mock.patch.object(
            pygame.mouse, "get_pos", return_value=center
        ), mock.patch.object(pygame.mouse, "get_focused", return_value=True):
            shell._draw(screen, pygame)
        self.assertNotEqual(shell._cached_profiles_key, baseline_key)


if __name__ == "__main__":
    unittest.main()
