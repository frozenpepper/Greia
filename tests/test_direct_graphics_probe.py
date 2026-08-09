from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from greia_platform.direct_graphics_probe import (
    DirectGraphicsProbe,
    ProbeInputs,
    _pygame_metadata,
)


class DirectGraphicsProbeTests(unittest.TestCase):
    def _fixture_root(self, temporary: str) -> Path:
        root = Path(temporary)
        dri = root / "dev" / "dri"
        dri.mkdir(parents=True)
        (dri / "card0").touch()
        (dri / "renderD128").touch()
        connector = root / "sys" / "class" / "drm" / "card0-eDP-1"
        connector.mkdir(parents=True)
        (connector / "status").write_text("connected\n", encoding="utf-8")
        (connector / "modes").write_text(
            "1024x600\n800x600\n", encoding="utf-8"
        )

        input_root = root / "dev" / "input"
        input_root.mkdir(parents=True)
        (input_root / "event3").touch()
        input_event = root / "sys" / "class" / "input" / "event3" / "device"
        input_event.mkdir(parents=True)
        (input_event / "name").write_text("Greia Test Touchpad\n", encoding="utf-8")

        (root / "run" / "systemd" / "system").mkdir(parents=True)
        seats = root / "run" / "systemd" / "seats"
        seats.mkdir(parents=True)
        (seats / "seat0").write_text("ACTIVE=u1\n", encoding="utf-8")
        sessions = root / "run" / "systemd" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "u1").write_text("SEAT=seat0\n", encoding="utf-8")
        active_vt = root / "sys" / "class" / "tty" / "tty0"
        active_vt.mkdir(parents=True)
        (active_vt / "active").write_text("tty1\n", encoding="utf-8")
        return root

    @staticmethod
    def _libraries(name: str) -> str | None:
        if name in {"drm", "gbm", "EGL", "input", "seat"}:
            return f"lib{name}.so"
        return None

    def test_probe_reports_prerequisites_without_claiming_active_kms_or_input_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(temporary)
            probe = DirectGraphicsProbe(
                ProbeInputs(
                    root=root,
                    environment={
                        "DISPLAY": ":0-secret-display-value",
                        "XAUTHORITY": "/secret/xauthority",
                        "SDL_VIDEODRIVER": "kmsdrm",
                        "XDG_SEAT": "seat0",
                        "XDG_VTNR": "1",
                        "XDG_SESSION_ID": "secret-session-id",
                    },
                ),
                library_finder=self._libraries,
                sdl_driver_probe=lambda: ("x11", "kmsdrm", "dummy"),
                pygame_probe=lambda: {
                    "available": True,
                    "version": "2.6.1",
                    "sdl_version": [2, 32, 4],
                },
            )
            snapshot = probe.snapshot()

        self.assertTrue(snapshot["passive"])
        self.assertTrue(snapshot["sdl"]["kmsdrm_compiled"])
        self.assertEqual(snapshot["drm"]["card_nodes"], ["card0"])
        self.assertEqual(snapshot["drm"]["render_nodes"], ["renderD128"])
        self.assertEqual(
            snapshot["drm"]["connectors"],
            [
                {
                    "name": "card0-eDP-1",
                    "status": "connected",
                    "modes": ["1024x600", "800x600"],
                }
            ],
        )
        self.assertEqual(snapshot["input"]["event_nodes"], ["event3"])
        self.assertEqual(
            snapshot["input"]["sysfs_events"],
            [{"event": "event3", "name": "Greia Test Touchpad"}],
        )
        self.assertTrue(snapshot["session"]["logind_runtime_present"])
        self.assertTrue(snapshot["session"]["seat0_runtime_present"])
        self.assertEqual(snapshot["session"]["session_runtime_count"], 1)
        self.assertEqual(snapshot["session"]["active_vt"], "tty1")
        self.assertTrue(snapshot["session"]["display_present"])
        self.assertTrue(snapshot["session"]["xauthority_present"])
        self.assertTrue(snapshot["assessment"]["scanout_connector_visible"])
        self.assertTrue(snapshot["assessment"]["input_topology_visible"])
        self.assertTrue(snapshot["assessment"]["seat_runtime_visible"])
        self.assertTrue(snapshot["assessment"]["kmsdrm_prerequisites_visible"])
        self.assertTrue(snapshot["assessment"]["active_kmsdrm_test_required"])
        self.assertTrue(snapshot["assessment"]["active_seat_input_test_required"])
        representation = repr(snapshot)
        self.assertNotIn(":0-secret-display-value", representation)
        self.assertNotIn("/secret/xauthority", representation)
        self.assertNotIn("secret-session-id", representation)
        self.assertNotIn("ACTIVE=u1", representation)

    def test_installed_libraries_do_not_substitute_for_compiled_kms_driver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(temporary)
            snapshot = DirectGraphicsProbe(
                ProbeInputs(root=root, environment={}),
                library_finder=self._libraries,
                sdl_driver_probe=lambda: ("x11", "wayland", "dummy"),
                pygame_probe=lambda: {"available": False},
            ).snapshot()

        self.assertFalse(snapshot["sdl"]["kmsdrm_compiled"])
        self.assertTrue(snapshot["assessment"]["scanout_connector_visible"])
        self.assertTrue(snapshot["assessment"]["input_topology_visible"])
        self.assertTrue(snapshot["assessment"]["seat_runtime_visible"])
        self.assertFalse(snapshot["assessment"]["kmsdrm_prerequisites_visible"])

    def test_card_without_connected_mode_is_not_a_visible_scanout_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(temporary)
            connector = root / "sys" / "class" / "drm" / "card0-eDP-1"
            (connector / "status").write_text("disconnected\n", encoding="utf-8")
            (connector / "modes").write_text("\n", encoding="utf-8")
            snapshot = DirectGraphicsProbe(
                ProbeInputs(root=root, environment={}),
                library_finder=self._libraries,
                sdl_driver_probe=lambda: ("kmsdrm", "dummy"),
                pygame_probe=lambda: {"available": True},
            ).snapshot()

        self.assertEqual(snapshot["drm"]["card_nodes"], ["card0"])
        self.assertFalse(snapshot["assessment"]["scanout_connector_visible"])
        self.assertFalse(snapshot["assessment"]["kmsdrm_prerequisites_visible"])

    def test_connected_connector_without_modes_is_not_a_visible_scanout_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(temporary)
            connector = root / "sys" / "class" / "drm" / "card0-eDP-1"
            (connector / "modes").write_text("\n", encoding="utf-8")
            snapshot = DirectGraphicsProbe(
                ProbeInputs(root=root, environment={}),
                library_finder=self._libraries,
                sdl_driver_probe=lambda: ("kmsdrm",),
                pygame_probe=lambda: {"available": True},
            ).snapshot()

        self.assertTrue(snapshot["drm"]["card_nodes"])
        self.assertFalse(snapshot["assessment"]["scanout_connector_visible"])
        self.assertFalse(snapshot["assessment"]["kmsdrm_prerequisites_visible"])

    def test_missing_runtime_facts_are_reported_without_active_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = DirectGraphicsProbe(
                ProbeInputs(root=Path(temporary), environment={}),
                library_finder=lambda name: None,
                sdl_driver_probe=lambda: (),
                pygame_probe=lambda: (_ for _ in ()).throw(ImportError("pygame")),
            ).snapshot()

        self.assertEqual(snapshot["drm"]["card_nodes"], [])
        self.assertEqual(snapshot["drm"]["connectors"], [])
        self.assertEqual(snapshot["input"]["event_nodes"], [])
        self.assertEqual(snapshot["input"]["sysfs_events"], [])
        self.assertFalse(snapshot["pygame"]["available"])
        self.assertFalse(snapshot["session"]["logind_runtime_present"])
        self.assertFalse(snapshot["session"]["seat0_runtime_present"])
        self.assertEqual(snapshot["session"]["session_runtime_count"], 0)
        self.assertEqual(snapshot["session"]["active_vt"], "")
        self.assertFalse(snapshot["assessment"]["scanout_connector_visible"])
        self.assertFalse(snapshot["assessment"]["input_topology_visible"])
        self.assertFalse(snapshot["assessment"]["seat_runtime_visible"])
        self.assertFalse(snapshot["assessment"]["kmsdrm_prerequisites_visible"])
        self.assertTrue(snapshot["assessment"]["active_kmsdrm_test_required"])
        self.assertTrue(snapshot["assessment"]["active_seat_input_test_required"])

    def test_input_inventory_is_bounded_and_does_not_open_devices(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dev_input = root / "dev" / "input"
            dev_input.mkdir(parents=True)
            sys_input = root / "sys" / "class" / "input"
            for index in range(140):
                (dev_input / f"event{index}").touch()
                device = sys_input / f"event{index}" / "device"
                device.mkdir(parents=True)
                (device / "name").write_text("device\n", encoding="utf-8")
            snapshot = DirectGraphicsProbe(
                ProbeInputs(root=root, environment={}),
                library_finder=lambda name: None,
                sdl_driver_probe=lambda: (),
                pygame_probe=lambda: {"available": False},
            ).snapshot()

        self.assertEqual(len(snapshot["input"]["event_nodes"]), 128)
        self.assertEqual(len(snapshot["input"]["sysfs_events"]), 128)

    def test_pygame_metadata_hides_support_prompt_and_restores_caller_environment(self) -> None:
        fake_pygame = SimpleNamespace(
            get_sdl_version=lambda: (2, 32, 4),
            version=SimpleNamespace(ver="2.6.1"),
        )

        def import_pygame(name: str) -> object:
            self.assertEqual(name, "pygame")
            self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
            return fake_pygame

        with patch.dict(os.environ, {"PYGAME_HIDE_SUPPORT_PROMPT": "caller"}):
            with patch(
                "greia_platform.direct_graphics_probe.importlib.import_module",
                side_effect=import_pygame,
            ):
                metadata = _pygame_metadata()
            self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "caller")

        self.assertEqual(metadata["version"], "2.6.1")
        self.assertEqual(metadata["sdl_version"], [2, 32, 4])


if __name__ == "__main__":
    unittest.main()
