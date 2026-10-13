"""Comprehensive test suite for Mondo Contrari (org.greia.mondo-contrari)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
import json
from unittest.mock import Mock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from activities.mondo_contrari.contrari_app import ContrariActivity
from activities.mondo_contrari.contrari_audio import ContrariAudio, ContrariSpeechQueue
from activities.mondo_contrari.contrari_model import (
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    ContrariModel,
    OppositeCategory,
)
from activities.mondo_contrari.contrari_renderer import (
    CATEGORY_OPPOSITE_KEYS,
    ContrariRenderer,
)
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "activities" / "mondo_contrari"


class TestContrariDomain(unittest.TestCase):
    """Test domain model invariants, physical state toggling, and categories."""

    def setUp(self) -> None:
        self.model = ContrariModel()

    def test_initial_state(self) -> None:
        self.assertEqual(self.model.category, OppositeCategory.UP_DOWN)
        self.assertFalse(self.model.is_up)
        self.assertFalse(self.model.completed_all)

    def test_category_transitions_and_completion(self) -> None:
        for cat in OppositeCategory:
            self.model.set_category(cat)
            self.assertEqual(self.model.category, cat)
            self.assertNotIn(cat, self.model.discovered_categories)
            first, complete = self.model.record_exploration()
            self.assertTrue(first)
            self.assertEqual(complete, cat == OppositeCategory.FAST_SLOW)
            self.assertFalse(self.model.record_exploration()[0])
        self.assertTrue(self.model.completed_all)
        self.assertFalse(self.model.record_exploration()[1])

    def test_up_down_toggle(self) -> None:
        is_up = self.model.toggle_up_down()
        self.assertTrue(is_up)
        self.assertEqual(self.model.target_balloon_y, 130.0)
        self.model.update(1.0)
        self.assertLess(self.model.balloon_y, 400.0)

        is_up = self.model.toggle_up_down()
        self.assertFalse(is_up)
        self.assertEqual(self.model.target_balloon_y, 410.0)

    def test_big_small_toggle(self) -> None:
        is_big = self.model.toggle_big_small()
        self.assertTrue(is_big)
        self.assertEqual(self.model.target_bubble_scale, 1.25)
        self.model.update(1.0)
        self.assertGreater(self.model.bubble_scale, 0.5)

    def test_in_out_toggle(self) -> None:
        is_out = self.model.toggle_in_out()
        self.assertTrue(is_out)
        self.assertFalse(self.model.is_in)
        self.assertEqual(self.model.target_box_y, 230.0)

    def test_open_closed_toggle(self) -> None:
        is_open = self.model.toggle_open_closed()
        self.assertTrue(is_open)
        self.assertEqual(self.model.target_shutter, 1.0)
        self.model.update(1.0)
        self.assertGreater(self.model.shutter_open_ratio, 0.5)

    def test_fast_slow_toggle(self) -> None:
        is_fast = self.model.toggle_fast_slow()
        self.assertTrue(is_fast)
        self.model.set_category(OppositeCategory.FAST_SLOW)
        prev_x = self.model.runner_x
        self.model.update(0.2)
        self.assertGreater(self.model.runner_x, prev_x)


class TestContrariAudioAndSpeech(unittest.TestCase):
    """Test audio queue and speech dispatch."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.mixer.init()

    def test_audio_and_queue(self) -> None:
        audio = ContrariAudio(PACKAGE_ROOT, locale="it")
        queue = ContrariSpeechQueue(audio)

        queue.enqueue("welcome", delay_after=0.1)
        queue.enqueue("up", delay_after=0.1)
        self.assertEqual(len(queue._queue), 2)

        queue.clear()
        self.assertEqual(len(queue._queue), 0)


