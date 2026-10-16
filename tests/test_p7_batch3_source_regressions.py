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



    def test_aquarium_rejects_platform_chrome(self) -> None:
        from activities.acquario_magico.acquarium_app import _is_safe_point
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        surface = pygame.Surface((1024, 600))
        region = activity_viewport_for_surface(surface).protected_regions[0]
        self.assertFalse(_is_safe_point(surface, (int(region.x) + 1, int(region.y) + 1)))
        self.assertTrue(_is_safe_point(surface, (500, 300)))


class OrcaPointerSafetyTests(TestCase):
    def test_rejects_chrome_and_outside_surface(self) -> None:
        from activities.baia_delle_orche.orca_app import OrcaBayActivity
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app = object.__new__(OrcaBayActivity)
        app.screen = pygame.Surface((1024, 600))
        region = activity_viewport_for_surface(app.screen).protected_regions[0]
        self.assertFalse(app._safe_pointer((int(region.x) + 1, int(region.y) + 1)))
        self.assertFalse(app._safe_pointer((-1, 200)))
        self.assertTrue(app._safe_pointer((500, 300)))

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
    """The reworked pet (one care day through the shared control kit) takes
    taps from the queued Pygame events and never polls the global mouse."""

    def test_care_tray_consumes_queued_events_not_global_mouse_polling(self) -> None:
        import random

        from activities.cucciolo_mio.cucciolo_content import CARE_FOR_NEED
        from activities.cucciolo_mio.cucciolo_model import Phase
        from activities.cucciolo_mio.cucciolo_services import PetProfile
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        pygame.init()
        screen = pygame.display.set_mode((1024, 600))
        now = [100.0]
        progress = Mock()
        progress.load.return_value = PetProfile(species="puppy", name="moon")
        app = CuccioloApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=None,
            audio=Mock(),
            progress=progress,
            events=Mock(),
            rng=random.Random(1),
            clock=lambda: now[0],
        )
        while app.day.phase is not Phase.NEED and now[0] < 120.0:
            now[0] += 0.1
            app.step()
        self.assertIs(app.day.phase, Phase.NEED)
        target = app.controls.tray_rect(CARE_FOR_NEED[app.day.current_need]).center
        with patch("pygame.mouse.get_pos", side_effect=AssertionError("polled")), patch(
            "pygame.mouse.get_pressed", side_effect=AssertionError("polled")
        ):
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": target}))
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": target}))
        self.assertIs(app.day.phase, Phase.CARE)

    def test_played_event_matches_manifest(self) -> None:
        manifest = tomllib.loads(
            (ROOT / "activities/cucciolo_mio/activity.toml").read_text()
        )
        self.assertIn(
            "pet.played",
            {e["id"] for e in manifest["education"]["events"]},
        )
