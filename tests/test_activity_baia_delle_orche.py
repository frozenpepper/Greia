from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.baia_delle_orche.orca_model import (
    FoodType,
    OrcaPod,
    OrcaState,
    ToyEntity,
    WATER_SURFACE_Y,
)
from activities.baia_delle_orche.orca_renderer import OrcaRenderer
from activities.baia_delle_orche.orca_services import GreiaOrcaEvents, GreiaOrcaProgress
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "baia_delle_orche"


class BaiaDelleOrcheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600), pygame.HIDDEN)

    def _renderer(self) -> OrcaRenderer:
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_DIR, context)
        return OrcaRenderer(GreiaTypography(), resources)

    def test_orca_pod_members_and_morphology(self) -> None:
        pod = OrcaPod()
        self.assertEqual([orca.id for orca in pod.orcas], ["kiko", "luna", "oskar"])
        self.assertLess(pod.orcas[0].scale, 1.0)
        self.assertEqual(pod.orcas[1].scale, 1.0)
        self.assertGreater(pod.orcas[2].scale, 1.0)
        for orca in pod.orcas:
            self.assertGreater(orca.width, 0)
            self.assertGreater(orca.height, 0)
            self.assertEqual(orca.state, OrcaState.SWIMMING)

    def test_cuddle_state_transition(self) -> None:
        pod = OrcaPod()
        kiko = pod.orcas[0]
        kiko.trigger_cuddle()
        self.assertEqual(kiko.state, OrcaState.CUDDLE_BELLY)
        self.assertGreater(kiko.cuddle_happiness, 0.0)
        kiko.update(3.0, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(kiko.state, OrcaState.SWIMMING)

    def test_breaching_jump_returns_to_swimming_with_feedback(self) -> None:
        pod = OrcaPod()
        luna = pod.orcas[1]
        luna.trigger_breach(jump_x=600.0, height_bonus=30.0)
        self.assertEqual(luna.state, OrcaState.BREACHING)
        luna.update(0.4, pod.foods, pod.toys, night_mode=False)
        events = luna.update(1.2, pod.foods, pod.toys, night_mode=False)
        self.assertEqual(luna.state, OrcaState.SWIMMING)
        self.assertIn("splash", events)
        self.assertIn("whistle", events)

    def test_food_and_toy_physics(self) -> None:
        pod = OrcaPod()
        food = pod.spawn_food(
            x=pod.orcas[0].x,
            y=pod.orcas[0].y - 20.0,
            kind=FoodType.HERRING,
        )
        self.assertIn(food, pod.foods)
        pod.update(0.1)

        ball = ToyEntity("ball", 400.0, WATER_SURFACE_Y - 50.0)
        ball.update(0.033)
        self.assertGreater(ball.vy, 0.0)
        ball.y = WATER_SURFACE_Y + 20.0
        ball.update(0.033)
        self.assertLess(ball.vy, 0.0)

    def test_progress_export_and_restore(self) -> None:
        pod = OrcaPod()
        pod.total_fed = 12
        pod.total_cuddled = 8
        pod.total_acrobatics = 5
        pod.total_songs = 3
        pod.night_mode = True

        restored = OrcaPod()
        restored.restore_progress(pod.export_progress())
        self.assertEqual(restored.total_fed, 12)
        self.assertEqual(restored.total_cuddled, 8)
        self.assertEqual(restored.total_acrobatics, 5)
        self.assertEqual(restored.total_songs, 3)
        self.assertTrue(restored.night_mode)

    def test_renderer_handles_day_night_and_fact_banner(self) -> None:
        renderer = self._renderer()
        surface = pygame.Surface((1024, 600))
        pod = OrcaPod()
        renderer.render_frame(surface, pod)
        pod.night_mode = True
        pod.trigger_fact("fact_breach")
        renderer.render_frame(surface, pod)
        self.assertEqual(surface.get_size(), (1024, 600))

    def test_app_tools_and_fact_flow(self) -> None:
        from activities.baia_delle_orche.orca_app import OrcaBayActivity
        from greia_platform.pygame_canvas import PygameReferenceCanvas

        renderer = self._renderer()
        screen = pygame.Surface((1024, 600))
        pod = OrcaPod()
        app = OrcaBayActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            pod=pod,
            renderer=renderer,
            audio=Mock(),
            progress=GreiaOrcaProgress(),
            events=GreiaOrcaEvents(),
        )

        app.handle_tool_click(0)
        self.assertGreaterEqual(len(pod.foods), 1)

        app.handle_tool_click(2)
        self.assertTrue(all(orca.state == OrcaState.BREACHING for orca in pod.orcas))

        app.handle_tool_click(4)
        self.assertTrue(pod.night_mode)

        app.handle_tool_click(5)
        first_fact = pod.active_fact
        self.assertIsNotNone(first_fact)
        self.assertIn(first_fact, pod.discovered_facts)

        banner_rect = renderer.fact_banner_rect
        app.handle_pointer_down(float(banner_rect.centerx), float(banner_rect.centery))
        self.assertIsNotNone(pod.active_fact)
        self.assertNotEqual(pod.active_fact, first_fact)


if __name__ == "__main__":
    unittest.main()
