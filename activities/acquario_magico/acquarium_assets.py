"""Acquario Magico — bounded asset cache.

The Aquarium hot path is a heavy mix of decoded PNG sprites, scaled
copies, and the two pre-rendered scene backgrounds. Per the
``docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`` 2026-08-22
case study, the pre-rendered background and the bidirectional
scaled-sprite cache together drop the per-frame background cost
under 0.15 ms on the Atom reference floor.

The cache owner is an explicit object so the bounds, the conversion
strategy and the rebuild invalidation rules live in one place.
Three caches, one owner:

- ``_image_cache``: raw decoded PNGs, ``convert_alpha()`` once
  when a display surface exists.
- ``_scale_cache``: ``smoothscale`` + facing-flip by
  ``(filename, w, h, facing_right)``; the existing 2026-08-22
  ``(asset, w, h, facing)`` key keeps the case study results
  reproducible.
- ``_background_cache``: pre-rendered day/night scene; one entry
  per (mode, w, h) tuple.

The caches are intentionally module-scoped for backwards
compatibility with the original module-level dicts (the test
suite reads ``_get_cached_background`` and ``_get_scaled_asset``
through this module). The :class:`AquariumAssetCache` wrapper
just owns and rebuilds those dicts.
"""

from __future__ import annotations

from typing import Optional

import pygame

from .acquarium_content import ASSETS_DIR, REFERENCE_HEIGHT, REFERENCE_WIDTH


def _convert_surface(image: pygame.Surface) -> pygame.Surface:
    """Convert a freshly decoded surface exactly once.

    Pygame's generic blit path is significantly slower for
    unconverted surfaces. We convert when a display surface
    exists, otherwise we hand back the unconverted surface so
    headless test runs still get a usable bitmap.
    """

    if pygame.display.get_surface() is not None:
        return image.convert_alpha()
    return image


