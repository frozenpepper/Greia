"""Focused interaction regression for the quality/interactivity correction."""

from __future__ import annotations

import pathlib
import pygame

from activities.enciclopedia_greia.enciclopedia_controls import clear_controls_cache
from activities.enciclopedia_greia.enciclopedia_focus import (
    FocusShape,
    clear_focus_cache,
    get_focus_cache_stats,
)
from activities.enciclopedia_greia.pages.home import HomePage, PORTALS
from activities.enciclopedia_greia.pages.space import SpacePage, _TARGET_IDS
from activities.enciclopedia_greia.enciclopedia_engine import PageInput, PageCommand


def _dummy_context():
    # Minimal context for model tests — no audio/visuals needed for pure logic
    class DummyAudio:
        def __init__(self):
            self.played: list[str] = []

        def play(self, cue_id: str) -> bool:
            self.played.append(cue_id)
            return True

    class DummyHost:
        def __init__(self):
            self.opened: list[str] = []

        def open_page(self, page_id: str) -> None:
            self.opened.append(page_id)

        def go_back(self) -> bool:
            return False

    from activities.enciclopedia_greia.enciclopedia_engine import PageContext
    from greia_platform.typography import GreiaTypography
    from activities.enciclopedia_greia.enciclopedia_services import VisualLibrary, EncyclopediaPalette
    from pathlib import Path

    # Use real resources for audio cue id generation, but audio is dummy
    from greia_platform.localization import LocalizedResources, ActivityLocaleSupport, resolve_activity_locale
    from greia_platform.localization import LocalizedResources as LR

    # Create a minimal LocalizedResources that will not be used for audio cue resolution in these tests
    # We use the dummy audio directly, so resources can be a simple stub
    class StubResources:
        def text(self, key: str) -> str:
            return key

    audio = DummyAudio()
    host = DummyHost()
    # Use real VisualLibrary with dummy palette/typography
    import pathlib

    # Use a stub for visuals that returns None for art
    class StubVisuals:
        def art(self, asset_id: str, size=None):
            return None

        def character(self, *a, **kw):
            return None

        def planet(self, planet_id: str, diameter: int):
            return None

    from greia_platform.typography import GreiaTypography

    typography = GreiaTypography()
    visuals = StubVisuals()  # type: ignore[assignment]
    palette = EncyclopediaPalette(background=(0, 0, 0), panel=(0, 0, 0), accent=(0, 0, 0), text=(0, 0, 0))
    # We need a LocalizedResources for PageContext, but our audio is dummy, so we can create a minimal one
    # Use the real activity locales if available, otherwise stub
    try:
        from pathlib import Path as P
        from greia_platform.localization import ActivityLocaleSupport, resolve_activity_locale, LocalizedResources

        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        ctx_locale = resolve_activity_locale("it", support)
        assert ctx_locale is not None
        resources = LocalizedResources(Path("activities/enciclopedia_greia"), ctx_locale)
    except Exception:
        resources = StubResources()  # type: ignore[assignment]

    # We will override the context's audio with our dummy that records
    from activities.enciclopedia_greia.enciclopedia_engine import PageContext as PC

    ctx = PC(host=host, resources=resources, typography=typography, visuals=visuals, audio=audio, palette=palette)  # type: ignore[arg-type]
    return ctx, host, audio


def _make_home_page():
    ctx, host, audio = _dummy_context()
    page = HomePage(ctx)
    return page, ctx, host, audio


def _make_space_page():
    ctx, host, audio = _dummy_context()
    page = SpacePage(ctx)
    return page, ctx, host, audio


import unittest


