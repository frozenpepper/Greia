"""Boot art is drawn at native pixel size and only shrinks to fit."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from greia_platform import boot_animation  # noqa: E402


class _Surface:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.center = (0, 0)

    def get_width(self) -> int:
        return self.size[0]

    def get_height(self) -> int:
        return self.size[1]

    def get_size(self) -> tuple[int, int]:
        return self.size

    def get_rect(self, center: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        return (center, self.size)

    def fill(self, _color: object) -> None:
        pass

    def blit(self, surface: "_Surface", rect: object) -> None:
        self.blitted = (surface.size, rect)


class _Transform:
    @staticmethod
    def smoothscale(surface: _Surface, size: tuple[int, int]) -> _Surface:
        return _Surface(size)


class _Pygame:
    transform = _Transform()


def _drawn_size(art: tuple[int, int], screen: tuple[int, int], *, frame: bool) -> tuple[int, int]:
    target = _Surface(screen)
    draw = boot_animation.draw_frame if frame else boot_animation.draw_canvas
    draw(target, _Pygame(), _Surface(art))
    return target.blitted[0]


class NativeBootArtTests(unittest.TestCase):
    CANVAS = (1024, 600)
    FRAME = (222, 600)

    def test_never_upscaled_on_larger_screens(self) -> None:
        for screen in ((1280, 800), (1920, 1080)):
            self.assertEqual(_drawn_size(self.CANVAS, screen, frame=False), self.CANVAS)
            self.assertEqual(_drawn_size(self.FRAME, screen, frame=True), self.FRAME)

    def test_centred(self) -> None:
        target = _Surface((1280, 800))
        boot_animation.draw_frame(target, _Pygame(), _Surface(self.FRAME))
        self.assertEqual(target.blitted[1], ((640, 400), self.FRAME))

    def test_exact_fit_is_native(self) -> None:
        self.assertEqual(_drawn_size(self.CANVAS, (1024, 600), frame=False), self.CANVAS)
        self.assertEqual(_drawn_size(self.FRAME, (1024, 600), frame=True), self.FRAME)

    def test_shrinks_only_when_it_does_not_fit(self) -> None:
        self.assertEqual(_drawn_size(self.FRAME, (1024, 480), frame=True), (178, 480))
        self.assertEqual(_drawn_size(self.CANVAS, (800, 480), frame=False), (800, 469))
        self.assertEqual(boot_animation.fitted_size(self.FRAME, 1080), self.FRAME)
        self.assertEqual(boot_animation.fitted_size(self.FRAME, 300), (111, 300))


if __name__ == "__main__":
    unittest.main()
