"""Prepared, bounded art for Mondo Contrari.

The opaque backdrop is the shared ``bg.meadow_day`` layers flattened once.
Props, creatures, FX and Flash come from the shared library by semantic id;
the balloon, the cardboard box and the gift box are this package's own
renditions (``assets/source/*.svg`` -> ``assets/runtime/*.png``, rendered by
``rsvg-convert``). Everything is decoded and scaled once (bounded caches);
drawing code only blits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
PRIVATE_ART: Final[tuple[str, ...]] = (
    "balloon",
    "box_back",
    "box_front",
    "gift_closed",
    "gift_open_back",
    "gift_open_front",
)
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 120,
    "star_burst": 170,
    "heart_pop": 96,
    "dust_puff": 84,
    "confetti": 260,
}
# Racers whose library picture faces left; they are mirrored once so every
# racer runs left -> right.
FACING_LEFT: Final[frozenset[str]] = frozenset({"creature.woodland.snail", "prop.vocab.train"})
SHADOW_STEPS: Final[int] = 6
CACHE_LIMIT: Final[int] = 24
HALO: Final[tuple[int, int, int]] = (255, 226, 138)


class ContrariArt:
    """Own every prepared surface the scenes blit (built once, bounded)."""

    def __init__(
        self,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
        size: tuple[int, int] = (1024, 600),
    ) -> None:
        # Content art has its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=72)
        self._runtime_dir = runtime_dir
        self._private_sources: dict[str, pygame.Surface | None] = {}
        self._private: dict[tuple[str, int], pygame.Surface | None] = {}
        self._mirrored: dict[tuple[str, int], pygame.Surface | None] = {}
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}
        self._halos: dict[tuple[int, int], pygame.Surface] = {}
        self._shadows: dict[int, pygame.Surface] = {}
        self.background = self._compose_background(size)

    # -- shared library -------------------------------------------------------

    def shared(self, asset_id: str, size: int, *, variant: str = "default") -> pygame.Surface | None:
        return self._art.image(asset_id, size, variant=variant)

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def racer(self, asset_id: str, size: int) -> pygame.Surface | None:
        """A racer facing right (mirrored once when the library art faces left)."""

        if asset_id not in FACING_LEFT:
            return self.shared(asset_id, size)
        key = (asset_id, size)
        if key not in self._mirrored:
            image = self.shared(asset_id, size)
            _store(self._mirrored, key, pygame.transform.flip(image, True, False) if image is not None else None)
        return self._mirrored[key]

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 128)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    # -- private renditions ---------------------------------------------------

    def private(self, name: str, size: int) -> pygame.Surface | None:
        key = (name, int(size))
        if key in self._private:
            return self._private[key]
        source = self._private_source(name)
        image = None
        if source is not None:
            image = source if source.get_width() == size else pygame.transform.smoothscale(source, (size, size))
        _store(self._private, key, image)
        return image

    def _private_source(self, name: str) -> pygame.Surface | None:
        if name not in self._private_sources:
            try:
                image = pygame.image.load(str(self._runtime_dir / f"{name}.png"))
                if pygame.display.get_surface() is not None:
                    image = image.convert_alpha()
            except (OSError, pygame.error):
                image = None
            self._private_sources[name] = image
        return self._private_sources[name]

    # -- small generated pieces -------------------------------------------------

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Soft rounded glow ring used for hints and demonstrations."""

        key = (int(size[0]), int(size[1]))
        cached = self._halos.get(key)
        if cached is not None:
            return cached
        width, height = key
        halo = pygame.Surface((width, height), pygame.SRCALPHA)
        for inset, alpha in ((0, 60), (5, 110), (10, 180)):
            pygame.draw.rect(
                halo,
                (*HALO, alpha),
                pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset),
                width=5,
                border_radius=max(8, 40 - inset),
            )
        _store(self._halos, key, halo)
        return halo

    def ground_shadow(self, step: int) -> pygame.Surface | None:
        """Contact shadow for the floating balloon; ``step`` 0 (high) .. 5 (low)."""

        step = max(0, min(SHADOW_STEPS - 1, int(step)))
        if step not in self._shadows:
            width = int(70 + 22 * step)
            image = self._art.image("shadow.contact.small.01", (width, max(8, width // 5)))
            if image is not None:
                image = image.copy()
                image.set_alpha(90 + 25 * step)
            self._shadows[step] = image
        return self._shadows[step]

    def _compose_background(self, size: tuple[int, int]) -> pygame.Surface:
        """Meadow layers flattened into one opaque surface (one blit per frame)."""

        surface = pygame.Surface(size)
        surface.fill((207, 234, 247))
        loader = ControlArt(max_entries=6)  # throwaway: layers are released after
        for name in ("sky", "far", "mid", "ground", "foreground"):
            image = loader.image(f"bg.meadow_day.{name}", size)
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def clear(self) -> None:
        self._art.clear()
        self._private.clear()
        self._private_sources.clear()
        self._mirrored.clear()
        self._fx.clear()
        self._halos.clear()
        self._shadows.clear()


def _store(cache: dict, key, value) -> None:
    if key not in cache and len(cache) >= CACHE_LIMIT:
        cache.pop(next(iter(cache)))
    cache[key] = value


__all__ = ["ContrariArt", "FACING_LEFT", "PRIVATE_ART", "RUNTIME_DIR"]
