"""Prepared, bounded art for Woodland Hide & Seek.

* Season backdrops are shared scene-kit layers (``bg.<kit>.*``) composed once
  through the scene-composition runtime (``SceneDefinition`` rendered by
  ``PygameSceneRenderer``) into one opaque surface per season.
* Friends are shared library creatures (``creature.woodland.*``, full
  ``default`` variant), clipped by their hiding place while they peek.
* Hiding props are shared library props or this package's own props
  (``assets/source/*.svg`` -> ``assets/runtime/*.png``).
* Lilli's poses and FX come from the shared library.

Every surface is scaled once per size and kept in a hard-bounded cache;
drawing only blits. Missing art degrades to simple fallbacks, never a crash.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.ui_core import BoundedCache

if __package__:
    from .woodland_content import FRIENDS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, PropKind, Season
else:
    from woodland_content import FRIENDS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, PropKind, Season

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
HOST: Final = "lilli"
HALO: Final = (255, 226, 138)
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 110,
    "star_burst": 170,
    "leaf_drift": 120,
    "snow": 120,
    "dust_puff": 120,
    "ripple": 120,
    "confetti": 220,
}
DEFAULT_PEEK_TOP: Final = 0.36


class WoodlandArt:
    """Own every prepared surface the renderer blits (bounded, built lazily once)."""

    def __init__(
        self,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
        scene_renderer: PygameSceneRenderer | None = None,
    ) -> None:
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=64)
        self._runtime_dir = runtime_dir
        self._scene_renderer = scene_renderer
        self._backdrops: BoundedCache[str, pygame.Surface] = BoundedCache(2)
        self._private: BoundedCache[str, pygame.Surface | None] = BoundedCache(8)
        self._props: BoundedCache[tuple[str, int, int], pygame.Surface | None] = BoundedCache(16)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(12)
        self._peek_tops: dict[str, float] = {}
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- backdrops ------------------------------------------------------------

    def backdrop(self, season: Season) -> pygame.Surface:
        """The season's layered shared backdrop, composed once (opaque)."""

        cached = self._backdrops.get(season.season_id)
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if not self._compose_scene(season, surface):
            self._compose_layers(season, surface)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backdrops[season.season_id] = surface
        return surface

    def _compose_scene(self, season: Season, surface: pygame.Surface) -> bool:
        try:
            renderer = self._scene_renderer or PygameSceneRenderer.for_activity(max_entries=6)
            renderer.draw(season.scene(), surface, motion_enabled=False, clear=True)
            if self._scene_renderer is None:
                renderer.clear()  # layers are baked; drop the scaled copies
            return True
        except (SceneRenderError, Exception):  # noqa: BLE001 - any failure -> layered fallback
            return False

    def _compose_layers(self, season: Season, surface: pygame.Surface) -> None:
        """Fallback when the scene runtime cannot resolve the catalogue."""

        surface.fill((207, 234, 247))
        pygame.draw.rect(surface, (122, 190, 110), (0, 390, REFERENCE_WIDTH, REFERENCE_HEIGHT - 390))
        loader = ControlArt(max_entries=len(season.layers) + 1)
        for asset_id in season.layers:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()

    # -- props ------------------------------------------------------------------

    def prop(self, kind: PropKind, size: tuple[int, int]) -> pygame.Surface | None:
        """Hiding-place art scaled once to ``size`` (``None`` for water)."""

        key = (kind.kind_id, int(size[0]), int(size[1]))
        if key in self._props:
            return self._props[key]
        image: pygame.Surface | None = None
        if kind.asset_id is not None:
            image = self._art.image(kind.asset_id, size)
        elif kind.art_file is not None:
            source = self._private_source(kind.art_file)
            if source is not None:
                image = pygame.transform.smoothscale(source, (int(size[0]), int(size[1])))
        self._props[key] = image
        return image

    def _private_source(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            image = None
        self._private[name] = image
        return image

    # -- friends ----------------------------------------------------------------

    def full(self, friend_id: str, size: int) -> pygame.Surface | None:
        return self._art.image(FRIENDS_BY_ID[friend_id].asset_id, size)

    def peek_top(self, friend_id: str) -> float:
        """Top of the friend's head as a fraction of its art canvas (measured once)."""

        cached = self._peek_tops.get(friend_id)
        if cached is not None:
            return cached
        value = DEFAULT_PEEK_TOP
        image = self.full(friend_id, 256)
        if image is not None:
            bounds = image.get_bounding_rect(min_alpha=40)
            if bounds.height > 0:
                value = bounds.top / image.get_height()
        self._peek_tops[friend_id] = value
        return value

    # -- cast / FX / glow ---------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{HOST}", height, variant=variant)

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 120)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def ripple(self, width: int) -> pygame.Surface | None:
        """Flattened library ripple marking a pond hiding place."""

        key = ("ripple", width)
        cached = self._misc.get(key)
        if cached is None:
            image = self._art.image("fx.ripple", (width, max(8, width // 3)))
            if image is None:
                return None
            cached = image
            self._misc[key] = cached
        return cached

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm hint glow drawn on the ground around a hiding place."""

        key = ("glow", *size)
        cached = self._misc.get(key)
        if cached is None:
            width, height = size
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 60), (8, 100), (16, 150)):
                rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.ellipse(cached, (*HALO, alpha), rect, width=7)
            self._misc[key] = cached
        return cached

    def clear(self) -> None:
        self._backdrops.clear()
        self._private.clear()
        self._props.clear()
        self._misc.clear()
        self._peek_tops.clear()
        self._fx.clear()


__all__ = ["HOST", "WoodlandArt"]
