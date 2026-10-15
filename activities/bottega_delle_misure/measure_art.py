"""Prepared, bounded art for La Bottega delle Misure.

Everything is loaded, scaled or painted once. The backdrop is the shared
``bg.indoor_room.wall_workshop`` + ``floor_wood`` layers with this package's
workbench composed into one opaque surface. Leo's poses come from the
canonical cast and FX from the shared ``fx.*`` set. Boards, shelves, the start
stop, the unit block, the block crate, the job card and the toy balance are
this package's SVG renditions
(``assets/source`` -> ``assets/runtime``, rendered at display size). Parcels,
the job-card pictograms, numerals and demonstration marks are painted with
the shared control-kit recipe (two-stop fill, one ink contour, one highlight)
and kept in small bounded caches. Drawing code only blits these surfaces.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.typography import FontRole

if __package__:
    from .measure_content import (
        BEAM_SIZE,
        BENCH_SIZE,
        BENCH_TOP,
        BOARD_SIZE,
        CRATE_SIZE,
        GOAL_PICTURE,
        PAN_SIZE,
        SIGN_SIZE,
        STAND_SIZE,
        STOP_SIZE,
        TILT_DEGREES,
        UNIT,
    )
    from .measure_model import Goal, TaskKind
else:
    from measure_content import (
        BEAM_SIZE,
        BENCH_SIZE,
        BENCH_TOP,
        BOARD_SIZE,
        CRATE_SIZE,
        GOAL_PICTURE,
        PAN_SIZE,
        SIGN_SIZE,
        STAND_SIZE,
        STOP_SIZE,
        TILT_DEGREES,
        UNIT,
    )
    from measure_model import Goal, TaskKind

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

INK: Final[tuple[int, int, int]] = (75, 55, 47)
COCOA: Final[tuple[int, int, int]] = (61, 44, 31)
CREAM: Final[tuple[int, int, int]] = (255, 251, 235)
SUNSHINE: Final[tuple[int, int, int]] = (255, 194, 52)
CORAL: Final[tuple[int, int, int]] = (244, 111, 97)
WOOD: Final[tuple[int, int, int]] = (247, 184, 116)
PALE: Final[tuple[int, int, int]] = (226, 214, 196)
WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
# Theme tokens (runtime/theme-defaults): ocean, leaf, raspberry, grape, turquoise.
PARCEL_COLOURS: Final[tuple[tuple[int, int, int], ...]] = (
    (74, 145, 216),
    (89, 184, 106),
    (216, 86, 131),
    (148, 100, 201),
    (68, 184, 174),
)
BLOCK_POP: Final[int] = UNIT + 10
BADGE_SIZE: Final[int] = 44
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 110,
    "confetti": 260,
    "star_burst": 200,
    "dust_puff": 90,
    "check_pop": 120,
}
_PARCEL_CACHE: Final[int] = 16
_FACE_CACHE: Final[int] = 16
_SS: Final[int] = 2  # supersampling for painted shapes


class MeasureArt:
    """Own every prepared surface the renderer blits (bounded, built once)."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
        size: tuple[int, int] = (1024, 600),
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=40)
        self._runtime_dir = runtime_dir
        self.background = self._compose_background(size)
        self.board = self._load_private("board.png", BOARD_SIZE)
        self.shelf = self._load_private("shelf.png", BOARD_SIZE)
        self.stop = self._load_private("stop.png", STOP_SIZE)
        self.crate = self._load_private("crate.png", CRATE_SIZE)
        self.sign = self._load_private("sign.png", SIGN_SIZE)
        self.stand = self._load_private("balance_stand.png", STAND_SIZE)
        self.pan = self._load_private("balance_pan.png", PAN_SIZE)
        self._beam = self._load_private("balance_beam.png", BEAM_SIZE)
        self._beam_frames: dict[int, pygame.Surface] = {}
        self._tall_stops: dict[int, pygame.Surface] = {}
        self.block = self._load_private("unit_block.png", (UNIT, UNIT))
        self.block_pop = self._load_private("unit_block.png", (BLOCK_POP, BLOCK_POP))
        self._parcels: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._faces: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._badges: dict[int, pygame.Surface] = {}
        self._numerals: dict[int, pygame.Surface] = {}
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self.missing_ghost = self._ghost((UNIT - 4, UNIT - 4))
        self.extra_ring = self._ring((UNIT + 6, UNIT + 6))

    # -- parcels ------------------------------------------------------------

    def parcel(self, size: tuple[int, int], colour: int, *, lit: bool = False) -> pygame.Surface:
        """A gift-wrapped parcel exactly ``size`` (the bow rises above its top).

        The box body spans the full width, so its ends line up with the start
        stop and the unit blocks to the pixel; the bow is drawn above the
        returned surface's ``box_top`` (``BOW_HEIGHT`` px).
        """

        key = (int(size[0]), int(size[1]), colour % len(PARCEL_COLOURS), lit)
        cached = self._parcels.get(key)
        if cached is not None:
            self._parcels.move_to_end(key)
            return cached
        surface = _paint_parcel(key[0], key[1], PARCEL_COLOURS[key[2]], lit)
        self._parcels[key] = surface
        while len(self._parcels) > _PARCEL_CACHE:
            self._parcels.popitem(last=False)
        return surface

    # -- balance --------------------------------------------------------------

    def beam(self, degrees: float) -> pygame.Surface | None:
        """Beam pre-rotated to the nearest whole degree (built once per angle)."""

        if self._beam is None:
            return None
        angle = int(round(max(-TILT_DEGREES, min(TILT_DEGREES, degrees))))
        frame = self._beam_frames.get(angle)
        if frame is None:
            frame = self._beam if angle == 0 else pygame.transform.rotozoom(self._beam, -angle, 1.0)
            self._beam_frames[angle] = frame
        return frame

    def preload_beam(self) -> None:
        limit = int(TILT_DEGREES)
        for angle in range(-limit, limit + 1):
            self.beam(angle)

    def tall_stop(self, height: int) -> pygame.Surface | None:
        """One start stop spanning several shelves (scaled once per height)."""

        if self.stop is None:
            return None
        cached = self._tall_stops.get(height)
        if cached is None:
            cached = pygame.transform.smoothscale(self.stop, (self.stop.get_width(), int(height)))
            if len(self._tall_stops) >= 2:
                self._tall_stops.pop(next(iter(self._tall_stops)))
            self._tall_stops[height] = cached
        return cached

    # -- job card pictograms --------------------------------------------------------

    def goal_face(self, kind: TaskKind, goal: Goal) -> pygame.Surface:
        """The job card picture: what to look for, never which parcel."""

        key = (kind.value, goal.value)
        cached = self._faces.get(key)
        if cached is None:
            cached = _paint_goal_face(kind, goal, (GOAL_PICTURE, GOAL_PICTURE))
            self._faces[key] = cached
            while len(self._faces) > _FACE_CACHE:
                self._faces.popitem(last=False)
        return cached

    # -- numbers ------------------------------------------------------------------

    def numeral(self, value: int, size: int = 66) -> pygame.Surface:
        cached = self._numerals.get(value)
        if cached is None:
            cached = self._painter.label(str(value), size, COCOA, role=FontRole.DISPLAY)
            if len(self._numerals) >= 12:
                self._numerals.pop(next(iter(self._numerals)))
            self._numerals[value] = cached
        return cached

    def badge(self, number: int) -> pygame.Surface:
        """Sunshine numeral token that pops above a block while it is counted."""

        cached = self._badges.get(number)
        if cached is None:
            body = self._painter.body(BodyShape.ROUND, (BADGE_SIZE, BADGE_SIZE), SUNSHINE)
            cached = body.copy()
            label = self._painter.label(str(number), int(BADGE_SIZE * 0.62), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(BADGE_SIZE // 2, BADGE_SIZE // 2 + 1)))
            if len(self._badges) >= 12:
                self._badges.pop(next(iter(self._badges)))
            self._badges[number] = cached
        return cached

    # -- FX -----------------------------------------------------------------------

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

    # -- demonstration marks ----------------------------------------------------------

    @staticmethod
    def _ghost(size: tuple[int, int]) -> pygame.Surface:
        """An empty block place that glows: the gap still to fill."""

        w, h = size
        big = pygame.Surface((w * _SS, h * _SS), pygame.SRCALPHA)
        rect = big.get_rect()
        pygame.draw.rect(big, (*INK, 220), rect, border_radius=10 * _SS)
        pygame.draw.rect(big, SUNSHINE, rect.inflate(-4 * _SS, -4 * _SS), border_radius=9 * _SS)
        pygame.draw.rect(big, (*CREAM, 225), rect.inflate(-14 * _SS, -14 * _SS), border_radius=6 * _SS)
        return pygame.transform.smoothscale(big, size)

    @staticmethod
    def _ring(size: tuple[int, int]) -> pygame.Surface:
        """A coral frame around a block that overhangs the parcel."""

        w, h = size
        big = pygame.Surface((w * _SS, h * _SS), pygame.SRCALPHA)
        rect = big.get_rect()
        pygame.draw.rect(big, INK, rect, border_radius=12 * _SS)
        pygame.draw.rect(big, CORAL, rect.inflate(-4 * _SS, -4 * _SS), border_radius=11 * _SS)
        pygame.draw.rect(big, (0, 0, 0, 0), rect.inflate(-14 * _SS, -14 * _SS), border_radius=7 * _SS)
        return pygame.transform.smoothscale(big, size)

    # -- loading ------------------------------------------------------------------

    def _load_private(self, name: str, size: tuple[int, int]) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            return None
        if image.get_size() != size:
            image = pygame.transform.smoothscale(image, size)
        return image

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        """Workshop wall + wood floor + workbench as one opaque surface."""

        surface = pygame.Surface(size)
        surface.fill((240, 224, 192))
        # Throwaway loader: full-screen layers are released once composed.
        loader = ControlArt(max_entries=4)
        for layer in ("wall_workshop", "floor_wood"):
            image = loader.image(f"bg.indoor_room.{layer}", size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        bench = self._load_private("bench.png", BENCH_SIZE)
        if bench is not None:
            surface.blit(bench, (0, BENCH_TOP - 4))
        else:
            surface.fill((217, 142, 66), pygame.Rect(0, BENCH_TOP, size[0], 30))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


# -- painted content (kit recipe) ---------------------------------------------------

BOW_HEIGHT: Final[int] = 22


def _box(canvas: pygame.Surface, rect: pygame.Rect, fill: tuple[int, int, int], radius: int, stroke: int) -> None:
    """Ink contour + two-stop light→base fill + one upper-left highlight."""

    pygame.draw.rect(canvas, INK, rect, border_radius=radius)
    inner = rect.inflate(-2 * stroke, -2 * stroke)
    if inner.width <= 0 or inner.height <= 0:
        return
    mask = pygame.Surface(inner.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=max(1, radius - stroke))
    gradient = pygame.Surface(inner.size)
    light = mix(fill, WHITE, 0.34)
    span = max(1, inner.height - 1)
    for row in range(inner.height):
        pygame.draw.line(gradient, mix(light, fill, min(1.0, row / (span * 0.8))), (0, row), (inner.width, row))
    mask.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    canvas.blit(mask, inner.topleft)


def _paint_parcel(width: int, height: int, colour: tuple[int, int, int], lit: bool) -> pygame.Surface:
    s = _SS
    w, h = width * s, (height + BOW_HEIGHT) * s
    canvas = pygame.Surface((w, h), pygame.SRCALPHA)
    stroke = 3 * s
    top = BOW_HEIGHT * s
    body = pygame.Rect(0, top, w, height * s)
    radius = min(9 * s, body.height // 4, body.width // 4)
    _box(canvas, body, colour, radius, stroke)
    # Lid band (light step), flush with the body so the ends stay exact.
    lid_h = max(8 * s, int(body.height * 0.2))
    lid = pygame.Rect(0, top, w, lid_h)
    _box(canvas, lid, mix(colour, WHITE, 0.4), radius, stroke)
    # Highlight on the body (one per mass).
    if body.width > 30 * s and body.height > 30 * s:
        gloss = pygame.Rect(body.x + 9 * s, top + lid_h + 6 * s, max(8 * s, int(body.width * 0.12)), 5 * s)
        if gloss.right < body.centerx - 12 * s:
            pygame.draw.rect(canvas, (255, 255, 255, 120), gloss, border_radius=gloss.height // 2)
    # Cream ribbon down the middle (ink sides), as on the Activity icon.
    band_w = max(10 * s, min(18 * s, int(min(body.width, body.height) * 0.2)))
    band = pygame.Rect(body.centerx - band_w // 2, top + stroke // 2, band_w, body.height - stroke)
    pygame.draw.rect(canvas, CREAM, band)
    pygame.draw.line(canvas, INK, band.topleft, band.bottomleft, 2 * s)
    pygame.draw.line(canvas, INK, (band.right - 1, band.top), (band.right - 1, band.bottom), 2 * s)
    # Bow: two loops and a knot.
    cx, cy = body.centerx, top - 4 * s
    loop = pygame.Rect(0, 0, 22 * s, 15 * s)
    for dx in (-11 * s, 11 * s):
        loop.center = (cx + dx, cy - 2 * s)
        pygame.draw.ellipse(canvas, INK, loop)
        pygame.draw.ellipse(canvas, CREAM, loop.inflate(-5 * s, -5 * s))
    knot = pygame.Rect(0, 0, 13 * s, 13 * s)
    knot.center = (cx, cy)
    pygame.draw.ellipse(canvas, INK, knot)
    pygame.draw.ellipse(canvas, CREAM, knot.inflate(-5 * s, -5 * s))
    if lit:
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*SUNSHINE, 255), body, width=5 * s, border_radius=radius)
        canvas.blit(glow, (0, 0))
    return pygame.transform.smoothscale(canvas, (width, height + BOW_HEIGHT))


def _bar(canvas: pygame.Surface, rect: pygame.Rect, target: bool) -> None:
    _box(canvas, rect, SUNSHINE if target else PALE, 5 * _SS, 3 * _SS)


def _squares(canvas: pygame.Surface, left: int, top: int, count: int, unit: int) -> None:
    for index in range(count):
        _box(canvas, pygame.Rect(left + index * unit, top, unit, unit), WOOD, 3 * _SS, 2 * _SS)


def _paint_goal_face(kind: TaskKind, goal: Goal, size: tuple[int, int]) -> pygame.Surface:
    """Small pictogram for the job card, painted at 2x then smooth-scaled once."""

    s = _SS
    w, h = 120 * s, 120 * s  # 120-unit design square, scaled once to ``size``
    canvas = pygame.Surface((w, h), pygame.SRCALPHA)
    more = goal is Goal.MORE
    start = 16 * s
    if kind is TaskKind.COMPARE_LENGTH:
        rows = ((26 * s, 84 * s), (66 * s, 48 * s))
        for index, (y, length) in enumerate(rows):
            _bar(canvas, pygame.Rect(start, y, length, 26 * s), target=(index == 0) == more)
        _stop(canvas, start, 18 * s, 84 * s)
    elif kind is TaskKind.COMPARE_HEIGHT:
        base = 100 * s
        for index, (x, height) in enumerate(((26 * s, 78 * s), (68 * s, 42 * s))):
            _bar(canvas, pygame.Rect(x, base - height, 28 * s, height), target=(index == 0) == more)
        pygame.draw.line(canvas, INK, (12 * s, base), (w - 12 * s, base), 4 * s)
    elif kind is TaskKind.WEIGH:
        _paint_mini_balance(canvas, more)
    elif kind is TaskKind.MEASURE:
        unit = 18 * s
        _bar(canvas, pygame.Rect(start, 32 * s, 4 * unit, 26 * s), target=True)
        _squares(canvas, start, 64 * s, 4, unit)
        _stop(canvas, start, 24 * s, 64 * s)
    else:  # MEASURE_COMPARE
        unit = 13 * s
        rows = ((12 * s, 6), (64 * s, 4))
        for index, (y, count) in enumerate(rows):
            _bar(canvas, pygame.Rect(start, y, count * unit, 20 * s), target=(index == 0) == more)
            _squares(canvas, start, y + 22 * s, count, unit)
        _stop(canvas, start, 8 * s, 104 * s)
    return pygame.transform.smoothscale(canvas, size)


def _stop(canvas: pygame.Surface, x: int, top: int, height: int) -> None:
    rect = pygame.Rect(x - 7 * _SS, top, 7 * _SS, height)
    _box(canvas, rect, SUNSHINE, 3 * _SS, 2 * _SS)


def _paint_mini_balance(canvas: pygame.Surface, more: bool) -> None:
    """Tilted balance: the target pan (down = heavier, up = lighter) is lit."""

    s = _SS
    w = canvas.get_width()
    cx, cy = w // 2, 34 * s
    dy = 14 * s
    left = (cx - 40 * s, cy + dy)  # left end down (the heavier side)
    right = (cx + 40 * s, cy - dy)
    pygame.draw.line(canvas, INK, (cx, cy), (cx, 106 * s), 6 * s)
    pygame.draw.line(canvas, INK, (cx - 22 * s, 106 * s), (cx + 22 * s, 106 * s), 6 * s)
    pygame.draw.line(canvas, INK, left, right, 7 * s)
    pygame.draw.line(canvas, SUNSHINE, left, right, 3 * s)
    pygame.draw.circle(canvas, INK, (cx, cy), 7 * s)
    for index, (ex, ey) in enumerate((left, right)):
        pan_y = ey + 30 * s
        pygame.draw.line(canvas, INK, (ex, ey), (ex - 16 * s, pan_y), 2 * s)
        pygame.draw.line(canvas, INK, (ex, ey), (ex + 16 * s, pan_y), 2 * s)
        pan = pygame.Rect(ex - 20 * s, pan_y - 2 * s, 40 * s, 8 * s)
        pygame.draw.rect(canvas, INK, pan, border_radius=4 * s)
        box = pygame.Rect(ex - 13 * s, pan_y - 22 * s, 26 * s, 20 * s)
        target = (index == 0) == more
        _box(canvas, box, SUNSHINE if target else PALE, 4 * s, 3 * s)


__all__ = ["BADGE_SIZE", "BLOCK_POP", "BOW_HEIGHT", "MeasureArt", "PARCEL_COLOURS"]
