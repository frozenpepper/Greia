from __future__ import annotations

import os
from pathlib import Path
import random
import sys
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "torre_forme"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from torre_content import (  # noqa: E402
    GRID_COLS,
    GRID_ROWS,
    SHAPES,
    ShapeDefinition,
    TowerMode,
)
from torre_app import TorreApp  # noqa: E402
from torre_model import (  # noqa: E402
    BlueprintSocket,
    StepOutcome,
    GridCell,
    TorreModel,
    rotate_blocks,
)


class TorreModelUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = random.Random(42)
        self.model = TorreModel(mode=TowerMode.SLOW_FALL, rng=self.rng)

    def test_grid_initialization(self) -> None:
        self.assertEqual(len(self.model.grid), GRID_ROWS)
        self.assertEqual(len(self.model.grid[0]), GRID_COLS)
        self.assertTrue(all(cell is None for row in self.model.grid for cell in row))
        self.assertEqual(self.model.current_height, 0)
        self.assertFalse(self.model.is_celebrating)

    def test_shape_rotation(self) -> None:
        # Horizontal bar 1x2 -> vertical 2x1
        bar = ((0, 0), (1, 0))
        rotated = rotate_blocks(bar)
        self.assertEqual(rotated, ((0, 0), (0, 1)))

        # Corner L rotation
        corner = ((0, 0), (0, 1), (1, 1))
        rot1 = rotate_blocks(corner)
        self.assertTrue(all(x >= 0 and y >= 0 for x, y in rot1))
        self.assertEqual(len(rot1), 3)

        # In-game rotation method
        self.model.active_shape = SHAPES["bar_2"]
        self.model.active_blocks = SHAPES["bar_2"].blocks
        self.model.active_col = 3
        self.model.active_row = 3
        rotated_ok = self.model.rotate_active()
        self.assertTrue(rotated_ok)
        self.assertEqual(self.model.active_blocks, ((0, 0), (0, 1)))

    def test_movement_and_boundary_collision(self) -> None:
        self.model.active_shape = SHAPES["bar_2"]
        self.model.active_blocks = ((0, 0), (1, 0))
        self.model.active_col = 0
        self.model.active_row = 2

        # Cannot move further left than column 0
        self.assertFalse(self.model.move_left())
        self.assertEqual(self.model.active_col, 0)

        # Move right
        self.assertTrue(self.model.move_right())
        self.assertEqual(self.model.active_col, 1)

        # Move to rightmost column (width is 2, so max col is 6)
        for _ in range(10):
            self.model.move_right()
        self.assertEqual(self.model.active_col, GRID_COLS - 2)
        self.assertFalse(self.model.move_right())

    def test_drop_and_lock_onto_ground(self) -> None:
        self.model.active_shape = SHAPES["bar_2"]
        self.model.active_blocks = ((0, 0), (1, 0))
        self.model.active_col = 2
        self.model.active_row = 0

        # Hard drop to the bottom row
        outcome = self.model.hard_drop()
        self.assertIn("clack", outcome.audio_cues)
        self.assertIsNotNone(self.model.grid[GRID_ROWS - 1][2])
        self.assertIsNotNone(self.model.grid[GRID_ROWS - 1][3])
        self.assertEqual(self.model.current_height, 1)

    def test_line_clearing(self) -> None:
        # Fill row 9 except columns 0 and 1
        for c in range(2, GRID_COLS):
            self.model.grid[GRID_ROWS - 1][c] = GridCell((245, 158, 11), "square")

        # Place a 1x2 bar at columns 0 and 1 of row 9
        self.model.active_shape = SHAPES["bar_2"]
        self.model.active_blocks = ((0, 0), (1, 0))
        self.model.active_col = 0
        self.model.active_row = GRID_ROWS - 2

        # Dropping should lock it into row 9 and complete the row!
        outcome = self.model.hard_drop()
        self.assertIn("line_clear", outcome.audio_cues)
        self.assertEqual(outcome.lines_count, 1)
        self.assertEqual(self.model.lines_cleared, 1)
        self.assertGreaterEqual(self.model.total_stars, 1)

        # Row 9 should now be empty (compacted)
        self.assertTrue(all(cell is None for cell in self.model.grid[GRID_ROWS - 1]))

    def test_rainbow_star_special_mechanic(self) -> None:
        # Put some blocks in row 9
        self.model.grid[GRID_ROWS - 1][0] = GridCell((245, 158, 11), "square")
        self.model.grid[GRID_ROWS - 1][3] = GridCell((59, 130, 246), "bar_2")

        # Active rainbow star
        self.model.active_shape = SHAPES["rainbow_star"]
        self.model.active_blocks = SHAPES["rainbow_star"].blocks
        self.model.active_col = 4
        self.model.active_row = GRID_ROWS - 2

        outcome = self.model.hard_drop()
        self.assertIn("rainbow", outcome.audio_cues)
        # Row 9 cleared by the magic rainbow star!
        self.assertTrue(all(cell is None for cell in self.model.grid[GRID_ROWS - 1]))

    def test_free_build_snapping_and_blueprints(self) -> None:
        self.model.set_mode(TowerMode.FREE_BUILD)
        self.assertEqual(len(self.model.shelf_shapes), 3)
        self.assertTrue(len(self.model.blueprints) >= 2)

        bp = self.model.blueprints[0]
        # Set first shelf shape to match blueprint shape
        self.model.shelf_shapes[0] = SHAPES[bp.shape_id]
        self.model.selected_shelf_idx = 0

        # Click near blueprint socket (within 1 cell)
        outcome = self.model.place_free_shape(bp.anchor_col + 1, bp.anchor_row)
        self.assertIn("snap", outcome.audio_cues)
        self.assertTrue(bp.is_filled)
        self.assertGreater(self.model.score, 0)

    def test_mode_switching(self) -> None:
        self.model.set_mode(TowerMode.FREE_BUILD)
        self.assertEqual(self.model.mode, TowerMode.FREE_BUILD)
        self.assertIsNone(self.model.active_shape)

        self.model.set_mode(TowerMode.TOWER_CHALLENGE)
        self.assertEqual(self.model.mode, TowerMode.TOWER_CHALLENGE)
        self.assertIsNotNone(self.model.active_shape)
        self.assertLess(self.model.fall_interval, 1.0)

    def test_positive_celebration_closure_when_reaching_top(self) -> None:
        # Stack blocks all the way to row 0
        for r in range(GRID_ROWS):
            self.model.grid[r][0] = GridCell((245, 158, 11), "square")

        self.model.set_mode(TowerMode.SLOW_FALL)
        # When attempting to spawn or lock at top, celebration triggers!
        self.model.active_shape = SHAPES["bar_2"]
        self.model.active_blocks = ((0, 0), (1, 0))
        self.model.active_col = 0
        self.model.active_row = 0
        outcome = self.model.drop_down()

        self.assertTrue(self.model.is_celebrating)
        self.assertIn("fanfare", outcome.audio_cues)

        # Test Restart after celebration
        self.model.restart_after_celebration()
        self.assertFalse(self.model.is_celebrating)
        self.assertEqual(self.model.current_height, 0)


class TorreAppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def test_app_lifecycle_and_input_handling(self) -> None:
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from torre_app import TorreApp
        from torre_audio import TorreAudio
        from torre_renderer import TorreRenderer

        screen = pygame.display.get_surface()
        assert screen is not None

        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)

        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        renderer = TorreRenderer(typography, resources)
        audio = TorreAudio()
        rng = random.Random(101)
        model = TorreModel(mode=TowerMode.FREE_BUILD, rng=rng)

        app = TorreApp(
            screen=screen,
            canvas=canvas,
            typography=typography,
            resources=resources,
            model=model,
            renderer=renderer,
            audio=audio,
            rng=rng,
        )

        # Test pointer input on Mode 2 tab
        app._handle_pointer((renderer.mode_slow_rect.centerx, renderer.mode_slow_rect.centery))
        self.assertEqual(model.mode, TowerMode.SLOW_FALL)

        # Test steering button click (Left button)
        init_col = model.active_col
        app._handle_pointer((renderer.left_button_rect.centerx, renderer.left_button_rect.centery))
        self.assertEqual(model.active_col, max(0, init_col - 1))

        # Test drawing one frame without errors
        renderer.draw(canvas.surface, model, 0.5, 100.0)
        canvas.present()


class TorreScriptParticleTests(unittest.TestCase):
    def test_snap_and_clear_effects_work_in_direct_script_import_context(self) -> None:
        """Greia launches main.py as a script, so torre_app has no package parent."""
        from unittest.mock import Mock

        app = object.__new__(TorreApp)
        app._audio = Mock()
        app._renderer = Mock()
        app._storage = None
        outcome = StepOutcome(
            snap_coords=[(1, 2)],
            cleared_coords=[(3, 4)],
        )
        app._process_outcome(outcome)
        self.assertEqual(app._renderer.spawn_particles.call_count, 2)



if __name__ == "__main__":
    unittest.main()
