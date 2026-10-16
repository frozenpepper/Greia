"""Prepared, bounded art for Momo's Happy Faces.

Everything is loaded and scaled once and kept in small bounded caches:

* the playroom backdrop (shared ``bg.indoor_room`` layers) flattened into one
  opaque surface;
* Momo's canonical expressions (``character.momo`` variants) at stage size
  and a soft "who is it?" silhouette for the explain stage;
* face tiles: a crop of a canonical cast expression around the face (a crop,
  never a redraw), so feelings stay readable on small screens;
* help items (shared props / HUD heart) and FX frames;
* picture-story cards composed from shared backdrops, props, creatures and FX
  plus two private props (``assets/runtime/gift.png``, ``lightning.png``).

Drawing code only blits these surfaces.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix

if __package__:
    from .momo_content import (
        BACKDROP_LAYERS,
        CARD_H,
        CARD_W,
        HELP_ITEMS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORIES_BY_ID,
        Backdrop,
        Emotion,
        Piece,
    )
    from .momo_layout import CARD_FRAME
else:
    from momo_content import (
        BACKDROP_LAYERS,
        CARD_H,
        CARD_W,
        HELP_ITEMS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORIES_BY_ID,
        Backdrop,
        Emotion,
        Piece,
    )
    from momo_layout import CARD_FRAME

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"

INK: Final = (75, 55, 47)
PLUM: Final = (86, 58, 100)
CREAM: Final = (255, 251, 235)
SILHOUETTE: Final = (205, 184, 236)
SKY_NIGHT: Final = (37, 59, 89)
CACHE_LIMIT: Final = 56
CARD_CACHE_LIMIT: Final = 4

# Face crops in the 256 px cast canvas: (centre x, centre y, side).
FACE_CROPS: Final[dict[str, tuple[int, int, int]]] = {
    "momo": (128, 146, 160),
    "lilli": (128, 124, 182),
    "leo": (128, 124, 178),
    "flash": (128, 136, 180),
    "dani": (128, 132, 174),
    "tito": (128, 140, 174),
}
CAST_CANVAS: Final = 256
# 1024x600 layer -> card aspect (440:300). Rooms crop to plain wall + floor
# (below the bunting and shelves) so the card never repeats the stage room.
STORY_CROP: Final = pygame.Rect(72, 0, 880, 600)
ROOM_CROP: Final = pygame.Rect(150, 150, 660, 450)


class _Bounded(OrderedDict):
    """Tiny LRU dictionary for prepared surfaces."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit

    def remember(self, key, value):
        self[key] = value
        self.move_to_end(key)
        while len(self) > self.limit:
            self.popitem(last=False)
        return value

    def recall(self, key):
        value = self.get(key)
        if value is not None:
            self.move_to_end(key)
        return value


