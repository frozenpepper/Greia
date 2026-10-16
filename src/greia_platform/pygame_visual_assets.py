"""Bounded runtime surface cache for explicit Greia shared visual assets.

The catalogue resolves semantic IDs to pre-rendered PNG renditions. This adapter
loads/scales those PNGs lazily and caches final surfaces by semantic variant and
requested size. It never scans asset directories and never rasterizes SVG source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from .assets import AssetCatalogue
from .ui_core import BoundedCache

SurfaceT = TypeVar("SurfaceT")
_MAX_SURFACE_DIMENSION = 2048
_DEFAULT_MAX_SURFACE_PIXELS = 1920 * 1080


class VisualSurfaceCacheError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VisualSurfaceKey:
    asset_id: str
    variant: str
    size: tuple[int, int]


class PygameVisualSurfaceCache(Generic[SurfaceT]):
    """Hard-bounded cache for decoded/scaled shared visual PNG surfaces.

    `image_loader` and `image_scaler` are injected so the cache remains
    provider-free in unit tests and does not initialize a display by itself.
    Use `for_pygame()` in Pygame consumers.

    The entry bound alone does not bound memory: one entry may be a 32x32
    glyph or a full-display scene layer. ``max_total_pixels`` adds an LRU
    pixel budget so a long session that visits every Collection/Activity
    plateaus at a known byte cost (about 4 bytes per pixel) instead of
    retaining up to ``max_entries`` display-sized renditions.
    """

    def __init__(
        self,
        catalogue: AssetCatalogue,
        *,
        image_loader: Callable[[Path], SurfaceT],
        image_scaler: Callable[[SurfaceT, tuple[int, int]], SurfaceT],
        max_entries: int = 12,
        max_surface_pixels: int = _DEFAULT_MAX_SURFACE_PIXELS,
        max_total_pixels: int | None = None,
        display_converter: Callable[[SurfaceT], SurfaceT] | None = None,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if max_surface_pixels < 1:
            raise ValueError("max_surface_pixels must be positive")
        if max_total_pixels is not None and max_total_pixels < max_surface_pixels:
            raise ValueError("max_total_pixels must hold at least one maximal surface")
        self.catalogue = catalogue
        self._image_loader = image_loader
        self._image_scaler = image_scaler
        # Optional one-time conversion applied to freshly loaded surfaces so
        # display-backed consumers never pay the slow generic blit path on
        # every frame. Provider-free consumers simply leave it as None.
        self._display_converter = display_converter
        self.max_surface_pixels = int(max_surface_pixels)
        self.max_total_pixels = (
            None if max_total_pixels is None else int(max_total_pixels)
        )
        self._total_pixels = 0
        self._surfaces: BoundedCache[VisualSurfaceKey, SurfaceT] = BoundedCache(
            max_entries, on_evict=self._forget_pixels
        )

    def _forget_pixels(self, key: VisualSurfaceKey, _surface: SurfaceT) -> None:
        self._total_pixels -= key.size[0] * key.size[1]

    @property
    def cached_pixels(self) -> int:
        """Pixels currently retained (cached surfaces are exactly key-sized)."""

        return self._total_pixels

    @classmethod
    def for_pygame(
        cls,
        catalogue: AssetCatalogue,
        *,
        max_entries: int = 12,
        max_surface_pixels: int = _DEFAULT_MAX_SURFACE_PIXELS,
        max_total_pixels: int | None = None,
        display_converter: Callable[[object], object] | None = None,
    ) -> "PygameVisualSurfaceCache[object]":
        """Create a cache using Pygame's PNG loader and one-time smooth scaler.

        Pygame is imported lazily so importing this module remains safe in
        provider-free tooling/tests. The loader deliberately does not call
        `convert()`/`convert_alpha()`, which would require an initialized
        display; pass `display_converter` when a live display exists so cached
        surfaces are converted exactly once before first use.
        """

        import pygame

        return cls(
            catalogue,
            image_loader=lambda path: pygame.image.load(str(path)),
            image_scaler=lambda surface, size: (
                surface
                if surface.get_size() == size
                else pygame.transform.smoothscale(surface, size)
            ),
            max_entries=max_entries,
            max_surface_pixels=max_surface_pixels,
            max_total_pixels=max_total_pixels,
            display_converter=display_converter,
        )

    @property
    def max_entries(self) -> int:
        return self._surfaces.max_entries

    def __len__(self) -> int:
        return len(self._surfaces)

    def get(
        self,
        asset_id: str,
        *,
        variant: str = "default",
        size: tuple[int, int],
    ) -> SurfaceT:
        normalized_size = _validate_size(size, self.max_surface_pixels)
        key = VisualSurfaceKey(
            asset_id=asset_id,
            variant=variant,
            size=normalized_size,
        )
        cached = self._surfaces.get(key)
        if cached is not None:
            return cached

        asset = self.catalogue.get_visual(asset_id)
        path = asset.path_for(variant)
        if path.suffix.lower() != ".png":
            raise VisualSurfaceCacheError(
                "runtime visual must resolve to a PNG rendition: "
                f"{asset_id!r}/{variant!r} -> {path.name}"
            )

        surface = self._image_loader(path)
        surface = self._image_scaler(surface, normalized_size)
        if self._display_converter is not None:
            try:
                converted = self._display_converter(surface)
            except Exception:
                # A converter failure must never make shared artwork fatal; the
                # unconverted surface remains usable through the slow path.
                converted = surface
            surface = converted
        self._surfaces[key] = surface
        self._total_pixels += normalized_size[0] * normalized_size[1]
        budget = self.max_total_pixels
        if budget is not None:
            # Evict least-recently-used renditions, never the one just made.
            while self._total_pixels > budget and len(self._surfaces) > 1:
                self._surfaces.pop_oldest()
        return surface

    def clear(self) -> None:
        self._surfaces.clear()


def pygame_display_converter() -> Callable[[object], object]:
    """Return a display-format converter for cached visual surfaces.

    Conversion happens once per cached surface at fetch time. Opaque surfaces
    become plain display surfaces (fast opaque blits) and alpha surfaces become
    display-alpha surfaces (hardware-friendly blended blits). The returned
    callable never raises for valid pygame surfaces.
    """

    import pygame

    def convert(surface: object) -> object:
        get_bitsize = getattr(surface, "get_bitsize", None)
        get_flags = getattr(surface, "get_flags", None)
        if not callable(get_bitsize) or not callable(get_flags):
            return surface
        if get_flags() & pygame.SRCALPHA:
            return surface.convert_alpha()
        return surface.convert()

    return convert


def _validate_size(
    size: tuple[int, int], max_surface_pixels: int
) -> tuple[int, int]:
    if not isinstance(size, tuple) or len(size) != 2:
        raise VisualSurfaceCacheError("size must be a (width, height) tuple")
    width, height = size
    for label, value in (("width", width), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise VisualSurfaceCacheError(f"{label} must be an integer")
        if value < 1 or value > _MAX_SURFACE_DIMENSION:
            raise VisualSurfaceCacheError(
                f"{label} must be between 1 and {_MAX_SURFACE_DIMENSION}"
            )
    pixels = width * height
    if pixels > max_surface_pixels:
        raise VisualSurfaceCacheError(
            f"requested surface is too large: {width}x{height} exceeds "
            f"{max_surface_pixels} cached pixels"
        )
    return (width, height)