class TestContrariRendererAndApp(unittest.TestCase):
    """Test scene rendering across all 5 opposites and input handling."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def setUp(self) -> None:
        self.screen = pygame.display.get_surface()
        self.model = ContrariModel()
        self.renderer = ContrariRenderer()
        self.audio = ContrariAudio(PACKAGE_ROOT, locale="it")
        self.app = ContrariActivity(self.screen, self.renderer, self.audio, self.model)

    def test_events_follow_interactions_once_not_toolbar_visits(self) -> None:
        events = Mock()
        app = ContrariActivity(self.screen, self.renderer, self.audio, self.model, events)
        for cat, rect in self.renderer.category_buttons.items():
            app._handle_pointer_down(rect.center)
            self.assertEqual(self.model.category, cat)
        events.opposite_explored.assert_not_called()
        events.all_opposites_completed.assert_not_called()
        for cat, rect in self.renderer.category_buttons.items():
            app._handle_pointer_down(rect.center)
            app._handle_pointer_down(self.renderer.play_surface_rect.center)
        self.assertEqual(events.opposite_explored.call_count, 5)
        events.all_opposites_completed.assert_called_once()
        app._handle_pointer_down(self.renderer.play_surface_rect.center)
        self.assertEqual(events.opposite_explored.call_count, 5)
        events.all_opposites_completed.assert_called_once()

    def test_protected_pointer_cannot_select_or_exit(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        app = ContrariActivity(self.screen, self.renderer, self.audio, self.model)
        vp = activity_viewport_for_surface(self.screen)
        rect = vp.protected_regions[0]
        initial = self.model.category
        app._handle_pointer_down((int(rect.x) + 1, int(rect.y) + 1))
        self.assertEqual(self.model.category, initial)
        self.assertTrue(app.running)

    def test_event_adapter_uses_platform_event_contract(self) -> None:
        from activities.mondo_contrari.contrari_app import GreiaContrariEvents
        with patch("activities.mondo_contrari.contrari_app.emit_activity_event") as emit:
            adapter = GreiaContrariEvents()
            adapter.opposite_explored(OppositeCategory.UP_DOWN)
            adapter.all_opposites_completed()
        self.assertEqual(emit.call_count, 2)
        self.assertEqual(emit.call_args_list[0].args[0], "mondo_contrari.opposite_explored")
        self.assertEqual(emit.call_args_list[0].args[1], {"category": "up_down"})
        self.assertEqual(emit.call_args_list[1].args[0], "mondo_contrari.all_opposites_completed")
        self.assertTrue(emit.call_args_list[0].kwargs["idempotency_key"])

    def test_real_locale_catalogue_controls_all_ten_state_banners_and_tabs(self) -> None:
        # Explicit four-language injection is a test-only fixture: production
        # remains EN/IT until its voice and human-acceptance gates close.
        support = ActivityLocaleSupport.localized(
            ("it", "en", "es", "fr"), default_ui_locale="it"
        )
        expected_keys = {f"opposite.{state}"
                         for pair in CATEGORY_OPPOSITE_KEYS.values() for state in pair}
        for language in ("it", "en", "es", "fr"):
            with self.subTest(language=language):
                context = resolve_activity_locale(language, support)
                self.assertIsNotNone(context)
                resources = LocalizedResources(PACKAGE_ROOT, context)
                strings = json.loads(
                    (PACKAGE_ROOT / "locales" / f"{language}.json").read_text(encoding="utf-8")
                )["strings"]
                self.assertTrue(all(strings[key] for key in expected_keys))
                renderer = ContrariRenderer(locale=language, resources=resources)
                self.assertEqual(
                    {state: resources.text(f"opposite.{state}")
                     for pair in CATEGORY_OPPOSITE_KEYS.values() for state in pair},
                    renderer._state_labels,
                )
                for category, (first, second) in CATEGORY_OPPOSITE_KEYS.items():
                    tab_text = renderer._toolbar_labels[category]
                    self.assertIn(renderer._state_labels[first], tab_text)
                    self.assertIn(renderer._state_labels[second], tab_text)
                    self.model.set_category(category)
                    renderer.render(self.screen, self.model)
                self.assertGreaterEqual(len(renderer._status_surfaces), 5)
                self.assertEqual(len(renderer._toolbar_surfaces), 5)
                # The first completed frame already cached the strings; no
                # per-frame translation or rasterization is needed.
                self.assertTrue(all(renderer._status_surfaces.values()))

    def test_render_all_categories_without_crash(self) -> None:
        for cat in OppositeCategory:
            self.model.set_category(cat)
            self.renderer.render(self.screen, self.model)

    def test_pointer_interaction(self) -> None:
        # Tap category button for BIG_SMALL
        big_btn = self.renderer.category_buttons[OppositeCategory.BIG_SMALL]
        self.app._handle_pointer_down(big_btn.center)
        self.assertEqual(self.model.category, OppositeCategory.BIG_SMALL)

        # Tap central play surface to toggle
        self.app._handle_pointer_down(self.renderer.play_surface_rect.center)
        self.assertTrue(self.model.is_big)


if __name__ == "__main__":
    unittest.main()
