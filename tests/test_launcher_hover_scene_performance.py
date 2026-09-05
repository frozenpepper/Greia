from __future__ import annotations

import os
import tempfile
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

from greia_launcher.presentation import idle_sleep_seconds
from greia_platform.pygame_visual_assets import PygameVisualSurfaceCache

_monotonic = __import__("time").monotonic


def _surface_pixels(surface: pygame.Surface) -> bytes:
    return pygame.image.tostring(surface.convert(24), "RGB")


class IdleSleepContractTests(unittest.TestCase):
    def test_active_window_polls_quickly(self) -> None:
        self.assertEqual(idle_sleep_seconds(0.0), 0.008)
        self.assertEqual(idle_sleep_seconds(0.999), 0.008)

    def test_quiet_period_relaxes_wake_cadence(self) -> None:
        self.assertEqual(idle_sleep_seconds(1.0), 0.04)
        self.assertEqual(idle_sleep_seconds(60.0), 0.04)


class VisualSurfaceDisplayConverterTests(unittest.TestCase):
    def test_converter_applies_once_and_cache_returns_same_surface(self) -> None:
        catalogue = MagicMock()
        asset = MagicMock()
        asset.path_for.return_value = Path("stub.png")
        catalogue.get_visual.return_value = asset
        source = pygame.Surface((4, 4))
        conversions: list[object] = []

        def converter(surface: object) -> object:
            conversions.append(surface)
            return surface

        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: source,
            image_scaler=lambda surface, size: surface,
            display_converter=converter,
        )
        first = cache.get("ui.panel.base", size=(4, 4))
        second = cache.get("ui.panel.base", size=(4, 4))
        self.assertIs(first, second)
        self.assertEqual(len(conversions), 1)

    def test_converter_failure_keeps_surface_usable(self) -> None:
        catalogue = MagicMock()
        asset = MagicMock()
        asset.path_for.return_value = Path("stub.png")
        catalogue.get_visual.return_value = asset
        source = pygame.Surface((4, 4))

        def broken_converter(surface: object) -> object:
            raise RuntimeError("no display")

        cache = PygameVisualSurfaceCache(
            catalogue,
            image_loader=lambda path: source,
            image_scaler=lambda surface, size: surface,
            display_converter=broken_converter,
        )
        surface = cache.get("ui.panel.base", size=(4, 4))
        self.assertEqual(surface.get_size(), (4, 4))


