"""Prepared, bounded art for The Big Seasons Tree.

* Season landscapes are shared scene-kit layers (``bg.<kit>.*``) composed once
  into one opaque surface per season. The kit sky layers carry a painted sun;
  the weather is the child's choice here, so the sky is rebuilt once from the
  kit's own sky colours (per row, the median of a few sample columns, which
  drops the sun and clouds) and only then do the far/mid/ground layers go on.
* The big tree is this package's own art: one trunk plus four canopy layers
  (``assets/source/tree_*.svg`` -> ``assets/runtime/*.png``), and so are the
  snowman and Tito's clothes. Everything else is the shared library: props,
  woodland friends, FX, HUD glyphs and Tito's canonical poses.
* Tito's clothes are separate layers on his canonical 256 canvas. Each pose
  master moves the whole character (``POSE_TRANSFORMS``), so a worn item is
  moved the same way once per pose and cached.

Every surface is scaled once per size and kept in a hard-bounded cache;
drawing only blits. Missing art degrades to small fallbacks, never a crash.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .tree_content import (
        EMBLEMS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES,
        SLOT_ICONS,
        TRUNK,
        ArtRef,
        CardLayer,
        Item,
        Season,
        Slot,
    )
    from .tree_layout import TREE_SIZE, TITO_HEIGHT
else:
    from tree_content import (
        EMBLEMS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES,
        SLOT_ICONS,
        TRUNK,
        ArtRef,
        CardLayer,
        Item,
        Season,
        Slot,
    )
    from tree_layout import TREE_SIZE, TITO_HEIGHT

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
HOST: Final = "tito"
HALO: Final = (255, 226, 138)
SKY_SAMPLE_COLUMNS: Final = 9
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 120,
    "star_burst": 180,
    "leaf_drift": 150,
    "snow": 150,
    "rain": 150,
    "bloom": 150,
    "dust_puff": 120,
}

# Whole-character transforms of Tito's canonical pose masters
# (``assets/visual/characters/canonical/v0.1/tito/<variant>.svg``, group
# ``character``): (dx, dy, clockwise degrees about (128, 214)) on the 256
# canvas. Worn clothes follow the same transform so they stay in place.
POSE_TRANSFORMS: Final[dict[str, tuple[float, float, float]]] = {
    "happy": (0.0, 0.0, 0.0),
    "default": (0.0, 0.0, 0.0),
    "pose_cheer": (0.0, -12.0, 0.0),
    "pose_think": (0.0, 0.0, -4.0),
    "pose_point": (0.0, 0.0, 3.0),
    "pose_wave": (0.0, 0.0, -3.0),
}
POSE_PIVOT: Final = (128.0, 214.0)


class SeasonsArt:
    """Own every prepared surface the renderer and controls blit."""

    def __init__(self, *, art: ControlArt | None = None, runtime_dir: Path = RUNTIME_DIR) -> None:
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=96)
        self._runtime_dir = runtime_dir
        self._backdrops: BoundedCache[str, pygame.Surface] = BoundedCache(2)
        self._private: BoundedCache[str, pygame.Surface | None] = BoundedCache(12)
        self._scaled: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(48)
        self._icons: BoundedCache[tuple, pygame.Surface] = BoundedCache(48)
        self._wear: BoundedCache[tuple, tuple[pygame.Surface, tuple[int, int]] | None] = BoundedCache(12)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(24)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- landscapes -------------------------------------------------------------

    def backdrop(self, season: Season) -> pygame.Surface:
        """The season's landscape (sky without weather), composed once, opaque."""

        cached = self._backdrops.get(season.value)
        if cached is not None:
            return cached
        kit = SCENES[season]
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self._paint_sky(surface, kit.sky)
        loader = ControlArt(max_entries=len(kit.layers) + 1)
        cloud = self.image(ArtRef.shared("prop.nature.cloud"), (120, 72))
        if cloud is not None:
            faint = cloud.copy()
            faint.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
            for x, y in ((120, 96), (560, 70), (930, 260)):
                surface.blit(faint, faint.get_rect(center=(x, y)))
        for asset_id in kit.layers:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backdrops[season.value] = surface
        return surface

    def _paint_sky(self, surface: pygame.Surface, sky_id: str) -> None:
        loader = ControlArt(max_entries=2)
        sky = loader.image(sky_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        loader.clear()
        if sky is None:
            surface.fill((207, 234, 247))
            return
        width, height = sky.get_size()
        columns = [int((index + 0.5) * width / SKY_SAMPLE_COLUMNS) for index in range(SKY_SAMPLE_COLUMNS)]
        for y in range(height):
            samples = sorted(
                (sky.get_at((x, y)) for x in columns),
                key=lambda c: c.r * 299 + c.g * 587 + c.b * 114,
            )
            # The sun and clouds are brighter than the sky, so the median
            # (at most two columns ever cross one of them) is the sky colour.
            colour = samples[len(samples) // 2]
            pygame.draw.line(surface, (colour.r, colour.g, colour.b), (0, y), (REFERENCE_WIDTH - 1, y))

    # -- generic pictures -----------------------------------------------------

    def image(self, ref: ArtRef, size: tuple[int, int] | int) -> pygame.Surface | None:
        """``ref`` scaled once to ``size`` (int = square), or ``None``."""

        width, height = (size, size) if isinstance(size, int) else size
        if ref.file is None:
            return self._art.image(str(ref.asset_id), (int(width), int(height)), variant=ref.variant)
        key = (ref.key, int(width), int(height))
        if key in self._scaled:
            return self._scaled[key]
        source = self._private_source(ref.file)
        result: pygame.Surface | None = None
        if source is not None:
            result = source if source.get_size() == (width, height) else pygame.transform.smoothscale(source, (int(width), int(height)))
        self._scaled[key] = result
        return result

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

    def compose(self, layers: Sequence[CardLayer], size: int, *, crop: bool = False, key: str = "") -> pygame.Surface:
        """A square icon of ``layers`` (cached; stable surface per content/size)."""

        cache_key = ("icon", key or "|".join(layer.art.key for layer in layers), size, crop)
        cached = self._icons.get(cache_key)
        if cached is not None:
            return cached
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        for layer in layers:
            bx, by, bw, bh = layer.box
            box = pygame.Rect(int(bx * size), int(by * size), max(1, int(bw * size)), max(1, int(bh * size)))
            if crop:
                picture = self._cropped(layer.art, size)
            else:
                picture = self.image(layer.art, (box.width, box.height))
            if picture is not None:
                canvas.blit(picture, picture.get_rect(center=box.center))
        self._icons[cache_key] = canvas
        return canvas

    def _cropped(self, ref: ArtRef, size: int) -> pygame.Surface | None:
        """The visible part of ``ref`` fitted into a ``size`` square."""

        source = self.image(ref, 256)
        if source is None:
            return None
        bounds = source.get_bounding_rect(min_alpha=24)
        if bounds.width <= 0 or bounds.height <= 0:
            return None
        piece = source.subsurface(bounds)
        scale = min(size * 0.92 / bounds.width, size * 0.92 / bounds.height)
        return pygame.transform.smoothscale(piece, (max(1, int(bounds.width * scale)), max(1, int(bounds.height * scale))))

    def card_icon(self, item: Item, size: int) -> pygame.Surface:
        return self.compose(item.card, size, crop=item.crop, key=f"card:{item.item_id}")

    def slot_icon(self, slot: Slot, size: int) -> pygame.Surface:
        return self.compose(SLOT_ICONS[slot], size, key=f"slot:{slot.value}")

    def emblem(self, season: Season, size: int, *, done: bool) -> pygame.Surface:
        """Season picker emblem; a dressed season wears a small star."""

        key = ("emblem", season.value, size, done)
        cached = self._icons.get(key)
        if cached is not None:
            return cached
        canvas = self.compose((CardLayer(EMBLEMS[season]),), size, key=f"emblem:{season.value}").copy()
        if done:
            star = self._art.image("ui.control.star", max(16, size // 2 - 4))
            if star is not None:
                canvas.blit(star, star.get_rect(bottomright=(size, size)))
        self._icons[key] = canvas
        return canvas

    # -- the tree ---------------------------------------------------------------

    def trunk(self) -> pygame.Surface | None:
        return self.image(TRUNK, TREE_SIZE)

    def canopy(self, item: Item) -> pygame.Surface | None:
        return self.image(item.scene, TREE_SIZE) if item.scene is not None else None

    # -- Tito -------------------------------------------------------------------

    def cast_pose(self, variant: str, height: int = TITO_HEIGHT) -> pygame.Surface | None:
        return self._art.image(f"character.{HOST}", height, variant=variant)

    def wear(self, item: Item, variant: str, height: int = TITO_HEIGHT) -> tuple[pygame.Surface, tuple[int, int]] | None:
        """A worn item moved like pose ``variant``: (surface, offset from Tito's rect)."""

        key = (item.item_id, variant, height)
        if key in self._wear:
            return self._wear[key]
        result = None
        base = self.image(item.scene, height) if item.scene is not None else None
        if base is not None:
            dx, dy, angle = POSE_TRANSFORMS.get(variant, (0.0, 0.0, 0.0))
            scale = height / 256.0
            if angle:
                rotated, offset = _rotate_about(base, angle, (POSE_PIVOT[0] * scale, POSE_PIVOT[1] * scale))
            else:
                rotated, offset = base, (0, 0)
            result = (rotated, (int(round(offset[0] + dx * scale)), int(round(offset[1] + dy * scale))))
        self._wear[key] = result
        return result

    # -- weather ----------------------------------------------------------------

    def sun(self, size: int) -> pygame.Surface | None:
        return self.image(ArtRef.shared("prop.nature.sun"), size)

    def halo(self, size: int) -> pygame.Surface:
        key = ("halo", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((size, size), pygame.SRCALPHA)
            centre = size // 2
            for radius, alpha in ((size // 2, 40), (int(size * 0.4), 60), (int(size * 0.32), 80)):
                pygame.draw.circle(cached, (*HALO, alpha), (centre, centre), radius)
            self._misc[key] = cached
        return cached

    def cloud(self, width: int, *, grey: bool) -> pygame.Surface | None:
        key = ("cloud", width, grey)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        image = self.image(ArtRef.shared("prop.nature.cloud"), (width, int(width * 0.62)))
        if image is None:
            return None
        if grey:
            image = image.copy()
            image.fill((206, 214, 228, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._misc[key] = image
        return image

    def particle(self, kind: str, size: int, turn: int = 0) -> pygame.Surface | None:
        """Small weather sprites (raindrop, snowflake, leaf), prepared once."""

        key = ("particle", kind, size, turn)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        asset = {"rain": "prop.nature.raindrop", "snow": "prop.nature.snowflake", "leaf": "prop.nature.leaf_autumn"}[kind]
        image = self.image(ArtRef.shared(asset), size)
        if image is None:
            return None
        if turn:
            image = pygame.transform.rotate(image, turn)
        self._misc[key] = image
        return image

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

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm hint glow drawn around a slot or a card."""

        key = ("glow", *size)
        cached = self._misc.get(key)
        if cached is None:
            width, height = size
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 60), (8, 105), (16, 160)):
                rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.ellipse(cached, (*HALO, alpha), rect, width=7)
            self._misc[key] = cached
        return cached

    def clear(self) -> None:
        self._backdrops.clear()
        self._private.clear()
        self._scaled.clear()
        self._icons.clear()
        self._wear.clear()
        self._misc.clear()
        self._fx.clear()


def _rotate_about(
    image: pygame.Surface, clockwise_degrees: float, pivot: tuple[float, float]
) -> tuple[pygame.Surface, tuple[float, float]]:
    """Rotate ``image`` about ``pivot``; return it and its blit offset."""

    rotated = pygame.transform.rotozoom(image, -clockwise_degrees, 1.0)
    width, height = image.get_size()
    cx, cy = width / 2.0, height / 2.0
    radians = math.radians(clockwise_degrees)
    px, py = pivot[0] - cx, pivot[1] - cy
    # Where the pivot lands when rotating about the centre (y points down).
    nx = px * math.cos(radians) - py * math.sin(radians)
    ny = px * math.sin(radians) + py * math.cos(radians)
    left = cx - rotated.get_width() / 2.0 + (pivot[0] - (cx + nx))
    top = cy - rotated.get_height() / 2.0 + (pivot[1] - (cy + ny))
    return rotated, (left, top)


__all__ = ["HOST", "POSE_TRANSFORMS", "SeasonsArt"]
