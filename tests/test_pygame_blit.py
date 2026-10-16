from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.pygame_blit import FadeSteps, HudOverlay, PreparedSurfaces, is_rle, prepare_static


def _sprite(size=(40, 30)) -> pygame.Surface:
    """A sprite with opaque, transparent and translucent pixels."""

    sprite = pygame.Surface(size, pygame.SRCALPHA)
    sprite.fill((0, 0, 0, 0))
    pygame.draw.circle(sprite, (200, 40, 90, 255), (size[0] // 2, size[1] // 2), min(size) // 3)
    pygame.draw.rect(sprite, (30, 160, 220, 120), (0, 0, size[0], 6))
    return sprite


def _max_diff(a: pygame.Surface, b: pygame.Surface) -> int:
    worst = 0
    for x in range(a.get_width()):
        for y in range(a.get_height()):
            pa, pb = a.get_at((x, y)), b.get_at((x, y))
            worst = max(worst, abs(pa.r - pb.r), abs(pa.g - pb.g), abs(pa.b - pb.b))
    return worst


class PygameBlitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        pygame.display.set_mode((64, 48))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.display.quit()

    def _background(self) -> pygame.Surface:
        target = pygame.Surface((48, 36))
        target.fill((90, 200, 120))
        return target

    def test_prepare_static_requests_rle_and_blits_the_same_pixels(self) -> None:
        sprite = _sprite()
        prepared = prepare_static(sprite)
        self.assertIsNot(prepared, sprite)
        self.assertTrue(is_rle(prepared))
        self.assertFalse(is_rle(sprite), "the shared source must stay untouched")
        direct, fast = self._background(), self._background()
        direct.blit(sprite, (4, 3))
        fast.blit(prepared, (4, 3))
        self.assertLessEqual(_max_diff(direct, fast), 1)
        fast.blit(prepared, (4, 3))  # encoded surface blits again unchanged
        direct.blit(sprite, (4, 3))
        self.assertLessEqual(_max_diff(direct, fast), 1)

    def test_for_target_encodes_only_for_opaque_targets(self) -> None:
        fast = PreparedSurfaces(max_entries=4)
        sprite = _sprite()
        opaque = self._background()
        prepared = fast.for_target(sprite, opaque)
        self.assertTrue(is_rle(prepared))
        self.assertIs(fast.for_target(sprite, opaque), prepared)
        # RLE alpha blits write opaque destination alpha: never onto SRCALPHA.
        overlay = pygame.Surface((48, 36), pygame.SRCALPHA)
        self.assertIs(fast.for_target(sprite, overlay), sprite)
        direct, encoded = pygame.Surface((48, 36), pygame.SRCALPHA), pygame.Surface((48, 36), pygame.SRCALPHA)
        direct.blit(sprite, (0, 0))
        encoded.blit(prepared, (0, 0))
        translucent = [(x, y) for y in range(30) for x in range(40) if 0 < sprite.get_at((x, y))[3] < 255]
        if translucent:
            point = translucent[0]
            self.assertNotEqual(direct.get_at(point)[3], encoded.get_at(point)[3], "the SDL caveat this guards")
        double = object()
        self.assertIs(fast.for_target(double, opaque), double)

    def test_prepare_static_keeps_opaque_surfaces_opaque_and_colorkeys(self) -> None:
        opaque = pygame.Surface((10, 10))
        opaque.fill((1, 2, 3))
        prepared = prepare_static(opaque)
        self.assertFalse(prepared.get_flags() & pygame.SRCALPHA)
        self.assertFalse(is_rle(prepared))
        keyed = pygame.Surface((10, 10))
        keyed.fill((255, 0, 255))
        keyed.set_colorkey((255, 0, 255))
        prepared = prepare_static(keyed)
        self.assertEqual(tuple(prepared.get_colorkey())[:3], (255, 0, 255))
        self.assertTrue(is_rle(prepared))

    def test_fade_steps_bake_alpha_instead_of_set_alpha(self) -> None:
        sprite = _sprite()
        steps = FadeSteps(sprite, steps=4)
        self.assertIsNone(steps.at(0.0))
        self.assertIsNone(steps.at(0.1))
        full = steps.at(1.0)
        assert full is not None
        self.assertTrue(is_rle(full))
        reference, fast = self._background(), self._background()
        reference.blit(sprite, (0, 0))
        fast.blit(full, (0, 0))
        self.assertLessEqual(_max_diff(reference, fast), 1)
        half = steps.at(0.5)
        assert half is not None
        modulated = sprite.copy()
        modulated.set_alpha(128)
        reference, fast = self._background(), self._background()
        reference.blit(modulated, (0, 0))
        fast.blit(half, (0, 0))
        self.assertLessEqual(_max_diff(reference, fast), 3)
        self.assertIs(steps.at(0.52), half, "levels are cached")
        self.assertEqual(sprite.get_alpha(), 255, "the source is never modulated")
        with self.assertRaises(ValueError):
            FadeSteps(sprite, steps=0)

    def test_hud_overlay_recomposes_only_when_key_size_or_invalidation_changes(self) -> None:
        calls: list[tuple[int, int]] = []

        def render(target: pygame.Surface) -> None:
            calls.append(target.get_size())
            pygame.draw.rect(target, (250, 250, 250), (2, 2, 10, 6))
            target.blit(_sprite((12, 10)), (20, 4))

        hud = HudOverlay()
        scene = self._background()
        self.assertTrue(hud.draw(scene, ("a",), render))
        self.assertFalse(hud.draw(scene, ("a",), render))
        self.assertTrue(hud.draw(scene, ("b",), render))
        hud.invalidate()
        self.assertTrue(hud.draw(scene, ("b",), render))
        self.assertTrue(hud.draw(scene, ("b",), render, stale=True))
        self.assertFalse(hud.draw(scene, ("b",), render))
        resized = pygame.Surface((60, 40))
        self.assertTrue(hud.draw(resized, ("b",), render), "a new target size recomposes")
        self.assertEqual(calls[-1], (60, 40))
        self.assertEqual(hud.compositions, len(calls))
        hud.clear()
        self.assertTrue(hud.draw(resized, ("b",), render))

    def test_prepared_surfaces_mirror_by_identity_and_stay_bounded(self) -> None:
        fast = PreparedSurfaces(max_entries=2, max_pixels=10_000)
        first, second, third = _sprite(), _sprite(), _sprite()
        mirrored = fast(first)
        assert mirrored is not None
        self.assertIsNot(mirrored, first)
        self.assertTrue(is_rle(mirrored))
        self.assertIs(fast(first), mirrored, "the same source maps to the same copy")
        fast(second)
        fast(third)
        self.assertEqual(len(fast), 2, "entry bound")
        self.assertIsNot(fast(first), mirrored, "evicted sources are prepared again")
        self.assertIsNone(fast(None))
        opaque = pygame.Surface((5, 5))
        self.assertIs(fast(opaque), opaque, "opaque surfaces need no copy")
        big = PreparedSurfaces(max_entries=10, max_pixels=1_500)
        big(_sprite())
        big(_sprite())
        self.assertEqual(len(big), 1, "pixel bound")
        self.assertLessEqual(big.cached_pixels, 1_500)
        big.clear()
        self.assertEqual((len(big), big.cached_pixels), (0, 0))
        sprite = _sprite()
        self.assertIsNone(fast.faded(sprite, 0.0))
        half = fast.faded(sprite, 0.5)
        assert half is not None
        self.assertTrue(is_rle(half))
        self.assertIs(fast.faded(sprite, 0.52), half)
        self.assertIs(fast.faded(sprite, 1.0), fast(sprite))
        self.assertEqual(sprite.get_alpha(), 255)
        with self.assertRaises(ValueError):
            PreparedSurfaces(max_entries=0)

    def test_hud_overlay_matches_drawing_directly(self) -> None:
        def render(target: pygame.Surface) -> None:
            pygame.draw.rect(target, (250, 250, 250), (2, 2, 10, 6))
            target.blit(_sprite((12, 10)), (20, 4))

        direct, cached = self._background(), self._background()
        render(direct)
        HudOverlay().draw(cached, 1, render)
        self.assertLessEqual(_max_diff(direct, cached), 1)


if __name__ == "__main__":
    unittest.main()
