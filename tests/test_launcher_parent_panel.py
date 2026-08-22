from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.parent_panel import (
    PanelHitTarget,
    ParentPanelState,
    ParentPanelTab,
    ParentSettingsOverlay,
)
from greia_platform.hardware import HardwareSettingsStore
from greia_platform.main_credential import MainCredentialStore
from greia_platform.ssh_maintenance import MockSshMaintenanceProvider, SshMaintenanceService
from greia_platform.wifi import DemoWifiBackend, WifiNetwork, WifiSecurity

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DummyPygame:
    K_ESCAPE = 27
    K_BACKSPACE = 8
    K_RETURN = 13
    K_KP_ENTER = 271
    K_TAB = 9
    K_UP = 273
    K_DOWN = 274
    K_RIGHT = 275
    K_LEFT = 276
    K_SPACE = 32


class DummyRect:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    def collidepoint(self, pos: tuple[int, int]) -> bool:
        px, py = pos
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


class ParentSettingsOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cred_path = Path(self.temp_dir.name) / "main-credential.json"
        self.credential_store = MainCredentialStore(self.cred_path)
        self.credential_store.ensure_initialized()

        self.hardware_store = HardwareSettingsStore.load(
            PROJECT_ROOT / "runtime" / "hardware-settings.toml",
            Path(self.temp_dir.name),
        )
        self.wifi_backend = DemoWifiBackend([
            WifiNetwork("HomeNetwork", WifiSecurity.PERSONAL, -45.0, "/net/connman/iwd/demo/1"),
            WifiNetwork("GuestOpen", WifiSecurity.OPEN, -60.0, "/net/connman/iwd/demo/2"),
        ])
        self.ssh_provider = MockSshMaintenanceProvider(active=False, enabled=False)
        self.ssh_service = SshMaintenanceService(self.ssh_provider)

        self.overlay = ParentSettingsOverlay(
            self.credential_store,
            wifi_backend=self.wifi_backend,
            ssh_service=self.ssh_service,
            hardware_store=self.hardware_store,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initial_state_is_closed(self) -> None:
        self.assertEqual(self.overlay.state, ParentPanelState.CLOSED)
        self.assertFalse(self.overlay.is_open)

    def test_open_transitions_to_auth_and_escape_closes(self) -> None:
        self.overlay.open()
        self.assertEqual(self.overlay.state, ParentPanelState.AUTH)
        self.assertTrue(self.overlay.is_open)

        # Press Escape
        stay = self.overlay.handle_key(DummyPygame.K_ESCAPE, DummyPygame)
        self.assertFalse(stay)
        self.assertEqual(self.overlay.state, ParentPanelState.CLOSED)
        self.assertFalse(self.overlay.is_open)

    def test_wrong_password_rejected_and_correct_password_unlocks(self) -> None:
        self.overlay.open()

        # Enter wrong password
        self.overlay.handle_text_input("wrongpass")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertEqual(self.overlay.state, ParentPanelState.AUTH)
        self.assertGreater(self.overlay.password_error_until, 0.0)

        # Clear error lock
        self.overlay.password_error_until = 0.0

        # Enter correct default password 'greia'
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertEqual(self.overlay.state, ParentPanelState.PANEL)
        self.assertTrue(self.overlay.is_open)

    def test_tab_cycling_in_panel(self) -> None:
        self.overlay.open()
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertEqual(self.overlay.state, ParentPanelState.PANEL)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.LANGUAGE)

        # Tab -> AUDIO
        self.overlay.handle_key(DummyPygame.K_TAB, DummyPygame)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.AUDIO)

        # Tab -> WIFI
        self.overlay.handle_key(DummyPygame.K_TAB, DummyPygame)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.WIFI)

        # Tab -> SSH
        self.overlay.handle_key(DummyPygame.K_TAB, DummyPygame)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.SSH)

        # Tab -> INFO
        self.overlay.handle_key(DummyPygame.K_TAB, DummyPygame)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.INFO)

        # Tab -> LANGUAGE
        self.overlay.handle_key(DummyPygame.K_TAB, DummyPygame)
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.LANGUAGE)

    def test_audio_gain_adjustment_in_audio_tab(self) -> None:
        self.overlay.open()
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.overlay.active_tab = ParentPanelTab.AUDIO

        # Initial gain is default 2.0
        self.assertAlmostEqual(self.overlay._current_mic_gain(), 2.0)

        # Right key increases gain
        self.overlay.handle_key(DummyPygame.K_RIGHT, DummyPygame)
        self.assertAlmostEqual(self.overlay._current_mic_gain(), 2.25)

        # Left key decreases gain
        self.overlay.handle_key(DummyPygame.K_LEFT, DummyPygame)
        self.assertAlmostEqual(self.overlay._current_mic_gain(), 2.0)

    def test_ssh_toggle_in_ssh_tab(self) -> None:
        self.overlay.open()
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.overlay.active_tab = ParentPanelTab.SSH

        self.assertFalse(self.ssh_service.get_status().active)
        # Press Space to toggle
        self.overlay.handle_key(DummyPygame.K_SPACE, DummyPygame)
        self.assertTrue(self.ssh_service.get_status().active)

        # Press Return to toggle off
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertFalse(self.ssh_service.get_status().active)

    def test_click_tab_switching_does_not_crash(self) -> None:
        self.overlay.open()
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertEqual(self.overlay.state, ParentPanelState.PANEL)

        # Simulate clicking the switch_tab targets
        self.overlay._targets = [
            PanelHitTarget("switch_tab", ParentPanelTab.AUDIO, DummyRect(100, 50, 100, 30)),
            PanelHitTarget("switch_tab", ParentPanelTab.WIFI, DummyRect(210, 50, 100, 30)),
            PanelHitTarget("switch_tab", ParentPanelTab.SSH, DummyRect(320, 50, 100, 30)),
            PanelHitTarget("switch_tab", ParentPanelTab.INFO, DummyRect(430, 50, 100, 30)),
            PanelHitTarget("switch_tab", ParentPanelTab.LANGUAGE, DummyRect(540, 50, 100, 30)),
        ]

        # Click Audio & Mic tab
        self.overlay.handle_click((120, 60))
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.AUDIO)

        # Click Wi-Fi tab
        self.overlay.handle_click((220, 60))
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.WIFI)

        # Click SSH tab
        self.overlay.handle_click((330, 60))
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.SSH)

        # Click Info tab
        self.overlay.handle_click((440, 60))
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.INFO)

        # Click Language tab
        self.overlay.handle_click((550, 60))
        self.assertEqual(self.overlay.active_tab, ParentPanelTab.LANGUAGE)

    def test_click_mic_gain_presets(self) -> None:
        self.overlay.open()
        self.overlay.handle_text_input("greia")
        self.overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.overlay.active_tab = ParentPanelTab.AUDIO

        self.overlay._targets = [
            PanelHitTarget("mic_gain_set", 3.0, DummyRect(100, 150, 50, 50)),
            PanelHitTarget("mic_gain_adjust", -0.25, DummyRect(200, 150, 50, 50)),
        ]

        self.overlay.handle_click((110, 160))
        self.assertAlmostEqual(self.overlay._current_mic_gain(), 3.0)

        self.overlay.handle_click((210, 160))
        self.assertAlmostEqual(self.overlay._current_mic_gain(), 2.75)


if __name__ == "__main__":
    unittest.main()
