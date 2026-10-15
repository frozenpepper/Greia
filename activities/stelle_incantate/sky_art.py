"""Prepared, bounded art for Stelle Incantate.

Everything is loaded, scaled and composed once. The backdrop is the shared
``bg.night_sky`` layers (hills lowered so the sky is the stage) plus a fixed
field of tiny distant dots, composed into one opaque surface. Stars are the
shared ``ui.control.star`` art (gold = lit, pale = not yet) with a cocoa
numeral; Leo's poses come from the canonical cast and FX from the shared
``fx.*`` set. Figure pictures are this package's SVG renditions
(``assets/source/figures`` -> ``assets/runtime/figures``), drawn in the sky's
own pixel space. Numerals, the goal strip, cards, the name plate and the fact
bubble are painted with the shared control-kit recipe and cached in small
bounded dictionaries. Drawing code only blits these surfaces.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import random
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter
from greia_platform.typography import FontRole

if __package__:
    from .sky_content import SKY_SIZE, STAR_POP_SIZE, STAR_SIZE
else:
    from sky_content import SKY_SIZE, STAR_POP_SIZE, STAR_SIZE

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
FIGURE_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime" / "figures"

HILLS_SHIFT: Final[int] = 150
DOTS: Final[int] = 70
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 72,
    "star_burst": 220,
    "firework": 200,
    "shooting_star": 150,
}
MINI_STAR: Final[int] = 46
GOAL_ARROW: Final[int] = 26
CARD_NUMERAL: Final[int] = 64
MAX_FACES: Final[int] = 48
MAX_PICTURES: Final[int] = 3

COCOA: Final[tuple[int, int, int]] = (61, 44, 31)
INK: Final[tuple[int, int, int]] = (75, 55, 47)
LINE_GLOW: Final[tuple[int, int, int]] = (255, 231, 166)
CREAM: Final[tuple[int, int, int]] = (255, 251, 235)
SUNSHINE: Final[tuple[int, int, int]] = (255, 194, 52)
CORAL: Final[tuple[int, int, int]] = (244, 111, 97)


class _Bounded(OrderedDict):
    """Tiny LRU dictionary for prepared surfaces."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit

    def remember(self, key, value):
        self[key] = value
        self.move_to_end(key)
        while len(self) > self.limit:
            self.popitem(last=False)
        return value

    def recall(self, key):
        value = self.get(key)
        if value is not None:
            self.move_to_end(key)
        return value


