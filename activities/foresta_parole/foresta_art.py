"""Art resolution and cached surfaces for The Word Forest.

Everything visible is library art, this package's own three props, or a
letter: the glade is composed from shared ``bg.woodland_pond`` sky/far/mid
layers over ``bg.meadow_day.ground``; the word pictures are shared ``prop.*``
/ ``creature.*`` art; Leo, HUD glyphs and ``fx.*`` come from the shared
library. The canopy band, the catching basket and the letter fruit are
Activity-private (``assets/source`` SVG → ``assets/runtime`` PNG, authored per
GREIA_SVG_AUTHORING_RULES). Letters are drawn once per letter/colour/size with
the Greia display font and an ink contour.

Images are decoded and scaled once into bounded caches; drawing only blits.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
from typing import Callable, Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlArt
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .foresta_content import PICTURE_PENDING
else:
    from foresta_content import PICTURE_PENDING  # type: ignore[no-redef]


PACKAGE_ROOT: Final = Path(__file__).resolve().parent
ACTIVITY_PREFIX: Final = "activity:"
GLADE_LAYERS: Final = (
    "bg.woodland_pond.sky",
    "bg.woodland_pond.far",
    "bg.woodland_pond.mid",
    "bg.meadow_day.ground",
)

INK: Final = (75, 55, 47)          # cast ink #4B372F
CREAM: Final = (255, 251, 235)     # cast cream #FFFBEB
GLOW: Final = (255, 194, 52)       # theme sunshine
ACCENTS: Final[dict[str, tuple[int, int, int]]] = {
    "coral": (244, 111, 97),
    "ocean": (74, 145, 216),
    "leaf": (89, 184, 106),
    "grape": (148, 100, 201),
    "raspberry": (216, 86, 131),
    "orange": (243, 154, 56),
    "turquoise": (68, 184, 174),
    "sunshine": (255, 194, 52),
}
SUPERSAMPLE: Final = 2
MAX_LETTERS: Final = 48


def accent(token: str) -> tuple[int, int, int]:
    return ACCENTS.get(token, ACCENTS["ocean"])


def resolve_picture(asset_id: str, variant: str = "default") -> Path:
    """Map ``activity:<name>``, ``<shared id>`` or ``<shared id>#<variant>`` to a file."""

    if asset_id.startswith(ACTIVITY_PREFIX):
        name = asset_id[len(ACTIVITY_PREFIX):]
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid Activity picture id: {asset_id!r}")
        return PACKAGE_ROOT / "assets" / "runtime" / f"{name}.png"
    if "#" in asset_id:
        asset_id, variant = asset_id.split("#", 1)
    return get_shared_visual_path(asset_id, variant=variant)


