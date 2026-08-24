"""Unit and regression tests for Nascondino nel Bosco (Woodland Hide and Seek)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tomllib
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pygame

from activities.nascondino_bosco.woodland_app import WoodlandApp
from activities.nascondino_bosco.woodland_art import WoodlandArtLibrary
from activities.nascondino_bosco.woodland_audio import WoodlandAudio
from activities.nascondino_bosco.woodland_model import (
    ALL_ANIMALS,
    ANIMALS_BY_ID,
    GROUNDED_SPOTS,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    WoodlandGameState,
)
from activities.nascondino_bosco.woodland_renderer import (
    WoodlandRenderer,
    compute_hud_layout,
)
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_completion import CompletionContent
from greia_platform.typography import GreiaTypography
from greia_platform.ui_preferences import InterfaceSize

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "nascondino_bosco"


class NascondinoNelBoscoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)

        self.assertEqual(data["activity"]["id"], "org.greia.nascondino-bosco")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertEqual(data["activity"]["title_key"], "activity.nascondino_bosco.title")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])
        self.assertEqual(data["runtime"]["type"], "python")
        self.assertEqual(data["runtime"]["entrypoint"], "main.py")
        self.assertEqual(data["input"]["profile"], "hybrid")

        events = {e["id"]: e["kind"] for e in data["education"]["events"]}
        self.assertEqual(events.get("woodland.animal_found"), "milestone")
        self.assertEqual(events.get("woodland.round_completed"), "completion")

    def test_locales_contain_all_required_keys(self) -> None:
        support = ActivityLocaleSupport.localized(
            ("it", "en"),
            default_ui_locale="it",
        )
        self.assertEqual(len(support.ui_locales), 2)

        for lang in ("it", "en"):
            ctx = resolve_activity_locale(lang, support)
            self.assertIsNotNone(ctx)
            assert ctx is not None
            res = LocalizedResources(ACTIVITY_DIR, ctx)
            self.assertTrue(res.text("activity.title"))
            self.assertTrue(res.text("activity.nascondino_bosco.title"))
            self.assertTrue(res.text("victory.title"))
            self.assertTrue(res.text("btn.play_again"))
            for animal in ALL_ANIMALS:
                self.assertTrue(
                    res.text(animal.name_key),
                    f"Missing text for {animal.name_key} in {lang}",
                )

    def test_grounded_spots_are_physically_grounded(self) -> None:
        self.assertEqual(len(GROUNDED_SPOTS), 5)
        for spot in GROUNDED_SPOTS:
            # Check spot bounds within 1024x600 reference
            self.assertGreaterEqual(spot.cx - spot.width // 2, 0)
            self.assertLessEqual(spot.cx + spot.width // 2, REFERENCE_WIDTH)
            # All ground spots must be anchored below y=300 (not floating in the sky)
            self.assertGreaterEqual(spot.cy, 300)
            self.assertLessEqual(spot.cy + spot.height // 2, REFERENCE_HEIGHT)

    def test_game_state_round_and_spot_inspection(self) -> None:
        state = WoodlandGameState(total_to_find=3)
        state.start_round()

        self.assertEqual(len(state.hiding_map), 5)
        self.assertIn(state.target_animal_id, state.hiding_map.values())
        self.assertEqual(state.found_count, 0)
        self.assertFalse(state.is_victory)

        # Identify target spot and non-target spot
        target_spot_id = next(
            spot_id
            for spot_id, animal_id in state.hiding_map.items()
            if animal_id == state.target_animal_id
        )
        non_target_spot_id = next(
            spot_id
            for spot_id, animal_id in state.hiding_map.items()
            if animal_id != state.target_animal_id
        )

        # Inspect non-target
        is_target, animal_id = state.inspect_spot(non_target_spot_id)
        self.assertFalse(is_target)
        self.assertIsNotNone(animal_id)
        self.assertEqual(state.found_count, 0)
        self.assertIsNotNone(state.leaping_animal)

        # Inspect target 1
        is_target, animal_id = state.inspect_spot(target_spot_id)
        self.assertTrue(is_target)
        self.assertEqual(state.found_count, 1)
        self.assertEqual(state.total_stars, 1)

        # Advance until victory
        for _ in range(2):
            next_target_spot = next(
                spot_id
                for spot_id, a_id in state.hiding_map.items()
                if a_id == state.target_animal_id
            )
            state.inspect_spot(next_target_spot)

        self.assertEqual(state.found_count, 3)
        self.assertTrue(state.is_victory)

    def test_art_library_portraits_and_background(self) -> None:
        art = WoodlandArtLibrary()
        bg = art.get_background()
        self.assertEqual(bg.get_size(), (REFERENCE_WIDTH, REFERENCE_HEIGHT))

        for animal in ALL_ANIMALS:
            portrait = art.get_animal_portrait(animal.id, 64)
            self.assertEqual(portrait.get_size(), (64, 64))

        # Test peeking clue drawing across all spots
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        for spot in GROUNDED_SPOTS:
            for animal in ALL_ANIMALS:
                art.draw_peeking_clue(surf, spot, animal.id, t_now=1.0)

    def test_audio_initialization(self) -> None:
        audio = WoodlandAudio()
        audio.play("pop")
        audio.play("rustle")
        audio.play("win")

    def test_renderer_active_game(self) -> None:
        support = ActivityLocaleSupport.localized(
            ("it", "en"),
            default_ui_locale="it",
        )
        ctx = resolve_activity_locale("it", support)
        assert ctx is not None
        resources = LocalizedResources(ACTIVITY_DIR, ctx)

        art = WoodlandArtLibrary()
        renderer = WoodlandRenderer(art, GreiaTypography(), resources)
        state = WoodlandGameState()
        state.start_round()

        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        renderer.draw_active_game(surf, state, InterfaceSize.NORMAL, t_now=0.5)

    def test_compute_hud_layout(self) -> None:
        for size in (InterfaceSize.NORMAL, InterfaceSize.LARGE, InterfaceSize.COMPACT):
            layout = compute_hud_layout(size)
            self.assertIn("target_card_rect", layout)
            self.assertIn("star_pill_rect", layout)

    def test_woodland_app_victory_and_click_handling(self) -> None:
        support = ActivityLocaleSupport.localized(
            ("it", "en"),
            default_ui_locale="it",
        )
        ctx = resolve_activity_locale("it", support)
        assert ctx is not None
        resources = LocalizedResources(ACTIVITY_DIR, ctx)

        art = WoodlandArtLibrary()
        renderer = WoodlandRenderer(art, GreiaTypography(), resources)
        audio = WoodlandAudio()
        screen = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        app = WoodlandApp(screen, resources, GreiaTypography(), audio)
        app.state.total_to_find = 2
        app.state.start_round()
        state = app.state

        # Non-spot click
        self.assertFalse(app._handle_click((50, 50)))

        # Protected UI click
        self.assertFalse(app._handle_click((36, 36)))

        # Find targets to reach victory
        for _ in range(2):
            target_spot = next(
                spot
                for spot in GROUNDED_SPOTS
                if state.hiding_map.get(spot.spot_id) == state.target_animal_id
            )
            self.assertTrue(app._handle_click((target_spot.cx, target_spot.cy)))

        self.assertTrue(state.is_victory)
        content = CompletionContent(
            title=resources.text("victory.title"),
            primary_label=resources.text("btn.play_again"),
            body_lines=(resources.text("victory.subtitle"),),
            achievement_count=state.found_count,
        )
        app.completion.prepare(content)
        self.assertTrue(app.completion.is_prepared)

        # Click Play Again button on completion screen
        btn_center = app.completion.primary_rect.center
        self.assertTrue(app._handle_click(btn_center))
        self.assertFalse(state.is_victory)

