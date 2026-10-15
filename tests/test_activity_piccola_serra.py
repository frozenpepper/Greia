"""Serra domain progression tests without display, audio or persistence fixtures."""

from __future__ import annotations

import unittest

from activities.piccola_serra.serra_model import SerraModel
from activities.piccola_serra.serra_content import TARGET_HARVEST


class SerraGrowthTests(unittest.TestCase):
    def test_each_plant_needs_seed_water_sun_water_then_harvest(self) -> None:
        model = SerraModel()
        for stage, tool in enumerate((0, 1, 2, 1, 3)):
            self.assertEqual(model.pots[0]["stage"], stage)
            self.assertIsNone(model.apply_tool(0, (tool + 1) % 4, 0))
            self.assertEqual(model.pots[0]["stage"], stage)
            self.assertIsNotNone(model.apply_tool(0, tool, 0))
        self.assertEqual(model.pots[0]["stage"], 0)
        self.assertEqual(model.harvest_count, 1)

    def test_harvest_completion_only_after_real_growth_cycles(self) -> None:
        model = SerraModel()
        for number in range(TARGET_HARVEST):
            for tool in (0, 1, 2, 1):
                self.assertIsNotNone(model.apply_tool(0, tool, number))
            result = model.apply_tool(0, 3, number)
            self.assertIsNotNone(result)
            self.assertEqual(bool(result.get("victory")), number + 1 == TARGET_HARVEST)
        self.assertTrue(model.is_victory)
        self.assertEqual(model.harvest_count, TARGET_HARVEST)
        model.reset()
        self.assertFalse(model.is_victory)
        self.assertEqual(model.harvest_count, 0)

def _pointer_pixel_is_drawn(target, position) -> bool:
    # draw_activity_pointer's default body colour, 8 px right of the hot spot.
    return tuple(target.get_at((position[0] + 8, position[1])))[:3] == (254, 202, 87)


class PiccolaSerraPointerTests(unittest.TestCase):
    """The OS cursor is hidden; the platform canvas must draw Greia's pointer."""

    def test_pointer_is_drawn_while_playing_and_follows_on_completion(self) -> None:
        import os
        from unittest import mock

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        from activities.piccola_serra.serra_app import SerraApp

        pygame.init()
        pygame.display.set_mode((1024, 600))
        app = SerraApp()
        target = app.canvas.target
        with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
            "pygame.mouse.get_pos", return_value=(300, 200)
        ):
            app._draw(0.0)
            self.assertTrue(_pointer_pixel_is_drawn(target, (300, 200)))
        app.model.is_victory = True
        for position in ((420, 260), (640, 340)):
            with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
                "pygame.mouse.get_pos", return_value=position
            ):
                app._present_completion()
                self.assertTrue(_pointer_pixel_is_drawn(target, position))


if __name__ == "__main__":
    unittest.main()
