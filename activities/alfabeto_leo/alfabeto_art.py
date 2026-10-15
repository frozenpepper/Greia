"""Art resolution and cached surfaces for L'Alfabeto di Leo.

Everything visible is library art or a letter: the ``bg.meadow_day.*`` scene
layers, shared ``prop.*`` / ``creature.*`` example pictures, ``fx.*`` bursts,
the canonical cast, and this package's own pictures for example words the
library lacks (``assets/runtime``, authored per GREIA_SVG_AUTHORING_RULES from
``assets/source``). Letters are drawn from the stroke font so the tiles, the
tracing guide and the child's ink always share one letter shape.

Images are decoded and scaled once into bounded caches; drawing only blits.
The live tracing ink is the one incremental surface: new ink is added as the
finger moves, never redrawn from scratch.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Callable, Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlArt, mix

if __package__:
    from .alfabeto_model import PICTURE_PENDING
    from .alfabeto_strokes import resample
    from .alfabeto_trace import TraceGuide
else:
    from alfabeto_model import PICTURE_PENDING
    from alfabeto_strokes import resample
    from alfabeto_trace import TraceGuide


PACKAGE_ROOT: Final = Path(__file__).resolve().parent
ACTIVITY_PREFIX: Final = "activity:"
MEADOW_LAYERS: Final = ("sky", "far", "mid", "ground", "foreground")

INK: Final = (75, 55, 47)          # cast ink #4B372F
CREAM: Final = (255, 251, 235)     # cast cream #FFFBEB
SAND: Final = (238, 221, 186)      # theme sand
GLOW: Final = (255, 194, 52)       # theme sunshine
# runtime/theme-defaults accent tokens used for letter inks
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
MAX_GLYPHS: Final = 40


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


def _thick_path(surface: pygame.Surface, points, radius: float, color) -> None:
    """Round-capped, round-joined thick polyline (circles along the path)."""

    r = max(1, int(round(radius)))
    for x, y in points:
        pygame.draw.circle(surface, color, (int(round(x)), int(round(y))), r)


class LetterGlyphs:
    """Render stroke-font letters (solid, hollow guide) once and cache them."""

    def __init__(self, *, max_entries: int = MAX_GLYPHS) -> None:
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

    def tile(self, char: str, size: int, token: str) -> pygame.Surface:
        """Solid letter centred in a ``size`` square (choice tiles, garden)."""

        size = max(8, int(size))
        guide = TraceGuide.fit(char, (0, 0, size, size))
        return self._cached(("tile", char, size, token), lambda: self._render(guide, (size, size), accent(token), hollow=False))

    def solid(self, guide: TraceGuide, size: tuple[int, int], token: str) -> pygame.Surface:
        key = ("solid", guide.char, guide.origin, guide.scale, size, token)
        return self._cached(key, lambda: self._render(guide, size, accent(token), hollow=False))

    def hollow(self, guide: TraceGuide, size: tuple[int, int]) -> pygame.Surface:
        key = ("hollow", guide.char, guide.origin, guide.scale, size)
        return self._cached(key, lambda: self._render(guide, size, CREAM, hollow=True))

    @staticmethod
    def _render(guide: TraceGuide, size: tuple[int, int], fill, *, hollow: bool) -> pygame.Surface:
        s = SUPERSAMPLE
        big = pygame.Surface((size[0] * s, size[1] * s), pygame.SRCALPHA)
        band = guide.band * s
        outline = max(2.0 * s, band * 0.12)
        paths = [resample([(x * s, y * s) for x, y in stroke.points], max(1.0, band * 0.12)) for stroke in guide.strokes]
        for points in paths:
            _thick_path(big, points, band / 2 + outline, INK)
        for points in paths:
            _thick_path(big, points, band / 2, fill)
        if not hollow:
            light = mix(fill, (255, 255, 255), 0.38)
            # One soft highlight per letter: a thin lighter line on the first stroke.
            first = paths[0]
            cut = max(2, len(first) // 3)
            offset = band * 0.16
            _thick_path(big, [(x - offset, y - offset) for x, y in first[:cut]], band * 0.11, light)
        else:
            # Gentle centre-line dots show the path inside the hollow letter.
            dot = max(2.0, band * 0.07)
            for points in paths:
                for x, y in resample(points, band * 0.75)[1:-1]:
                    pygame.draw.circle(big, SAND, (int(x), int(y)), int(dot))
        return pygame.transform.smoothscale(big, size)


class TraceInk:
    """The child's ink inside the tracing box, added incrementally as they trace."""

    def __init__(self, guide: TraceGuide, size: tuple[int, int], token: str) -> None:
        self.guide = guide
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        self.color = accent(token)
        self.radius = max(2, int(guide.band * 0.40))
        self._drawn = [0.0 for _ in guide.strokes]

    def sync(self, stroke_index: int, progress: float) -> bool:
        """Draw any newly traced ink; True when the surface changed."""

        changed = False
        for index, stroke in enumerate(self.guide.strokes):
            target = stroke.length if index < stroke_index else (progress if index == stroke_index else 0.0)
            if target <= self._drawn[index] + 0.5:
                continue
            start = stroke.index_at(self._drawn[index])
            stop = stroke.index_at(target)
            for x, y in stroke.points[max(0, start - 1): stop + 1]:
                pygame.draw.circle(self.surface, self.color, (int(round(x)), int(round(y))), self.radius)
            self._drawn[index] = target
            changed = True
        return changed


class AlfabetoArt:
    """Own the meadow backdrop and every cached picture, pose, FX and glyph."""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        resolver: Callable[[str, str], Path] = resolve_picture,
        art: ControlArt | None = None,
    ) -> None:
        self._size = (int(width), int(height))
        self.art = art if art is not None else ControlArt(resolver, max_entries=96)
        self.glyphs = LetterGlyphs()
        self.background = self._build_background(resolver)
        self._glows: dict[int, pygame.Surface] = {}

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
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def picture(self, picture_id: str, size: int) -> pygame.Surface | None:
        if not picture_id or picture_id == PICTURE_PENDING:
            return None
        return self.art.image(picture_id, int(size))

    def fx(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self.art.image(asset_id, int(size))

    def hud(self, glyph: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"icon.hud.{glyph}", int(size))

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the speaking/hinted element (built once per size)."""

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
        self.glyphs.clear()
        self._glows.clear()


__all__ = ["AlfabetoArt", "LetterGlyphs", "TraceInk", "accent", "resolve_picture"]
