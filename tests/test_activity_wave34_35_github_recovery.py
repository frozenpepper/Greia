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
from activities.clinica_cuccioli.clinic_content import BodyPart
from activities.clinica_cuccioli.clinic_model import ClinicDay, ClinicDayFactory, Phase
from activities.clinica_cuccioli.clinic_services import ClinicProgressState
from activities.baia_delle_orche.orca_app import OrcaBayActivity


class ClinicKeyboardRecoveryTests(TestCase):
    """Keyboard-only play of a whole clinic day (reworked 2026-10-16).

    The old choose-then-apply palette and its hand-rolled touch/keyboard
    handlers were replaced by the shared control kit (ADR 0037); touch
    normalization and synthetic-mouse suppression now live in
    ``PygameControlInput`` and are covered by the platform kit tests.
    """

    def test_five_patients_keyboard_only(self) -> None:
        import os
        from pathlib import Path

        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        screen = pygame.display.get_surface() or pygame.display.set_mode((1024, 600))
        root = Path(__file__).resolve().parents[1] / "activities" / "clinica_cuccioli"
        context = resolve_activity_locale("en", ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it"))
        factory = ClinicDayFactory(random.Random(42))
        progress = Mock()
        clock = [0.0]
        app = ClinicActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            day=ClinicDay(factory.build(1), level=1),
            factory=factory,
            typography=GreiaTypography(),
            resources=LocalizedResources(root, context),
            progress=progress,
            saved=ClinicProgressState(),
            events=Mock(),
            audio=Mock(),
            clock=lambda: clock[0],
        )

        def advance(seconds: float) -> None:
            end = clock[0] + seconds
            while clock[0] < end:
                clock[0] += 0.05
                app.step()

        def press_until(control_id: str) -> None:
            layer = app.controls.layer
            for key in (pygame.K_RIGHT, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN) * 4:
                if layer.focused_id == control_id:
                    break
                for _ in range(6):
                    if layer.focused_id == control_id:
                        break
                    app.press(key)
            self.assertEqual(layer.focused_id, control_id)
            app.press(pygame.K_RETURN)

        parts = {BodyPart.EAR: "part.ear_right", BodyPart.PAW: "part.paw", BodyPart.TUMMY: "part.tummy", BodyPart.FUR: "part.tummy"}
        for _ in range(5):
            advance(1.3)
            press_until(parts[app.day.case.ailment.part])
            advance(1.2)
            while app.day.phase is Phase.CARE:
                press_until(f"tool.{app.day.expected_tool.value}")
                advance(1.3)
            advance(3.6)
        advance(0.5)
        self.assertEqual(app.day.healed_count, 5)
        self.assertEqual(app.state.value, "terminal")
        app.press(pygame.K_RETURN)
        self.assertEqual(app.state.value, "playing")


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
