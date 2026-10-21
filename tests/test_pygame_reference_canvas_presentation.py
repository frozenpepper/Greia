"""PygameReferenceCanvas on displays that are not the 1024x600 reference.

Regression contract for the installed 1280x800 Aspire: the CONTAIN bands must
never keep stale Shell/launch-card pixels or Greia pointer trails, non-integer
scales must not use nearest-neighbour row duplication, and pointer/region
updates must stay cheap (no full-frame re-scale) when the frame is scaled.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from greia_platform import activity_ui
from greia_platform.pygame_canvas import PygameReferenceCanvas

STALE = (255, 0, 255)
SCENE = (60, 140, 220)
POINTER = (255, 0, 0)


def scripted_pointer(positions):
    """Replace the mouse-driven pointer with a scripted sequence of positions."""

    iterator = iter(positions)

    def draw(surface, pos=None, **_):
        x, y = next(iterator)
        rect = pygame.Rect(x - 6, y - 6, 12, 12)
        surface.fill(POINTER, rect)
        return rect

    return draw


def band_pixels(surface: pygame.Surface, colour) -> int:
    width, height = surface.get_size()
    count = 0
    for y in list(range(0, 25)) + list(range(height - 25, height)):
        for x in range(0, width, 4):
            if surface.get_at((x, y))[:3] == colour:
                count += 1
    return count


class ReferenceCanvasPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.display.quit()

    def canvas(self, size: tuple[int, int]) -> tuple[pygame.Surface, PygameReferenceCanvas]:
        target = pygame.Surface(size)
        target.fill(STALE)
        canvas = PygameReferenceCanvas(target)
        canvas.surface.fill(SCENE)
        return target, canvas

    def test_bands_never_keep_stale_pixels(self) -> None:
        for size in ((1280, 800), (1366, 768), (1920, 1080), (1280, 1024), (800, 480)):
            with self.subTest(size=size):
                target, canvas = self.canvas(size)
                canvas.present(pointer=False)
                width, height = size
                stale = sum(
                    1
                    for x in range(0, width, 7)
                    for y in range(0, height, 7)
                    if target.get_at((x, y))[:3] == STALE
                )
                self.assertEqual(stale, 0)

    def test_band_continues_the_scene_edge_slightly_shaded(self) -> None:
        target, canvas = self.canvas((1280, 800))
        canvas.present(pointer=False)
        band = target.get_at((640, 10))[:3]
        self.assertNotEqual(band, STALE)
        for channel, scene in zip(band, SCENE):
            self.assertLessEqual(channel, scene)
            self.assertGreater(channel, scene * 0.7)

    def test_explicit_clear_colours_the_bands(self) -> None:
        target, canvas = self.canvas((1280, 800))
        canvas.present(clear=(1, 2, 3), pointer=False)
        self.assertEqual(target.get_at((640, 5))[:3], (1, 2, 3))

    def test_pointer_moving_through_a_band_leaves_no_trail(self) -> None:
        target, canvas = self.canvas((1280, 800))
        path = [(100 + 60 * step, 12) for step in range(12)]
        with mock.patch.object(activity_ui, "draw_activity_pointer", scripted_pointer(path)):
            canvas.present()
            for _ in path[1:]:
                self.assertTrue(canvas.present_pointer())
        # Only the final 12x12 pointer square remains in the bands.
        self.assertLessEqual(band_pixels(target, POINTER), 12 * 12 // 4 + 4)
        self.assertEqual(target.get_at(path[0])[:3] != POINTER, True)

    def test_pointer_refresh_never_rescales_the_frame(self) -> None:
        target, canvas = self.canvas((1280, 800))
        positions = [(500, 400)] * 6
        with mock.patch.object(activity_ui, "draw_activity_pointer", scripted_pointer(positions)):
            canvas.present()
            with mock.patch.object(pygame.transform, "smoothscale") as smooth, mock.patch.object(
                pygame.transform, "scale"
            ) as nearest:
                for _ in range(5):
                    canvas.present_pointer()
        smooth.assert_not_called()
        nearest.assert_not_called()

    def test_non_integer_scale_resamples_smoothly(self) -> None:
        target, canvas = self.canvas((1280, 800))
        with mock.patch.object(
            pygame.transform, "smoothscale", wraps=pygame.transform.smoothscale
        ) as smooth:
            canvas.present(pointer=False)
        self.assertIn(((canvas.surface, (1280, 750)), {}), [tuple(c) for c in smooth.call_args_list])

    def test_whole_number_scale_keeps_crisp_pixels(self) -> None:
        target, canvas = self.canvas((2048, 1200))
        with mock.patch.object(pygame.transform, "scale", wraps=pygame.transform.scale) as nearest:
            canvas.present(pointer=False)
        self.assertTrue(any(call.args[1] == (2048, 1200) for call in nearest.call_args_list))

    def test_scaled_region_update_matches_a_full_present(self) -> None:
        target, canvas = self.canvas((1280, 800))
        canvas.present(pointer=False)
        region = pygame.Rect(400, 200, 64, 48)
        canvas.surface.fill((250, 200, 40), region)
        with mock.patch.object(activity_ui, "draw_activity_pointer", return_value=None):
            self.assertTrue(canvas.present_regions([region]))
        reference, full = self.canvas((1280, 800))
        full.surface.fill((250, 200, 40), region)
        full.present(pointer=False)
        centre = canvas.mapper.point(*region.center)
        self.assertEqual(target.get_at(centre)[:3], reference.get_at(centre)[:3])
        outside = canvas.mapper.point(100, 100)
        self.assertEqual(target.get_at(outside)[:3], reference.get_at(outside)[:3])

    def test_reference_display_is_untouched_by_band_logic(self) -> None:
        target, canvas = self.canvas((1024, 600))
        with mock.patch.object(pygame.transform, "smoothscale") as smooth:
            canvas.present(pointer=False)
        smooth.assert_not_called()
        self.assertEqual(target.get_at((0, 0))[:3], SCENE)


if __name__ == "__main__":
    unittest.main()
