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
        "serra": (
            PROJECT_ROOT / "activities" / "piccola_serra" / "main.py",
            PROJECT_ROOT / "activities" / "piccola_serra" / "serra_app.py",
            PROJECT_ROOT / "activities" / "piccola_serra" / "serra_renderer.py",
            PROJECT_ROOT / "activities" / "piccola_serra" / "serra_model.py",
        ),
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
        # Victory gate must be before the reference render marker.
        # Monolith used `if is_victory:` while decomposed uses
        # `if self.model.is_victory:` – accept either but require ordering.
        victory_markers_serra = [
            "if is_victory:\n            if not completion_presented:",
            "if self.model.is_victory:\n                if not self.completion_presented:",
            "if self.model.is_victory:",
        ]
        victory_idx_serra = min(
            (serra.index(m) for m in victory_markers_serra if m in serra),
            default=None,
        )
        self.assertIsNotNone(victory_idx_serra, "serra must contain victory gate")
        assert victory_idx_serra is not None
        # Render marker lives in serra_app._draw (`# RENDER TO CANVAS`)
        self.assertIn("# RENDER TO CANVAS", serra)
        self.assertLess(victory_idx_serra, serra.index("# RENDER TO CANVAS"))
        # Active particle update must be gated behind victory check.
        self.assertTrue(
            "if not is_victory:\n            surviving = []" in serra
            or "if not self.model.is_victory:\n            surviving = []" in serra,
            "serra must gate particle update on non-victory",
        )

    def test_completion_facts_are_declared_and_once_only_terminal_transitions(self) -> None:
        maze = self._source("labirinto")
        self.assertEqual(maze.count('emit_activity_event(\n                            "maze.completed"'), 1)

        serra = self._source("serra")
        # Harvest completion is emitted once; one-liner vs multi-line still counts once.
        self.assertEqual(serra.count('"greenhouse.harvest_completed"'), 1)

    def test_number_express_uses_the_shared_completion_overlay(self) -> None:
        """Treno Numeri moved to the ADR 0037 kit: the shared cast completion
        scene is a modal Overlay (no per-Activity terminal loop), facts are
        published once each, and keys are scoped per journey so a replayed
        journey is never deduplicated against the previous one."""

        root = PROJECT_ROOT / "activities" / "treno_numeri"
        app = (root / "treno_app.py").read_text(encoding="utf-8")
        services = (root / "treno_services.py").read_text(encoding="utf-8")
        self.assertIn("CompletionOverlay(self.completion", app)
        self.assertIn("CompletionScene(self.kit", app)
        self.assertIn("self.completion.prepare(", app)
        self.assertIsNone(
            re.search(r"Surface\(\(REFERENCE_WIDTH,\s*REFERENCE_HEIGHT\),\s*pygame\.SRCALPHA\)", app)
        )
        self.assertEqual(services.count('"train.station_completed"'), 1)
        self.assertEqual(services.count('"train.journey_completed"'), 1)
        self.assertNotIn('"train.problem_solved"', services)
        self.assertIn('f"train:{journey_id}:station:{index}"', services)
        self.assertIn('f"train:{journey_id}:completed"', services)
        self.assertEqual(app.count("self._journey_id = uuid4().hex"), 2)  # start + restart


if __name__ == "__main__":
    unittest.main()
