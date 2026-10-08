"""Comprehensive test suite for Le Faccine di Momo (org.greia.faccine-momo)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import tomllib

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from activities.faccine_momo.momo_app import MomoActivity
from activities.faccine_momo.momo_audio import MomoAudio, MomoSpeechQueue
from activities.faccine_momo.momo_model import (
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    Emotion,
    GameMode,
    MomoModel,
)
from activities.faccine_momo.momo_renderer import MomoRenderer

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "activities" / "faccine_momo"


class TestMomoDomain(unittest.TestCase):
    """Test Momo emotional states, cuddle comfort mechanics, and quiz logic."""

    def setUp(self) -> None:
        self.model = MomoModel()

    def test_initial_state(self) -> None:
        self.assertEqual(self.model.emotion, Emotion.HAPPY)
        self.assertEqual(self.model.mode, GameMode.FREE_MIRROR)
        self.assertFalse(self.model.is_comforted)
        self.assertFalse(self.model.completed_all)

    def test_emotion_transitions_and_completion(self) -> None:
        for emo in Emotion:
            self.model.set_emotion(emo)
            self.assertEqual(self.model.emotion, emo)
            self.assertIn(emo, self.model.discovered_emotions)

        self.assertTrue(self.model.completed_all)

    def test_sad_comfort_cuddle(self) -> None:
        self.model.set_emotion(Emotion.SAD)
        self.assertFalse(self.model.is_comforted)

        # Stroke cheek to comfort
        cuddled = self.model.comfort_momo()
        self.assertTrue(cuddled)
        self.assertTrue(self.model.is_comforted)

        # Hearts spawned in particles
        hearts = [p for p in self.model.particles if p.kind == "heart"]
        self.assertGreater(len(hearts), 0)

        # Second comfort is no-op
        self.assertFalse(self.model.comfort_momo())

    def test_quiz_mode_flow(self) -> None:
        self.model.start_quiz_round()
        self.assertEqual(self.model.mode, GameMode.GUESS_EMOTION)
        self.assertEqual(len(self.model.quiz_choices), 2)
        self.assertIn(self.model.quiz_target, self.model.quiz_choices)

        # Test incorrect answer
        distractor = [c for c in self.model.quiz_choices if c != self.model.quiz_target][0]
        correct = self.model.answer_quiz(distractor)
        self.assertFalse(correct)
        self.assertGreater(self.model.shake_offset, 0.0)

        # Test correct answer
        correct = self.model.answer_quiz(self.model.quiz_target)
        self.assertTrue(correct)
        self.assertEqual(self.model.quiz_streak, 1)
        self.assertGreater(self.model.hop_offset, 0.0)


class TestMomoAudioAndSpeech(unittest.TestCase):
    """Test Momo speech queue and procedural SFX."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.mixer.init()

    def test_audio_and_queue(self) -> None:
        audio = MomoAudio(PACKAGE_ROOT, locale="it")
        queue = MomoSpeechQueue(audio)

        queue.enqueue("welcome", delay_after=0.1)
        queue.enqueue("happy", delay_after=0.1)
        self.assertEqual(len(queue._queue), 2)

        queue.clear()
        self.assertEqual(len(queue._queue), 0)


class TestMomoRendererAndApp(unittest.TestCase):
    """Test renderer execution across emotions and input handling."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def setUp(self) -> None:
        self.screen = pygame.display.get_surface()
        self.model = MomoModel()
        self.renderer = MomoRenderer()
        self.audio = MomoAudio(PACKAGE_ROOT, locale="it")
        self.app = MomoActivity(self.screen, self.renderer, self.audio, self.model)

    def test_render_all_emotions_without_crash(self) -> None:
        for emo in Emotion:
            self.model.set_emotion(emo)
            self.renderer.render(self.screen, self.model)

    def test_render_comforted_state_without_crash(self) -> None:
        self.model.set_emotion(Emotion.SAD)
        self.model.comfort_momo()
        self.renderer.render(self.screen, self.model)

    def test_render_quiz_mode_without_crash(self) -> None:
        self.model.start_quiz_round()
        self.renderer.render(self.screen, self.model)

    def test_declared_events_only_on_new_discoveries_and_completion(self) -> None:
        events = Mock()
        app = MomoActivity(self.screen, self.renderer, self.audio, MomoModel(), events)
        app._set_emotion(Emotion.SAD)
        app._set_emotion(Emotion.SAD)
        self.assertEqual(events.emotion_discovered.call_count, 1)
        for emotion in Emotion:
            app._set_emotion(emotion)
        self.assertEqual(events.emotion_discovered.call_count, len(Emotion) - 1)
        events.all_emotions_explored.assert_called_once_with()

        declared = {
            item["id"]
            for item in tomllib.loads((PACKAGE_ROOT / "activity.toml").read_text())["education"]["events"]
        }
        self.assertEqual(declared, {
            "faccine_momo.emotion_discovered",
            "faccine_momo.all_emotions_explored",
        })

    def test_correct_quiz_answers_discover_emotions(self) -> None:
        events = Mock()
        app = MomoActivity(self.screen, self.renderer, self.audio, MomoModel(), events)
        app.model.start_quiz_round()
        app.model.quiz_target = Emotion.ANGRY
        app.model.quiz_choices = [Emotion.ANGRY, Emotion.SAD]
        app._handle_pointer_down(self.renderer.quiz_choice_rects[0].center)
        events.emotion_discovered.assert_called_once_with(Emotion.ANGRY.value)

    def test_reference_canvas_refuses_protected_chrome_and_letterbox(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        viewport = activity_viewport_for_surface(self.screen)
        protected = viewport.protected_regions[0]
        events = Mock()
        app = MomoActivity(self.screen, self.renderer, self.audio, MomoModel(), events)
        app._handle_pointer_down((int(protected.x) + 1, int(protected.y) + 1))
        events.emotion_discovered.assert_not_called()

        # The dedicated reference canvas owns fit/pointer mapping, not
        # independent X/Y stretch factors.
        self.assertEqual(app._to_reference_pos((-3, 10)), None)

    def test_pointer_interaction(self) -> None:
        # Tap sad button (first right button)
        sad_rect = self.renderer.right_buttons[0][1]
        self.app._handle_pointer_down(sad_rect.center)
        self.assertEqual(self.model.emotion, Emotion.SAD)

        # Tap cheek to comfort
        self.app._handle_pointer_down(self.renderer.momo_left_cheek.center)
        self.assertTrue(self.model.is_comforted)

        # Tap mode button to enter quiz
        self.app._handle_pointer_down(self.renderer.mode_button_rect.center)
        self.assertEqual(self.model.mode, GameMode.GUESS_EMOTION)


if __name__ == "__main__":
    unittest.main()
