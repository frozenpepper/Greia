"""Transparent high-resolution layer (greia_platform.hires_surface)."""

from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from greia_platform import hires_surface
from greia_platform.hires_surface import RAW, hires_scale_for
from greia_platform.pygame_canvas import PygameReferenceCanvas

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def raw_rgb(surface, position):
    return tuple(RAW.get_at(surface, position))[:3]


class HiresSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def tearDown(self):
        hires_surface.deactivate()

    # -- threshold ---------------------------------------------------------
    def test_scale_threshold_and_opt_out(self):
        self.assertIsNone(hires_scale_for(1.19, {}))
        self.assertEqual(hires_scale_for(1.2, {}), 1.2)
        self.assertEqual(hires_scale_for(1.25, {}), 1.25)
        self.assertIsNone(hires_scale_for(1.25, {"GREIA_ACTIVITY_HIRES": "0"}))

    # -- surfaces ----------------------------------------------------------
    def test_logical_api_over_physical_pixels(self):
        hires_surface.activate(1.25)
        surface = pygame.Surface((100, 50))
        self.assertEqual(surface.get_size(), (100, 50))
        pw, ph = RAW.get_size(surface)
        self.assertEqual((pw, ph), (round(125.0), round(62.5)))
        self.assertTrue(isinstance(RAW.Surface((1, 1)), pygame.Surface))

    def test_draw_rect_maps_to_physical_pixels(self):
        hires_surface.activate(1.25)
        surface = pygame.Surface((40, 40))
        surface.fill((0, 0, 0))
        pygame.draw.rect(surface, RED, (10, 10, 20, 20))
        left = round(12.5)
        self.assertEqual(raw_rgb(surface, (left, left)), RED)
        self.assertEqual(raw_rgb(surface, (left - 1, left - 1)), (0, 0, 0))
        self.assertEqual(tuple(surface.get_at((15, 15)))[:3], RED)

    def test_one_pixel_lines_leave_no_empty_physical_row(self):
        hires_surface.activate(1.25)
        surface = pygame.Surface((40, 40))
        surface.fill((0, 0, 0))
        for y in range(40):
            pygame.draw.line(surface, RED, (0, y), (39, y), 1)
        width, height = RAW.get_size(surface)
        for y in range(height):
            self.assertEqual(raw_rgb(surface, (width // 2, y)), RED, f"empty row {y}")

    def test_blit_scaled_and_plain_sources(self):
        hires_surface.activate(1.25)
        target = pygame.Surface((40, 40))
        target.fill((0, 0, 0))
        sprite = pygame.Surface((8, 8))
        sprite.fill(RED)
        target.blit(sprite, (8, 8))
        self.assertEqual(raw_rgb(target, (10, 10)), RED)
        self.assertEqual(raw_rgb(target, (9, 9)), (0, 0, 0))
        self.assertEqual(raw_rgb(target, (19, 19)), RED)

        plain = RAW.Surface((8, 8))
        RAW.fill(plain, BLUE)
        other = pygame.Surface((40, 40))
        other.fill((0, 0, 0))
        other.blit(plain, (8, 8))
        self.assertEqual(raw_rgb(other, (10, 10)), BLUE)
        self.assertEqual(raw_rgb(other, (19, 19)), BLUE)  # resampled to 10x10
        self.assertEqual(raw_rgb(other, (21, 21)), (0, 0, 0))

    def test_fill_copy_and_convert_alpha_keep_logical_size(self):
        hires_surface.activate(1.25)
        surface = pygame.Surface((40, 40))
        surface.fill((0, 0, 0))
        surface.fill(RED, (0, 0, 20, 20))
        for derived in (surface.copy(), surface.convert_alpha()):
            self.assertEqual(derived.get_size(), (40, 40))
            self.assertEqual(RAW.get_size(derived), RAW.get_size(surface))
            self.assertEqual(tuple(derived.get_at((5, 5)))[:3], RED)
            self.assertEqual(tuple(derived.get_at((30, 30)))[:3], (0, 0, 0))

    def test_image_load_and_smoothscale_keep_channel_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "red.png")
            source = RAW.Surface((8, 8), pygame.SRCALPHA)
            RAW.fill(source, (255, 0, 0, 255))
            pygame.image.save(source, path)
            hires_surface.activate(1.25)
            image = pygame.image.load(path)
            self.assertEqual(image.get_size(), (8, 8))
            scaled = pygame.transform.smoothscale(image, (16, 16))
            for candidate in (image, scaled):
                r, g, b = raw_rgb(candidate, (4, 4))
                self.assertGreater(r, 200)
                self.assertLess(b, 50)

    def test_font_metrics_logical_render_physical(self):
        plain = RAW.Font(None, 20)
        hires_surface.activate(1.25)
        font = pygame.font.Font(None, 20)
        self.assertLessEqual(abs(font.get_height() - plain.get_height()), 1)
        text = font.render("Hello", True, RED)
        plain_width, plain_height = plain.size("Hello")
        raw_width, raw_height = RAW.get_size(text)
        self.assertAlmostEqual(raw_width / plain_width, 1.25, delta=0.1)
        self.assertAlmostEqual(raw_height / plain_height, 1.25, delta=0.1)

    def test_deactivate_restores_pygame(self):
        hires_surface.activate(1.25)
        self.assertIsNot(pygame.Surface, RAW.Surface)
        hires_surface.deactivate()
        self.assertIs(pygame.Surface, RAW.Surface)
        self.assertIs(pygame.draw.rect, RAW.draw.rect)

    # -- canvas ------------------------------------------------------------
    def test_canvas_hires_presents_one_to_one(self):
        target = RAW.Surface((1280, 800))
        RAW.fill(target, (10, 10, 10))
        canvas = PygameReferenceCanvas(target, hires=True)
        self.assertEqual(canvas.render_scale, 1.25)
        self.assertEqual(RAW.get_size(canvas.surface), (1280, 750))
        canvas.surface.fill(RED, (0, 0, 1024, 600))
        canvas.present(pointer=False)
        self.assertEqual(raw_rgb(target, (640, 400)), RED)
        self.assertNotEqual(raw_rgb(target, (640, 5)), RED)

    def test_canvas_below_threshold_stays_cheap(self):
        target = RAW.Surface((1100, 645))
        canvas = PygameReferenceCanvas(target, hires=True)
        self.assertEqual(canvas.render_scale, 1.0)
        self.assertEqual(RAW.get_size(canvas.surface), (1024, 600))


class HiresSiblingLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        pygame.display.set_mode((1, 1))

    def tearDown(self) -> None:
        hires_surface.deactivate()

    def test_loader_prefers_the_2x_rendition_and_keeps_the_1x_logical_size(self) -> None:
        import tempfile, os
        with tempfile.TemporaryDirectory() as raw_dir:
            base = os.path.join(raw_dir, "thing.png")
            small = hires_surface.RAW.Surface((10, 6)); small.fill((255, 0, 0))
            big = hires_surface.RAW.Surface((20, 12)); big.fill((0, 0, 255))
            pygame.image.save(small, base)
            pygame.image.save(big, os.path.join(raw_dir, "thing@2x.png"))
            hires_surface.activate(1.25)
            loaded = pygame.image.load(base)
            self.assertEqual(loaded.get_size(), (10, 6))
            self.assertEqual(hires_surface.RAW.get_size(loaded), (round(10 * 1.25), round(6 * 1.25)))
            colour = loaded.get_at((5, 3))
            self.assertGreater(colour.b, 200)
            self.assertLess(colour.r, 50)

    def test_loader_uses_the_1x_file_below_the_threshold(self) -> None:
        import tempfile, os
        with tempfile.TemporaryDirectory() as raw_dir:
            base = os.path.join(raw_dir, "thing.png")
            small = hires_surface.RAW.Surface((10, 6)); small.fill((255, 0, 0))
            pygame.image.save(small, base)
            pygame.image.save(hires_surface.RAW.Surface((20, 12)), os.path.join(raw_dir, "thing@2x.png"))
            self.assertEqual(pygame.image.load(base).get_at((5, 3))[:3], (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
