"""Prepared, bounded art for Wonder Match.

Card back and card face frame are this package's art
(``assets/source/card_{back,face}.svg`` -> ``assets/runtime/*.png``); every
picture, backdrop, FX and Lilli pose is shared library art resolved by
semantic ID. Surfaces are scaled once per size and kept in hard-bounded LRU
caches: a card face (frame + picture), its two flip-squash frames, the
sticker and its "not yet collected" silhouette, the album covers on the
picker and one composed opaque backdrop per screen. Drawing only blits.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.ui_core import BoundedCache

if __package__:
    from .memory_content import ALBUM_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH, Album
    from .memory_layout import picture_rect
else:
    from memory_content import ALBUM_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH, Album
    from memory_layout import picture_rect

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
HOST: Final = "lilli"
INK: Final = (75, 55, 47)
CREAM: Final = (255, 251, 235)
HALO: Final = (255, 226, 138)
# Width fractions of the two squash frames shown while a card turns over.
FLIP_STEPS: Final[tuple[float, ...]] = (0.62, 0.22)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 120, "star_burst": 150, "confetti": 240, "heart_pop": 90}


class Side(StrEnum):
    BACK = "back"
    FACE = "face"


class MemoryArt:
    """Own every prepared surface the renderer blits (bounded, built lazily once)."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=64)
        self._runtime_dir = runtime_dir
        self._sources: dict[Side, pygame.Surface | None] = {
            Side.BACK: self._load("card_back.png"),
            Side.FACE: self._load("card_face.png"),
        }
        self._cards: BoundedCache[tuple, pygame.Surface] = BoundedCache(48)
        self._stickers: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(24)
        self._covers: BoundedCache[tuple, pygame.Surface] = BoundedCache(8)
        self._backgrounds: BoundedCache[tuple[str, ...], pygame.Surface] = BoundedCache(2)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(16)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- cards --------------------------------------------------------------

    def card(self, side: Side, size: tuple[int, int], asset_id: str | None = None) -> pygame.Surface:
        """Full-width card (back, or face frame + picture)."""

        key = (side, size, asset_id if side is Side.FACE else None)
        cached = self._cards.get(key)
        if cached is None:
            cached = self._build_card(side, size, asset_id)
            self._cards[key] = cached
        return cached

    def card_squash(self, side: Side, size: tuple[int, int], asset_id: str | None, step: int) -> pygame.Surface:
        """One of the narrow frames of the turn-over (built once per card)."""

        key = (side, size, asset_id if side is Side.FACE else None, step)
        cached = self._cards.get(key)
        if cached is None:
            full = self.card(side, size, asset_id)
            width = max(4, int(size[0] * FLIP_STEPS[step]))
            cached = pygame.transform.smoothscale(full, (width, size[1]))
            self._cards[key] = cached
        return cached

    def _build_card(self, side: Side, size: tuple[int, int], asset_id: str | None) -> pygame.Surface:
        source = self._sources.get(side)
        if source is not None:
            surface = pygame.transform.smoothscale(source, size)
        else:
            fill = (148, 100, 201) if side is Side.BACK else CREAM
            surface = self._painter.body(BodyShape.TILE, size, fill, lip=max(3, size[1] // 30)).copy()
        if side is Side.FACE and asset_id is not None:
            spot = picture_rect(pygame.Rect(0, 0, *size))
            picture = self._art.image(asset_id, spot.width)
            if picture is not None:
                surface = surface.copy()
                surface.blit(picture, spot)
        return surface

    # -- stickers -----------------------------------------------------------

    def sticker(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self._art.image(asset_id, size)

    def silhouette(self, asset_id: str, size: int) -> pygame.Surface | None:
        """Soft cocoa outline-shape of a picture not collected yet."""

        key = ("silhouette", asset_id, size)
        if key in self._stickers:
            return self._stickers[key]
        picture = self._art.image(asset_id, size)
        shape: pygame.Surface | None = None
        if picture is not None:
            shape = picture.copy()
            shape.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
            shape.fill((*INK, 0), special_flags=pygame.BLEND_RGB_ADD)
            shape.fill((255, 255, 255, 46), special_flags=pygame.BLEND_RGBA_MULT)
        self._stickers[key] = shape
        return shape

    def well(self, size: int) -> pygame.Surface:
        """An empty sticker well (also left behind where a found pair was)."""

        return self._slot(("well", size, size), (size, size), radius=max(10, size // 5))

    def empty_card(self, size: tuple[int, int]) -> pygame.Surface:
        """Faint place mark where a matched pair used to lie."""

        return self._slot(("empty", *size), size, radius=max(12, size[0] // 8), inset=6)

    def _slot(self, key: tuple, size: tuple[int, int], *, radius: int, inset: int = 0) -> pygame.Surface:
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            rect = cached.get_rect().inflate(-2 * inset, -2 * inset)
            pygame.draw.rect(cached, (255, 253, 247, 110 if inset == 0 else 70), rect, border_radius=radius)
            pygame.draw.rect(cached, (*INK, 60 if inset == 0 else 34), rect, width=2, border_radius=radius)
            self._misc[key] = cached
        return cached

    def page(self, size: tuple[int, int], album: Album) -> pygame.Surface:
        """Lilli's sticker page behind the eight wells, in the album colour."""

        key = ("page", album.album_id, *size)
        cached = self._misc.get(key)
        if cached is None:
            cached = self._painter.body(BodyShape.PANEL, size, album.tint, lip=6, contour_width=3)
            self._misc[key] = cached
        return cached

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm glow ring around a card (hints, matches, Lilli's peek)."""

        key = ("halo", *size)
        cached = self._misc.get(key)
        if cached is None:
            width, height = size[0] + 28, size[1] + 28
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 70), (5, 130), (10, 200)):
                pygame.draw.rect(
                    cached,
                    (*HALO, alpha),
                    pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset),
                    width=5,
                    border_radius=max(10, 30 - inset),
                )
            self._misc[key] = cached
        return cached

    # -- album covers -----------------------------------------------------

    def album_cover(self, album: Album, size: int, collected: int, star) -> pygame.Surface:
        """Picker tile content: three album pictures over the album colour + 8 stars."""

        key = (album.album_id, size, collected)
        cached = self._covers.get(key)
        if cached is not None:
            return cached
        inner = int(size * 0.84)
        cover = pygame.Surface((inner, inner), pygame.SRCALPHA)
        panel = self._painter.body(BodyShape.TILE, (inner, int(inner * 0.74)), album.tint, contour=mix(album.tint_deep, INK, 0.45), contour_width=3)
        cover.blit(panel, (0, 0))
        big = int(inner * 0.5)
        small = int(inner * 0.36)
        centre_y = int(inner * 0.38)
        placements = ((album.cover[1], -0.27, small), (album.cover[2], 0.27, small), (album.cover[0], 0.0, big))
        for subject_id, dx, picture_size in placements:
            picture = self._art.image(album.subject(subject_id).asset_id, picture_size)
            if picture is not None:
                cx = inner // 2 + int(dx * inner)
                cy = centre_y + (int(inner * 0.05) if picture_size == small else 0)
                cover.blit(picture, picture.get_rect(center=(cx, cy)))
        star_size = max(10, int(inner / (ALBUM_SIZE * 1.12)))
        spacing = int(star_size * 1.1)
        start = inner // 2 - (spacing * (ALBUM_SIZE - 1)) // 2
        star_y = int(inner * 0.87)
        for index in range(ALBUM_SIZE):
            image = star(star_size, filled=index < collected)
            cover.blit(image, image.get_rect(center=(start + index * spacing, star_y)))
        self._covers[key] = cover
        return cover

    def album_badge(self, album: Album, size: int) -> pygame.Surface | None:
        """Small picture for the round album button on the board."""

        return self._art.image(album.subject(album.cover[0]).asset_id, size)

    # -- scenes / cast / FX -------------------------------------------------

    def background(self, layers: tuple[str, ...]) -> pygame.Surface:
        """Shared scene layers flattened once into one opaque frame."""

        cached = self._backgrounds.get(layers)
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((207, 234, 247))
        loader = ControlArt(max_entries=len(layers) + 1)
        for asset_id in layers:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backgrounds[layers] = surface
        return surface

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{HOST}", height, variant=variant)

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

    def clear(self) -> None:
        self._cards.clear()
        self._stickers.clear()
        self._covers.clear()
        self._backgrounds.clear()
        self._misc.clear()
        self._fx.clear()

    # -- loading ------------------------------------------------------------

    def _load(self, name: str) -> pygame.Surface | None:
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            return None
        return image


__all__ = ["FLIP_STEPS", "MemoryArt", "Side"]
