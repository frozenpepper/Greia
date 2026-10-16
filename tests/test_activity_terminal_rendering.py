from __future__ import annotations

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FirstPartyTerminalRenderingContractTests(unittest.TestCase):
    """Keep the Acer-sensitive terminal loops on the shared owner."""

    def test_little_green_thumb_uses_the_shared_completion_overlay(self) -> None:
        """Piccola Serra moved to the ADR 0037 kit (its old per-Activity
        terminal loop and victory gate are retired): the shared cast
        completion scene is a modal Overlay, gameplay drawing and hints stop
        in the terminal state, and facts are published once each with
        per-visit keys."""

        root = PROJECT_ROOT / "activities" / "piccola_serra"
        app = (root / "serra_app.py").read_text(encoding="utf-8")
        services = (root / "serra_services.py").read_text(encoding="utf-8")
        self.assertIn("CompletionOverlay(self.completion", app)
        self.assertIn("CompletionScene(self.kit", app)
        self.assertIn("self.completion.prepare(", app)
        self.assertIn("if self.state is AppState.PLAYING:\n            self._maybe_hint(now)", app)
        self.assertIn("if self.state is not AppState.TERMINAL:\n            self.renderer.draw(", app)
        self.assertIsNone(
            re.search(r"Surface\(\(REFERENCE_WIDTH,\s*REFERENCE_HEIGHT\),\s*pygame\.SRCALPHA\)", app)
        )
        self.assertEqual(services.count('"greenhouse.harvest_completed"'), 1)
        self.assertEqual(services.count('"greenhouse.plant_grown"'), 1)
        self.assertIn('f"piccola-serra:{visit_id}"', services)
        self.assertEqual(app.count("self._visit_id = uuid4().hex"), 2)  # start + restart

    def test_magical_labyrinth_uses_the_shared_completion_overlay(self) -> None:
        """Il Labirinto Magico moved to the ADR 0037 kit: the shared cast
        completion scene is a modal Overlay, gameplay stops in the terminal
        state, and facts are published once each with per-visit keys."""

        root = PROJECT_ROOT / "activities" / "labirinto_magico"
        app = (root / "maze_app.py").read_text(encoding="utf-8")
        services = (root / "maze_services.py").read_text(encoding="utf-8")
        self.assertIn("CompletionOverlay(self.completion", app)
        self.assertIn("CompletionScene(self.kit", app)
        self.assertIn("self.completion.prepare(", app)
        self.assertIn("if self.state is not AppState.PLAYING:\n            return False", app)
        self.assertIsNone(
            re.search(r"Surface\(\(REFERENCE_WIDTH,\s*REFERENCE_HEIGHT\),\s*pygame\.SRCALPHA\)", app)
        )
        self.assertEqual(services.count('"maze.completed"'), 1)
        self.assertEqual(services.count('"maze.solved"'), 1)
        self.assertIn('f"labirinto:{visit_id}:completed"', services)
        self.assertEqual(app.count("self._visit_id = uuid4().hex"), 2)  # start + restart

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
