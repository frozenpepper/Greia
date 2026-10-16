"""Acquario Magico — bounded asset cache.

The Aquarium hot path mixes decoded sprites, scaled copies and two baked scene
backgrounds. Art comes from the shared Greia library (``bg.underwater.*``,
``creature.marine.*``, ``fx.*``, props) resolved semantically, plus a few
Activity-private renditions under ``assets/runtime`` (pufferfish, kelp, chest,
food, bubble). The cache owner is explicit so decoding, cropping, scaling,
bounds and invalidation live in one place: drawing only ever blits.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Optional

import pygame

if __package__:
    from .acquarium_content import ASSETS_DIR, REFERENCE_HEIGHT, REFERENCE_WIDTH, _Species
else:
    from acquarium_content import ASSETS_DIR, REFERENCE_HEIGHT, REFERENCE_WIDTH, _Species

VisualResolver = Callable[[str, str], Path]

# Layer order of the shared underwater scene kit; the kelp forest (the
# aquarium's signature) is planted between the far reef and the mid corals.
_UNDERWATER_BACK = ("bg.underwater.far",)
_UNDERWATER_FRONT = ("bg.underwater.mid", "bg.underwater.ground", "bg.underwater.foreground")
_KELP_POSITIONS = ((150, 1.0), (300, 0.86), (560, 0.94), (730, 0.82), (850, 1.0))

# The aquarium's recognisable colour mood: a vivid blue tank. The shared
# water layer keeps its light rays; this gradient multiplies it bluer.
_WATER_TINT_TOP = (52, 178, 240)
_WATER_TINT_BOTTOM = (16, 116, 196)
# Night is the same reef under moonlight (one multiply at bake time).
_NIGHT_TINT = (86, 98, 176)

_MAX_SCALED = 256


def _default_resolver(asset_id: str, variant: str) -> Path:
    from greia_platform.activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


def _convert_surface(image: pygame.Surface) -> pygame.Surface:
    """Convert a freshly decoded surface once when a display exists."""

    if pygame.display.get_surface() is not None:
        try:
            return image.convert_alpha()
        except pygame.error:
            return image
    return image


def _fit(size: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    """Largest size with ``size``'s aspect that fits inside ``box``."""

    width, height = size
    box_w, box_h = box
    scale = min(box_w / max(1, width), box_h / max(1, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


class AquariumAssetCache:
    """Owner of decoded, cropped, scaled and baked Aquarium surfaces.

    The working set is bounded by the fixed species/prop/FX catalogue; the
    scaled-surface cache is additionally hard-capped. Background entries are
    explicitly invalidated on resize. Missing art degrades to ``None`` so the
    renderer can fall back to simple vector shapes instead of failing.
    """

    def __init__(self, resolver: VisualResolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self._images: dict[str, Optional[pygame.Surface]] = {}
        self._shared: dict[tuple[str, str], Optional[pygame.Surface]] = {}
        self._crops: dict[str, pygame.Rect] = {}
        self._scales: dict[tuple, Optional[pygame.Surface]] = {}
        self._backgrounds: dict[tuple[str, int, int], pygame.Surface] = {}
        self._glow: dict[int, pygame.Surface] = {}
        self._composite: Optional[pygame.Surface] = None

    # ------------------------------------------------------------------
    # Decoding
    # ------------------------------------------------------------------

    def load_image(self, filename: str) -> Optional[pygame.Surface]:
        """Decode one Activity-private runtime PNG once."""

        if filename in self._images:
            return self._images[filename]
        path = ASSETS_DIR / filename
        image: Optional[pygame.Surface] = None
        if path.exists():
            try:
                image = _convert_surface(pygame.image.load(str(path)))
            except Exception:
                image = None
        self._images[filename] = image
        return image

    def shared_image(self, asset_id: str, variant: str = "default") -> Optional[pygame.Surface]:
        """Decode one shared-library rendition once (semantic id + variant)."""

        key = (asset_id, variant)
        if key in self._shared:
            return self._shared[key]
        image: Optional[pygame.Surface] = None
        try:
            image = _convert_surface(pygame.image.load(str(self._resolver(asset_id, variant))))
        except Exception:
            image = None
        self._shared[key] = image
        return image

    def _remember(self, key: tuple, surface: Optional[pygame.Surface]) -> Optional[pygame.Surface]:
        if len(self._scales) >= _MAX_SCALED:
            self._scales.clear()
        self._scales[key] = surface
        return surface

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------

    def scaled(
        self,
        filename: str,
        width: int,
        height: int,
        facing_right: bool = True,
    ) -> Optional[pygame.Surface]:
        """Activity-private PNG scaled once to exactly ``width`` x ``height``."""

        key = ("file", filename, width, height, facing_right)
        if key in self._scales:
            return self._scales[key]
        original = self.load_image(filename)
        if original is None:
            return self._remember(key, None)
        try:
            surface = pygame.transform.smoothscale(original, (width, height))
        except Exception:
            return self._remember(key, None)
        if not facing_right:
            surface = pygame.transform.flip(surface, True, False)
        return self._remember(key, surface)

    def shared_fit(
        self,
        asset_id: str,
        box: tuple[int, int],
        variant: str = "default",
    ) -> Optional[pygame.Surface]:
        """Shared art cropped to its content and fitted inside ``box`` once."""

        key = ("shared", asset_id, variant, box)
        if key in self._scales:
            return self._scales[key]
        source = self.shared_image(asset_id, variant)
        if source is None:
            return self._remember(key, None)
        crop = source.get_bounding_rect(min_alpha=8)
        if crop.width <= 0 or crop.height <= 0:
            return self._remember(key, None)
        cropped = source.subsurface(crop)
        return self._remember(key, pygame.transform.smoothscale(cropped, _fit(crop.size, box)))

    def creature(
        self,
        species: _Species,
        variant: str,
        box: tuple[int, int],
        facing_right: bool = True,
    ) -> Optional[pygame.Surface]:
        """Creature sprite fitted into its hit box, cached per variant/facing.

        Every variant of one species is cropped with the same rectangle (the
        union of its swim and happy art) so swapping to ``happy`` never makes
        the body jump. The private ``puffed`` pufferfish is cropped on its own
        because it is deliberately bigger.
        """

        key = ("creature", species["id"], variant, box, facing_right)
        if key in self._scales:
            return self._scales[key]
        source = self._creature_source(species, variant)
        if source is None:
            if variant != "default":
                return self._remember(key, self.creature(species, "default", box, facing_right))
            return self._remember(key, None)
        crop = self._creature_crop(species, variant, source)
        cropped = source.subsurface(crop.clip(source.get_rect()))
        surface = pygame.transform.smoothscale(cropped, _fit(cropped.get_size(), box))
        if not facing_right:
            surface = pygame.transform.flip(surface, True, False)
        return self._remember(key, surface)

    def _creature_source(self, species: _Species, variant: str) -> Optional[pygame.Surface]:
        private = species.get("private")
        if private:
            suffix = "" if variant == "default" else f"_{variant}"
            return self.load_image(f"{private}{suffix}.png")
        visual = species.get("visual")
        if not visual or variant == "puffed":
            return None
        return self.shared_image(visual, variant)

    def _creature_crop(self, species: _Species, variant: str, source: pygame.Surface) -> pygame.Rect:
        if variant == "puffed":
            return source.get_bounding_rect(min_alpha=8)
        cached = self._crops.get(species["id"])
        if cached is not None:
            return cached
        rect = source.get_bounding_rect(min_alpha=8)
        for other in ("default", "happy"):
            image = self._creature_source(species, other)
            if image is not None:
                rect = rect.union(image.get_bounding_rect(min_alpha=8))
        self._crops[species["id"]] = rect
        return rect

    def bubble(self, diameter: int) -> Optional[pygame.Surface]:
        """Rising-bubble sprite, quantized to even sizes so the cache stays tiny."""

        size = max(6, min(48, int(diameter) // 2 * 2))
        return self.scaled("bubble.png", size, size)

    def glow(self, radius: int) -> pygame.Surface:
        """Soft night glow (a light source, built once per radius)."""

        cached = self._glow.get(radius)
        if cached is not None:
            return cached
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 10
        for step in range(steps, 0, -1):
            ring = radius * step / steps
            alpha = int(70 * (1.0 - step / steps) ** 1.4) + 6
            pygame.draw.circle(surface, (214, 160, 255, alpha), (radius, radius), int(ring))
        if len(self._glow) > 8:
            self._glow.clear()
        self._glow[radius] = surface
        return surface

    # ------------------------------------------------------------------
    # Backgrounds
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
        """Drop cached scene backgrounds after a viewport-size change."""

        self._backgrounds.clear()

    def _bake_background(self, glow_mode: bool, width: int, height: int) -> pygame.Surface:
        # The day scene composite (five full-screen alpha layers, ~0.7 s on
        # the Atom) is kept once; night is that composite with the night tint,
        # so the day/night toggle no longer re-composes it.
        if self._composite is None:
            self._composite = self._compose_scene()
        bg = self._composite.copy()
        if glow_mode:
            bg.fill(_NIGHT_TINT, special_flags=pygame.BLEND_MULT)
        if (width, height) != (REFERENCE_WIDTH, REFERENCE_HEIGHT):
            bg = pygame.transform.smoothscale(bg, (width, height))
        if pygame.display.get_surface() is not None:
            try:
                bg = bg.convert()
            except pygame.error:
                pass
        return bg

    def _compose_scene(self) -> pygame.Surface:
        """The untinted day scene at the reference size (composed once)."""

        bg = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        water = self.shared_image("bg.underwater.water")
        if water is not None:
            bg.blit(water, (0, 0))
            bg.blit(_vertical_gradient(_WATER_TINT_TOP, _WATER_TINT_BOTTOM), (0, 0), special_flags=pygame.BLEND_MULT)
        else:
            bg.blit(_vertical_gradient((14, 165, 233), (2, 130, 195)), (0, 0))
        for layer in _UNDERWATER_BACK:
            image = self.shared_image(layer)
            if image is not None:
                bg.blit(image, (0, 0))
        for x, scale in _KELP_POSITIONS:
            kelp = self.scaled("kelp.png", int(78 * scale), int(270 * scale))
            if kelp is not None:
                bg.blit(kelp, (x, 492 - kelp.get_height()))
        front = [self.shared_image(layer) for layer in _UNDERWATER_FRONT]
        if any(image is None for image in front):
            pygame.draw.rect(bg, (254, 243, 199), (0, 490, REFERENCE_WIDTH, REFERENCE_HEIGHT - 490))
        for image in front:
            if image is not None:
                bg.blit(image, (0, 0))
        return bg


def _vertical_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> pygame.Surface:
    surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
    for y in range(0, REFERENCE_HEIGHT, 4):
        ratio = y / float(REFERENCE_HEIGHT - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        pygame.draw.rect(surface, color, (0, y, REFERENCE_WIDTH, 4))
    return surface
