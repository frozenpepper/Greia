from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.composition import provisional_installed_system_chrome
from greia_launcher.system_chrome_legacy_x import LegacyXSystemChromeBackend
from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "greia_launcher" / "system_chrome_legacy_x.py"


class _Bridge:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.points: list[tuple[int, int]] = []
        self.layout: ActivitySystemChromeLayout | None = None

    def prepare(self, *, back_available: bool) -> ActivitySystemChromeLayout:
        self.calls.append(("prepare", back_available))
        self.layout = ActivitySystemChromeLayout.for_surface(
            1024,
            600,
            back_available=back_available,
        )
        return self.layout

    def show(self) -> None:
        self.calls.append(("show",))

    def poll_pointer_release(self) -> tuple[int, int] | None:
        self.calls.append(("poll",))
        return self.points.pop(0) if self.points else None

    def hide(self) -> None:
        self.calls.append(("hide",))


class LegacyXSystemChromeBackendTests(unittest.TestCase):
    def test_installed_composition_selects_legacy_x_chrome_only_below_coordinator(self) -> None:
        coordinator = provisional_installed_system_chrome()
        self.assertEqual(coordinator.backend_id, "legacy-x11-system-chrome")

    def test_home_is_mapped_by_platform_layout(self) -> None:
        bridge = _Bridge()
        backend = LegacyXSystemChromeBackend(bridge=bridge)
        backend.prepare("session-a", back_available=False)
        backend.show("session-a")
        assert bridge.layout is not None
        home = bridge.layout.home_hitbox
        bridge.points.append((home.x + home.width // 2, home.y + home.height // 2))

        self.assertIs(
            backend.poll_action("session-a"),
            SystemNavigationAction.HOME,
        )
        backend.hide("session-a")
        self.assertEqual(
            bridge.calls,
            [("prepare", False), ("show",), ("poll",), ("hide",)],
        )

    def test_back_is_emitted_only_when_platform_context_enables_it(self) -> None:
        bridge = _Bridge()
        backend = LegacyXSystemChromeBackend(bridge=bridge)
        backend.prepare("session-a", back_available=True)
        backend.show("session-a")
        assert bridge.layout is not None
        back = bridge.layout.back_hitbox
        bridge.points.append((back.x + back.width // 2, back.y + back.height // 2))
        self.assertIs(
            backend.poll_action("session-a"),
            SystemNavigationAction.BACK,
        )
        backend.hide("session-a")

        bridge = _Bridge()
        backend = LegacyXSystemChromeBackend(bridge=bridge)
        backend.prepare("session-b", back_available=False)
        backend.show("session-b")
        assert bridge.layout is not None
        back = bridge.layout.back_hitbox
        bridge.points.append((back.x + back.width // 2, back.y + back.height // 2))
        self.assertIsNone(backend.poll_action("session-b"))
        backend.hide("session-b")

    def test_foreign_session_cannot_show_poll_or_hide_chrome(self) -> None:
        backend = LegacyXSystemChromeBackend(bridge=_Bridge())
        backend.prepare("session-a", back_available=False)
        for operation in (
            lambda: backend.show("session-b"),
            lambda: backend.poll_action("session-b"),
            lambda: backend.hide("session-b"),
        ):
            with self.assertRaisesRegex(RuntimeError, "session mismatch"):
                operation()
        backend.hide("session-a")

    def test_backend_cannot_prepare_two_sessions_at_once(self) -> None:
        backend = LegacyXSystemChromeBackend(bridge=_Bridge())
        backend.prepare("session-a", back_available=False)
        with self.assertRaisesRegex(RuntimeError, "already owns"):
            backend.prepare("session-b", back_available=False)
        backend.hide("session-a")

    def test_launch_picture_matches_the_native_home_geometry(self) -> None:
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame

        surface = pygame.Surface((1024, 600))
        surface.fill((0, 0, 0))
        box = LegacyXSystemChromeBackend(bridge=_Bridge()).paint_launch_picture(surface, pygame)
        self.assertEqual((box.x, box.y, box.width, box.height), (8, 8, 60, 60))
        outline = (0x4E, 0x38, 0x28)
        # Roof and cottage body in the outline colour, attic window cream,
        # capsule background, and nothing painted outside the capsule.
        self.assertEqual(tuple(surface.get_at((30, 34)))[:3], outline)
        self.assertEqual(tuple(surface.get_at((27, 40)))[:3], outline)
        self.assertEqual(tuple(surface.get_at((38, 33)))[:3], (0xFF, 0xF8, 0xEB))
        self.assertEqual(tuple(surface.get_at((38, 72)))[:3], (0xFF, 0xF8, 0xEB))
        self.assertEqual(tuple(surface.get_at((100, 38)))[:3], (0, 0, 0))

    def test_source_is_not_a_second_pygame_or_process_render_path(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import pygame", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("multiprocessing", source)
        self.assertNotIn("pygame.Surface", source)
        self.assertIn("XCreateSimpleWindow", source)
        self.assertIn("protected_region", source)


if __name__ == "__main__":
    unittest.main()
