"""Source regressions for the early-child P7 Activity review.

Focused provider-free tests; execute in the consolidated acceptance run.
"""
from __future__ import annotations

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
import tomllib

import pygame

from activities.acquario_magico.acquarium_app import AquariumApp
from activities.baia_delle_orche.orca_services import GreiaOrcaEvents
from activities.cucciolo_mio.cucciolo_app import CuccioloApp

ROOT = Path(__file__).resolve().parents[1]


class AquariumEventLoopTests(TestCase):
    def test_run_processes_queued_child_input_before_rendering(self) -> None:
        app = object.__new__(AquariumApp)
        app._running = True
        app.handle_event = Mock()
        app._step_frame = Mock()
        app._autosave = Mock()
        events = [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (300, 300)}),
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}),
        ]
        with patch("activities.acquario_magico.acquarium_app.activity_stop_requested", side_effect=[False, True]), patch(
            "activities.acquario_magico.acquarium_app.pygame.event.get", return_value=events
        ):
            self.assertEqual(app.run(), 0)
        self.assertEqual(app.handle_event.call_count, 2)
        app.handle_event.assert_any_call(events[0])
        app._step_frame.assert_called_once_with(0.033)
        app._autosave.assert_called_once()

    def test_declared_milestones_are_emitted_from_real_model_transitions(self) -> None:
        app = object.__new__(AquariumApp)
        app.session = Mock(total_fed=0, glow_mode=False)
        app.session.update.side_effect = lambda dt: setattr(app.session, "total_fed", 2)
        app.audio = Mock()
        app.storage = None
        app._draw = Mock()
        app.ready_published = True
        app.clock = Mock()
        with patch("activities.acquario_magico.acquarium_app.emit_activity_event") as emit:
            app._step_frame(0.033)
            app._toggle_glow_mode()
        self.assertEqual(emit.call_args_list[0].args, (
            "aquarium.fish_fed", {"count": 2, "total_fed": 2}
        ))
        self.assertEqual(emit.call_args_list[1].args, (
            "aquarium.glow_mode_toggled", {"glow_mode": True}
        ))


class OrcaEventManifestTests(TestCase):
    def test_service_event_ids_are_declared(self) -> None:
        declared = {
            e["id"] for e in tomllib.loads(
                (ROOT / "activities/baia_delle_orche/activity.toml").read_text()
            )["education"]["events"]
        }
        with patch("activities.baia_delle_orche.orca_services.emit_activity_event") as emit:
            events = GreiaOrcaEvents()
            events.record_feeding(2)
            events.record_fact_discovered("fact_breach")
        self.assertEqual([call.args[0] for call in emit.call_args_list],
                         ["orca.fed", "orca.fact_discovered"])
        self.assertIn("orca.fact_discovered", declared)
        self.assertIn("orca.fed", declared)


class CuccioloQueuedPointerTests(TestCase):
    def test_ball_drag_consumes_events_not_global_mouse_polling(self) -> None:
        app = object.__new__(CuccioloApp)
        app._screen = pygame.Surface((1024, 600))
        app._canvas = Mock()
        app._canvas.pointer.side_effect = lambda point: point
        app._active_tab = "play"
        app._ball_pos = [512.0, 440.0]
        app._ball_last_pos = [512.0, 440.0]
        app._ball_vel = [0.0, 0.0]
        app._is_dragging_ball = False
        app._pet = Mock()
        app._handle_pointer_click = Mock()
        with patch("activities.cucciolo_mio.cucciolo_app._is_safe_point", return_value=True):
            app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
                "button": 1, "pos": (512, 440)
            }))
            app._handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (542, 420)}))
            self.assertEqual(app._ball_pos, [542, 420])
            app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {
                "button": 1, "pos": (542, 420)
            }))
            app._handle_pointer_click.assert_not_called()
            self.assertFalse(app._is_dragging_ball)
            self.assertGreater(app._ball_vel[0], 0)

            app._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {
                "button": 1, "pos": (542, 420)
            }))
            app._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST, {}))
            self.assertFalse(app._is_dragging_ball)
            self.assertEqual(app._ball_vel, [0.0, 0.0])

    def test_played_event_matches_manifest(self) -> None:
        manifest = tomllib.loads(
            (ROOT / "activities/cucciolo_mio/activity.toml").read_text()
        )
        self.assertIn(
            "pet.played",
            {e["id"] for e in manifest["education"]["events"]},
        )