class HoverRepairSceneEquivalenceTests(unittest.TestCase):
    """Hover transitions must produce pixels identical to a full rebuild."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def _prepared_shell(self):
        from greia_launcher.child_shell import GreiaChildShell

        shell = GreiaChildShell(windowed=True)
        shell.profiles = shell.profile_store.ensure_initialized()
        shell._activate_profile(shell.profiles[0], pygame)
        assert shell._mode == "activities"
        shell._synthetic_pointer_active = True
        category_id = next(
            (
                collection.collection_id
                for collection in shell._catalogue.collections
                if collection.collection_id != "all" and collection.items
            ),
            None,
        )
        if category_id is None:
            self.skipTest("no populated collection available in source tree")
        shell._set_category(category_id)
        screen = pygame.display.set_mode((1024, 600))
        return shell, screen

    def _card_targets(self, shell):
        return [
            target
            for target in shell._cached_activities_targets
            if target.action == "presented_activity"
        ]

    def _hover(self, shell, screen, rect_center):
        shell._pointer_position = rect_center
        shell._draw(screen, pygame)

    def _rebuild_and_draw(self, shell, screen):
        shell._cached_activities_key = None
        shell._draw(screen, pygame)

    def test_hover_transition_matches_full_rebuild(self) -> None:
        shell, screen = self._prepared_shell()

        # Baseline scene with no hover; also populates cached hit targets.
        shell._pointer_position = (2, 2)
        self._rebuild_and_draw(shell, screen)
        baseline = _surface_pixels(shell._cached_activities_surface)

        cards = self._card_targets(shell)
        if len(cards) < 2:
            self.skipTest("need at least two activity cards")

        for card in cards[:2]:
            self._hover(shell, screen, card.rect.center)
            repaired = _surface_pixels(shell._cached_activities_surface)
            self._rebuild_and_draw(shell, screen)
            rebuilt = _surface_pixels(shell._cached_activities_surface)
            self.assertEqual(
                repaired,
                rebuilt,
                "incremental hover repair diverged from full rebuild",
            )

        # Returning to no-hover must also match the untouched baseline.
        self._hover(shell, screen, (2, 2))
        repaired = _surface_pixels(shell._cached_activities_surface)
        self.assertEqual(repaired, baseline)

    def test_launch_tick_repair_matches_full_rebuild(self) -> None:
        import time as _time

        shell, screen = self._prepared_shell()

        self._rebuild_and_draw(shell, screen)
        cards = self._card_targets(shell)
        if not cards:
            self.skipTest("no activity cards available")

        manifest_index = int(cards[0].value)
        activities = shell._presented_activities
        shell._pointer_position = (2, 2)
        shell._launching_activity_id = activities[manifest_index].activity_id

        # Freeze the animation clock so the incremental repair and the forced
        # full rebuild sample exactly the same launch-motion phase. The stdlib
        # monotonic is patched because several presentation modules import the
        # shared time module directly.
        t0 = _monotonic()
        frozen = t0
        real_monotonic = _time.monotonic
        try:
            _time.monotonic = lambda: frozen
            # First draw rebuilds with the new launching state and refreshes
            # signatures; advance the sampled tick, then exercise the repair.
            shell._launch_animation_started = t0 - 0.08
            shell._draw(screen, pygame)
            shell._launch_animation_started = t0 - 0.21
            shell._draw(screen, pygame)
            repaired = _surface_pixels(shell._cached_activities_surface)

            self._rebuild_and_draw(shell, screen)
            rebuilt = _surface_pixels(shell._cached_activities_surface)
        finally:
            _time.monotonic = real_monotonic
            shell._launching_activity_id = None
        self.assertEqual(repaired, rebuilt)

    def test_chrome_controls_hover_repair_matches_full_rebuild(self) -> None:
        shell, screen = self._prepared_shell()
        shell._pointer_position = (2, 2)
        self._rebuild_and_draw(shell, screen)
        baseline = _surface_pixels(shell._cached_activities_surface)

        chrome_targets = [
            target
            for target in shell._cached_activities_targets
            if target.action in (
                "presented_activity_page_prev",
                "presented_activity_page_next",
                "activity_category",
                "activity_category_back",
            )
        ]
        if not chrome_targets:
            self.skipTest("no chrome targets available")

        # Spy on full scene rebuilds
        render_calls = 0
        real_render = shell._render_activities_content

        def spy_render(*args, **kwargs):
            nonlocal render_calls
            render_calls += 1
            return real_render(*args, **kwargs)

        shell._render_activities_content = spy_render

        for target in chrome_targets:
            render_calls = 0
            self._hover(shell, screen, target.rect.center)
            self.assertEqual(
                render_calls,
                0,
                f"hover on {target.action} triggered full scene rebuild",
            )
            repaired = _surface_pixels(shell._cached_activities_surface)

            # Rebuild forces full render
            self._rebuild_and_draw(shell, screen)
            rebuilt = _surface_pixels(shell._cached_activities_surface)
            self.assertEqual(
                repaired,
                rebuilt,
                f"hover repair for {target.action} diverged from full rebuild",
            )

        # Returning to no-hover
        render_calls = 0
        self._hover(shell, screen, (2, 2))
        self.assertEqual(render_calls, 0, "unhover triggered full scene rebuild")
        repaired = _surface_pixels(shell._cached_activities_surface)
        self.assertEqual(repaired, baseline)


if __name__ == "__main__":
    unittest.main()
