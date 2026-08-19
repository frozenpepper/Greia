from __future__ import annotations

import unittest
from pathlib import Path
import tomllib

from activities.labirinto_magico.main import (
    BIOMES,
    DIFFICULTIES,
    HEROES,
    LabyrinthAudio,
    MazeEngine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = PROJECT_ROOT / "activities" / "labirinto_magico"


class LabirintoMagicoTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.labirinto-magico")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

    def test_locales_contain_required_strings(self) -> None:
        import json
        it_json = json.loads((ACTIVITY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        en_json = json.loads((ACTIVITY_DIR / "locales" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("btn.hint", it_json["strings"])
        self.assertIn("victory.title", it_json["strings"])
        self.assertIn("activity.title", en_json["strings"])
        self.assertIn("btn.hint", en_json["strings"])

    def test_maze_generator_creates_solvable_perfect_maze(self) -> None:
        for diff in DIFFICULTIES:
            grid, entrance, exit_pos, collectibles = MazeEngine.generate(
                diff["cols"], diff["rows"], diff["stars"]
            )
            rows = len(grid)
            cols = len(grid[0])
            self.assertGreaterEqual(cols, diff["cols"])
            self.assertGreaterEqual(rows, diff["rows"])
            self.assertEqual(grid[entrance["r"]][entrance["c"]], 0)
            self.assertEqual(grid[exit_pos["r"]][exit_pos["c"]], 0)

            # BFS must find a solution path from entrance to exit
            path = MazeEngine.solve_bfs(
                grid, entrance["r"], entrance["c"], exit_pos["r"], exit_pos["c"]
            )
            self.assertTrue(len(path) >= 2)
            self.assertEqual(path[0], (entrance["r"], entrance["c"]))
            self.assertEqual(path[-1], (exit_pos["r"], exit_pos["c"]))

            # Verify collectibles are positioned on floor tiles
            self.assertEqual(len(collectibles), diff["stars"])
            for star in collectibles:
                self.assertEqual(grid[star["r"]][star["c"]], 0)

    def test_difficulty_levels_contain_large_and_colossal_sizes(self) -> None:
        self.assertGreaterEqual(len(DIFFICULTIES), 8)
        difficulty_ids = [d["id"] for d in DIFFICULTIES]
        self.assertIn("small", difficulty_ids)
        self.assertIn("medium", difficulty_ids)
        self.assertIn("large", difficulty_ids)
        self.assertIn("giant", difficulty_ids)
        self.assertIn("epic", difficulty_ids)
        self.assertIn("master", difficulty_ids)
        self.assertIn("titan", difficulty_ids)
        self.assertIn("colossal", difficulty_ids)
        self.assertIn("infinite", difficulty_ids)

    def test_biomes_and_heroes_metadata_integrity(self) -> None:
        self.assertEqual(len(BIOMES), 4)
        self.assertEqual(len(HEROES), 6)
        for b in BIOMES:
            self.assertIn("bg", b)
            self.assertIn("wall", b)
            self.assertIn("path", b)
            self.assertIn("hint", b)
        for h in HEROES:
            self.assertIn("id", h)
            self.assertIn("color", h)

    def test_compute_slide_path_stops_at_wall_and_decision_points(self) -> None:
        # 1. Straight corridor: stops at wall/exit
        grid_straight = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        path = MazeEngine.compute_slide_path(grid_straight, 1, 1, 0, 1, {"r": 1, "c": 5})
        self.assertEqual(path, [(1, 2), (1, 3), (1, 4), (1, 5)])

        # 2. T-junction: stops at crossing where choice exists
        grid_junction = [
            [1, 1, 1, 0, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        path_j = MazeEngine.compute_slide_path(grid_junction, 1, 1, 0, 1, {"r": 1, "c": 5})
        self.assertEqual(path_j, [(1, 2), (1, 3)])

        # 3. Blocked direction: returns empty
        path_blocked = MazeEngine.compute_slide_path(grid_straight, 1, 1, -1, 0, {"r": 1, "c": 5})
        self.assertEqual(path_blocked, [])

    def test_audio_synthesizer_initializes(self) -> None:
        audio = LabyrinthAudio()
        self.assertIsNotNone(audio)


if __name__ == "__main__":
    unittest.main()
