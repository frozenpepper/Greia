"""Focused behavioral tests for recovered Clinic/Orca audit defects.

No real voice provider, profile save, hardware or rendered acceptance implied.
"""
from __future__ import annotations

import random
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

import pygame

from activities.clinica_cuccioli.clinic_app import ClinicActivity
from activities.clinica_cuccioli.clinic_model import ClinicSession, TOOL_IDS
from activities.baia_delle_orche.orca_app import OrcaBayActivity


class ClinicKeyboardRecoveryTests(TestCase):
    def make_app(self) -> ClinicActivity:
        app = ClinicActivity.__new__(ClinicActivity)
        app._session = ClinicSession(rng=random.Random(42))
        app._focused_tool_index = 0
        app._renderer = Mock()
        app._events = Mock()
        app._progress = Mock()
        app._audio = Mock()
        app._running = True
        return app

    def test_five_patients_keyboard_only_choose_then_apply(self) -> None:
        app = self.make_app()
        while not app._session.is_victory:
            needed = app._session.next_needed
            self.assertIsNotNone(needed)
            assert needed is not None
            destination = TOOL_IDS.index(needed)
            while app._focused_tool_index != destination:
                app._handle_keyboard(pygame.K_RIGHT)
            # First press selects the explicit tool and must not apply it.
            previous = app._session.completed_steps.copy()
            app._handle_keyboard(pygame.K_RETURN)
            self.assertEqual(app._session.completed_steps, previous)
            app._handle_keyboard(pygame.K_RETURN)
            self.assertNotEqual(app._session.completed_steps, previous)
        self.assertEqual(app._session.total_stars, 5)
        self.assertEqual(app._events.patient_healed.call_count, 5)
        self.assertEqual(app._progress.save_stars.call_count, 5)
        app._handle_keyboard(pygame.K_SPACE)
        self.assertFalse(app._session.is_victory)
        self.assertEqual(app._session.total_stars, 5)
        self.assertEqual(app._focused_tool_index, 0)

    def test_keyboard_without_selection_does_not_treat_patient(self) -> None:
        app = self.make_app()
        self.assertIsNone(app._session.selected_tool_id)
        self.assertEqual(app._session.patient_index, 0)
        app._handle_keyboard(pygame.K_RETURN)
        self.assertIsNotNone(app._session.selected_tool_id)
        self.assertEqual(app._session.patient_index, 0)

    def test_touch_normalizes_and_synthetic_mouse_is_suppressed(self) -> None:
        app = self.make_app()
        app._screen = pygame.Surface((800, 480))
        app._handle_pointer = Mock()
        app._handle_event(pygame.event.Event(
            pygame.FINGERDOWN, x=0.25, y=0.5,
        ))
        app._handle_pointer.assert_called_once_with((200, 240))
        app._handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 240), touch=True,
        ))
        self.assertEqual(app._handle_pointer.call_count, 1)


class OrcaGestureAndLocaleRecoveryTests(TestCase):
    def make_app(self) -> OrcaBayActivity:
        app = OrcaBayActivity.__new__(OrcaBayActivity)
        app.renderer = SimpleNamespace(resources=SimpleNamespace(
            context=SimpleNamespace(selected=SimpleNamespace(value="en"))
        ))
        app.pod = Mock()
        app.pod.trigger_fact.return_value = "orca.fact.1"
        app.pod.total_cuddled = 0
        app.audio = Mock()
        app.events = Mock()
        app._gesture_cuddled_ids = set()
        return app

    def test_spoken_facts_use_selected_locale_not_italian_default(self) -> None:
        app = self.make_app()
        app._play_fact()
        app.audio.play_voice.assert_called_once_with("orca.fact.1", "en")
        app.events.record_fact_discovered.assert_called_once_with("orca.fact.1")

    def test_drag_has_at_most_one_cuddle_reward_per_orca(self) -> None:
        app = self.make_app()
        orca = SimpleNamespace(
            id="a", x=500, y=300, trigger_cuddle=Mock(),
        )
        app._cuddle_once(orca, drag=True)
        app._cuddle_once(orca, drag=True)
        self.assertEqual(app.pod.total_cuddled, 1)
        app.events.record_cuddled.assert_called_once_with("a", "belly_rub")
        orca.trigger_cuddle.assert_called_once()
        self.assertEqual(app.audio.play.call_count, 1)
        app._gesture_cuddled_ids.clear()  # next independent gesture
        app._cuddle_once(orca, drag=True)
        self.assertEqual(app.pod.total_cuddled, 2)
