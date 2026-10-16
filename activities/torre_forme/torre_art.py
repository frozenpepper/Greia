"""Prepared, bounded art for La Torre delle Forme.

* The room is the shared indoor scene kit (``bg.indoor_room.wall_playroom``
  over ``bg.indoor_room.floor_wood``), composed once with the workbench and
  the kit tray into one opaque surface per tray size.
* Blocks are the shared wooden toy blocks (``prop.blocks.<kind>``, one colour
  variant per kind), scaled once per size and turned in exact 90-degree steps.
* Outlines are made from the same block art: each block's silhouette (or the
  union of all of them for the older rungs) becomes a cream paper shape with
  a dashed cocoa contour, supersampled and cached once per build. The "it
  fits here" glow and the see-through demonstration block come from the same
  masks.
* Dani's poses, the sparkles/confetti and the picture card's vocabulary
  picture are the shared library (``character.dani``, ``fx.*``,
  ``prop.vocab.*``).

Every surface is built once per content/size in a hard-bounded cache;
drawing only blits. Missing art degrades to simple vector fallbacks.
"""

from __future__ import annotations

import math
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .torre_layout import BENCH_RECT, CARD_RECT, CELL, SLOT, tray_block_size, tray_panel, tray_rects
    from .torre_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, Block, BlockKind, BuildPlan, OutlineStyle
else:
    from torre_layout import BENCH_RECT, CARD_RECT, CELL, SLOT, tray_block_size, tray_panel, tray_rects
    from torre_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, Block, BlockKind, BuildPlan, OutlineStyle

ROOM_LAYERS: Final = ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood")
# One shared colour variant per block kind, so a kind looks the same in the
# kit and in the build (the library has wood + four paint colours).
BLOCK_VARIANT: Final[dict[BlockKind, str]] = {
    BlockKind.SQUARE: "coral",
    BlockKind.RECTANGLE: "ocean",
    BlockKind.TRIANGLE: "sunshine",
    BlockKind.HALF_CIRCLE: "leaf",
    BlockKind.ARCH: "default",
    BlockKind.CYLINDER: "default",
}
FALLBACK_RGB: Final[dict[BlockKind, tuple[int, int, int]]] = {
    BlockKind.SQUARE: (244, 111, 97),
    BlockKind.RECTANGLE: (74, 145, 216),
    BlockKind.TRIANGLE: (255, 194, 52),
    BlockKind.HALF_CIRCLE: (89, 184, 106),
    BlockKind.ARCH: (232, 176, 120),
    BlockKind.CYLINDER: (232, 176, 120),
}
INK: Final = (75, 55, 47)           # cast ink #4B372F
CREAM: Final = (255, 246, 227)
SAND: Final = (238, 221, 186)
PAPER: Final = (255, 250, 238)
DASH_INK: Final = (110, 84, 70)
GOLD: Final = (251, 191, 36)
GOLD_DEEP: Final = (245, 158, 11)
GLOW: Final = (255, 214, 102)
WOOD_LIGHT: Final = (226, 172, 116)
WOOD: Final = (196, 134, 82)
WOOD_DARK: Final = (150, 98, 58)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 96, "star_burst": 150, "confetti": 220, "dust_puff": 110}
SS: Final = 2  # supersampling factor for vector drawing
OUTLINE_PAD: Final = 10  # outline surfaces are padded so shadows/dashes fit