class AquariumAssetCache:
    """Bounded decoded/scaled/baked asset cache.

    The cache is intentionally not LRU-bounded: the working set
    is the 8 species sprites at 2 facings + the chest and the
    two backgrounds. That sits comfortably under any reasonable
    bound; if the catalogue grows a 100-species Activity this
    owner can grow an explicit max_size without changing callers.
    """

    def __init__(self) -> None:
        self._images: dict[str, Optional[pygame.Surface]] = {}
        self._scales: dict[tuple[str, int, int, bool], Optional[pygame.Surface]] = {}
        self._backgrounds: dict[tuple[str, int, int], pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Image cache
    # ------------------------------------------------------------------

    def load_image(self, filename: str) -> Optional[pygame.Surface]:
        if filename in self._images:
            return self._images[filename]
        path = ASSETS_DIR / filename
        if not path.exists():
            self._images[filename] = None
            return None
        try:
            image = pygame.image.load(str(path))
        except Exception:
            self._images[filename] = None
            return None
        try:
            image = _convert_surface(image)
        except Exception:
            pass
        self._images[filename] = image
        return image

    # ------------------------------------------------------------------
    # Scale cache (asset, w, h, facing_right)
    # ------------------------------------------------------------------

    def scaled(
        self,
        filename: str,
        width: int,
        height: int,
        facing_right: bool = True,
    ) -> Optional[pygame.Surface]:
        key = (filename, width, height, facing_right)
        if key in self._scales:
            return self._scales[key]
        original = self.load_image(filename)
        if original is None:
            self._scales[key] = None
            return None
        try:
            scaled_surface = pygame.transform.smoothscale(original, (width, height))
        except Exception:
            self._scales[key] = None
            return None
        if not facing_right:
            scaled_surface = pygame.transform.flip(scaled_surface, True, False)
        self._scales[key] = scaled_surface
        return scaled_surface

    # ------------------------------------------------------------------
    # Pre-rendered background cache
    # ------------------------------------------------------------------

    def background(
        self,
        glow_mode: bool,
        width: int = REFERENCE_WIDTH,
        height: int = REFERENCE_HEIGHT,
    ) -> pygame.Surface:
        key = ("night" if glow_mode else "day", width, height)
        cached = self._backgrounds.get(key)
        if cached is not None:
            return cached
        baked = self._bake_background(glow_mode, width, height)
        self._backgrounds[key] = baked
        return baked

    def invalidate_background(self) -> None:
        """Drop cached backgrounds. Used on resize."""

        self._backgrounds.clear()

    # ------------------------------------------------------------------
    # Background bake (replaces ``_get_cached_background``)
    # ------------------------------------------------------------------

    def _bake_background(
        self,
        glow_mode: bool,
        width: int,
        height: int,
    ) -> pygame.Surface:
        bg = pygame.Surface((width, height))
        sand_h = 90
        sand_y = height - sand_h

        if glow_mode:
            for gy in range(0, height, 4):
                ratio = gy / float(height)
                r = int(8 + (18 - 8) * ratio)
                g = int(12 + (24 - 12) * ratio)
                b = int(38 + (65 - 38) * ratio)
                pygame.draw.rect(bg, (r, g, b), (0, gy, width, 4))

            kelp = self.scaled("kelp_night.png", 80, 280)
            if kelp is not None:
                for kx in [70, 200, 360, 560, 720, 880, 950]:
                    bg.blit(kelp, (kx, sand_y - 250))

            pygame.draw.rect(bg, (30, 20, 50), (0, sand_y, width, sand_h))
            pygame.draw.line(bg, (147, 51, 234), (0, sand_y), (width, sand_y), 3)

            coral = self.scaled("coral_reef.png", 220, 165, facing_right=True)
            if coral is not None:
                bg.blit(coral, (20, sand_y - 125))
            coral_flipped = self.scaled("coral_reef.png", 220, 165, facing_right=False)
            if coral_flipped is not None:
                bg.blit(coral_flipped, (width - 240, sand_y - 125))

            for sx in [280, 440, 620, 800]:
                pygame.draw.circle(bg, (250, 204, 21), (sx, sand_y + 25), 10)
                pygame.draw.circle(bg, (255, 255, 255), (sx, sand_y + 25), 5)
        else:
            for gy in range(0, height, 4):
                ratio = gy / float(height)
                r = int(14 + (2 - 14) * ratio)
                g = int(165 + (130 - 165) * ratio)
                b = int(233 + (195 - 233) * ratio)
                pygame.draw.rect(bg, (r, g, b), (0, gy, width, 4))

            kelp = self.scaled("kelp.png", 80, 280)
            if kelp is not None:
                for kx in [70, 200, 360, 560, 720, 880, 950]:
                    bg.blit(kelp, (kx, sand_y - 250))

            pygame.draw.rect(bg, (254, 243, 199), (0, sand_y, width, sand_h))
            pygame.draw.line(bg, (217, 119, 6), (0, sand_y), (width, sand_y), 3)

            coral = self.scaled("coral_reef.png", 220, 165, facing_right=True)
            if coral is not None:
                bg.blit(coral, (20, sand_y - 125))
            coral_flipped = self.scaled("coral_reef.png", 220, 165, facing_right=False)
            if coral_flipped is not None:
                bg.blit(coral_flipped, (width - 240, sand_y - 125))

            for sx in [280, 440, 620, 800]:
                pygame.draw.circle(bg, (244, 114, 182), (sx, sand_y + 25), 11)
                pygame.draw.circle(bg, (255, 255, 255), (sx, sand_y + 25), 5)

        return bg


# ----------------------------------------------------------------------
# Module-level compatibility shims
# ----------------------------------------------------------------------
#
# The original main.py exposed ``_load_asset_surface``,
# ``_get_scaled_asset`` and ``_get_cached_background`` as module-
# level functions backed by three module-level dicts. Existing
# contract tests (test_activity_acquario_magico.py,
# test_activities_phase5.py) and any first-party caller rely on
# the public name ``_get_cached_background`` and
# ``_get_scaled_asset`` still being importable. We keep those
# names but route them through a single shared cache instance so
# the bound and invalidation story is owned in one place.
_SHARED_CACHE = AquariumAssetCache()


def _load_asset_surface(filename: str) -> Optional[pygame.Surface]:
    return _SHARED_CACHE.load_image(filename)


def _get_scaled_asset(
    filename: str,
    width: int,
    height: int,
    facing_right: bool = True,
) -> Optional[pygame.Surface]:
    return _SHARED_CACHE.scaled(filename, width, height, facing_right)


def _get_cached_background(
    glow_mode: bool,
    width: int = REFERENCE_WIDTH,
    height: int = REFERENCE_HEIGHT,
) -> pygame.Surface:
    return _SHARED_CACHE.background(glow_mode, width, height)
