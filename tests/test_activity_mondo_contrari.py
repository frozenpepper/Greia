"""Comprehensive test suite for Mondo Contrari (org.greia.mondo-contrari)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

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
from activities.mondo_contrari.contrari_renderer import ContrariRenderer

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
            self.assertIn(cat, self.model.discovered_categories)

        self.assertTrue(self.model.completed_all)

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
