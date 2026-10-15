"""Art resolution and cached surfaces for Officina dei Suoni.

Everything visible comes from library art: the shared ``bg.indoor_room``
workshop wall and wooden floor, shared ``prop.*`` pictures, ``fx.*`` bursts,
HUD glyphs, the canonical cast, and this package's own Sound Machine, gear and
five missing pictures (``assets/runtime``, authored per
GREIA_SVG_AUTHORING_RULES from ``assets/source``). Capital letters are the
taught object, rendered once per size with the display font and an ink
contour. Images are decoded and scaled once into bounded caches; drawing only
blits.
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
    from .sound_content import WordItem
else:
    from sound_content import WordItem


PACKAGE_ROOT: Final = Path(__file__).resolve().parent
ACTIVITY_PREFIX: Final = "activity:"
ROOM_LAYERS: Final = ("bg.indoor_room.wall_workshop", "bg.indoor_room.floor_wood")
MACHINE_ID: Final = "activity:machine"
GEAR_ID: Final = "activity:gear"
# Picture used where a staged word has no art yet (never in EN/IT targets).
FALLBACK_PICTURE: Final = "icon.hud.ear"
GEAR_FRAMES: Final = 6  # 8 teeth -> 45° symmetry; 6 frames of 7.5° look smooth

INK: Final = (75, 55, 47)
LETTER_FILL: Final = (74, 145, 216)      # theme "ocean" (Dani's family)
LETTER_DONE: Final = (243, 154, 56)      # theme "orange" (learn accent)
GLOW_COLOR: Final = (255, 194, 52)       # theme "sunshine"
MAX_LETTERS: Final = 64


def resolve_picture(asset_id: str, variant: str = "default") -> Path:
    """Map an Activity-private ``activity:<name>`` ID or a shared visual ID to a file."""

    if asset_id.startswith(ACTIVITY_PREFIX):
        name = asset_id[len(ACTIVITY_PREFIX):]
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid Activity picture id: {asset_id!r}")
        return PACKAGE_ROOT / "assets" / "runtime" / f"{name}.png"
    return get_shared_visual_path(asset_id, variant=variant)


class LetterGlyphs:
    """Capital letters with an ink contour, rendered once per (letter, size, colour)."""

    def __init__(self, typography: GreiaTypography, *, max_entries: int = MAX_LETTERS) -> None:
        self._typography = typography
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._max = int(max_entries)

    def glyph(self, letter: str, size: int, color: tuple[int, int, int] = LETTER_FILL) -> pygame.Surface:
        key = (letter, int(size), tuple(color))
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached
        surface = self._render(letter, int(size), color)
        self._cache[key] = surface
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return surface

    def _render(self, letter: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        fill = self._typography.render(letter, FontRole.DISPLAY, size, color)
        ink = self._typography.render(letter, FontRole.DISPLAY, size, INK)
        r = max(2, size // 16)
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


class SoundWorkshopArt:
    """Own the workshop backdrop and every cached picture/machine/FX surface."""

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
        self.letters = LetterGlyphs(typography)
        self.room = self._build_room(resolver)
        self._glows: dict[int, pygame.Surface] = {}
        self._gears: dict[int, tuple[pygame.Surface, ...]] = {}

    # -- static scene ----------------------------------------------------------
    def _build_room(self, resolver: Callable[[str, str], Path]) -> pygame.Surface:
        # Full-screen layers are composed once through a throwaway loader so
        # the decoded 1024×600 layers are not retained in the cache.
        loader = ControlArt(resolver, max_entries=2)
        surface = pygame.Surface(self._size)
        surface.fill((240, 228, 200))  # wall cream until the layers load
        for layer in ROOM_LAYERS:
            image = loader.image(layer, self._size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def machine(self, size: tuple[int, int]) -> pygame.Surface | None:
        return self.art.image(MACHINE_ID, size)

    def gear_frames(self, size: int) -> tuple[pygame.Surface, ...]:
        """Pre-rotated gear frames (built once per size, never per frame)."""

        size = int(size)
        cached = self._gears.get(size)
        if cached is not None:
            return cached
        base = self.art.image(GEAR_ID, size)
        if base is None:
            return ()
        step = 45.0 / GEAR_FRAMES
        frames = []
        for index in range(GEAR_FRAMES):
            rotated = pygame.transform.rotozoom(base, -step * index, 1.0)
            frames.append(rotated)
        self._gears[size] = tuple(frames)
        return self._gears[size]

    # -- pictures --------------------------------------------------------------
    def picture(self, item: WordItem, size: int) -> pygame.Surface | None:
        asset_id = item.picture if item.has_picture else FALLBACK_PICTURE
        image = self.art.image(asset_id, int(size))
        if image is None and asset_id != FALLBACK_PICTURE:
            image = self.art.image(FALLBACK_PICTURE, int(size))
        return image

    def letter(self, letter: str, size: int, *, done: bool = False) -> pygame.Surface:
        return self.letters.glyph(letter, size, LETTER_DONE if done else LETTER_FILL)

    def plain_letter(self, letter: str, size: int) -> pygame.Surface:
        """A given (not chosen) letter of the word: quiet ink, no contour."""

        return self.letters.glyph(letter, size, INK)

    def hud(self, glyph: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"icon.hud.{glyph}", int(size))

    def fx(self, asset_id: str, size: int, variant: str = "default") -> pygame.Surface | None:
        return self.art.image(asset_id, int(size), variant=variant)

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the speaking/hinted item (built once per size)."""

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
        self.letters.clear()
        self._glows.clear()
        self._gears.clear()


__all__ = ["SoundWorkshopArt", "LetterGlyphs", "resolve_picture", "INK"]
