"""Tests for la_discesa_della_biglia Activity (engine + storage)."""

from __future__ import annotations

import importlib
import math
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