class SkyArt:
    """Own every prepared surface the renderer blits (bounded, built once)."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        figure_dir: Path = FIGURE_DIR,
        size: tuple[int, int] = (1024, 600),
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=40)
        self._figure_dir = figure_dir
        self.background = self._compose_background(size)
        self.glow = _glow(STAR_SIZE + 26)
        self.miss_ring = _ring(STAR_POP_SIZE + 6, CORAL)
        self._faces: _Bounded = _Bounded(MAX_FACES)
        self._pictures: _Bounded = _Bounded(MAX_PICTURES)
        self._goals: _Bounded = _Bounded(6)
        self._plates: _Bounded = _Bounded(4)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    # -- stars --------------------------------------------------------------

    def star_face(self, number: int | None, *, lit: bool, size: int = STAR_SIZE) -> pygame.Surface:
        """A star with its numeral (``None`` = the star that lost its number)."""

        key = (number, lit, size)
        cached = self._faces.recall(key)
        if cached is not None:
            return cached
        body = self._art.image("ui.control.star", size, variant="default" if lit else "off")
        face = body.copy() if body is not None else self._painter.star(size, filled=lit).copy()
        if number is not None:
            digits = len(str(number))
            label = self._painter.label(
                str(number), int(size * (0.42 if digits == 1 else 0.37)), COCOA, role=FontRole.DISPLAY
            )
            # The five-point star's visual centre sits a little below its box centre.
            face.blit(label, label.get_rect(center=(size // 2, int(size * 0.56))))
        return self._faces.remember(key, face)

    def preload(self, numbers: tuple[int | None, ...]) -> None:
        """Prepare one figure's faces (lit, unlit, pop) before it appears."""

        for number in numbers:
            for lit in (False, True):
                for size in (STAR_SIZE, STAR_POP_SIZE):
                    self.star_face(number, lit=lit, size=size)

    def mini_star(self, number: int | None, *, lit: bool) -> pygame.Surface:
        return self.star_face(number, lit=lit, size=MINI_STAR)

    # -- pictures -----------------------------------------------------------

    def picture(self, figure_id: str) -> pygame.Surface | None:
        """The figure's illustration in sky-local space (``None`` when missing)."""

        if figure_id in self._pictures:
            return self._pictures.recall(figure_id)
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._figure_dir / f"{figure_id}.png"))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            if image.get_size() != SKY_SIZE:
                image = pygame.transform.smoothscale(image, SKY_SIZE)
        except (OSError, pygame.error):
            image = None
        self._pictures.remember(figure_id, image)
        return image

    # -- goal strip, cards, plates -------------------------------------------

    def goal_icon(self, numbers: tuple[int, int, int], given: bool) -> pygame.Surface:
        """Three mini stars with arrows: where to start and which way to count."""

        key = (numbers, given)
        cached = self._goals.recall(key)
        if cached is not None:
            return cached
        stars = [self.mini_star(number, lit=given and index == 0) for index, number in enumerate(numbers)]
        width = MINI_STAR * 3 + GOAL_ARROW * 2 + 16
        icon = pygame.Surface((width, MINI_STAR), pygame.SRCALPHA)
        x = 0
        for index, star in enumerate(stars):
            icon.blit(star, (x, 0))
            x += MINI_STAR
            if index < 2:
                _chevron(icon, (x + 8 + GOAL_ARROW // 2, MINI_STAR // 2 + 2), GOAL_ARROW)
                x += GOAL_ARROW + 8
        return self._goals.remember(key, icon)

    def card_numeral(self, number: int) -> pygame.Surface:
        return self._painter.label(str(number), CARD_NUMERAL, COCOA, role=FontRole.DISPLAY)

    def name_plate(self, text: str) -> pygame.Surface:
        cached = self._plates.recall(("name", text))
        if cached is not None:
            return cached
        label = self._painter.label(text, 34, self._painter.theme.text, max_width=560)
        body = self._painter.body(BodyShape.PANEL, (label.get_width() + 56, label.get_height() + 24), CREAM, lip=4)
        plate = body.copy()
        plate.blit(label, label.get_rect(center=(plate.get_width() // 2, (plate.get_height() - 4) // 2)))
        return self._plates.remember(("name", text), plate)

    def fact_bubble(self, text: str, width: int = 560) -> pygame.Surface:
        cached = self._plates.recall(("fact", text))
        if cached is not None:
            return cached
        color = self._painter.theme.text
        size = 24
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if self._painter.label(candidate, size, color, role=FontRole.TITLE).get_width() <= width - 48:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        rendered = [self._painter.label(line, size, color, role=FontRole.TITLE) for line in lines[:3]]
        height = sum(item.get_height() for item in rendered) + 28
        body = self._painter.body(BodyShape.PANEL, (width, height + 4), CREAM, lip=4)
        bubble = body.copy()
        y = 14
        for item in rendered:
            bubble.blit(item, item.get_rect(midtop=(width // 2, y)))
            y += item.get_height()
        return self._plates.remember(("fact", text), bubble)

    # -- FX + cast ----------------------------------------------------------------

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 128)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    # -- backdrop -----------------------------------------------------------------

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        """Shared night-sky layers with the hills lowered (one opaque surface)."""

        surface = pygame.Surface(size)
        # A throwaway loader: the full-screen layers are released once the
        # opaque composite exists.
        loader = ControlArt(max_entries=5)

        def layer(name: str) -> pygame.Surface | None:
            return loader.image(f"bg.night_sky.{name}", size)

        sky = layer("sky")
        if sky is None:
            surface.fill((37, 59, 89))
        else:
            surface.blit(sky, (0, 0))
        # Tiny distant dots (never star-shaped, so they cannot be mistaken for
        # a numbered star) keep the big sky alive.
        rng = random.Random(11)
        for _ in range(DOTS):
            x = rng.randrange(8, size[0] - 8)
            y = rng.randrange(8, int(size[1] * 0.66))
            shade = rng.choice(((207, 214, 236), (236, 228, 205), (180, 190, 222)))
            radius = 1 if rng.random() < 0.7 else 2
            pygame.draw.circle(surface, shade, (x, y), radius)
        # Lowered hills: the ground layer still reaches below the canvas edge.
        for name in ("far", "mid", "ground"):
            image = layer(name)
            if image is not None:
                surface.blit(image, (0, HILLS_SHIFT))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


def _glow(size: int) -> pygame.Surface:
    """Soft warm halo behind a lit star (concentric alpha discs, built once)."""

    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    centre = (size // 2, size // 2)
    for radius, alpha in ((size // 2, 22), (size // 2 - 7, 30), (size // 2 - 14, 40)):
        pygame.draw.circle(glow, (*SUNSHINE, alpha), centre, max(1, radius))
    return glow


def _ring(size: int, colour: tuple[int, int, int]) -> pygame.Surface:
    """"Not this one" ring around a mistaken star (ink | colour | ink)."""

    ring = pygame.Surface((size, size), pygame.SRCALPHA)
    centre = (size // 2, size // 2)
    pygame.draw.circle(ring, INK, centre, size // 2)
    pygame.draw.circle(ring, colour, centre, size // 2 - 2)
    pygame.draw.circle(ring, INK, centre, size // 2 - 7)
    pygame.draw.circle(ring, (0, 0, 0, 0), centre, size // 2 - 9)
    return ring


def _chevron(surface: pygame.Surface, centre: tuple[int, int], size: int) -> None:
    cx, cy = centre
    half = size // 2
    points = [(cx - half // 2, cy - half), (cx + half // 2 + 2, cy), (cx - half // 2, cy + half)]
    pygame.draw.lines(surface, INK, False, points, 8)
    pygame.draw.lines(surface, (243, 154, 56), False, points, 4)


__all__ = ["COCOA", "INK", "LINE_GLOW", "SkyArt"]
