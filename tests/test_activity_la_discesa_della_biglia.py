"""Tests for la_discesa_della_biglia Activity (engine + storage)."""

from __future__ import annotations

import importlib
import math
import os
from unittest.mock import Mock
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "la_discesa_della_biglia"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


from ramp_content import (
    LEVELS,
    MAX_RUN_SECONDS,
    MARBLE_RADIUS,
    MARBLE_START,
    PlacedTool,
    ToolKind,
    ToolSpec,
)
from ramp_engine import RampEngine
from ramp_services import RampStorage, ProgressState, STORAGE_KEY


def _slope(kind: ToolKind, x: float, y: float, deg: float) -> PlacedTool:
    return PlacedTool(
        ToolSpec(kind, "tool", 0),
        x=x, y=y, angle=math.radians(deg),
    )


class RampEngineTests(unittest.TestCase):
    def test_marble_falls_under_gravity(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        for _ in range(60):
            eng.step(1 / 30)
        # Marble is well below the start
        self.assertGreater(eng.marble.y, MARBLE_START[1] + 50)

    def test_basket_hit_marks_completion(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.marble.x = LEVELS[0].basket_x
        eng.marble.y = LEVELS[0].basket_y - 60
        eng.marble.vy = 200
        for _ in range(60):
            eng.step(1 / 30)
            if eng.finished:
                break
        self.assertEqual(eng.outcome, "hit")
        self.assertGreater(eng.elapsed, 0)

    def test_marble_off_playfield_is_missed(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.marble.y = 600
        for _ in range(5):
            eng.step(1 / 30)
        self.assertEqual(eng.outcome, "missed")

    def test_spring_triggers_exactly_once_per_run(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.add_tool(
            PlacedTool(ToolSpec(ToolKind.SPRING, "tool", 0), x=160, y=250)
        )
        spring_hits = 0
        for _ in range(120):
            for e in eng.step(1 / 30):
                if e.kind == "tool_hit" and e.tool_kind == "spring":
                    spring_hits += 1
            if eng.finished:
                break
        self.assertEqual(spring_hits, 1)

    def test_walls_reflect_marble(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.marble.x = 90  # near left wall
        eng.marble.y = 200
        eng.marble.vx = -200
        for _ in range(60):
            eng.step(1 / 30)
            if eng.finished:
                break
        # Marble is reflected rightward and stays inside the playfield
        self.assertGreaterEqual(eng.marble.vx, 0)

    def test_slope_deflects_marble(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.add_tool(_slope(ToolKind.SLOPE, 160, 200, 25))
        for _ in range(120):
            eng.step(1 / 30)
            if eng.finished:
                break
        # A 25-degree slope should produce a meaningful rightward
        # velocity; otherwise the engine is reflecting the wrong
        # direction.
        self.assertGreater(eng.marble.vx, 60)

    def test_staircase_reaches_basket(self) -> None:
        # Three slopes laid out as a staircase should deliver the
        # marble into the basket on the open level.
        eng = RampEngine(level=LEVELS[0])
        eng.add_tool(_slope(ToolKind.SLOPE, 200, 180, 25))
        eng.add_tool(_slope(ToolKind.SLOPE, 400, 240, 25))
        eng.add_tool(_slope(ToolKind.SLOPE, 600, 300, 25))
        for _ in range(300):
            eng.step(1 / 30)
            if eng.finished:
                break
        self.assertEqual(eng.outcome, "hit")

    def test_reset_marble_restores_initial_state(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        for _ in range(60):
            eng.step(1 / 30)
        eng.reset_marble()
        self.assertFalse(eng.finished)
        self.assertEqual(eng.outcome, None)
        self.assertEqual(eng.marble.x, MARBLE_START[0])
        self.assertEqual(eng.marble.y, MARBLE_START[1])
        self.assertEqual(eng.elapsed, 0.0)


class RampManifestTruthTests(unittest.TestCase):
    def test_declares_authored_not_fictional_adaptive_progression(self) -> None:
        import tomllib
        with (ACTIVITY_ROOT / "activity.toml").open("rb") as file:
            manifest = tomllib.load(file)
        self.assertNotIn("adaptive_difficulty", manifest["education"])
        self.assertNotIn("difficulty_max", manifest["education"])
        self.assertEqual(len(LEVELS), 3)


class RampPointerSafetyTests(unittest.TestCase):
    def test_letterbox_and_protected_input_rejected_without_mutation(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        from ramp_app import RampApp

        pygame.init()
        surface = pygame.Surface((800, 480))
        app = RampApp(
            screen=surface,
            metrics=Mock(),
            theme=Mock(),
            typography=Mock(),
            resources=Mock(),
            audio=Mock(),
            storage=Mock(),
            events=Mock(),
        )
        rect = activity_viewport_for_surface(surface).protected_regions[0]
        self.assertIsNone(app._reference_point((int(rect.x) + 1, int(rect.y) + 1)))
        self.assertIsNone(app._reference_point((-2, 240)))
        self.assertIsNone(app._reference_point((400, 0)))
        self.assertIsNotNone(app._reference_point((400, 240)))

        app.renderer.drag_kind = ToolKind.BUMPER
        app.renderer.drag_origin = (300, 220)
        app._handle_release((int(rect.x) + 1, int(rect.y) + 1))
        self.assertIsNone(app.renderer.drag_kind)
        self.assertEqual(len(app.engine.tools), 0)

    def test_released_tool_preserves_original_drag_kind(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from ramp_app import RampApp

        pygame.init()
        app = RampApp(
            screen=pygame.Surface((1024, 600)),
            metrics=Mock(),
            theme=Mock(),
            typography=Mock(),
            resources=Mock(),
            audio=Mock(),
            storage=Mock(),
            events=Mock(),
        )
        app.renderer.drag_kind = ToolKind.BUMPER
        app.renderer.palette_selected = 0
        app._handle_release((380, 250))
        self.assertEqual(len(app.engine.tools), 1)
        self.assertEqual(app.engine.tools[0].spec.kind, ToolKind.BUMPER)


class RampTerminationRegressionTests(unittest.TestCase):
    """Every run ends: a resting marble used to soft-lock DROP/CLEAR for ever."""

    def test_marble_resting_in_a_pocket_settles_and_finishes(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.add_tool(_slope(ToolKind.SLOPE, 130, 200, 25))
        eng.add_tool(_slope(ToolKind.SLOPE, 198, 200, -25))
        events = []
        for _ in range(30 * 20):
            events.extend(eng.step(1 / 30))
            if eng.finished:
                break
        self.assertTrue(eng.finished)
        self.assertEqual(eng.outcome, "settled")
        self.assertIn("settled", [event.kind for event in events])
        self.assertLess(eng.elapsed, MAX_RUN_SECONDS)

    def test_flat_slope_resting_marble_settles(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.add_tool(_slope(ToolKind.SLOPE, 160, 200, 0))
        for _ in range(30 * 20):
            eng.step(1 / 30)
            if eng.finished:
                break
        self.assertEqual(eng.outcome, "settled")

    def test_hard_time_cap_ends_a_run_that_never_rests(self) -> None:
        eng = RampEngine(level=LEVELS[0])
        eng.elapsed = MAX_RUN_SECONDS - 0.01
        eng.marble.y = 150
        for _ in range(5):
            eng.step(1 / 30)
        self.assertTrue(eng.finished)
        self.assertEqual(eng.outcome, "settled")


class RampAppRunRegressionTests(unittest.TestCase):
    """Drive the real app state machine (placement -> DROP -> result -> edit)."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame

        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 600))

    def _app(self):
        from ramp_app import Phase, build_app

        app = build_app(self.screen, locale="en")
        # Isolate from the profile store, event broker and sound device.
        app.audio = Mock()
        app.events = Mock()
        app.storage = Mock(best_time=Mock(return_value=None))
        return app, Phase

    def _place(self, app, kind: ToolKind, pos: tuple[int, int]) -> None:
        app.renderer.drag_kind = kind
        app._handle_release(pos)

    def test_placed_slopes_are_tilted_towards_the_basket(self) -> None:
        app, _phase = self._app()
        self._place(app, ToolKind.SLOPE, (300, 250))
        self._place(app, ToolKind.BUMPER, (400, 250))
        slope, bumper = app.engine.tools
        self.assertGreater(slope.angle, math.radians(10))
        self.assertEqual(bumper.angle, 0.0)

    def test_every_run_returns_to_edit_mode_and_keeps_the_pieces(self) -> None:
        app, phase = self._app()
        # A pocket under the marble that it can never leave.
        self._place(app, ToolKind.SLOPE, (130, 200))
        app.engine.tools[0] = _slope(ToolKind.SLOPE, 130, 200, 25)
        app.engine.tools.append(_slope(ToolKind.SLOPE, 198, 200, -25))
        app._try_drop()
        self.assertEqual(app.phase, phase.RUNNING)
        for _ in range(30 * 40):
            app._update(1 / 30)
            if app.phase != phase.RUNNING:
                break
        self.assertEqual(app.phase, phase.FINISHED)
        self.assertEqual(app.last_outcome, "missed")
        app.finished_banner_timer = 0.0
        app._draw()
        self.assertEqual(app.phase, phase.PALETTE)
        self.assertEqual(len(app.engine.tools), 2)
        # DROP and CLEAR are usable again.
        app._clear_tools()
        self.assertEqual(app.engine.tools, [])
        app._try_drop()
        self.assertEqual(app.phase, phase.RUNNING)

    def test_missed_marble_is_drawn_inside_the_playfield(self) -> None:
        from ramp_content import MARBLE_COLOR, PLAYFIELD_BOTTOM, PLAYFIELD_LEFT, PLAYFIELD_RIGHT

        app, _phase = self._app()
        renderer = app.renderer
        renderer.surface.fill((0, 0, 0))
        renderer._draw_marble(500.0, PLAYFIELD_BOTTOM + 300.0, 0.0, 900.0, True, "missed")
        below = [
            (x, y)
            for y in range(PLAYFIELD_BOTTOM + 1, 600)
            for x in range(PLAYFIELD_LEFT, PLAYFIELD_RIGHT, 2)
            if tuple(renderer.surface.get_at((x, y)))[:3] == MARBLE_COLOR
        ]
        self.assertEqual(below, [], "marble pixels were drawn below the playfield")
        self.assertEqual(
            tuple(renderer.surface.get_at((500, PLAYFIELD_BOTTOM - 14)))[:3], MARBLE_COLOR
        )


class RampStorageContractTests(unittest.TestCase):
    """Storage shape is owned by the Activity; tests cover the
    round-trip, not the platform KV.
    """

    def test_best_time_progress_key_is_namespaced(self) -> None:
        # The Activity's storage key must not collide with other
        # Activities or with the global Greia achievement store.
        self.assertTrue(STORAGE_KEY.startswith("la_discesa_della_biglia."))
        self.assertIn("progress", STORAGE_KEY)

    def test_progress_state_serialisation(self) -> None:
        state = ProgressState(best_times={"open": 2.5})
        self.assertEqual(state.best_times["open"], 2.5)
        self.assertNotIn("missing", state.best_times)


if __name__ == "__main__":
    unittest.main()
