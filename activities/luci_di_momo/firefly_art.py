"""Prepared, bounded art for Luci di Momo.

Everything is loaded, scaled or painted once. The opaque backdrop is the
shared ``bg.night_sky`` layers flattened into one surface. Fireflies are the
shared ``creature.woodland.firefly`` at a few prepared sizes, FX come from the
shared ``fx.*`` set and Momo's poses from the canonical cast. Momo's firefly
jar is this package's own art (``assets/source/jar_{back,front}.svg`` ->
``assets/runtime``). Count badges, answer-card faces and the ten-frame tray
are painted with the shared control-kit recipe and cached in small bounded
dictionaries; soft glows are built once. Drawing code only blits.

The previous version allocated seven alpha surfaces per frame on its ready
screen (button aura) plus two per firefly; nothing here is allocated per frame.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.typography import FontRole

if __package__:
    from .firefly_layout import CARD_SIZE, FRAME_RECT, JAR_SIZE
    from .firefly_model import FRAME_CELL, FRAME_COLUMNS, FRAME_ROWS, ROUND_COUNT
else:
    from firefly_layout import CARD_SIZE, FRAME_RECT, JAR_SIZE
    from firefly_model import FRAME_CELL, FRAME_COLUMNS, FRAME_ROWS, ROUND_COUNT

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

FIREFLY_ID: Final = "creature.woodland.firefly"
# Glimpse sizes per arrangement, the "pop" size of the first glow frames, the
# blink-out size, the flying size and the size of a light resting in the jar.
GLIMPSE_SIZES: Final[dict[str, int]] = {"dice": 112, "scatter": 104, "groups": 84, "ten_frame": 84}
POP_SCALE: Final = 1.18
BLINK_SCALE: Final = 0.6
FIREFLY_SIZES: Final[dict[str, int]] = {
    **GLIMPSE_SIZES,
    **{f"{role}.pop": int(px * POP_SCALE) for role, px in GLIMPSE_SIZES.items()},
    **{f"{role}.blink": int(px * BLINK_SCALE) for role, px in GLIMPSE_SIZES.items()},
    "flying": 64,
    "jar": 56,
}
FX_SIZES: Final[dict[str, int]] = {"sparkle": 110, "star_burst": 220, "confetti": 280, "firework": 240}
BADGE_SIZE: Final = 46
GROUP_BADGE_SIZE: Final = 62
HALO_SIZE: Final = 140
CACHE_LIMIT: Final = 24

COCOA: Final = (61, 44, 31)
NAVY: Final = (37, 59, 89)
SUNSHINE: Final = (255, 194, 52)
SUNSHINE_LIGHT: Final = (255, 218, 133)
GLOW: Final = (255, 214, 110)
# The second part of a grouped glimpse glows in a cool tone (turquoise light),
# so "two and four" is seen as two parts without recolouring the creature.
GLOW_SECOND: Final = (143, 222, 214)


class FireflyArt:
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
        self.jar_back = self._load_private("jar_back.png", (JAR_SIZE, JAR_SIZE))
        self.jar_front = self._load_private("jar_front.png", (JAR_SIZE, JAR_SIZE))
        self.fireflies: dict[str, pygame.Surface | None] = {
            name: self._art.image(FIREFLY_ID, px) for name, px in FIREFLY_SIZES.items()
        }
        # A warm light behind every firefly so a glimpse reads as glowing lights.
        self._glows: dict[str, pygame.Surface] = {
            name: _soft_disc(int(px * 1.5), GLOW, peak=110, power=1.4) for name, px in FIREFLY_SIZES.items()
        }
        self._second_glows: dict[str, pygame.Surface] = {
            name: _soft_disc(int(px * 1.5), GLOW_SECOND, peak=130, power=1.2)
            for name, px in FIREFLY_SIZES.items()
            if name.startswith("groups")
        }
        self.halo = _soft_disc(HALO_SIZE, GLOW, peak=215, power=0.75)
        self.cue_glow = _soft_disc(220, GLOW, peak=95, power=1.7)
        self.jar_glow = _soft_disc(300, GLOW, peak=150, power=1.5)
        self.ten_frame = self._build_ten_frame()
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._badges: dict[tuple[int, bool], pygame.Surface] = {}
        self._cards: dict[tuple[int, bool], pygame.Surface] = {}

    # -- cast / creatures ---------------------------------------------------

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def firefly(self, role: str) -> pygame.Surface | None:
        return self.fireflies.get(role)

    def glow(self, role: str, *, second: bool = False) -> pygame.Surface | None:
        """Warm light behind a firefly; ``second`` = the cool tone of a second part."""

        if second:
            return self._second_glows.get(role) or self._glows.get(role)
        return self._glows.get(role)

    def jar_glow_alpha(self, lights: int) -> int:
        """Glow strength for ``lights`` collected lights (0 = no glow)."""

        if lights <= 0:
            return 0
        return min(255, 70 + int(185 * lights / ROUND_COUNT))

    # -- FX -----------------------------------------------------------------

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

    # -- numbers ------------------------------------------------------------

    def badge(self, number: int, *, group: bool = False) -> pygame.Surface:
        """Sunshine numeral token that pops above a counted firefly (or group)."""

        key = (number, group)
        cached = self._badges.get(key)
        if cached is None:
            size = GROUP_BADGE_SIZE if group else BADGE_SIZE
            cached = self._painter.body(BodyShape.ROUND, (size, size), SUNSHINE).copy()
            label = self._painter.label(str(number), int(size * 0.6), COCOA, role=FontRole.DISPLAY)
            cached.blit(label, label.get_rect(center=(size // 2, size // 2 + 1)))
            _store(self._badges, key, cached)
        return cached

    def card_face(self, number: int, *, dots: bool) -> pygame.Surface:
        """Answer-card content: a big numeral, over a firefly dot frame when ``dots``."""

        key = (number, dots)
        cached = self._cards.get(key)
        if cached is not None:
            return cached
        width, height = CARD_SIZE
        face = pygame.Surface((int(width * 0.86), int(height * 0.8)), pygame.SRCALPHA)
        if dots:
            numeral = self._painter.label(str(number), int(height * (0.42 if number <= 5 else 0.36)), COCOA, role=FontRole.DISPLAY)
            frame = self._dot_frame(number, face.get_width() - 4)
            gap = 6
            top = max(0, (face.get_height() - numeral.get_height() - gap - frame.get_height()) // 2)
            face.blit(numeral, numeral.get_rect(midtop=(face.get_width() // 2, top)))
            face.blit(frame, frame.get_rect(midtop=(face.get_width() // 2, top + numeral.get_height() + gap)))
        else:
            numeral = self._painter.label(str(number), int(height * 0.6), COCOA, role=FontRole.DISPLAY)
            face.blit(numeral, numeral.get_rect(center=(face.get_width() // 2, face.get_height() // 2 + 2)))
        _store(self._cards, key, face)
        return face

    def _dot_frame(self, number: int, width: int) -> pygame.Surface:
        """A five-frame (or 2x5 ten-frame) of firefly-gold dots in reading order."""

        wells = 10 if number > 5 else 5
        rows = wells // 5
        gap = max(3, width // 36)
        dot = (width - 6 * gap) // 5
        frame = pygame.Surface((width, rows * dot + (rows + 1) * gap), pygame.SRCALPHA)
        theme = self._painter.theme
        tray = self._painter.body(
            BodyShape.PANEL,
            frame.get_size(),
            mix(theme.surface, theme.ink, 0.08),
            contour_width=2,
            highlight=False,
        )
        frame.blit(tray, (0, 0))
        filled = self._painter.body(BodyShape.ROUND, (dot, dot), SUNSHINE, contour_width=max(2, dot // 10))
        empty = self._painter.body(
            BodyShape.ROUND,
            (dot, dot),
            mix(theme.surface, theme.ink, 0.04),
            contour=mix(theme.ink, theme.surface, 0.5),
            contour_width=2,
            highlight=False,
        )
        for index in range(wells):
            row, column = divmod(index, 5)
            frame.blit(filled if index < number else empty, (gap + column * (dot + gap), gap + row * (dot + gap)))
        return frame

    # -- building -------------------------------------------------------------

    def _build_ten_frame(self) -> pygame.Surface:
        """The firefly ten-frame tray: a night-blue board with ten dark cups."""

        tray = self._painter.body(
            BodyShape.PANEL,
            FRAME_RECT.size,
            mix(NAVY, (255, 255, 255), 0.2),
            contour_width=4,
            highlight=False,
        ).copy()
        cup = FRAME_CELL - 14
        socket = self._painter.body(
            BodyShape.ROUND,
            (cup, cup),
            mix(NAVY, (0, 0, 0), 0.12),
            contour=mix(NAVY, (255, 255, 255), 0.42),
            contour_width=3,
            highlight=False,
        )
        for index in range(FRAME_COLUMNS * FRAME_ROWS):
            row, column = divmod(index, FRAME_COLUMNS)
            x = 14 + column * FRAME_CELL + (FRAME_CELL - cup) // 2
            y = 14 + row * FRAME_CELL + (FRAME_CELL - cup) // 2
            tray.blit(socket, (x, y))
        return tray

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
        """Shared night-sky layers flattened into one opaque surface."""

        surface = pygame.Surface(size)
        surface.fill(NAVY)
        # A throwaway loader: the layers are released once the composite exists.
        loader = ControlArt(max_entries=6)
        for name in ("sky", "stars", "far", "mid", "ground"):
            image = loader.image(f"bg.night_sky.{name}", size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface


def _soft_disc(size: int, color: tuple[int, int, int], *, peak: int, power: float) -> pygame.Surface:
    """A radial light glow built once (radial falloff for light sources only)."""

    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for radius in range(center, 0, -2):
        alpha = int(peak * (1.0 - radius / center) ** power)
        pygame.draw.circle(surface, (*color, alpha), (center, center), radius)
    return surface


def _store(cache: dict, key, value: pygame.Surface) -> None:
    if len(cache) >= CACHE_LIMIT:
        cache.pop(next(iter(cache)))
    cache[key] = value


__all__ = ["BADGE_SIZE", "FIREFLY_SIZES", "GLIMPSE_SIZES", "FireflyArt", "GROUP_BADGE_SIZE", "HALO_SIZE"]
