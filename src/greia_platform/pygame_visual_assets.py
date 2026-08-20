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
_DEFAULT_MAX_SURFACE_PIXELS = 1024 * 600


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
    """

    def __init__(
        self,
        catalogue: AssetCatalogue,
        *,
        image_loader: Callable[[Path], SurfaceT],
        image_scaler: Callable[[SurfaceT, tuple[int, int]], SurfaceT],
        max_entries: int = 12,
        max_surface_pixels: int = _DEFAULT_MAX_SURFACE_PIXELS,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if max_surface_pixels < 1:
            raise ValueError("max_surface_pixels must be positive")
        self.catalogue = catalogue
        self._image_loader = image_loader
        self._image_scaler = image_scaler
        self.max_surface_pixels = int(max_surface_pixels)
        self._surfaces: BoundedCache[VisualSurfaceKey, SurfaceT] = BoundedCache(
            max_entries
        )

    @classmethod
    def for_pygame(
        cls,
        catalogue: AssetCatalogue,
        *,
        max_entries: int = 12,
        max_surface_pixels: int = _DEFAULT_MAX_SURFACE_PIXELS,
    ) -> "PygameVisualSurfaceCache[object]":
        """Create a cache using Pygame's PNG loader and one-time smooth scaler.

        Pygame is imported lazily so importing this module remains safe in
        provider-free tooling/tests. The loader deliberately does not call
        `convert()`/`convert_alpha()`, which would require an initialized display.
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
        self._surfaces[key] = surface
        return surface

    def clear(self) -> None:
        self._surfaces.clear()


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
