from __future__ import annotations

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FirstPartyTerminalRenderingContractTests(unittest.TestCase):
    """Keep the three Acer-sensitive terminal loops on the shared owner."""

    SOURCES = {
        "labirinto": (
            PROJECT_ROOT / "activities" / "labirinto_magico" / "maze_app.py",
            PROJECT_ROOT / "activities" / "labirinto_magico" / "maze_renderer.py",
        ),
        "serra": (PROJECT_ROOT / "activities" / "piccola_serra" / "main.py",),
        "treno": (PROJECT_ROOT / "activities" / "treno_numeri" / "main.py",),
    }

    def _source(self, activity: str) -> str:
        return "\n".join(path.read_text(encoding="utf-8") for path in self.SOURCES[activity])

    def test_all_affected_activities_use_prepared_terminal_owner_and_stable_action(self) -> None:
        for activity in self.SOURCES:
            with self.subTest(activity=activity):
                source = self._source(activity)
                self.assertIn("PygameCompletionScreen", source)
                self.assertIn("completion.prepare", source)
                self.assertIn("completion.draw", source)
                self.assertIn("completion.primary_contains", source)
                self.assertIn("clock.tick(25)", source)

    def test_terminal_paths_have_no_frame_sized_alpha_modal(self) -> None:
        frame_overlay = re.compile(
            r"Surface\(\(REFERENCE_WIDTH,\s*REFERENCE_HEIGHT\),\s*pygame\.SRCALPHA\)"
        )
        for activity in self.SOURCES:
            with self.subTest(activity=activity):
                self.assertIsNone(frame_overlay.search(self._source(activity)))

    def test_active_simulation_is_structurally_after_terminal_gate(self) -> None:
        maze = self._source("labirinto")
        self.assertLess(
            maze.index("if self.state is not None and self.state.is_victory:"),
            maze.index("self.update(dt, self.canvas.surface, self.metrics)"),
        )

        serra = self._source("serra")
        self.assertLess(
            serra.index("if is_victory:\n            if not completion_presented:"),
            serra.index("# RENDER TO CANVAS"),
        )
        self.assertIn("if not is_victory:\n            surviving = []", serra)

        treno = self._source("treno")
        self.assertLess(
            treno.index("if is_victory:\n            if not completion_presented:"),
            treno.index("if train_state == \"arriving\":"),
        )

    def test_completion_facts_are_declared_and_once_only_terminal_transitions(self) -> None:
        maze = self._source("labirinto")
        self.assertEqual(maze.count('emit_activity_event(\n                            "maze.completed"'), 1)

        serra = self._source("serra")
        self.assertEqual(serra.count('emit_activity_event("greenhouse.harvest_completed"'), 1)

        treno = self._source("treno")
        self.assertEqual(treno.count('"train.station_completed"'), 1)
        self.assertEqual(treno.count('"train.journey_completed"'), 1)
        self.assertNotIn('"train.problem_solved"', treno)
        self.assertIn('idempotency_key=f"station-{round_idx}"', treno)
        self.assertIn('idempotency_key="journey-completed"', treno)


if __name__ == "__main__":
    unittest.main()
