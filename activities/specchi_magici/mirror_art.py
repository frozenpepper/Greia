"""Prepared, bounded art for Specchi Magici.

* The stage is the shared ``bg.stage`` scene kit (wall, boards, curtains,
  valance), composed once into one opaque surface.
* The magic mirror board (gilded frame, cream mosaic side, glass mirror side,
  the shining mirror line) is drawn from theme/cast tokens with the kit's
  recipe (flat 2-stop fills, one ink contour, one highlight), supersampled
  once and cached per board shape; the tray panel is baked in with it.
* Mosaic tiles are this package's art (``assets/source/mosaic_tile_*.svg`` ->
  ``assets/runtime/*.png``, a ``prop.mosaic_tile.*`` shared-library
  candidate), scaled and turned in 90-degree steps once per size.
* Lilli's poses and the sparkles are the shared library (``character.lilli``
  variants, ``fx.*``).

Every surface is built once per content/size and kept in a hard-bounded
cache; drawing only blits. Missing art degrades to simple fallbacks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.ui_core import BoundedCache

if __package__:
    from .mirror_layout import CELL, FRAME_RECT, GRID_RECT, MIRROR_X, MIRROR_Y, SLOT, cell_rect, tray_panel, tray_rects
    from .mirror_model import GRID_COLS, GRID_ROWS, REFERENCE_HEIGHT, REFERENCE_WIDTH, MirrorAxis, Piece, ShapeKind
else:
    from mirror_layout import CELL, FRAME_RECT, GRID_RECT, MIRROR_X, MIRROR_Y, SLOT, cell_rect, tray_panel, tray_rects
    from mirror_model import GRID_COLS, GRID_ROWS, REFERENCE_HEIGHT, REFERENCE_WIDTH, MirrorAxis, Piece, ShapeKind

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
# Tile colour tokens (theme-defaults accents), index = Piece.color_index.
COLOUR_TOKENS: Final = ("coral", "orange", "sunshine", "leaf", "ocean", "grape")
COLOUR_RGB: Final = ((244, 111, 97), (243, 154, 56), (255, 194, 52), (89, 184, 106), (74, 145, 216), (148, 100, 201))
STAGE_LAYERS: Final = (
    "bg.stage.wall_dark",
    "bg.stage.boards",
    "bg.stage.curtain_left",
    "bg.stage.curtain_right",
    "bg.stage.valance",
)
INK: Final = (75, 55, 47)               # cast ink #4B372F
GOLD: Final = (251, 191, 36)            # cast gold
GOLD_DEEP: Final = (245, 158, 11)
GOLD_LIGHT: Final = (253, 223, 146)     # gold mixed 45 % white
CREAM: Final = (255, 246, 227)
SAND: Final = (238, 221, 186)           # sand token (grout, tray slots)
GLASS_TOP: Final = (232, 244, 251)      # sky mixed 45 % white
GLASS: Final = (207, 234, 247)          # sky token
GLASS_SLOT: Final = (150, 190, 222)
MIRROR_LIGHT: Final = (255, 251, 235)
GLOW: Final = (255, 214, 102)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 96, "star_burst": 150, "check_pop": 88}
SS: Final = 2  # supersampling factor for the vector-drawn board


def _lerp(a: Sequence[int], b: Sequence[int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def _vertical_gradient(size: tuple[int, int], top: Sequence[int], bottom: Sequence[int]) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(height):
        pygame.draw.line(surface, _lerp(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surface


def _rounded_mask(size: tuple[int, int], radius: int) -> pygame.Surface:
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    return mask


def _clip_to(surface: pygame.Surface, mask: pygame.Surface) -> pygame.Surface:
    clipped = surface.copy()
    clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return clipped


class MirrorArt:
    """Own every prepared surface the renderer blits."""

    def __init__(self, *, loader: ControlArt | None = None, runtime_dir: Path = RUNTIME_DIR) -> None:
        self._art = loader if loader is not None else ControlArt(max_entries=48)
        self._runtime_dir = runtime_dir
        self._stage: pygame.Surface | None = None
        self._scenes: BoundedCache[tuple, pygame.Surface] = BoundedCache(3)
        self._boards: BoundedCache[tuple, pygame.Surface] = BoundedCache(3)
        self._tile_sources: BoundedCache[tuple[str, int], pygame.Surface | None] = BoundedCache(24)
        self._tiles: BoundedCache[tuple, pygame.Surface] = BoundedCache(72)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(16)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- static scene -----------------------------------------------------------

    def scene(self, picture_cells: frozenset[tuple[int, int]], axis: MirrorAxis, tray_count: int) -> pygame.Surface:
        """Stage + magic mirror board + tray panel, opaque, cached per shape."""

        key = (picture_cells, axis, tray_count)
        cached = self._scenes.get(key)
        if cached is not None:
            return cached
        surface = self._stage_surface().copy()
        surface.blit(self.board(picture_cells, axis), FRAME_RECT.move(-6, -6).topleft)
        surface.blit(self._tray_panel(tray_count), tray_panel(tray_count).move(-6, -6).topleft)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._scenes[key] = surface
        return surface

    def _stage_surface(self) -> pygame.Surface:
        if self._stage is not None:
            return self._stage
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((86, 58, 100))  # plum token: the stage wall without art
        loader = ControlArt(max_entries=len(STAGE_LAYERS))
        for asset_id in STAGE_LAYERS:
            layer = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if layer is not None:
                surface.blit(layer, (0, 0))
        loader.clear()
        self._stage = surface
        return surface

    def board(self, picture_cells: frozenset[tuple[int, int]], axis: MirrorAxis) -> pygame.Surface:
        """The magic mirror: gilded frame, mosaic + glass halves, mirror line(s)."""

        key = (picture_cells, axis)
        cached = self._boards.get(key)
        if cached is not None:
            return cached
        pad = 6  # room for the frame's flat shadow
        width, height = FRAME_RECT.width + 2 * pad, FRAME_RECT.height + 2 * pad
        big = pygame.Surface((width * SS, height * SS), pygame.SRCALPHA)
        ox, oy = (FRAME_RECT.x - pad), (FRAME_RECT.y - pad)

        def r(rect: pygame.Rect) -> pygame.Rect:
            return pygame.Rect((rect.x - ox) * SS, (rect.y - oy) * SS, rect.width * SS, rect.height * SS)

        frame = r(FRAME_RECT)
        radius = 30 * SS
        # Flat contact shadow under the frame.
        shadow = pygame.Surface(frame.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (*INK, 70), shadow.get_rect(), border_radius=radius)
        big.blit(shadow, frame.move(0, 6 * SS))
        # Gilded frame: gold light -> gold, ink contour, one highlight.
        gold = _clip_to(_vertical_gradient(frame.size, GOLD_LIGHT, GOLD), _rounded_mask(frame.size, radius))
        big.blit(gold, frame)
        pygame.draw.rect(big, INK, frame, width=4 * SS, border_radius=radius)
        highlight = pygame.Rect(frame.x + 30 * SS, frame.y + 6 * SS, frame.width // 3, 5 * SS)
        hl = pygame.Surface(highlight.size, pygame.SRCALPHA)
        pygame.draw.rect(hl, (255, 255, 255, 170), hl.get_rect(), border_radius=3 * SS)
        big.blit(hl, highlight)

        # Inner panel: mosaic cells on the picture side, glass on the mirror side.
        inner = r(GRID_RECT.inflate(8, 8))
        inner_radius = 16 * SS
        panel = pygame.Surface(inner.size, pygame.SRCALPHA)
        glass = _vertical_gradient(inner.size, GLASS_TOP, GLASS)
        panel.blit(glass, (0, 0))
        # Diagonal shine streaks across the glass (static).
        for offset, thickness in ((0.18, 26), (0.30, 10), (0.70, 18)):
            streak = pygame.Surface(inner.size, pygame.SRCALPHA)
            x0 = int(inner.width * offset)
            points = [
                (x0, 0), (x0 + thickness * SS, 0),
                (x0 + thickness * SS - inner.height // 2, inner.height), (x0 - inner.height // 2, inner.height),
            ]
            pygame.draw.polygon(streak, (255, 255, 255, 70), points)
            panel.blit(streak, (0, 0))
        for row, col in picture_cells:
            cell = r(cell_rect(row, col)).move(-inner.x, -inner.y)
            pygame.draw.rect(panel, SAND, cell)
            pygame.draw.rect(panel, CREAM, cell.inflate(-5 * SS, -5 * SS), border_radius=8 * SS)
        panel = _clip_to(panel, _rounded_mask(inner.size, inner_radius))
        big.blit(panel, inner)
        pygame.draw.rect(big, INK, inner, width=3 * SS, border_radius=inner_radius)
        # Empty building slots on the glass: soft rounded outlines.
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if (row, col) in picture_cells:
                    continue
                slot = r(cell_rect(row, col)).inflate(-12 * SS, -12 * SS)
                pygame.draw.rect(big, GLASS_SLOT, slot, width=2 * SS, border_radius=12 * SS)

        # The magic line(s): soft glow, bright core, ink edges, star caps.
        lines: list[pygame.Rect] = []
        if axis in (MirrorAxis.VERTICAL, MirrorAxis.BOTH):
            lines.append(pygame.Rect(MIRROR_X - 6, GRID_RECT.top - 10, 12, GRID_RECT.height + 20))
        if axis in (MirrorAxis.HORIZONTAL, MirrorAxis.BOTH):
            lines.append(pygame.Rect(GRID_RECT.left - 10, MIRROR_Y - 6, GRID_RECT.width + 20, 12))
        for line in lines:
            area = r(line)
            for grow, alpha in ((30, 45), (18, 80), (9, 130)):
                glow = pygame.Surface(area.inflate(grow * SS, grow * SS).size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (*GLOW, alpha), glow.get_rect(), border_radius=glow.get_height() // 2 if line.width > line.height else glow.get_width() // 2)
                big.blit(glow, area.inflate(grow * SS, grow * SS))
        for line in lines:
            area = r(line)
            round_r = min(area.width, area.height) // 2
            pygame.draw.rect(big, MIRROR_LIGHT, area, border_radius=round_r)
            pygame.draw.rect(big, GOLD_DEEP, area, width=2 * SS, border_radius=round_r)
            for cap in ((area.midtop, area.midbottom) if line.height > line.width else (area.midleft, area.midright)):
                _star(big, cap, 11 * SS)

        surface = pygame.transform.smoothscale(big, (width, height))
        self._boards[key] = surface
        return surface

    def _tray_panel(self, count: int) -> pygame.Surface:
        panel_rect = tray_panel(count)
        pad = 6
        size = (panel_rect.width + 2 * pad, panel_rect.height + 2 * pad)
        big = pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)
        body = pygame.Rect(pad * SS, pad * SS, panel_rect.width * SS, panel_rect.height * SS)
        radius = 30 * SS
        shadow = pygame.Surface(body.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (*INK, 70), shadow.get_rect(), border_radius=radius)
        big.blit(shadow, body.move(0, 6 * SS))
        fill = _clip_to(_vertical_gradient(body.size, (255, 251, 240), CREAM), _rounded_mask(body.size, radius))
        big.blit(fill, body)
        pygame.draw.rect(big, INK, body, width=4 * SS, border_radius=radius)
        for slot in tray_rects(count):
            local = pygame.Rect(
                (slot.x - panel_rect.x + pad) * SS, (slot.y - panel_rect.y + pad) * SS, slot.width * SS, slot.height * SS
            )
            pygame.draw.rect(big, SAND, local, border_radius=20 * SS)
        return pygame.transform.smoothscale(big, size)

    # -- tiles --------------------------------------------------------------------

    def tile(self, piece: Piece, size: int) -> pygame.Surface:
        """The tile turned to its rotation, scaled once to ``size``."""

        key = ("tile", piece, size)
        cached = self._tiles.get(key)
        if cached is not None:
            return cached
        source = self._tile_source(piece.kind, piece.color_index)
        if source is None:
            image = self._fallback_tile(piece, size)
        else:
            image = pygame.transform.smoothscale(source, (size, size))
            if piece.rotation:
                image = pygame.transform.rotate(image, -90 * piece.rotation)
        self._tiles[key] = image
        return image

    def ghost(self, piece: Piece, size: int) -> pygame.Surface:
        """A see-through copy used when Lilli demonstrates a spot."""

        key = ("ghost", piece, size)
        cached = self._tiles.get(key)
        if cached is None:
            cached = self.tile(piece, size).copy()
            cached.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            self._tiles[key] = cached
        return cached

    def _tile_source(self, kind: ShapeKind, colour: int) -> pygame.Surface | None:
        key = (kind.value, colour)
        if key in self._tile_sources:
            return self._tile_sources[key]
        path = self._runtime_dir / f"mosaic_tile_{kind.value}_{COLOUR_TOKENS[colour]}.png"
        try:
            image: pygame.Surface | None = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (pygame.error, OSError, FileNotFoundError):
            image = None
        self._tile_sources[key] = image
        return image

    @staticmethod
    def _fallback_tile(piece: Piece, size: int) -> pygame.Surface:
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        rect = surface.get_rect().inflate(-6, -6)
        pygame.draw.ellipse(surface, COLOUR_RGB[piece.color_index], rect)
        pygame.draw.ellipse(surface, INK, rect, width=3)
        return surface

    # -- hint & feedback overlays ---------------------------------------------------

    def glow_ring(self, size: int) -> pygame.Surface:
        """A warm pulsing ring that says "look here" on cream and on glass."""

        key = ("glow", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
            rect = big.get_rect()
            pygame.draw.rect(big, (*GLOW, 90), rect, width=7 * SS, border_radius=20 * SS)
            inner = rect.inflate(-6 * SS, -6 * SS)
            pygame.draw.rect(big, (*GOLD_DEEP, 255), inner, width=5 * SS, border_radius=17 * SS)
            pygame.draw.rect(big, (255, 255, 255, 230), inner.inflate(-10 * SS, -10 * SS), width=2 * SS, border_radius=13 * SS)
            cached = pygame.transform.smoothscale(big, (size, size))
            self._misc[key] = cached
        return cached

    def hand_ring(self, size: int) -> pygame.Surface:
        """The ring around the tile in hand (and the tray hover)."""

        key = ("hand", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * SS, size * SS), pygame.SRCALPHA)
            rect = big.get_rect().inflate(-4 * SS, -4 * SS)
            pygame.draw.rect(big, (255, 255, 255, 235), rect, border_radius=22 * SS)
            pygame.draw.rect(big, GOLD_DEEP, rect, width=4 * SS, border_radius=22 * SS)
            pygame.draw.rect(big, INK, rect, width=2 * SS, border_radius=22 * SS)
            cached = pygame.transform.smoothscale(big, (size, size))
            self._misc[key] = cached
        return cached

    def line_flash(self, axis: MirrorAxis) -> pygame.Surface:
        """A bright overlay for the mirror line(s) while a mosaic is celebrated."""

        key = ("flash", axis)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(GRID_RECT.inflate(40, 40).size, pygame.SRCALPHA)
            origin = GRID_RECT.inflate(40, 40).topleft
            if axis in (MirrorAxis.VERTICAL, MirrorAxis.BOTH):
                line = pygame.Rect(MIRROR_X - 9 - origin[0], 0, 18, cached.get_height())
                pygame.draw.rect(cached, (255, 255, 255, 210), line, border_radius=9)
            if axis in (MirrorAxis.HORIZONTAL, MirrorAxis.BOTH):
                line = pygame.Rect(0, MIRROR_Y - 9 - origin[1], cached.get_width(), 18)
                pygame.draw.rect(cached, (255, 255, 255, 210), line, border_radius=9)
            self._misc[key] = cached
        return cached

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

    def lilli(self, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image("character.lilli", height, variant=variant)

    def clear(self) -> None:
        self._scenes.clear()
        self._boards.clear()
        self._tiles.clear()
        self._tile_sources.clear()
        self._misc.clear()
        self._fx.clear()


def _star(surface: pygame.Surface, center: tuple[int, int], radius: int) -> None:
    """A small four-point gold sparkle with an ink contour (mirror-line caps)."""

    cx, cy = center
    inner = radius * 0.38
    points = []
    for index in range(8):
        length = radius if index % 2 == 0 else inner
        dx, dy = ((0, -1), (0.7071, -0.7071), (1, 0), (0.7071, 0.7071), (0, 1), (-0.7071, 0.7071), (-1, 0), (-0.7071, -0.7071))[index]
        points.append((cx + dx * length, cy + dy * length))
    pygame.draw.polygon(surface, GOLD, points)
    pygame.draw.polygon(surface, INK, points, width=max(2, radius // 6))


__all__ = ["COLOUR_RGB", "COLOUR_TOKENS", "MirrorArt", "RUNTIME_DIR", "SLOT", "CELL"]
