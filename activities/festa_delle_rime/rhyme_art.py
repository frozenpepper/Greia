"""Art resolution and cached surfaces for Festa delle Rime.

Everything visible comes from library art: the ``bg.night_sky.*`` scene
layers, shared ``prop.*`` pictures, ``fx.*`` bursts, the canonical cast, and
this package's own paper lanterns and three missing pictures (``assets/runtime``,
authored per GREIA_SVG_AUTHORING_RULES from ``assets/source``). Images are
decoded and scaled once into bounded caches; drawing only blits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlArt

if __package__:
    from .rhyme_content import RhymeItem
else:
    from rhyme_content import RhymeItem


PACKAGE_ROOT: Final = Path(__file__).resolve().parent
ACTIVITY_PREFIX: Final = "activity:"
NIGHT_LAYERS: Final = ("sky", "stars", "far", "mid", "ground")
FIREWORK_FRAMES: Final = ("default", "frame_2", "frame_3")
# Picture used where a staged word has no art yet (never in EN/IT content).
FALLBACK_PICTURE: Final = "icon.hud.ear"

GLOW_COLOR: Final = (255, 194, 52)  # theme "sunshine"


def resolve_picture(asset_id: str, variant: str = "default") -> Path:
    """Map an Activity-private ``activity:<name>`` ID or a shared visual ID to a file."""

    if asset_id.startswith(ACTIVITY_PREFIX):
        name = asset_id[len(ACTIVITY_PREFIX):]
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid Activity picture id: {asset_id!r}")
        return PACKAGE_ROOT / "assets" / "runtime" / f"{name}.png"
    return get_shared_visual_path(asset_id, variant=variant)


class RhymeArt:
    """Own the festival backdrop and every cached picture/lantern/FX surface."""

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
        self.background = self._build_background(resolver)
        self._glows: dict[int, pygame.Surface] = {}

    # -- static scene ----------------------------------------------------------
    def _build_background(self, resolver: Callable[[str, str], Path]) -> pygame.Surface:
        # Full-screen layers are composed once through a throwaway loader so
        # the five decoded 1024×600 layers are not retained in the cache.
        loader = ControlArt(resolver, max_entries=2)
        surface = pygame.Surface(self._size)
        surface.fill((37, 59, 89))  # theme navy until the sky layer loads
        for layer in NIGHT_LAYERS:
            image = loader.image(f"bg.night_sky.{layer}", self._size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    # -- pictures --------------------------------------------------------------
    def picture(self, item: RhymeItem, size: int) -> pygame.Surface | None:
        asset_id = item.picture if item.has_picture else FALLBACK_PICTURE
        image = self.art.image(asset_id, int(size))
        if image is None and asset_id != FALLBACK_PICTURE:
            image = self.art.image(FALLBACK_PICTURE, int(size))
        return image

    def lantern(self, lit: bool, size: int) -> pygame.Surface | None:
        return self.art.image(f"{ACTIVITY_PREFIX}{'lantern_lit' if lit else 'lantern_dark'}", int(size))

    def ear(self, size: int) -> pygame.Surface | None:
        return self.art.image("icon.hud.ear", int(size))

    def fx(self, asset_id: str, size: int, variant: str = "default") -> pygame.Surface | None:
        return self.art.image(asset_id, int(size), variant=variant)

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the speaking/hinted picture (built once per size)."""

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
            # Zero alpha at the rim so the halo has no visible edge on the sky.
            alpha = int(190 * (step / steps) ** 1.25)
            pygame.draw.circle(surface, (*GLOW_COLOR, alpha), (radius, radius), max(1, r))
        self._glows[diameter] = surface
        return surface

    def clear(self) -> None:
        self.art.clear()
        self._glows.clear()
