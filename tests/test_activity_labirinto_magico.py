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

    def test_difficulty_levels_match_declared_d1_to_d6_scope(self) -> None:
        # The release roster is six levels (manifest difficulty 1-6); the
        # titan/colossal/infinite sizes were retired because their cells were
        # unreadable on the 1024x600 reference surface.
        difficulty_ids = [d["id"] for d in DIFFICULTIES]
        self.assertEqual(
            difficulty_ids,
            ["small", "medium", "large", "giant", "epic", "master"],
        )
        for retired in ("titan", "colossal", "infinite"):
            self.assertNotIn(retired, difficulty_ids)

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

    def test_resolve_click_direction_cardinal_and_fallbacks(self) -> None:
        # 1. Straight horizontal corridor
        grid = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        exit_pos = {"r": 1, "c": 5}
        # Player at (1, 1), clicks at (1, 4) -> should resolve to (0, 1) (Right)
        dr, dc = MazeEngine.resolve_click_direction(grid, 1, 1, 1, 4, exit_pos)
        self.assertEqual((dr, dc), (0, 1))

        # Player at (1, 4), clicks at (1, 1) -> should resolve to (0, -1) (Left)
        dr, dc = MazeEngine.resolve_click_direction(grid, 1, 4, 1, 1, exit_pos)
        self.assertEqual((dr, dc), (0, -1))

        # Click on same cell -> (0, 0)
        dr, dc = MazeEngine.resolve_click_direction(grid, 1, 1, 1, 1, exit_pos)
        self.assertEqual((dr, dc), (0, 0))

        # 2. Corner: player at (1, 1), right is blocked by wall, but down is open
        grid_corner = [
            [1, 1, 1, 1],
            [1, 0, 1, 1],
            [1, 0, 0, 1],
            [1, 1, 1, 1],
        ]
        # Click at (1, 3) (Rightwards, but right is blocked -> falls back to Down (1, 0))
        dr, dc = MazeEngine.resolve_click_direction(grid_corner, 1, 1, 1, 3, {"r": 2, "c": 2})
        self.assertEqual((dr, dc), (1, 0))

    def test_largest_difficulty_grid_size_and_complexity(self) -> None:
        largest = next(d for d in DIFFICULTIES if d["id"] == "master")
        self.assertGreaterEqual(largest["cols"], 59)
        self.assertGreaterEqual(largest["rows"], 29)
        self.assertGreaterEqual(largest["stars"], 20)
        sizes = [(d["cols"], d["rows"], d["stars"]) for d in DIFFICULTIES]
        self.assertEqual(sizes, sorted(sizes))

    def test_maze_renderer_computes_fullscreen_viewport(self) -> None:
        from greia_platform.activity_ui import ChildUiMetrics
        from activities.labirinto_magico.maze_renderer import MazeRenderer

        renderer = MazeRenderer()
        metrics = ChildUiMetrics.for_size(1024, 600)
        # Small maze
        cs, ox, oy, rect = renderer.compute_maze_viewport(1024, 600, 13, 9, metrics)
        self.assertGreaterEqual(cs, 50)
        self.assertGreater(rect.width, 600)
        self.assertGreater(rect.height, 400)
        self.assertGreaterEqual(rect.top, 76)  # Below platform chrome

        # Largest shipped maze
        largest = next(d for d in DIFFICULTIES if d["id"] == "master")
        cs_inf, ox_inf, oy_inf, rect_inf = renderer.compute_maze_viewport(
            1024, 600, largest["cols"], largest["rows"], metrics
        )
        self.assertGreaterEqual(cs_inf, 10)
        self.assertGreater(rect_inf.width, 900)
        self.assertGreater(rect_inf.height, 400)

    def test_bake_static_maze_creates_surface(self) -> None:
        import pygame
        from activities.labirinto_magico.maze_art import MazeArt

        pygame.init()
        grid = [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1],
        ]
        surf = MazeArt.bake_static_maze(grid, BIOMES[0], cs=20, maze_w=5, maze_h=3)
        self.assertEqual(surf.get_size(), (100, 60))


if __name__ == "__main__":
    unittest.main()