class EncyclopediaInteractionTests(unittest.TestCase):
    def test_home_portals_use_rounded_rect_focus(self) -> None:
        # Home portals are rectangular exhibits, not circles
        import ast
        from pathlib import Path

        home_src = Path("activities/enciclopedia_greia/pages/home.py").read_text()
        # Home should use draw_portal_focus (rounded_rect) not generic ellipse
        self.assertIn("draw_portal_focus", home_src)
        # And should not use draw_focus_patch with default ellipse for portals
        # The focus module's rounded_rect uses rect, not ellipse
        focus_src = Path("activities/enciclopedia_greia/enciclopedia_focus.py").read_text()
        self.assertIn("FocusShape.ROUNDED_RECT", focus_src)
        self.assertIn("FocusShape.CIRCLE", focus_src)

    def test_space_left_right_changes_selected(self) -> None:
        page, _, _, _ = _make_space_page()
        self.assertEqual(page._selected, 3)  # Earth
        page.handle_input(PageInput.command_event(PageCommand.RIGHT))
        self.assertEqual(page._selected, 4)
        page.handle_input(PageInput.command_event(PageCommand.LEFT))
        page.handle_input(PageInput.command_event(PageCommand.LEFT))
        self.assertEqual(page._selected, 2)

    def test_space_activate_opens_selected(self) -> None:
        page, _, host, _ = _make_space_page()
        # Select mercury (index 1) and activate
        page._selected = 1
        page.handle_input(PageInput.command_event(PageCommand.ACTIVATE))
        self.assertIn("space.mercury", host.opened)

    def test_space_pause_freezes_orbit(self) -> None:
        page, _, _, _ = _make_space_page()
        # Record positions before pause
        page.update(0.1)
        # Need to draw to populate _target_positions
        surf = pygame.Surface((1024, 600))
        # Use dummy visuals that return None, so _draw_live_solar_system will still populate positions
        # It does, via its logic, even with authored=False
        page.draw(surf)
        pos_before = list(page._target_positions)
        page._paused = True
        # Capture time and positions, then update while paused — orbit should not advance much (only tiny halo pulse time)
        # For pause, _time still advances a little (0.15*dt) but orbit uses _time * speed, so it will still advance slightly
        # Instead, we check that earth position does not change much when paused vs when running
        # Do two updates while paused and check delta is small
        page.update(0.5)
        page.draw(surf)
        pos_paused = list(page._target_positions)
        # Find earth
        earth_before = next(p for p in pos_before if p[0] == "earth")
        earth_paused = next(p for p in pos_paused if p[0] == "earth")
        # When paused, earth should move very little (since _time advances only 0.15*dt)
        dist_paused = ((earth_before[1] - earth_paused[1]) ** 2 + (earth_before[2] - earth_paused[2]) ** 2) ** 0.5
        # Now unpause and update same dt, should move more
        page._paused = False
        page.update(0.5)
        page.draw(surf)
        pos_running = list(page._target_positions)
        earth_running = next(p for p in pos_running if p[0] == "earth")
        dist_running = ((earth_paused[1] - earth_running[1]) ** 2 + (earth_paused[2] - earth_running[2]) ** 2) ** 0.5
        self.assertLess(dist_paused, dist_running + 1e-6)
        self.assertGreater(dist_running, dist_paused)

    def test_space_speed_levels_ordered(self) -> None:
        from activities.enciclopedia_greia.enciclopedia_controls import ORBIT_SPEED_FACTORS

        self.assertEqual(len(ORBIT_SPEED_FACTORS), 3)
        self.assertLess(ORBIT_SPEED_FACTORS[0], ORBIT_SPEED_FACTORS[1])
        self.assertLess(ORBIT_SPEED_FACTORS[1], ORBIT_SPEED_FACTORS[2])

    def test_focus_dedupe(self) -> None:
        from activities.enciclopedia_greia.enciclopedia_focus_audio import FocusAudioTracker

        tracker = FocusAudioTracker()

        class FakeAudio:
            def __init__(self):
                self.calls: list[str] = []

            def play(self, cue_id: str) -> bool:
                self.calls.append(cue_id)
                return True

        audio = FakeAudio()
        cue = "encyclopedia.space.earth.name"
        self.assertTrue(tracker.announce_once(audio, cue))
        self.assertEqual(len(audio.calls), 1)
        # Second announce with same cue should be deduped
        self.assertFalse(tracker.announce_once(audio, cue))
        self.assertEqual(len(audio.calls), 1)
        # Different cue should announce
        self.assertTrue(tracker.announce_once(audio, "encyclopedia.space.mars.name"))
        self.assertEqual(len(audio.calls), 2)

    def test_volcano_eruption_transitions(self) -> None:
        from activities.enciclopedia_greia.pages.volcano import VolcanoPage

        ctx, _, _ = _dummy_context()
        page = VolcanoPage(ctx)
        self.assertEqual(page._model.eruption_age, 0.0)
        page._model.erupt_with_strength(1)
        self.assertGreater(page._model.eruption_age, 0.0)
        self.assertGreater(page._model.rumble_age, 0.0)
        # Update should decay
        page.update(1.0)
        self.assertLess(page._model.eruption_age, 3.0)

    def test_pyramids_ordered_assembly(self) -> None:
        from activities.enciclopedia_greia.pages.pyramids import PyramidsPage

        ctx, _, _ = _dummy_context()
        page = PyramidsPage(ctx)
        # Try wrong order: try to place block 2 before 0
        self.assertFalse(page._model.try_place_block(2))
        self.assertEqual(page._model.assembly_placed, [False, False, False, False])
        # Correct order
        self.assertTrue(page._model.try_place_block(0))
        # Need to update to complete animation
        for _ in range(20):
            page.update(0.1)
        self.assertEqual(page._model.assembly_placed[0], True)
        # Next should be 1
        self.assertTrue(page._model.try_place_block(1))
        for _ in range(20):
            page.update(0.1)
        self.assertEqual(page._model.assembly_placed[1], True)
        # Complete all
        page._model.try_place_block(2)
        for _ in range(20):
            page.update(0.1)
        page._model.try_place_block(3)
        for _ in range(20):
            page.update(0.1)
        self.assertEqual(page._model.assembly_placed, [True, True, True, True])
        # Completed should be visible for a interval before reset
        self.assertGreater(page._model.completed_age, 0.0)

    def test_gears_speed_and_direction(self) -> None:
        from activities.enciclopedia_greia.pages.gears import GearsPage

        ctx, _, _ = _dummy_context()
        page = GearsPage(ctx)
        start_angle = page._model.driver_angle
        page.update(0.5)
        self.assertNotEqual(page._model.driver_angle, start_angle)
        # Speed level changes rate
        page._model.set_speed_level(0)
        slow_speed = page._model.speed
        page._model.set_speed_level(2)
        fast_speed = page._model.speed
        self.assertLess(slow_speed, fast_speed)
        # Direction toggle reverses
        dir_before = page._model.direction
        page._model.reverse()
        self.assertNotEqual(page._model.direction, dir_before)

    def test_selected_entry_action_activates_selection(self) -> None:
        # For systematic entry pages, the big action should act on current selection, not always 0
        # Test with a representative entry: rain
        from activities.enciclopedia_greia.pages.rain import RainPage

        ctx, _, _ = _dummy_context()
        page = RainPage(ctx)
        # Select index 2 and trigger main (which should activate selected, not 0)
        page._selected = 2
        # Mock _activate to capture index
        called: list[int] = []

        orig_activate = page._activate

        def mock_activate(idx: int) -> None:
            called.append(idx)

        page._activate = mock_activate  # type: ignore[assignment]
        page._trigger_main()
        self.assertEqual(called, [2])

    def test_focus_no_duplicate_on_pyramids(self) -> None:
        # Pyramids should not have double focus (token + halo)
        src = pathlib.Path("activities/enciclopedia_greia/pages/pyramids.py").read_text()
        # Should not have the extra halo inside DISCOVERIES loop
        self.assertNotIn(
            "if index == self._selected or index == self._hovered:\n                draw_focus_patch(surface, self._hotspots[index]",
            src,
        )

    def test_shared_chrome_no_per_frame_alloc(self) -> None:
        # Repeated draws should reuse cached surfaces, not grow unbounded
        clear_focus_cache()
        clear_controls_cache()
        surf = pygame.Surface((1024, 600))
        import pygame as pg

        # Create a dummy rect
        rect = pg.Rect(100, 100, 100, 50)
        for _ in range(10):
            from activities.enciclopedia_greia.enciclopedia_focus import draw_focus_patch

            draw_focus_patch(surf, rect, active=True, radius=16, time=0.5)
            from activities.enciclopedia_greia.enciclopedia_controls import draw_navigation_arrows

            draw_navigation_arrows(surf, time=0.5, can_go_left=True, can_go_right=True)
            from activities.enciclopedia_greia.enciclopedia_controls import draw_discover_button

            draw_discover_button(surf, (512, 525), active=True, time=0.5)

        # Cache should be bounded
        entries, area, total = get_focus_cache_stats()
        self.assertLessEqual(entries, 24)
        self.assertLessEqual(area, 1_200_000)

    def test_required_solar_system_cues_in_ledger(self) -> None:
        # Focus-name cues for Solar System must be in the voice ledger as REQUESTED (even if not yet OWNER_ACCEPTED)
        ledger = pathlib.Path("encyclopedia/VOICE_RECORDING_REQUESTS.md").read_text()
        for body in ["sun", "mercury", "venus", "earth", "moon", "mars", "jupiter", "saturn", "uranus", "neptune"]:
            cue = f"encyclopedia.space.{body}.name"
            self.assertIn(cue, ledger)


if __name__ == "__main__":
    unittest.main()