class MomoArt:
    """Own every prepared surface the renderer blits (bounded, built once)."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
    ) -> None:
        self._painter = painter
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=64)
        self._runtime_dir = runtime_dir
        self.background = self._compose_background()
        self._surfaces = _Bounded(CACHE_LIMIT)
        self._cards = _Bounded(CARD_CACHE_LIMIT)
        self._private: dict[str, pygame.Surface | None] = {}

    # -- cast ------------------------------------------------------------------

    def cast(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def momo(self, emotion: Emotion | str, height: int) -> pygame.Surface | None:
        return self.cast("momo", str(emotion), height)

    def silhouette(self, height: int) -> pygame.Surface | None:
        """Momo's shape with a big question mark: the feeling is still hidden."""

        key = ("silhouette", height)
        cached = self._surfaces.recall(key)
        if cached is not None:
            return cached
        source = self.cast("momo", "default", height)
        if source is None:
            return None
        shape = source.copy()
        shape.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        shape.fill((*SILHOUETTE, 0), special_flags=pygame.BLEND_RGBA_ADD)
        mark = self._painter.label("?", int(height * 0.36), PLUM)
        shape.blit(mark, mark.get_rect(center=(height // 2, int(height * 0.56))))
        return self._surfaces.remember(key, shape)

    def face(self, character: str, emotion: Emotion | str, size: int) -> pygame.Surface | None:
        """A face crop of ``character`` feeling ``emotion`` at ``size`` px."""

        key = ("face", character, str(emotion), size)
        cached = self._surfaces.recall(key)
        if cached is not None:
            return cached
        full = self._art.image(f"character.{character}", CAST_CANVAS, variant=str(emotion))
        if full is None:
            return None
        cx, cy, side = FACE_CROPS.get(character, (128, 128, 200))
        box = pygame.Rect(cx - side // 2, cy - side // 2, side, side).clip(full.get_rect())
        crop = full.subsurface(box).copy()
        return self._surfaces.remember(key, pygame.transform.smoothscale(crop, (size, size)))

    # -- items / FX ------------------------------------------------------------

    def item(self, item_id: str, size: int) -> pygame.Surface | None:
        help_item = HELP_ITEMS.get(item_id)
        if help_item is None:
            return None
        if not help_item.stack:
            return self._art.image(help_item.asset, size, variant=help_item.variant)
        key = ("stack", item_id, size)
        cached = self._surfaces.recall(key)
        if cached is not None:
            return cached
        tower = pygame.Surface((size, size), pygame.SRCALPHA)
        block = int(size / (len(help_item.stack) + 0.15))
        y = size
        for asset, variant in help_item.stack:
            image = self._art.image(asset, block, variant=variant)
            if image is not None:
                tower.blit(image, image.get_rect(midbottom=(size // 2, y)))
            y -= int(block * 0.94)
        return self._surfaces.remember(key, tower)

    def fx_frames(self, name: str, size: int) -> tuple[pygame.Surface, ...]:
        key = ("fx", name, size)
        cached = self._surfaces.recall(key)
        if cached is not None:
            return cached
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        return self._surfaces.remember(key, tuple(frames))

    def zzz(self, size: int) -> pygame.Surface:
        """A sleepy 'z' (pictogram, painted once)."""

        key = ("zzz", size)
        cached = self._surfaces.recall(key)
        if cached is None:
            glyph = self._painter.label("z", size, (74, 112, 186))
            outline = self._painter.label("z", size, CREAM)
            cached = pygame.Surface((glyph.get_width() + 4, glyph.get_height() + 4), pygame.SRCALPHA)
            for dx, dy in ((0, 0), (4, 0), (0, 4), (4, 4)):
                cached.blit(outline, (dx, dy))
            cached.blit(glyph, (2, 2))
            self._surfaces.remember(key, cached)
        return cached

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Soft glow frame used to show where to look (hints)."""

        key = ("halo", size)
        cached = self._surfaces.recall(key)
        if cached is None:
            width, height = size[0] + 24, size[1] + 24
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 70), (4, 120), (8, 190)):
                pygame.draw.rect(
                    cached,
                    (255, 214, 102, alpha),
                    pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset),
                    width=4,
                    border_radius=36 - inset,
                )
            self._surfaces.remember(key, cached)
        return cached

    # -- picture stories ---------------------------------------------------------

    def story_card(self, story_id: str) -> pygame.Surface | None:
        """The framed picture card for one story (composed once, LRU of 4)."""

        cached = self._cards.recall(story_id)
        if cached is not None:
            return cached
        story = STORIES_BY_ID.get(story_id)
        if story is None:
            return None
        scene = self._story_backdrop(story.backdrop).copy()
        for piece in story.pieces:
            self._place(scene, piece)
        return self._cards.remember(story_id, self._frame(scene))

    def _story_backdrop(self, backdrop: Backdrop) -> pygame.Surface:
        """Card-sized crop of a shared backdrop (decoded once, then cached)."""

        key = ("backdrop", backdrop)
        cached = self._surfaces.recall(key)
        if cached is not None:
            return cached
        full = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        full.fill(SKY_NIGHT if backdrop in {Backdrop.NIGHT, Backdrop.STORM} else (207, 234, 247))
        loader = ControlArt(max_entries=6)
        for layer in BACKDROP_LAYERS[backdrop]:
            image = loader.image(layer, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                full.blit(image, (0, 0))
        loader.clear()
        if backdrop is Backdrop.STORM:
            full.fill((150, 150, 175), special_flags=pygame.BLEND_RGB_MULT)
        crop = ROOM_CROP if backdrop in {Backdrop.PLAYROOM, Backdrop.BEDROOM} else STORY_CROP
        card = pygame.transform.smoothscale(full.subsurface(crop), (CARD_W, CARD_H))
        if pygame.display.get_surface() is not None:
            card = card.convert_alpha()
        return self._surfaces.remember(key, card)

    def _piece_image(self, piece: Piece) -> pygame.Surface | None:
        if piece.asset.startswith("private:"):
            source = self._load_private(piece.asset.split(":", 1)[1])
            if source is None:
                return None
            width = max(1, round(source.get_width() * piece.height / max(1, source.get_height())))
            image = pygame.transform.smoothscale(source, (width, piece.height))
        else:
            image = self._art.fit(piece.asset, piece.height, variant=piece.variant)
            if image is None:
                return None
        if piece.flip:
            image = pygame.transform.flip(image, True, False)
        if piece.dim > 0:
            image = image.copy()
            level = int(255 * (1.0 - piece.dim))
            image.fill((level, level, min(255, level + 24), 255), special_flags=pygame.BLEND_RGBA_MULT)
        return image

    def _place(self, scene: pygame.Surface, piece: Piece) -> None:
        image = self._piece_image(piece)
        if image is None:
            return
        base = image.get_rect(center=(piece.x, piece.y)) if piece.center else image.get_rect(midbottom=(piece.x, piece.y))
        if piece.angle:
            image = pygame.transform.rotozoom(image, piece.angle, 1.0)
        scene.blit(image, image.get_rect(center=base.center))

    def _frame(self, scene: pygame.Surface) -> pygame.Surface:
        width, height = CARD_W + 2 * CARD_FRAME, CARD_H + 2 * CARD_FRAME
        card = self._painter.body(BodyShape.PANEL, (width, height), CREAM).copy()
        radius = 22
        rounded = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        rounded.blit(scene, (0, 0))
        mask = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        card.blit(rounded, (CARD_FRAME, CARD_FRAME))
        pygame.draw.rect(
            card,
            mix(INK, CREAM, 0.25),
            pygame.Rect(CARD_FRAME, CARD_FRAME, CARD_W, CARD_H),
            width=3,
            border_radius=radius,
        )
        return card

    # -- loading -----------------------------------------------------------------

    def _load_private(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        try:
            image = pygame.image.load(str(self._runtime_dir / f"{name}.png"))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error, FileNotFoundError):
            image = None
        self._private[name] = image
        return image

    def _compose_background(self) -> pygame.Surface:
        """Playroom wall + wood floor, flattened into one opaque surface."""

        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((216, 238, 248))
        loader = ControlArt(max_entries=4)
        for layer in BACKDROP_LAYERS[Backdrop.PLAYROOM]:
            image = loader.image(layer, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def clear(self) -> None:
        self._surfaces.clear()
        self._cards.clear()
        self._private.clear()
        self._art.clear()


__all__ = ["FACE_CROPS", "MomoArt"]
