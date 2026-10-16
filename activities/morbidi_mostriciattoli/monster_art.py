"""Monster compositor for Fluffy Monsters (Activity-private part art).

Parts are build-time PNG renditions (384 px for the 256-unit monster canvas)
of the SVG sources in ``assets/source/parts``. A portrait is composed once per
(recipe look, height, expression) into a bounded cache:

    shadow -> arms/horns/ears (behind) -> body fill (palette gradient) ->
    pattern (tinted, clipped to the body) -> body ink line -> feet ->
    mouth -> eyes -> crown -> accessory

Tinted parts ship as a white silhouette (``*_fill``) plus an ink layer
(``*_line``): the silhouette is multiplied by a palette gradient (light step ->
base, GREIA_SVG_AUTHORING_RULES §2/§5) so the cocoa ink contour is never
recoloured. Every scale, tint, mirror and composition happens once and is
cached in hard-bounded LRU caches; drawing a portrait is one blit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import mix
from greia_platform.ui_core import BoundedCache

if __package__:
    from .monster_content import (
        AUTHORED_ARM_ROOT,
        AUTHORED_FOOT_ROOT,
        BODY_COLORS,
        CATEGORY_ORDER,
        Anchor,
        BodyShape,
        Category,
        ColorOption,
        Layer,
        PartOption,
        Tint,
        option,
    )
else:
    from monster_content import (
        AUTHORED_ARM_ROOT,
        AUTHORED_FOOT_ROOT,
        BODY_COLORS,
        CATEGORY_ORDER,
        Anchor,
        BodyShape,
        Category,
        ColorOption,
        Layer,
        PartOption,
        Tint,
        option,
    )

PACKAGE_ROOT: Final = Path(__file__).resolve().parent
PARTS_DIR: Final = PACKAGE_ROOT / "assets" / "runtime" / "parts"
UI_DIR: Final = PACKAGE_ROOT / "assets" / "runtime"

INK: Final = (75, 55, 47)
WHITE: Final = (255, 255, 255)
SHADOW: Final = (106, 81, 71)

# The 256-unit part canvas sits at ORIGIN inside a BOX_W x BOX_H composition
# box, leaving room for ears/hats above and arms beside every body shape.
BOX_W: Final = 300
BOX_H: Final = 288
ORIGIN: Final = (22, 20)
PART_UNITS: Final = 256
GRADIENT_TOP: Final = 56
GRADIENT_BOTTOM: Final = 212

# Preview crops in box units (x, y, size): the face, the head top and the feet
# are zoomed so small parts read on a tile; everything else shows the friend.
WHOLE_CROP: Final = (32, 28, 236)
FOCUS: Final[dict[Category, str]] = {
    Category.EYES: "face",
    Category.MOUTH: "face",
    Category.TUFT: "top",
    Category.FEET: "feet",
}


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (channel / 255 for channel in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def colour(color_id: str) -> tuple[int, int, int]:
    item = option(Category.BODY_COLOR, color_id)
    assert isinstance(item, ColorOption)
    return item.base


def tint_colour(tint: Tint, base: tuple[int, int, int]) -> tuple[int, int, int]:
    if tint is Tint.SHADE:
        return mix(base, INK, 0.24)
    if tint is Tint.LIGHT:
        # Light marks vanish on pale bodies: fall back to a soft shade there.
        return mix(base, INK, 0.16) if luminance(base) > 0.66 else mix(base, WHITE, 0.55)
    return base


class PartImages:
    """Load part renditions lazily and keep scaled/tinted copies bounded."""

    def __init__(self, parts_dir: Path = PARTS_DIR, *, max_sources: int = 16, max_scaled: int = 192) -> None:
        self._dir = parts_dir
        self._sources: BoundedCache[str, pygame.Surface | None] = BoundedCache(max_sources)
        self._scaled: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(max_scaled)

    def exists(self, stem: str) -> bool:
        return (self._dir / f"{stem}.png").is_file()

    def _source(self, stem: str) -> pygame.Surface | None:
        if stem in self._sources:
            return self._sources[stem]
        surface: pygame.Surface | None
        try:
            surface = pygame.image.load(str(self._dir / f"{stem}.png"))
            if pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            surface = None
        self._sources[stem] = surface
        return surface

    def scaled(self, stem: str, px: int) -> pygame.Surface | None:
        key = ("scaled", stem, px)
        if key in self._scaled:
            return self._scaled[key]
        source = self._source(stem)
        result = None
        if source is not None and px > 0:
            result = source if source.get_width() == px else pygame.transform.smoothscale(source, (px, px))
        self._scaled[key] = result
        return result

    def tinted(self, stem: str, px: int, tint: Tint, base: tuple[int, int, int]) -> pygame.Surface | None:
        """A white silhouette multiplied by its palette colour (cached)."""

        key = ("tinted", stem, px, tint, base)
        if key in self._scaled:
            return self._scaled[key]
        mask = self.scaled(stem, px)
        result = None
        if mask is not None:
            result = mask.copy()
            if tint is Tint.BODY:
                result.blit(self.gradient(px, base), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                result.fill((*tint_colour(tint, base), 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._scaled[key] = result
        return result

    def gradient(self, px: int, base: tuple[int, int, int]) -> pygame.Surface:
        """Two-stop body gradient: light step at the head -> base at the feet."""

        key = ("gradient", px, base)
        cached = self._scaled.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((px, px), pygame.SRCALPHA)
        light = mix(base, WHITE, 0.42)
        top = GRADIENT_TOP * px / PART_UNITS
        bottom = GRADIENT_BOTTOM * px / PART_UNITS
        for row in range(px):
            t = min(1.0, max(0.0, (row - top) / max(1.0, bottom - top)))
            pygame.draw.line(surface, (*mix(light, base, t), 255), (0, row), (px, row))
        self._scaled[key] = surface
        return surface

    def flipped(self, surface: pygame.Surface, key: tuple) -> pygame.Surface:
        full = ("flip", *key)
        cached = self._scaled.get(full)
        if cached is None:
            cached = pygame.transform.flip(surface, True, False)
            self._scaled[full] = cached
        return cached

    def clear(self) -> None:
        self._sources.clear()
        self._scaled.clear()


class MonsterArt:
    """Compose monster portraits, option previews and drawer icons."""

    def __init__(self, parts: PartImages | None = None, *, max_portraits: int = 48) -> None:
        self.parts = parts if parts is not None else PartImages()
        self._portraits: BoundedCache[tuple, pygame.Surface] = BoundedCache(max_portraits)
        self._squash: BoundedCache[tuple, pygame.Surface] = BoundedCache(8)
        self._icons: BoundedCache[tuple, pygame.Surface] = BoundedCache(24)
        self._ui: dict[tuple[str, int], pygame.Surface | None] = {}

    # -- portraits ---------------------------------------------------------------------

    def portrait(self, recipe, height: int, *, blink: bool = False, laugh: bool = False) -> pygame.Surface:
        """The whole friend in a BOX_W x BOX_H box scaled to ``height`` px."""

        key = (recipe.parts_key, int(height), blink, laugh)
        cached = self._portraits.get(key)
        if cached is not None:
            return cached
        surface = self._compose(recipe, height / BOX_H, blink=blink, laugh=laugh)
        self._portraits[key] = surface
        return surface

    def squashed(self, recipe, height: int, *, laugh: bool, stretch: bool) -> pygame.Surface:
        """A squash or stretch key frame of a portrait (built once, cached)."""

        key = (recipe.parts_key, int(height), laugh, stretch)
        cached = self._squash.get(key)
        if cached is not None:
            return cached
        base = self.portrait(recipe, height, laugh=laugh)
        sx, sy = (0.94, 1.07) if stretch else (1.07, 0.92)
        size = (max(1, round(base.get_width() * sx)), max(1, round(base.get_height() * sy)))
        surface = pygame.transform.smoothscale(base, size)
        self._squash[key] = surface
        return surface

    def preview(self, recipe, focus: Category | None, size: int) -> pygame.Surface:
        """A square option tile picture: the friend, zoomed on ``focus`` parts."""

        crop = self._crop(recipe, FOCUS.get(focus) if focus is not None else None)
        x, y, side = crop
        key = ("preview", recipe.parts_key, crop, int(size))
        cached = self._portraits.get(key)
        if cached is not None:
            return cached
        scale = size / side
        full = self._compose(recipe, scale)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.blit(full, (-round(x * scale), -round(y * scale)))
        self._portraits[key] = surface
        return surface

    def _crop(self, recipe, focus: str | None) -> tuple[int, int, int]:
        shape = option(Category.BODY_SHAPE, recipe.body_shape)
        assert isinstance(shape, BodyShape)
        ox, oy = ORIGIN
        if focus == "face":
            return (ox + 128 - 64, oy + 144 + shape.face_dy - 64, 128)
        if focus == "top":
            return (ox + 128 - 74, oy + 76 + shape.top_dy - 74, 148)
        if focus == "feet":
            fx, fy = shape.foot
            return (ox + 128 - 86, oy + fy - 84, 172)
        return WHOLE_CROP

    def _compose(self, recipe, scale: float, *, blink: bool = False, laugh: bool = False) -> pygame.Surface:
        surface = pygame.Surface((max(1, round(BOX_W * scale)), max(1, round(BOX_H * scale))), pygame.SRCALPHA)
        px = max(1, round(PART_UNITS * scale))
        shape = option(Category.BODY_SHAPE, recipe.body_shape)
        assert isinstance(shape, BodyShape)
        base = colour(recipe.body_color)
        chosen = {category: option(category, recipe.get(category)) for category in CATEGORY_ORDER}

        self._shadow(surface, shape, scale)
        for category in (Category.ARMS, Category.TUFT):
            part = chosen[category]
            if isinstance(part, PartOption) and part.layer is Layer.BEHIND:
                self._part(surface, part, shape, base, px, scale)
        # Body: palette gradient, pattern, then ink.
        fill = self.parts.tinted(f"{shape.art}_fill", px, Tint.BODY, base)
        if fill is not None:
            surface.blit(fill, self._at((0, 0), scale))
        pattern = chosen[Category.PATTERN]
        if isinstance(pattern, PartOption) and not pattern.is_none:
            marks = self._pattern(pattern, shape, base, px)
            if marks is not None:
                surface.blit(marks, self._at((0, 0), scale))
        line = self.parts.scaled(f"{shape.art}_line", px)
        if line is not None:
            surface.blit(line, self._at((0, 0), scale))
        feet = chosen[Category.FEET]
        if isinstance(feet, PartOption):
            self._part(surface, feet, shape, base, px, scale)
        mouth = chosen[Category.MOUTH]
        if isinstance(mouth, PartOption):
            stem = "mouth_laugh" if laugh else mouth.art
            self._blit_stem(surface, stem, (0, shape.face_dy), px, scale)
        eyes = chosen[Category.EYES]
        if isinstance(eyes, PartOption) and eyes.art is not None:
            stem = f"{eyes.art}_blink" if blink and self.parts.exists(f"{eyes.art}_blink") else eyes.art
            self._blit_stem(surface, stem, (0, shape.face_dy), px, scale)
        top = chosen[Category.TUFT]
        if isinstance(top, PartOption) and top.layer is Layer.FRONT:
            self._part(surface, top, shape, base, px, scale)
        accessory = chosen[Category.ACCESSORY]
        if isinstance(accessory, PartOption):
            self._part(surface, accessory, shape, base, px, scale)
        return surface

    @staticmethod
    def _at(offset: tuple[float, float], scale: float) -> tuple[int, int]:
        return (round((ORIGIN[0] + offset[0]) * scale), round((ORIGIN[1] + offset[1]) * scale))

    def _shadow(self, surface: pygame.Surface, shape: BodyShape, scale: float) -> None:
        rx = shape.shadow_rx * scale
        ry = max(1.0, rx / 6.5)
        cx = (ORIGIN[0] + 128) * scale
        cy = (ORIGIN[1] + 229) * scale
        # Supersample once so the flat ellipse is anti-aliased (no blur).
        big = pygame.Surface((max(2, round(rx * 4)), max(2, round(ry * 4))), pygame.SRCALPHA)
        pygame.draw.ellipse(big, (*SHADOW, 38), big.get_rect())
        small = pygame.transform.smoothscale(big, (max(1, round(rx * 2)), max(1, round(ry * 2))))
        surface.blit(small, small.get_rect(center=(round(cx), round(cy))))

    def _offset(self, part: PartOption, shape: BodyShape) -> tuple[int, int]:
        if part.anchor is Anchor.FACE:
            return (0, shape.face_dy)
        if part.anchor is Anchor.TOP:
            return (shape.spread_dx if (part.pair or part.follows_spread) else 0, shape.top_dy)
        if part.anchor is Anchor.ARM:
            return (shape.arm[0] - AUTHORED_ARM_ROOT[0], shape.arm[1] - AUTHORED_ARM_ROOT[1])
        if part.anchor is Anchor.FOOT:
            return (shape.foot[0] - AUTHORED_FOOT_ROOT[0], shape.foot[1] - AUTHORED_FOOT_ROOT[1])
        return (0, shape.neck_dy)

    def _layers(self, part: PartOption, base: tuple[int, int, int], px: int) -> list[tuple[pygame.Surface, tuple]]:
        layers: list[tuple[pygame.Surface, tuple]] = []
        if part.art is None:
            return layers
        if part.tint is not Tint.NONE:
            fill = self.parts.tinted(f"{part.art}_fill", px, part.tint, base)
            line = self.parts.scaled(f"{part.art}_line", px)
            if fill is not None:
                layers.append((fill, ("tinted", f"{part.art}_fill", px, part.tint, base)))
            if line is not None:
                layers.append((line, ("scaled", f"{part.art}_line", px)))
        else:
            image = self.parts.scaled(part.art, px)
            if image is not None:
                layers.append((image, ("scaled", part.art, px)))
        return layers

    def _part(self, surface: pygame.Surface, part: PartOption, shape: BodyShape, base, px: int, scale: float) -> None:
        if part.is_none:
            return
        dx, dy = self._offset(part, shape)
        for image, key in self._layers(part, base, px):
            surface.blit(image, self._at((dx, dy), scale))
            if part.pair:
                surface.blit(self.parts.flipped(image, key), self._at((-dx, dy), scale))

    def _blit_stem(self, surface: pygame.Surface, stem: str | None, offset: tuple[int, int], px: int, scale: float) -> None:
        if stem is None:
            return
        image = self.parts.scaled(stem, px)
        if image is not None:
            surface.blit(image, self._at(offset, scale))

    def _pattern(self, pattern: PartOption, shape: BodyShape, base, px: int) -> pygame.Surface | None:
        assert pattern.art is not None
        if pattern.tint is Tint.NONE:
            marks = self.parts.scaled(pattern.art, px)
        else:
            marks = self.parts.tinted(pattern.art, px, pattern.tint, base)
        mask = self.parts.scaled(f"{shape.art}_fill", px)
        if marks is None or mask is None:
            return None
        clipped = marks.copy()
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return clipped

    # -- drawer icons -----------------------------------------------------------------------

    def drawer_icon(self, category: Category, recipe, size: int) -> pygame.Surface:
        """A small picture for each drawer, in the current monster's colours."""

        key = (category, recipe.body_shape, recipe.body_color, int(size))
        cached = self._icons.get(key)
        if cached is not None:
            return cached
        if category is Category.BODY_COLOR:
            surface = self._colour_icon(size)
        else:
            sample = recipe
            representative = {
                Category.PATTERN: "spots",
                Category.EYES: "big_goggles",
                Category.MOUTH: "tongue_out",
                Category.TUFT: "horns",
                Category.ARMS: "noodle",
                Category.FEET: "paws",
                Category.ACCESSORY: "bow_tie",
            }
            for other in CATEGORY_ORDER:
                if other in (Category.BODY_SHAPE, Category.BODY_COLOR):
                    continue
                sample = sample.with_choice(other, representative.get(other, "none") if other is category else _plain(other))
            surface = self._icon_crop(sample, category, size)
        self._icons[key] = surface
        return surface

    def _icon_crop(self, sample, category: Category, size: int) -> pygame.Surface:
        shape = option(Category.BODY_SHAPE, sample.body_shape)
        assert isinstance(shape, BodyShape)
        ox, oy = ORIGIN
        crops = {
            Category.EYES: (ox + 128 - 38, oy + 122 + shape.face_dy - 38, 76),
            Category.MOUTH: (ox + 128 - 38, oy + 166 + shape.face_dy - 38, 76),
            Category.TUFT: (ox + 128 - 64, oy + 70 + shape.top_dy - 56, 128),
            Category.ARMS: (ox + 128 - 104, oy + shape.arm[1] - 92, 208),
            Category.BODY_SHAPE: (ox + 128 - 84, oy + 146 - 84, 168),
            Category.FEET: (ox + 128 - 76, oy + shape.foot[1] - 70, 140),
            Category.ACCESSORY: (ox + 128 - 58, oy + 180 + shape.neck_dy - 58, 116),
            Category.PATTERN: (ox + 128 - 76, oy + 146 - 76, 152),
        }
        x, y, side = crops.get(category, WHOLE_CROP)
        scale = size / side
        full = self._compose(sample, scale)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.blit(full, (-round(x * scale), -round(y * scale)))
        return surface

    def _colour_icon(self, size: int) -> pygame.Surface:
        """Three overlapping paint blobs from the body palette."""

        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        blob = max(4, int(size * 0.62))
        mask = self.parts.scaled("body_round_fill", int(blob * PART_UNITS / 150))
        line = self.parts.scaled("body_round_line", int(blob * PART_UNITS / 150))
        spots = ((0.30, 0.36, BODY_COLORS[3]), (0.68, 0.40, BODY_COLORS[5]), (0.50, 0.68, BODY_COLORS[0]))
        for fx, fy, item in spots:
            if mask is None:
                pygame.draw.circle(surface, item.base, (round(size * fx), round(size * fy)), blob // 3)
                continue
            tinted = mask.copy()
            tinted.blit(self.parts.gradient(mask.get_width(), item.base), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            rect = tinted.get_rect(center=(round(size * fx), round(size * fy) + round(blob * 0.06)))
            surface.blit(tinted, rect)
            if line is not None:
                surface.blit(line, rect)
        return surface

    # -- small private UI art ---------------------------------------------------------------

    def ui(self, name: str, size: int) -> pygame.Surface | None:
        """``assets/runtime/ui_<name>.png`` scaled once (name tag, gallery)."""

        key = (name, int(size))
        if key not in self._ui:
            image = None
            try:
                image = pygame.image.load(str(UI_DIR / f"ui_{name}.png"))
                if pygame.display.get_surface() is not None:
                    image = image.convert_alpha()
                image = pygame.transform.smoothscale(image, (int(size), int(size)))
            except (pygame.error, FileNotFoundError, OSError):
                image = None
            if len(self._ui) >= 12:
                self._ui.pop(next(iter(self._ui)))
            self._ui[key] = image
        return self._ui[key]

    def clear(self) -> None:
        self._portraits.clear()
        self._squash.clear()
        self._icons.clear()
        self._ui.clear()
        self.parts.clear()

    @property
    def cached_count(self) -> int:
        return len(self._portraits) + len(self._squash) + len(self._icons)


def _plain(category: Category) -> str:
    """The quietest choice of a drawer (used to isolate one part in an icon)."""

    return {
        Category.PATTERN: "none",
        Category.EYES: "two_dots",
        Category.MOUTH: "broad_grin",
        Category.TUFT: "none",
        Category.ARMS: "none",
        Category.FEET: "none",
        Category.ACCESSORY: "none",
    }.get(category, "none")


__all__ = ["BOX_H", "BOX_W", "MonsterArt", "PartImages", "colour", "luminance", "tint_colour"]
