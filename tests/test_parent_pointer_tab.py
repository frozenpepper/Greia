from __future__ import annotations

import json
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
from greia_platform.display_metrics import (
    PHYSICAL_UI_CEILING_PX,
    PHYSICAL_UI_FLOOR_PX,
)
from greia_platform.hardware import HardwareSettingsStore
from greia_platform.hardware_session import (
    PointerCapabilities,
    PointerDeviceInfo,
    PointerKind,
    preset_to_speed,
    speed_preset_names,
)
from greia_platform.main_credential import MainCredentialStore
from greia_platform.ssh_maintenance import (
    MockSshMaintenanceProvider,
    SshMaintenanceService,
)
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


def _touchpad_info() -> PointerDeviceInfo:
    return PointerDeviceInfo(
        kind=PointerKind.TOUCHPAD,
        label="Touchpad",
        capabilities=PointerCapabilities(
            supports_tap=True,
            supports_natural_scrolling=True,
            supports_disable_while_typing=True,
            supports_speed=True,
        ),
    )


def _mouse_info() -> PointerDeviceInfo:
    return PointerDeviceInfo(
        kind=PointerKind.MOUSE,
        label="Mouse",
        capabilities=PointerCapabilities(
            supports_natural_scrolling=True,
            supports_speed=True,
        ),
    )


class FakePointerController:
    def __init__(self, infos) -> None:
        self._infos = tuple(infos)
        self.probe_calls = 0

    def probe_pointers(self):
        self.probe_calls += 1
        return self._infos


def _overlay(temp_dir: str, *, controller=None) -> ParentSettingsOverlay:
    cred_path = Path(temp_dir) / "main-credential.json"
    credential_store = MainCredentialStore(cred_path)
    credential_store.ensure_initialized()
    hardware_store = HardwareSettingsStore.load(
        PROJECT_ROOT / "runtime" / "hardware-settings.toml",
        Path(temp_dir),
    )
    return ParentSettingsOverlay(
        credential_store,
        wifi_backend=DemoWifiBackend([
            WifiNetwork("HomeNetwork", WifiSecurity.PERSONAL, -45.0, "/net/connman/iwd/demo/1"),
        ]),
        ssh_service=SshMaintenanceService(MockSshMaintenanceProvider()),
        hardware_store=hardware_store,
        pointer_controller=controller,
    )


def _unlock(overlay: ParentSettingsOverlay) -> None:
    overlay.open()
    overlay.handle_text_input("greia")
    overlay.handle_key(DummyPygame.K_RETURN, DummyPygame)
    assert overlay.state == ParentPanelState.PANEL
    overlay.active_tab = ParentPanelTab.POINTER


class PointerTabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def test_pointer_tab_exists_and_reachable(self) -> None:
        overlay = _overlay(self.temp_dir.name)
        self.assertIn("pointer", [tab.value for tab in ParentPanelTab])
        _unlock(overlay)
        self.assertEqual(overlay.active_tab, ParentPanelTab.POINTER)

    def test_touchpad_preset_round_trips_through_store(self) -> None:
        controller = FakePointerController([_touchpad_info(), _mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        overlay._set_pointer_preset("touchpad", "fast")
        self.assertEqual(
            overlay.hardware_store.read().touchpad_speed, preset_to_speed("fast")
        )
        self.assertEqual(overlay._pointer_current_preset("touchpad"), "fast")

    def test_mouse_preset_round_trips_through_store(self) -> None:
        controller = FakePointerController([_mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        overlay._set_pointer_preset("mouse", "slow")
        self.assertEqual(
            overlay.hardware_store.read().mouse_speed, preset_to_speed("slow")
        )

    def test_preset_names_come_from_shared_helper(self) -> None:
        self.assertEqual(
            list(speed_preset_names()),
            ["very slow", "slow", "medium", "fast", "very fast"],
        )
        overlay = _overlay(self.temp_dir.name)
        _unlock(overlay)
        # Unknown preset names are ignored, never written.
        before = overlay.hardware_store.read()
        overlay._set_pointer_preset("touchpad", "ludicrous")
        self.assertEqual(overlay.hardware_store.read(), before)

    def test_toggles_round_trip_through_store(self) -> None:
        controller = FakePointerController([_touchpad_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        overlay._toggle_pointer_setting("touchpad_tap")
        self.assertTrue(overlay.hardware_store.read().touchpad_tap)
        overlay._toggle_pointer_setting("touchpad_tap")
        self.assertFalse(overlay.hardware_store.read().touchpad_tap)
        overlay._toggle_pointer_setting("natural_scrolling")
        self.assertTrue(overlay.hardware_store.read().natural_scrolling)
        overlay._toggle_pointer_setting("disable_while_typing")
        self.assertTrue(overlay.hardware_store.read().disable_while_typing)

    def test_reset_returns_central_defaults(self) -> None:
        controller = FakePointerController([_touchpad_info(), _mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        overlay._set_pointer_preset("touchpad", "very fast")
        overlay._toggle_pointer_setting("touchpad_tap")
        overlay._reset_pointer_defaults()
        expected = overlay.hardware_store.default_settings()
        self.assertEqual(overlay.hardware_store.read(), expected)
        self.assertFalse(overlay.hardware_store.settings_path.exists())

    def test_no_touchpad_gates_touchpad_controls(self) -> None:
        controller = FakePointerController([_mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        self.assertFalse(overlay._pointer_has_touchpad())
        before = overlay.hardware_store.read()
        overlay._set_pointer_preset("touchpad", "fast")
        self.assertEqual(overlay.hardware_store.read().touchpad_speed, before.touchpad_speed)
        overlay._toggle_pointer_setting("touchpad_tap")
        self.assertEqual(overlay.hardware_store.read().touchpad_tap, before.touchpad_tap)
        # Mouse controls stay active without a touchpad.
        overlay._set_pointer_preset("mouse", "fast")
        self.assertEqual(
            overlay.hardware_store.read().mouse_speed, preset_to_speed("fast")
        )

    def test_keyboard_operates_pointer_tab(self) -> None:
        controller = FakePointerController([_touchpad_info(), _mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        items = overlay._pointer_focus_items()
        self.assertIn("touchpad_speed", items)
        self.assertIn("reset", items)
        # Move focus to a toggle and flip it by keyboard.
        overlay._pointer_focus = items.index("touchpad_tap")
        overlay._pointer_handle_key(DummyPygame.K_SPACE, DummyPygame)
        self.assertTrue(overlay.hardware_store.read().touchpad_tap)
        # Arrow keys step the touchpad preset.
        overlay._pointer_focus = items.index("touchpad_speed")
        overlay._set_pointer_preset("touchpad", "medium")
        overlay._pointer_handle_key(DummyPygame.K_RIGHT, DummyPygame)
        self.assertEqual(
            overlay.hardware_store.read().touchpad_speed, preset_to_speed("fast")
        )
        overlay._pointer_handle_key(DummyPygame.K_LEFT, DummyPygame)
        self.assertEqual(
            overlay.hardware_store.read().touchpad_speed, preset_to_speed("medium")
        )
        # Test targets flash by keyboard without any scoring.
        overlay._pointer_focus = items.index("test0")
        overlay._pointer_handle_key(DummyPygame.K_SPACE, DummyPygame)
        self.assertEqual(overlay._pointer_test_flash, 0)
        # Reset by keyboard.
        overlay._pointer_focus = items.index("reset")
        overlay._pointer_handle_key(DummyPygame.K_RETURN, DummyPygame)
        self.assertEqual(
            overlay.hardware_store.read(), overlay.hardware_store.default_settings()
        )

    def test_keyboard_escapes_with_adversarial_stored_values(self) -> None:
        overlay = _overlay(self.temp_dir.name)
        _unlock(overlay)
        overlay.hardware_store.settings_path.write_text(
            json.dumps({
                "schema_version": 2,
                "touchpad_tap": "yes",
                "touchpad_speed": 999.0,
                "mouse_speed": "wild",
                "natural_scrolling": 1,
                "resolution": "auto",
                "keyboard_layout": "us",
                "mic_gain": 2.0,
                "disable_while_typing": "maybe",
            }),
            encoding="utf-8",
        )
        overlay._cached_pointer_settings = None
        overlay._pointer_settings_read_at = 0.0
        # Nothing here may raise, even with garbage on disk.
        overlay._pointer_handle_key(DummyPygame.K_RIGHT, DummyPygame)
        overlay._pointer_handle_key(DummyPygame.K_SPACE, DummyPygame)
        overlay._pointer_handle_key(DummyPygame.K_DOWN, DummyPygame)
        stay = overlay.handle_key(DummyPygame.K_ESCAPE, DummyPygame)
        self.assertFalse(stay)
        self.assertEqual(overlay.state, ParentPanelState.CLOSED)

    def test_click_actions_cover_presets_toggles_reset_and_test(self) -> None:
        controller = FakePointerController([_touchpad_info(), _mouse_info()])
        overlay = _overlay(self.temp_dir.name, controller=controller)
        _unlock(overlay)
        overlay._targets = [
            PanelHitTarget("pointer_touchpad_preset", "slow", DummyRect(0, 0, 40, 40)),
            PanelHitTarget("pointer_toggle", "natural_scrolling", DummyRect(50, 0, 40, 40)),
            PanelHitTarget("pointer_test", 2, DummyRect(100, 0, 40, 40)),
            PanelHitTarget("pointer_reset", None, DummyRect(150, 0, 40, 40)),
        ]
        overlay.handle_click((10, 10))
        self.assertEqual(
            overlay.hardware_store.read().touchpad_speed, preset_to_speed("slow")
        )
        overlay.handle_click((60, 10))
        self.assertTrue(overlay.hardware_store.read().natural_scrolling)
        overlay.handle_click((110, 10))
        self.assertEqual(overlay._pointer_test_flash, 2)
        overlay.handle_click((160, 10))
        self.assertEqual(
            overlay.hardware_store.read(), overlay.hardware_store.default_settings()
        )

    def test_settings_and_probe_reads_are_bounded(self) -> None:
        overlay = _overlay(self.temp_dir.name)
        store = overlay.hardware_store
        original_read = store.read
        counter = {"reads": 0}

        def counting_read():
            counter["reads"] += 1
            return original_read()

        with mock.patch.object(store, "read", side_effect=counting_read):
            for _ in range(12):
                overlay._pointer_settings()
        self.assertLessEqual(counter["reads"], 2)

        controller = FakePointerController([_touchpad_info()])
        overlay2 = _overlay(self.temp_dir.name, controller=controller)
        overlay2._pointer_probe()
        overlay2._pointer_probe()
        overlay2._pointer_probe()
        self.assertEqual(controller.probe_calls, 1)

    def test_physical_floor_bounds_essential_controls(self) -> None:
        overlay = _overlay(self.temp_dir.name)
        floor = overlay._pointer_min_touch_px()
        self.assertGreaterEqual(floor, PHYSICAL_UI_FLOOR_PX)
        self.assertLessEqual(floor, PHYSICAL_UI_CEILING_PX)


if __name__ == "__main__":
    unittest.main()
