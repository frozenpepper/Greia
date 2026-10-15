"""Baia delle Orche — bounded asset cache.

Art comes from the shared Greia library (``bg.sea_surface.*``,
``bg.night_sky.*``, ``creature.marine.orca_*``, props and ``fx.*``) resolved
semantically, plus a few Activity-private renditions under ``assets/runtime``
(the fjord range and aurora, Oskar the elder, herring, squid, hoop). One owner
decodes, crops, scales, rotates and bakes, so drawing only ever blits.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import pygame

try:
    from orca_content import (
        ASSETS_DIR,
        FOOD_ART,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        ArtRef,
    )
except ImportError:
    from .orca_content import (
        ASSETS_DIR,
        FOOD_ART,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WATER_SURFACE_Y,
        ArtRef,
    )

VisualResolver = Callable[[str, str], Path]

# Horizon of the shared sea layer; it is stretched once to the bay's horizon.
_SEA_LAYER_HORIZON = 334
# The private fjord range is authored for the bay's horizon.
_FJORD_HORIZON = 290
# Night is the same fjord under moonlight (one multiply at bake time); the
# sea keeps a little more blue than the mountains so the orcas stay readable.
_NIGHT_RANGE_TINT = (78, 92, 150)
_NIGHT_SEA_TINT = (88, 112, 170)
# Day water keeps the bay's original deep, saturated ocean blue (the old
# renderer's gradient); the shared sea layer contributes only its wavelets.
_DAY_WATER_TOP = (2, 132, 199)
_DAY_WATER_BOTTOM = (3, 105, 161)
_WAVELET_STRENGTH = (150, 150, 150)
# The night sky's moon (and glow) sits top-right under the HUD counters; it
# is moved left along the same rows (the sky gradient is vertical) so it rises
# clear of the counters between the fjord peaks.
_MOON_PATCH = pygame.Rect(812, 12, 176, 176)
_MOON_TARGET_X = 162
_SKY_FILL_COLUMN = 760

_MAX_SCALED = 128
# Orca rotation is quantized so a long session touches a small, bounded set.
ANGLE_STEP = 6
MAX_ANGLE = 30


def _default_resolver(asset_id: str, variant: str) -> Path:
    from greia_platform.activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


def _convert(image: pygame.Surface, *, alpha: bool = True) -> pygame.Surface:
    """Convert a freshly decoded/baked surface once when a display exists."""

    if pygame.display.get_surface() is not None:
        try:
            return image.convert_alpha() if alpha else image.convert()
        except pygame.error:
            return image
    return image


def fit_size(size: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    """Largest size with ``size``'s aspect that fits inside ``box``."""

    width, height = size
    scale = min(box[0] / max(1, width), box[1] / max(1, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def quantize_angle(angle: float) -> int:
    clamped = max(-MAX_ANGLE, min(MAX_ANGLE, angle))
    return int(round(clamped / ANGLE_STEP) * ANGLE_STEP)


class OrcaAssetCache:
    """Owner of decoded, cropped, scaled, rotated and baked bay surfaces.

    The decoded working set is bounded by the fixed art list; scaled/rotated
    sprites live in a hard-capped LRU so a long session on the Acer floor never
    grows memory. Missing art degrades to ``None`` and the renderer falls back
    to simple shapes instead of failing.
    """

    def __init__(self, resolver: VisualResolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self._private: dict[str, Optional[pygame.Surface]] = {}
        self._shared: dict[tuple[str, str], Optional[pygame.Surface]] = {}
        self._crops: dict[str, pygame.Rect] = {}
        self._scaled: OrderedDict[tuple, Optional[pygame.Surface]] = OrderedDict()
        self._backgrounds: dict[bool, pygame.Surface] = {}

    # -- decoding ----------------------------------------------------------

    def private_image(self, stem: str) -> Optional[pygame.Surface]:
        if stem in self._private:
            return self._private[stem]
        path = ASSETS_DIR / f"{stem}.png"
        image: Optional[pygame.Surface] = None
        try:
            image = _convert(pygame.image.load(str(path)))
        except Exception:
            image = None
        self._private[stem] = image
        return image

    def shared_image(self, asset_id: str, variant: str = "default") -> Optional[pygame.Surface]:
        key = (asset_id, variant)
        if key in self._shared:
            return self._shared[key]
        image: Optional[pygame.Surface] = None
        try:
            image = _convert(pygame.image.load(str(self._resolver(asset_id, variant))))
        except Exception:
            image = None
        self._shared[key] = image
        return image

    def art_image(self, art: ArtRef, variant: str = "default") -> Optional[pygame.Surface]:
        if art.private:
            suffix = "" if variant == "default" else f"_{variant}"
            return self.private_image(f"{art.private}{suffix}")
        if art.shared:
            return self.shared_image(art.shared, variant)
        return None

    # -- bounded scaled cache ---------------------------------------------

    def _get(self, key: tuple) -> tuple[bool, Optional[pygame.Surface]]:
        if key in self._scaled:
            self._scaled.move_to_end(key)
            return True, self._scaled[key]
        return False, None

    def _put(self, key: tuple, surface: Optional[pygame.Surface]) -> Optional[pygame.Surface]:
        self._scaled[key] = surface
        while len(self._scaled) > _MAX_SCALED:
            self._scaled.popitem(last=False)
        return surface

    @property
    def scaled_count(self) -> int:
        return len(self._scaled)

    def fitted(self, art: ArtRef, box: tuple[int, int], variant: str = "default") -> Optional[pygame.Surface]:
        """Art cropped to its content and fitted inside ``box`` (cached)."""

        key = ("fit", art, variant, box)
        hit, surface = self._get(key)
        if hit:
            return surface
        source = self.art_image(art, variant)
        if source is None:
            return self._put(key, None)
        crop = source.get_bounding_rect(min_alpha=8)
        if crop.width <= 0 or crop.height <= 0:
            return self._put(key, None)
        cropped = source.subsurface(crop)
        return self._put(key, pygame.transform.smoothscale(cropped, fit_size(crop.size, box)))

    def shared_fit(self, asset_id: str, box: tuple[int, int], variant: str = "default") -> Optional[pygame.Surface]:
        return self.fitted(ArtRef(shared=asset_id), box, variant)

    def food(self, kind: str, size: int) -> Optional[pygame.Surface]:
        art = FOOD_ART.get(kind)
        return self.fitted(art, (size, size)) if art is not None else None

    def orca(self, orca_id: str, variant: str, facing_right: bool, angle: float) -> Optional[pygame.Surface]:
        """One orca pose, fitted into its box, flipped and rotated (cached).

        Every variant of one orca is cropped with the same rectangle (the union
        of its swim/happy/asleep art) so swapping the face never makes the body
        jump. ``angle`` is in degrees, counter-clockwise, and quantized.
        """

        look = ORCA_LOOKS[orca_id]
        quant = quantize_angle(angle)
        key = ("orca", orca_id, variant, facing_right, quant)
        hit, surface = self._get(key)
        if hit:
            return surface
        upright_key = ("orca", orca_id, variant, facing_right, 0)
        upright = self._scaled.get(upright_key) if quant != 0 else None
        if upright is None:
            source = self.art_image(look.art, variant)
            if source is None and variant != "default":
                source = self.art_image(look.art, "default")
            if source is None:
                return self._put(key, None)
            crop = self._orca_crop(orca_id, source)
            cropped = source.subsurface(crop.clip(source.get_rect()))
            upright = pygame.transform.smoothscale(cropped, fit_size(cropped.get_size(), look.box))
            if not facing_right:
                upright = pygame.transform.flip(upright, True, False)
            if quant == 0:
                return self._put(key, upright)
            self._put(upright_key, upright)
        return self._put(key, pygame.transform.rotozoom(upright, quant, 1.0))

    def _orca_crop(self, orca_id: str, source: pygame.Surface) -> pygame.Rect:
        cached = self._crops.get(orca_id)
        if cached is not None:
            return cached
        art = ORCA_LOOKS[orca_id].art
        rect = source.get_bounding_rect(min_alpha=8)
        for variant in ("default", "happy", "asleep"):
            image = self.art_image(art, variant)
            if image is not None:
                rect = rect.union(image.get_bounding_rect(min_alpha=8))
        self._crops[orca_id] = rect
        return rect

    def rotated(self, art: ArtRef, box: tuple[int, int], angle: int) -> Optional[pygame.Surface]:
        """Small prop (the ball) rotated in coarse steps (cached)."""

        step = int(angle) % 360 // 15 * 15
        key = ("rot", art, box, step)
        hit, surface = self._get(key)
        if hit:
            return surface
        base = self.fitted(art, box)
        if base is None:
            return self._put(key, None)
        return self._put(key, pygame.transform.rotate(base, step) if step else base)

    # -- backgrounds -------------------------------------------------------

    def background(self, night: bool) -> pygame.Surface:
        cached = self._backgrounds.get(night)
        if cached is None:
            cached = self._bake_background(night)
            self._backgrounds[night] = cached
        return cached

    def invalidate_background(self) -> None:
        self._backgrounds.clear()

    def _bake_background(self, night: bool) -> pygame.Surface:
        bg = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        horizon = int(WATER_SURFACE_Y)
        sky_layers = ("bg.night_sky.sky", "bg.night_sky.stars") if night else ("bg.sea_surface.sky",)
        drew_sky = False
        for layer in sky_layers:
            image = self.shared_image(layer)
            if image is not None:
                bg.blit(image, (0, 0))
                drew_sky = True
                if layer == "bg.night_sky.sky":
                    _move_moon(bg)
        if not drew_sky:
            bg.fill((24, 36, 70) if night else (186, 226, 247))
        if night:
            aurora = self.private_image("fjord_aurora")
            if aurora is not None:
                bg.blit(aurora, (0, 0))
        fjord = self.private_image("fjord_far")
        if fjord is not None:
            if night:
                fjord = fjord.copy()
                fjord.fill(_NIGHT_RANGE_TINT, special_flags=pygame.BLEND_RGB_MULT)
            bg.blit(fjord, (0, horizon - _FJORD_HORIZON))
        sea = self.shared_image("bg.sea_surface.sea")
        water_rect = pygame.Rect(0, horizon, REFERENCE_WIDTH, REFERENCE_HEIGHT - horizon)
        band: pygame.Surface | None = None
        if sea is not None and sea.get_height() > _SEA_LAYER_HORIZON:
            band = sea.subsurface(pygame.Rect(0, _SEA_LAYER_HORIZON, sea.get_width(), sea.get_height() - _SEA_LAYER_HORIZON))
            band = pygame.transform.smoothscale(band, water_rect.size)
        if night:
            if band is not None:
                water = band.copy()
            else:
                water = pygame.Surface(water_rect.size)
                water.fill((74, 145, 216))
            water.fill(_NIGHT_SEA_TINT, special_flags=pygame.BLEND_RGB_MULT)
        else:
            water = _vertical_gradient(water_rect.size, _DAY_WATER_TOP, _DAY_WATER_BOTTOM)
            if band is not None:
                water.blit(_wavelets(band), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        bg.blit(water, water_rect.topleft)
        return _convert(bg, alpha=False)


def _vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> pygame.Surface:
    surface = pygame.Surface(size)
    width, height = size
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        pygame.draw.line(surface, color, (0, y), (width, y))
    return surface


def _wavelets(band: pygame.Surface) -> pygame.Surface:
    """Only what is brighter than each row's average (the wavelets/sparkles)."""

    width, height = band.get_size()
    average = pygame.Surface((width, height))
    for y in range(height):
        color = pygame.transform.average_color(band, pygame.Rect(0, y, width, 1))[:3]
        pygame.draw.line(average, color, (0, y), (width, y))
    highlights = band.copy()
    highlights.blit(average, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    highlights.fill(_WAVELET_STRENGTH, special_flags=pygame.BLEND_RGB_MULT)
    return highlights


def _move_moon(sky: pygame.Surface) -> None:
    patch_rect = _MOON_PATCH.clip(sky.get_rect())
    if patch_rect.width <= 0:
        return
    patch = sky.subsurface(patch_rect).copy()
    column = sky.subsurface(pygame.Rect(_SKY_FILL_COLUMN, patch_rect.top, 1, patch_rect.height))
    sky.blit(pygame.transform.scale(column, patch_rect.size), patch_rect.topleft)
    sky.blit(patch, (_MOON_TARGET_X, patch_rect.top))


__all__ = ["ANGLE_STEP", "MAX_ANGLE", "OrcaAssetCache", "fit_size", "quantize_angle"]