class LetterArt:
    """Capital letters in an accent ink with a cocoa contour, cached by size."""

    def __init__(self, typography: GreiaTypography, *, max_entries: int = MAX_LETTERS) -> None:
        self._typography = typography
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._max = int(max_entries)

    def clear(self) -> None:
        self._cache.clear()

    def _cached(self, key: tuple, build: Callable[[], pygame.Surface]) -> pygame.Surface:
        surface = self._cache.get(key)
        if surface is not None:
            self._cache.move_to_end(key)
            return surface
        surface = build()
        self._cache[key] = surface
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return surface

    def glyph(self, text: str, size: int, color: tuple[int, int, int], *, outline: bool = True) -> pygame.Surface:
        size = max(8, int(size))
        return self._cached(("glyph", text, size, color, outline), lambda: self._render(text, size, color, outline))

    def letter(self, char: str, size: int, token: str) -> pygame.Surface:
        return self.glyph(char, size, accent(token))

    def _render(self, text: str, size: int, color: tuple[int, int, int], outline: bool) -> pygame.Surface:
        s = SUPERSAMPLE
        face = self._typography.render(text, FontRole.DISPLAY, size * s, color)
        if not outline:
            return pygame.transform.smoothscale(face, (max(1, face.get_width() // s), max(1, face.get_height() // s)))
        ink = self._typography.render(text, FontRole.DISPLAY, size * s, INK)
        pad = max(2, int(size * s * 0.07))
        big = pygame.Surface((face.get_width() + pad * 2, face.get_height() + pad * 2), pygame.SRCALPHA)
        # A round contour: the ink face stamped on a small circle of offsets.
        steps = 16
        for i in range(steps):
            angle = math.tau * i / steps
            big.blit(ink, (pad + round(math.cos(angle) * pad), pad + round(math.sin(angle) * pad)))
        big.blit(face, (pad, pad))
        return pygame.transform.smoothscale(big, (max(1, big.get_width() // s), max(1, big.get_height() // s)))


class ForestArt:
    """Own the glade backdrop, the canopy band and every cached picture/pose/FX."""

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
        self.letters = LetterArt(typography)
        self.background = self._build_background(resolver)
        self.canopy = self._load_private(resolver, "canopy", (self._size[0], int(self._size[0] * 220 / 1024)))
        self._glows: dict[int, pygame.Surface] = {}
        self._fruit: dict[tuple, pygame.Surface] = {}

    def _build_background(self, resolver: Callable[[str, str], Path]) -> pygame.Surface:
        # Full-screen layers are composed once through a throwaway loader so
        # the decoded 1024×600 layers are not retained in the cache.
        loader = ControlArt(resolver, max_entries=2)
        surface = pygame.Surface(self._size)
        surface.fill((207, 234, 247))  # theme sky until the sky layer loads
        for layer in GLADE_LAYERS:
            image = loader.image(layer, self._size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    @staticmethod
    def _load_private(resolver: Callable[[str, str], Path], name: str, size: tuple[int, int]) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(resolver(f"{ACTIVITY_PREFIX}{name}", "default")))
        except (pygame.error, OSError, ValueError, FileNotFoundError):
            return None
        if image.get_size() != size:
            image = pygame.transform.smoothscale(image, size)
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        return image

    def picture(self, picture_id: str, size: int) -> pygame.Surface | None:
        if not picture_id or picture_id == PICTURE_PENDING:
            return None
        return self.art.image(picture_id, int(size))

    def private(self, name: str, size: tuple[int, int] | int) -> pygame.Surface | None:
        return self.art.image(f"{ACTIVITY_PREFIX}{name}", size)

    def fx(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self.art.image(asset_id, int(size))

    def hud(self, glyph: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"icon.hud.{glyph}", int(size))

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def fruit(self, char: str, size: int, token: str) -> pygame.Surface:
        """A letter fruit (private fruit art + the letter), built once per letter/colour."""

        key = (char, int(size), token)
        cached = self._fruit.get(key)
        if cached is not None:
            return cached
        if len(self._fruit) >= 40:
            self._fruit.clear()
        size = int(size)
        body = self.private("token", size)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        if body is not None:
            surface.blit(body, body.get_rect(center=(size // 2, size // 2)))
        else:  # vector fallback when the rendition is missing
            centre = (size // 2, int(size * 0.55))
            radius = int(size * 0.40)
            pygame.draw.circle(surface, INK, centre, radius + 3)
            pygame.draw.circle(surface, CREAM, centre, radius)
        glyph = self.letters.letter(char, int(size * 0.56), token)
        # Fruit body centre is (64, 70) on the 128 master.
        surface.blit(glyph, glyph.get_rect(center=(size // 2, int(size * 70 / 128) + 1)))
        self._fruit[key] = surface
        return surface

    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the hinted letter (built once per size)."""

        diameter = max(8, int(diameter))
        cached = self._glows.get(diameter)
        if cached is not None:
            return cached
        if len(self._glows) >= 8:
            self._glows.clear()
        surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        radius = diameter // 2
        steps = 24
        for step in range(steps):
            r = int(radius * (1.0 - step / steps))
            alpha = int(170 * (step / steps) ** 1.25)
            pygame.draw.circle(surface, (*GLOW, alpha), (radius, radius), max(1, r))
        self._glows[diameter] = surface
        return surface

    def clear(self) -> None:
        self.art.clear()
        self.letters.clear()
        self._glows.clear()
        self._fruit.clear()


__all__ = ["CREAM", "INK", "ForestArt", "LetterArt", "accent", "resolve_picture"]