def _lerp(a: Sequence[int], b: Sequence[int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def _vertical_gradient(size: tuple[int, int], top: Sequence[int], bottom: Sequence[int]) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(height):
        pygame.draw.line(surface, _lerp(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surface


def _rounded(surface: pygame.Surface, radius: int) -> pygame.Surface:
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    clipped = surface.copy()
    clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return clipped


def _tinted(mask: pygame.mask.Mask, color: tuple[int, int, int], alpha: int = 255) -> pygame.Surface:
    return mask.to_surface(setcolor=(*color, alpha), unsetcolor=(0, 0, 0, 0))


def _grown(mask: pygame.mask.Mask, radius: int) -> pygame.mask.Mask:
    """``mask`` dilated by ``radius`` px (a disc), on a canvas padded by it."""

    width, height = mask.get_size()
    grown = pygame.mask.Mask((width + 2 * radius, height + 2 * radius))
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                grown.draw(mask, (radius + dx, radius + dy))
    return grown


def _dashed_contour(surface: pygame.Surface, points: Sequence[tuple[int, int]], color, width: int, dash: float, gap: float) -> None:
    """Draw dashes along a closed polyline (outline points of a mask)."""

    if len(points) < 2:
        return
    loop = list(points) + [points[0]]
    on, left = True, dash
    for (x0, y0), (x1, y1) in zip(loop, loop[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        start = 0.0
        while length - start > 1e-6:
            step = min(left, length - start)
            if on:
                a = (x0 + (x1 - x0) * start / length, y0 + (y1 - y0) * start / length)
                b = (x0 + (x1 - x0) * (start + step) / length, y0 + (y1 - y0) * (start + step) / length)
                pygame.draw.line(surface, color, a, b, width)
                pygame.draw.circle(surface, color, (int(round(a[0])), int(round(a[1]))), width // 2)
                pygame.draw.circle(surface, color, (int(round(b[0])), int(round(b[1]))), width // 2)
            start += step
            left -= step
            if left <= 1e-6:
                on = not on
                left = dash if on else gap


class TorreArt:
    """Own every prepared surface the renderer blits."""

    def __init__(self, *, loader: ControlArt | None = None, blocks: ControlArt | None = None) -> None:
        self._art = loader if loader is not None else ControlArt(max_entries=48)
        # Blocks use their own loader so the 12 block sources never evict
        # Dani's poses or the FX frames from the source cache.
        self._block_art = blocks if blocks is not None else ControlArt(max_entries=32)
        self._room: pygame.Surface | None = None
        self._scenes: BoundedCache[int, pygame.Surface] = BoundedCache(3)
        self._outlines: BoundedCache[tuple, pygame.Surface] = BoundedCache(4)
        self._blocks: BoundedCache[tuple, pygame.Surface] = BoundedCache(48)
        self._masks: BoundedCache[tuple, pygame.mask.Mask] = BoundedCache(24)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(24)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- static scene ---------------------------------------------------------------

    def scene(self, tray_count: int) -> pygame.Surface:
        """Room + workbench + kit tray panel, opaque, cached per tray size."""

        cached = self._scenes.get(tray_count)
        if cached is not None:
            return cached
        surface = self._room_surface().copy()
        surface.blit(self._bench(), BENCH_RECT.move(-8, -8).topleft)
        surface.blit(self._tray_panel(tray_count), tray_panel(tray_count).move(-6, -6).topleft)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._scenes[tray_count] = surface
        return surface

    def _room_surface(self) -> pygame.Surface:
        if self._room is not None:
            return self._room
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((214, 236, 248))
        pygame.draw.rect(surface, (226, 172, 116), (0, 432, REFERENCE_WIDTH, REFERENCE_HEIGHT - 432))
        loader = ControlArt(max_entries=len(ROOM_LAYERS))
        for asset_id in ROOM_LAYERS:
            layer = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if layer is not None:
                surface.blit(layer, (0, 0))
        loader.clear()
        self._room = surface
        return surface

    def _bench(self) -> pygame.Surface:
        """A low wooden workbench top: wood gradient, ink contour, one highlight."""

        pad = 8
        size = (BENCH_RECT.width + 2 * pad, BENCH_RECT.height + 2 * pad + 6)
        big = pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)
        body = pygame.Rect(pad * SS, pad * SS, BENCH_RECT.width * SS, BENCH_RECT.height * SS)
        radius = 10 * SS
        shadow = pygame.Surface((body.width, body.height), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (*INK, 60), shadow.get_rect())
        big.blit(shadow, body.move(0, 10 * SS))
        big.blit(_rounded(_vertical_gradient(body.size, WOOD_LIGHT, WOOD), radius), body)
        pygame.draw.line(big, WOOD_DARK, (body.left + 18 * SS, body.centery + 2 * SS), (body.right - 40 * SS, body.centery + 2 * SS), 2 * SS)
        pygame.draw.rect(big, INK, body, width=3 * SS, border_radius=radius)
        highlight = pygame.Rect(body.left + 16 * SS, body.top + 4 * SS, body.width // 3, 3 * SS)
        pygame.draw.rect(big, (255, 236, 205), highlight, border_radius=2 * SS)
        return pygame.transform.smoothscale(big, size)

    def _tray_panel(self, count: int) -> pygame.Surface:
        panel_rect = tray_panel(count)
        pad = 6
        size = (panel_rect.width + 2 * pad, panel_rect.height + 2 * pad)
        big = pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)
        body = pygame.Rect(pad * SS, pad * SS, panel_rect.width * SS, panel_rect.height * SS)
        radius = 26 * SS
        shadow = pygame.Surface(body.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (*INK, 70), shadow.get_rect(), border_radius=radius)
        big.blit(shadow, body.move(0, 6 * SS))
        big.blit(_rounded(_vertical_gradient(body.size, WOOD_LIGHT, WOOD), radius), body)
        pygame.draw.rect(big, INK, body, width=4 * SS, border_radius=radius)
        highlight = pygame.Rect(body.left + 26 * SS, body.top + 5 * SS, body.width // 3, 4 * SS)
        pygame.draw.rect(big, (255, 236, 205), highlight, border_radius=2 * SS)
        for slot in tray_rects(count):
            local = pygame.Rect(
                (slot.x - panel_rect.x + pad) * SS, (slot.y - panel_rect.y + pad) * SS, slot.width * SS, slot.height * SS
            )
            pygame.draw.rect(big, CREAM, local, border_radius=18 * SS)
            pygame.draw.rect(big, WOOD_DARK, local, width=2 * SS, border_radius=18 * SS)
        return pygame.transform.smoothscale(big, size)

    # -- blocks -----------------------------------------------------------------------

    def block(self, block: Block, unit: int) -> pygame.Surface:
        """The coloured wooden block, ``unit`` px per cell, turned as ``block``."""

        key = ("block", block, unit)
        cached = self._blocks.get(key)
        if cached is not None:
            return cached
        base_w, base_h = Block(block.kind).size
        image = self._block_art.image(
            f"prop.blocks.{block.kind.value}", (base_w * unit, base_h * unit), variant=BLOCK_VARIANT[block.kind]
        )
        if image is None:
            image = self._fallback_block(block.kind, (base_w * unit, base_h * unit))
        if block.rotation:
            image = pygame.transform.rotate(image, -90 * block.rotation)
        self._blocks[key] = image
        return image

    def ghost(self, block: Block, unit: int) -> pygame.Surface:
        """A see-through copy used when Dani demonstrates."""

        key = ("ghost", block, unit)
        cached = self._blocks.get(key)
        if cached is None:
            cached = self.block(block, unit).copy()
            cached.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            self._blocks[key] = cached
        return cached

    def glow(self, block: Block, unit: int) -> pygame.Surface:
        """"It fits here": a warm gold halo the shape of the block (centred)."""

        key = ("glow", block, unit)
        cached = self._misc.get(key)
        if cached is None:
            mask = self._mask(block, unit)
            grown = _grown(mask, 7)
            cached = _tinted(grown, GLOW, 150)
            inner = _grown(mask, 3)
            cached.blit(_tinted(inner, GOLD_DEEP, 230), (4, 4))
            cached.blit(_tinted(mask, (255, 251, 235), 235), (7, 7))
            self._misc[key] = cached
        return cached

    def _mask(self, block: Block, unit: int) -> pygame.mask.Mask:
        key = (block, unit)
        cached = self._masks.get(key)
        if cached is None:
            cached = pygame.mask.from_surface(self.block(block, unit), 100)
            self._masks[key] = cached
        return cached

    @staticmethod
    def _fallback_block(kind: BlockKind, size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        rect = surface.get_rect().inflate(-4, -4)
        color = FALLBACK_RGB[kind]
        if kind is BlockKind.TRIANGLE:
            points = [rect.midtop, rect.bottomright, rect.bottomleft]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, INK, points, 3)
        elif kind is BlockKind.HALF_CIRCLE:
            pygame.draw.ellipse(surface, color, rect.inflate(0, rect.height).move(0, rect.height // 2))
            pygame.draw.rect(surface, (0, 0, 0, 0), (0, rect.bottom, size[0], size[1]))
        else:
            pygame.draw.rect(surface, color, rect, border_radius=8)
            pygame.draw.rect(surface, INK, rect, width=3, border_radius=8)
        return surface

    # -- outlines ---------------------------------------------------------------------

    def outline(self, plan: BuildPlan, style: OutlineStyle) -> pygame.Surface:
        """The paper outline of a build: one dashed shape per block, or the union.

        Returned surface is ``plan.size * CELL`` padded by ``OUTLINE_PAD`` on
        every side (blit it at the board's top-left minus the pad).
        """

        key = (plan.build_id, style)
        cached = self._outlines.get(key)
        if cached is not None:
            return cached
        width, height = plan.size
        pad = OUTLINE_PAD
        unit = CELL * SS
        big = pygame.Surface(((width * CELL + 2 * pad) * SS, (height * CELL + 2 * pad) * SS), pygame.SRCALPHA)
        # Block art has soft rounded edges, so neighbouring blocks do not quite
        # touch at the pixel level: each block mask is grown a little (the
        # dashes then sit just outside the wood) before the union is traced.
        grow = 3 * SS
        masks: list[tuple[pygame.mask.Mask, tuple[int, int]]] = []
        for item in plan.placements:
            mask = _grown(pygame.mask.from_surface(self.block(item.block, unit), 100), grow)
            masks.append((mask, (pad * SS + item.col * unit - grow, pad * SS + item.row * unit - grow)))
        union = pygame.mask.Mask(big.get_size())
        for mask, offset in masks:
            union.draw(mask, offset)
        # Soft cocoa shadow + paper fill for the whole build.
        big.blit(_tinted(union, INK, 45), (0, 5 * SS))
        big.blit(_tinted(union, PAPER, 240), (0, 0))
        groups = [union] if style is OutlineStyle.SILHOUETTE else [self._placed_mask(m, o, big.get_size()) for m, o in masks]
        for group in groups:
            for component in group.connected_components():
                _dashed_contour(big, component.outline(), DASH_INK, 4 * SS, 10.0 * SS, 7.0 * SS)
        surface = pygame.transform.smoothscale(big, (width * CELL + 2 * pad, height * CELL + 2 * pad))
        self._outlines[key] = surface
        return surface

    @staticmethod
    def _placed_mask(mask: pygame.mask.Mask, offset: tuple[int, int], size: tuple[int, int]) -> pygame.mask.Mask:
        placed = pygame.mask.Mask(size)
        placed.draw(mask, offset)
        return placed

    # -- tray / hints -----------------------------------------------------------------

    def tray_block(self, block: Block) -> pygame.Surface:
        width, _ = tray_block_size(block)
        unit = width // block.size[0]
        return self.block(block, unit)

    def hand_ring(self) -> pygame.Surface:
        """The bright ring around the kit slot of the block in hand."""

        key = ("hand",)
        cached = self._misc.get(key)
        if cached is None:
            size = SLOT + 8
            big = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
            rect = big.get_rect().inflate(-4 * SS, -4 * SS)
            pygame.draw.rect(big, (255, 255, 255, 240), rect, border_radius=22 * SS)
            pygame.draw.rect(big, GOLD_DEEP, rect, width=5 * SS, border_radius=22 * SS)
            pygame.draw.rect(big, INK, rect, width=2 * SS, border_radius=22 * SS)
            cached = pygame.transform.smoothscale(big, (size, size))
            self._misc[key] = cached
        return cached

    def slot_glow(self, size: int = SLOT + 14) -> pygame.Surface:
        """A warm pulsing ring that says "this one" around a kit slot or button."""

        key = ("slot_glow", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
            rect = big.get_rect()
            pygame.draw.rect(big, (*GLOW, 110), rect, width=8 * SS, border_radius=26 * SS)
            pygame.draw.rect(big, GOLD_DEEP, rect.inflate(-8 * SS, -8 * SS), width=5 * SS, border_radius=22 * SS)
            cached = pygame.transform.smoothscale(big, (size, size))
            self._misc[key] = cached
        return cached

    def turn_badge(self, size: int) -> pygame.Surface:
        """"Turn it": the shared turn glyph on a round cream badge with a gold ring."""

        key = ("turn_badge", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
            center = (size * SS // 2, size * SS // 2)
            radius = size * SS // 2 - 2 * SS
            pygame.draw.circle(big, (*INK, 60), (center[0], center[1] + 3 * SS), radius)
            pygame.draw.circle(big, (255, 251, 240), center, radius)
            pygame.draw.circle(big, GOLD_DEEP, center, radius, width=4 * SS)
            pygame.draw.circle(big, INK, center, radius, width=2 * SS)
            cached = pygame.transform.smoothscale(big, (size, size))
            glyph = self._art.image("icon.hud.rotate", int(size * 0.7))
            if glyph is not None:
                cached.blit(glyph, glyph.get_rect(center=(size // 2, size // 2)))
            self._misc[key] = cached
        return cached

    def card(self, picture: str | None) -> pygame.Surface | None:
        """The "picture on the box" card: a cream card standing on the
        wall shelf with the shared picture."""

        if picture is None:
            return None
        key = ("card", picture)
        if key in self._misc:
            return self._misc[key]
        image = self._art.image(picture, CARD_RECT.width - 30)
        if image is None:
            self._misc[key] = None  # type: ignore[assignment]
            return None
        pad = 8
        size = (CARD_RECT.width + 2 * pad, CARD_RECT.height + 2 * pad)
        big = pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)
        body = pygame.Rect(pad * SS, pad * SS, CARD_RECT.width * SS, CARD_RECT.height * SS)
        radius = 18 * SS
        shadow = pygame.Surface(body.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (*INK, 60), shadow.get_rect(), border_radius=radius)
        big.blit(shadow, body.move(0, 4 * SS))
        big.blit(_rounded(_vertical_gradient(body.size, (255, 253, 246), CREAM), radius), body)
        pygame.draw.rect(big, INK, body, width=3 * SS, border_radius=radius)
        card = pygame.transform.smoothscale(big, size)
        card.blit(image, image.get_rect(center=(size[0] // 2, size[1] // 2)))
        self._misc[key] = card
        return card

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 96)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def dani(self, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image("character.dani", height, variant=variant)

    def clear(self) -> None:
        self._scenes.clear()
        self._outlines.clear()
        self._blocks.clear()
        self._masks.clear()
        self._misc.clear()
        self._fx.clear()
        self._block_art.clear()


__all__ = ["BLOCK_VARIANT", "OUTLINE_PAD", "ROOM_LAYERS", "TorreArt"]
