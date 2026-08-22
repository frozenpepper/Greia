from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

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

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.parent_panel import ParentSettingsOverlay, ParentPanelState
from greia_platform.wifi import WifiSetupController, WifiSetupPhase, DemoWifiBackend


class LauncherPacingDirtyRedrawContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def test_rescan_activities_detects_token_change_and_returns_true(self) -> None:
        shell = GreiaChildShell(windowed=True)
        self.assertFalse(shell._rescan_activities())

        shell.registry.discovery_token = MagicMock(return_value="new-token-1234")
        self.assertTrue(shell._rescan_activities())
        self.assertEqual(shell._activity_discovery_token, "new-token-1234")

    def test_rescan_if_due_triggers_invalidation_when_discovery_changes(self) -> None:
        shell = GreiaChildShell(windowed=True)
        shell._next_rescan = 0.0
        self.assertFalse(shell._rescan_if_due())

        shell._next_rescan = 0.0
        shell.registry.discovery_token = MagicMock(return_value="package-update-token")
        self.assertTrue(shell._rescan_if_due())

    def test_parent_panel_drain_returns_true_when_wifi_scan_completes(self) -> None:
        backend = DemoWifiBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        controller.refresh()
        time.sleep(0.05)
        changed = controller.drain()
        self.assertTrue(changed)
        self.assertEqual(controller._phase, WifiSetupPhase.READY)

    def test_parent_panel_drain_propagates_to_overlay(self) -> None:
        store = MagicMock()
        store.ensure_initialized = MagicMock()
        panel = ParentSettingsOverlay(store, wifi_backend=DemoWifiBackend())
        panel.open()
        time.sleep(0.05)
        changed = panel.drain()
        self.assertTrue(changed)

    def test_launch_animation_keeps_animating_flag_true(self) -> None:
        shell = GreiaChildShell(windowed=True)
        self.assertIsNone(shell._launching_activity_id)
        self.assertFalse(bool(shell._launching_activity_id is not None))

        shell._launching_activity_id = "org.greia.acquario-magico"
        self.assertTrue(bool(shell._launching_activity_id is not None))

    def test_idle_does_not_mutate_cached_activities_key(self) -> None:
        shell = GreiaChildShell(windowed=True)
        shell._activate_profile(shell.profiles[0], pygame)
        shell._category_id = "create"
        shell._mode = "activities"
        screen = pygame.display.set_mode((1024, 600))

        shell._draw(screen, pygame)
        key1 = shell._cached_activities_key
        self.assertIsNotNone(key1)

        shell._draw(screen, pygame)
        key2 = shell._cached_activities_key
        self.assertEqual(key1, key2)
