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
        return root

    @staticmethod
    def _libraries(name: str) -> str | None:
        if name in {"drm", "gbm", "EGL", "input"}:
            return f"lib{name}.so"
        return None

    def test_probe_reports_prerequisites_without_claiming_active_kms_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._fixture_root(temporary)
            probe = DirectGraphicsProbe(
                ProbeInputs(
                    root=root,
                    environment={
                        "DISPLAY": ":0-secret-display-value",
                        "SDL_VIDEODRIVER": "kmsdrm",
                        "XDG_SEAT": "seat0",
                        "XDG_VTNR": "1",
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
        self.assertTrue(snapshot["assessment"]["kmsdrm_prerequisites_visible"])
        self.assertTrue(snapshot["assessment"]["active_kmsdrm_test_required"])
        self.assertTrue(snapshot["session"]["display_present"])
        self.assertNotIn(":0-secret-display-value", repr(snapshot))

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
        self.assertFalse(snapshot["pygame"]["available"])
        self.assertFalse(snapshot["assessment"]["kmsdrm_prerequisites_visible"])
        self.assertTrue(snapshot["assessment"]["active_kmsdrm_test_required"])

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
