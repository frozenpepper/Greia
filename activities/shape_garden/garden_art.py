"""Shape Garden art: shared-library shapes, backdrops and ghost slots.

Every picture comes from the shared visual catalogue by semantic id:

* shapes are ``prop.shape.<kind>`` tokens. Colour variants are made once per
  (shape, colour) with a gradient map (``PIL.ImageOps.colorize``): the ink
  contour stays cocoa, the white highlight stays white and the two-stop fill
  takes the new accent, so a recoloured token keeps the library finish;
* ghost slots are the matching ``prop.shape.<kind>`` ``slot`` variants;
* backdrops stack ``bg.<biome>.<layer>`` scene layers once into one opaque
  1024x600 surface.

All work happens on first use of a bounded key; drawing is blits only. The
caches are sized for the Acer floor: 16 recoloured 256 px sources (~4 MiB),
a few hundred small sized/turned shapes and two composed backdrops.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageOps
import pygame

from greia_platform.ui_core import BoundedCache

if __package__:
    from .garden_content import (
        BACKDROPS,
        COLOURS,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        SIZE_LEVELS,
        TURN_STEPS,
        backdrop_spec,
    )
else:  # pragma: no cover - direct script fallback
    from garden_content import (
        BACKDROPS,
        COLOURS,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        SIZE_LEVELS,
        TURN_STEPS,
        backdrop_spec,
    )

Resolver = Callable[[str, str], Path]
INK = (75, 55, 47)
WHITE = (255, 255, 255)
SLOT = "slot"


def _default_resolver(asset_id: str, variant: str) -> Path:
    from greia_platform.activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


def _display_ready(surface: pygame.Surface, *, alpha: bool = True) -> pygame.Surface:
    if pygame.display.get_surface() is None:
        return surface
    return surface.convert_alpha() if alpha else surface.convert()


def _pil_to_surface(image: Image.Image) -> pygame.Surface:
    rgba = image.convert("RGBA")
    return pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA")


def recolour(image: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    """Gradient-map one library token to ``colour`` keeping ink and highlight.

    The map is anchored on the token's own median fill luminance, so bright
    (sunshine) and dark (ocean) source tokens recolour to the same accent.
    """

    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    grey = ImageOps.grayscale(rgba.convert("RGB"))
    opaque = alpha.point(lambda value: 255 if value > 250 else 0)
    histogram = grey.histogram(mask=opaque)
    total = sum(histogram)
    median, running = 160, 0
    if total:
        for level, count in enumerate(histogram):
            running += count
            if running * 2 >= total:
                median = level
                break
    black = max(0, median - 95)
    white = min(255, int(median + (255 - median) * 0.78))
    mapped = ImageOps.colorize(
        grey, black=INK, white=WHITE, mid=colour,
        blackpoint=black, whitepoint=max(white, median + 1), midpoint=median,
    ).convert("RGBA")
    mapped.putalpha(alpha)
    return mapped


class ShapeArt:
    """Shared ``prop.shape.*`` tokens: recoloured, sized and turned once."""

    def __init__(self, resolver: Resolver | None = None, *, max_entries: int = 240) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self._pil: BoundedCache[tuple[str, str], Image.Image | None] = BoundedCache(18)
        self._sources: BoundedCache[tuple[str, str], pygame.Surface | None] = BoundedCache(18)
        self._images: BoundedCache[tuple[str, str, int, int], pygame.Surface | None] = BoundedCache(max_entries)

    def _pil_source(self, kind: str, variant: str) -> Image.Image | None:
        key = (kind, variant)
        if key not in self._pil:
            try:
                with Image.open(self._resolver(f"prop.shape.{kind}", variant)) as opened:
                    self._pil[key] = opened.convert("RGBA")
            except Exception:  # noqa: BLE001 - missing art degrades to None
                self._pil[key] = None
        return self._pil[key]

    def _source(self, kind: str, colour: str) -> pygame.Surface | None:
        key = (kind, colour)
        if key in self._sources:
            return self._sources[key]
        surface: pygame.Surface | None = None
        if colour == SLOT:
            base = self._pil_source(kind, "slot")
            surface = _pil_to_surface(base) if base is not None else None
        else:
            base = self._pil_source(kind, "default")
            if base is not None:
                image = base if colour == "natural" else recolour(base, COLOURS.get(colour, COLOURS["coral"]))
                surface = _pil_to_surface(image)
        if surface is not None:
            surface = _display_ready(surface)
        self._sources[key] = surface
        return surface

    def image(self, kind: str, colour: str, side: int, turn: int = 0) -> pygame.Surface | None:
        """The shape art in a ``side`` px box, turned ``turn`` x 45 deg clockwise."""

        side = max(4, int(side))
        turn %= TURN_STEPS
        key = (kind, colour, side, turn)
        if key in self._images:
            return self._images[key]
        source = self._source(kind, colour)
        result: pygame.Surface | None = None
        if source is not None:
            result = source if source.get_width() == side else pygame.transform.smoothscale(source, (side, side))
            if turn:
                result = pygame.transform.rotozoom(result, -45 * turn, 1.0)
        self._images[key] = result
        return result

    def clear(self) -> None:
        self._images.clear()
        self._sources.clear()


class BackdropArt:
    """Compose a scene kit once, then hand out scaled views and thumbnails."""

    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self._full: BoundedCache[str, pygame.Surface] = BoundedCache(2)
        self._scaled: BoundedCache[tuple[str, int, int], pygame.Surface] = BoundedCache(14)

    def full(self, backdrop_id: str) -> pygame.Surface:
        """The opaque 1024x600 composition for one backdrop id."""
        if backdrop_id in self._full:
            return self._full[backdrop_id]
        spec = backdrop_spec(backdrop_id)
        surface = pygame.Surface((GARDEN_WIDTH, GARDEN_HEIGHT))
        surface.fill(spec.paper)
        for layer in spec.layers:
            try:
                image = pygame.image.load(str(self._resolver(layer, "default")))
            except Exception:  # noqa: BLE001 - a missing layer leaves paper behind
                continue
            if image.get_size() != (GARDEN_WIDTH, GARDEN_HEIGHT):
                image = pygame.transform.smoothscale(image, (GARDEN_WIDTH, GARDEN_HEIGHT))
            surface.blit(image, (0, 0))
        surface = _display_ready(surface, alpha=False)
        self._full[backdrop_id] = surface
        return surface

    def scaled(self, backdrop_id: str, size: tuple[int, int]) -> pygame.Surface:
        key = (backdrop_id, int(size[0]), int(size[1]))
        if key in self._scaled:
            return self._scaled[key]
        surface = pygame.transform.smoothscale(self.full(backdrop_id), key[1:])
        self._scaled[key] = surface
        return surface

    def clear(self) -> None:
        self._full.clear()
        self._scaled.clear()

    @staticmethod
    def ids() -> tuple[str, ...]:
        return tuple(spec.backdrop_id for spec in BACKDROPS)


def box_side(size_index: int, scale: float) -> int:
    """Pixel box side of one size step at a drawing scale."""
    return max(4, int(round(SIZE_LEVELS[size_index] * scale)))


__all__ = ["BackdropArt", "ShapeArt", "box_side", "recolour"]
