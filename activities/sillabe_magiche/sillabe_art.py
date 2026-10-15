"""Art resolution and cached surfaces for Leo's Syllable Train.

Everything visible is library art or a taught syllable: the shared
``bg.meadow_day.*`` scene (Leo's meadow, as in Leo's Letter Garden), shared
``prop.*`` word pictures, ``fx.*`` bursts, HUD glyphs and the canonical cast,
plus this package's train (locomotive, wheel and station board copied from
Treno Numeri; two wagon hues) and four missing word pictures, authored per
GREIA_SVG_AUTHORING_RULES in ``assets/source`` and rendered to
``assets/runtime``. Syllables are rendered once per (text, size, colour) with
the display font and an ink contour. Images are decoded and scaled once into
bounded caches; drawing only blits.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Callable, Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlArt
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .sillabe_content import TrainWord
else:
    from sillabe_content import TrainWord


PACKAGE_ROOT: Final = Path(__file__).resolve().parent
ACTIVITY_PREFIX: Final = "activity:"
MEADOW_LAYERS: Final = ("sky", "far", "mid", "ground", "foreground")
LOCO_ID: Final = "activity:locomotive"
WHEEL_ID: Final = "activity:wheel"
SIGN_ID: Final = "activity:station_sign"
WAGON_IDS: Final = ("activity:wagon_ocean", "activity:wagon_coral")
FALLBACK_PICTURE: Final = "icon.hud.ear"
WHEEL_FRAMES: Final = 4  # cross spokes -> 90° symmetry; 4 frames of 22.5°

INK: Final = (75, 55, 47)
NAVY: Final = (37, 59, 89)
WAGON_INK: Final = ((74, 145, 216), (244, 111, 97))  # ocean, coral: one hue per wagon
GLOW_COLOR: Final = (255, 194, 52)                    # theme "sunshine"
RAIL: Final = (151, 100, 51)
SLEEPER: Final = (201, 129, 54)
TRACK_Y: Final = 404
MAX_GLYPHS: Final = 64


def resolve_picture(asset_id: str, variant: str = "default") -> Path:
    """Map an Activity-private ``activity:<name>`` ID or a shared visual ID to a file."""

    if asset_id.startswith(ACTIVITY_PREFIX):
        name = asset_id[len(ACTIVITY_PREFIX):]
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid Activity picture id: {asset_id!r}")
        return PACKAGE_ROOT / "assets" / "runtime" / f"{name}.png"
    return get_shared_visual_path(asset_id, variant=variant)


class SyllableGlyphs:
    """Taught syllables / vowels, rendered once per (text, size, colour)."""

    def __init__(self, typography: GreiaTypography, *, max_entries: int = MAX_GLYPHS) -> None:
        self._typography = typography
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._max = int(max_entries)

    def glyph(self, text: str, size: int, color: tuple[int, int, int], *, contour: bool = True) -> pygame.Surface:
        key = (text, int(size), tuple(color), contour)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached
        surface = self._render(text, int(size), color, contour)
        self._cache[key] = surface
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return surface

    def _render(self, text: str, size: int, color: tuple[int, int, int], contour: bool) -> pygame.Surface:
        fill = self._typography.render(text, FontRole.DISPLAY, size, color)
        if not contour:
            return fill
        ink = self._typography.render(text, FontRole.DISPLAY, size, INK)
        r = max(2, size // 18)
        surface = pygame.Surface((fill.get_width() + 2 * r, fill.get_height() + 2 * r), pygame.SRCALPHA)
        # Ink contour: the dark glyph stamped around a small circle, then the fill.
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    surface.blit(ink, (r + dx, r + dy))
        surface.blit(fill, (r, r))
        return surface

    def clear(self) -> None:
        self._cache.clear()


class SillabeArt:
    """Own the meadow backdrop and every cached picture / train / FX surface."""

    def __init__(
        self,
        width: int,
        height: int,
        typography: GreiaTypography,
        *,
        resolver: Callable[[str, str], Path] = resolve_picture,
        art: ControlArt | None = None,
    ) -> None:
        self._size = (int(width), int(height))
        self.art = art if art is not None else ControlArt(resolver, max_entries=96)
        self.glyphs = SyllableGlyphs(typography)
        self.background = self._build_background(resolver)
        self._glows: dict[int, pygame.Surface] = {}
        self._wheels: dict[int, tuple[pygame.Surface, ...]] = {}

    # -- static scene ------------------------------------------------------------
    def _build_background(self, resolver: Callable[[str, str], Path]) -> pygame.Surface:
        # Full-screen layers are composed once through a throwaway loader so
        # the decoded 1024×600 layers are not retained in the cache.
        loader = ControlArt(resolver, max_entries=2)
        surface = pygame.Surface(self._size)
        surface.fill((207, 234, 247))  # theme sky until the sky layer loads
        for layer in MEADOW_LAYERS:
            image = loader.image(f"bg.meadow_day.{layer}", self._size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        _draw_track(surface, TRACK_Y)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    # -- train ----------------------------------------------------------------------
    def locomotive(self, size: tuple[int, int]) -> pygame.Surface | None:
        return self.art.image(LOCO_ID, size)

    def wagon(self, index: int, size: tuple[int, int]) -> pygame.Surface | None:
        return self.art.image(WAGON_IDS[index % len(WAGON_IDS)], size)

    def sign(self, size: tuple[int, int]) -> pygame.Surface | None:
        return self.art.image(SIGN_ID, size)

    def wheel_frames(self, size: int) -> tuple[pygame.Surface, ...]:
        """Pre-rotated wheel frames (built once per size, never per frame)."""

        size = int(size)
        cached = self._wheels.get(size)
        if cached is not None:
            return cached
        base = self.art.image(WHEEL_ID, size)
        if base is None:
            return ()
        step = 90.0 / WHEEL_FRAMES
        frames = []
        for index in range(WHEEL_FRAMES):
            rotated = pygame.transform.rotozoom(base, -step * index, 1.0)
            frames.append(rotated)
        self._wheels[size] = tuple(frames)
        return self._wheels[size]

    # -- pictures / glyphs ------------------------------------------------------------
    def picture(self, word: TrainWord, size: int) -> pygame.Surface | None:
        asset_id = word.picture if word.has_picture else FALLBACK_PICTURE
        image = self.art.image(asset_id, int(size))
        if image is None and asset_id != FALLBACK_PICTURE:
            image = self.art.image(FALLBACK_PICTURE, int(size))
        return image

    def tile_text(self, text: str, size: int) -> pygame.Surface:
        """A choice tile's syllable / vowel: calm navy, no contour."""

        return self.glyphs.glyph(text, size, NAVY, contour=False)

    def wagon_text(self, text: str, size: int, wagon: int) -> pygame.Surface:
        """A built syllable on its wagon, in the wagon's hue with an ink contour."""

        return self.glyphs.glyph(text, size, WAGON_INK[wagon % len(WAGON_INK)])

    def given_text(self, text: str, size: int) -> pygame.Surface:
        """A given consonant on a wagon (quiet ink)."""

        return self.glyphs.glyph(text, size, INK, contour=False)

    def hud(self, glyph: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"icon.hud.{glyph}", int(size))

    def fx(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self.art.image(asset_id, int(size))

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the speaking/hinted element (built once per size)."""

        diameter = max(8, int(diameter))
        cached = self._glows.get(diameter)
        if cached is not None:
            return cached
        if len(self._glows) >= 10:
            self._glows.clear()
        surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        radius = diameter // 2
        steps = 24
        for step in range(steps):
            r = int(radius * (1.0 - step / steps))
            alpha = int(170 * (step / steps) ** 1.25)
            pygame.draw.circle(surface, (*GLOW_COLOR, alpha), (radius, radius), max(1, r))
        self._glows[diameter] = surface
        return surface

    def clear(self) -> None:
        self.art.clear()
        self.glyphs.clear()
        self._glows.clear()
        self._wheels.clear()


def _draw_track(surface: pygame.Surface, y: int) -> None:
    """Wooden sleepers and two rails across the meadow, baked into the backdrop."""

    width = surface.get_width()
    for x in range(-6, width + 24, 34):
        sleeper = pygame.Rect(x, y - 4, 22, 16)
        pygame.draw.rect(surface, SLEEPER, sleeper, border_radius=4)
        pygame.draw.rect(surface, INK, sleeper, width=2, border_radius=4)
    for offset in (-2, 7):
        rail = pygame.Rect(0, y + offset, width, 5)
        pygame.draw.rect(surface, RAIL, rail)
        pygame.draw.line(surface, INK, (0, rail.top), (width, rail.top), 2)
        pygame.draw.line(surface, INK, (0, rail.bottom), (width, rail.bottom), 2)


__all__ = ["SillabeArt", "SyllableGlyphs", "resolve_picture", "INK", "TRACK_Y", "WAGON_INK"]
