"""Art resolution and cached surfaces for Tito's Number Forest.

Everything visible is library art or a numeral: the ``bg.woodland_*`` scene
layers (pond, autumn and snow walks), shared ``creature.woodland.*`` /
``prop.nature.*`` forest friends, ``fx.*`` bursts, ``icon.hud.*`` glyphs and
the canonical Tito. Numerals are drawn from this package's stroke font so the
tiles, the tracing guide and the child's ink always share one shape. Quantity
frames (five- and ten-frames) are painted with the shared control-kit body
recipe and filled with library creatures.

Images are decoded and scaled once into bounded caches; drawing only blits.
The live tracing ink is the one incremental surface: new ink is added as the
finger moves, never redrawn from scratch.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix

if __package__:
    from .bosco_strokes import resample
    from .bosco_trace import TraceGuide
else:
    from bosco_strokes import resample
    from bosco_trace import TraceGuide


WOODLAND_LAYERS: Final = ("sky", "far", "mid", "ground", "foreground")
# One season per walk, so replaying walks through a changing forest.
SEASONS: Final = ("woodland_pond", "woodland_autumn", "woodland_snow")

INK: Final = (75, 55, 47)          # cast ink #4B372F
CREAM: Final = (255, 251, 235)     # cast cream #FFFBEB
SAND: Final = (238, 221, 186)      # theme sand
GLOW: Final = (255, 194, 52)       # theme sunshine
WOOD: Final = (214, 168, 112)      # tray wood (forest log)
CELL: Final = (255, 248, 228)
# runtime/theme-defaults accent tokens used for numeral inks
ACCENTS: Final[dict[str, tuple[int, int, int]]] = {
    "coral": (244, 111, 97),
    "ocean": (74, 145, 216),
    "leaf": (89, 184, 106),
    "grape": (148, 100, 201),
    "raspberry": (216, 86, 131),
    "orange": (243, 154, 56),
    "turquoise": (68, 184, 174),
    "sunshine": (255, 194, 52),
}
SUPERSAMPLE: Final = 2
MAX_GLYPHS: Final = 40
MAX_FRAMES: Final = 24
FRAME_COLUMNS: Final = 5


def accent(token: str) -> tuple[int, int, int]:
    return ACCENTS.get(token, ACCENTS["ocean"])


def resolve_picture(asset_id: str, variant: str = "default") -> Path:
    """Map ``<shared id>`` or ``<shared id>#<variant>`` to a catalogue file."""

    if "#" in asset_id:
        asset_id, variant = asset_id.split("#", 1)
    return get_shared_visual_path(asset_id, variant=variant)


def frame_cells_for(*quantities: int) -> int:
    """Five-frame while every quantity fits in it, otherwise a ten-frame."""

    return 10 if max(quantities, default=0) > 5 else 5


@dataclass(frozen=True, slots=True)
class FrameGeometry:
    """A five- or ten-frame of square cells.

    Horizontal frames are rows of five (the usual ten-frame); vertical frames
    are columns of five, filled column by column, used where a tall narrow
    option card has room for bigger friends that way.
    """

    cells: int
    cell: int
    vertical: bool = False

    @classmethod
    def fit(
        cls, cells: int, box: tuple[int, int], *, max_cell: int = 96, allow_vertical: bool = False
    ) -> "FrameGeometry":
        """Largest cell size whose frame (with its padding and lip) fits ``box``."""

        width, height = box
        lines = max(1, cells // FRAME_COLUMNS)
        across = min(width / (FRAME_COLUMNS + 0.4), (height - 6) / (lines + 0.4), max_cell)
        best = cls(cells, max(12, int(across)))
        if allow_vertical:
            down = min(width / (lines + 0.4), (height - 6) / (FRAME_COLUMNS + 0.4), max_cell)
            if down > across * 1.15:
                best = cls(cells, max(12, int(down)), True)
        return best

    @property
    def lines(self) -> int:
        return max(1, self.cells // FRAME_COLUMNS)

    @property
    def pad(self) -> int:
        return max(4, int(self.cell * 0.2))

    @property
    def lip(self) -> int:
        return max(3, self.cell // 12)

    @property
    def size(self) -> tuple[int, int]:
        across, down = (self.lines, FRAME_COLUMNS) if self.vertical else (FRAME_COLUMNS, self.lines)
        return (across * self.cell + 2 * self.pad, down * self.cell + 2 * self.pad + self.lip)

    def cell_center(self, index: int) -> tuple[int, int]:
        """Centre of cell ``index`` (in filling order) relative to the frame's top-left."""

        line, place = divmod(int(index), FRAME_COLUMNS)
        col, row = (line, place) if self.vertical else (place, line)
        return (self.pad + col * self.cell + self.cell // 2, self.pad + row * self.cell + self.cell // 2)

    @property
    def item_size(self) -> int:
        return max(8, int(self.cell * 0.98))


def _thick_path(surface: pygame.Surface, points, radius: float, color) -> None:
    """Round-capped, round-joined thick polyline (circles along the path)."""

    r = max(1, int(round(radius)))
    for x, y in points:
        pygame.draw.circle(surface, color, (int(round(x)), int(round(y))), r)


class NumeralGlyphs:
    """Render stroke-font numerals (solid, hollow guide) once and cache them."""

    def __init__(self, *, max_entries: int = MAX_GLYPHS) -> None:
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._max = int(max_entries)

    def clear(self) -> None:
        self._cache.clear()

    def _cached(self, key: tuple, build: Callable[[], pygame.Surface]) -> pygame.Surface:
        surface = self._cache.get(key)
        if surface is not None:
            self._cache.move_to_end(key)
            return surface
        surface = build()
        self._cache[key] = surface
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)
        return surface

    def tile(self, value: int, size: int | tuple[int, int], token: str) -> pygame.Surface:
        """Solid numeral centred in a ``size`` box (choice tiles, signposts)."""

        width, height = (size, size) if isinstance(size, int) else size
        width, height = max(8, int(width)), max(8, int(height))
        guide = TraceGuide.fit(value, (0, 0, width, height))
        return self._cached(("tile", value, width, height, token), lambda: self._render(guide, (width, height), accent(token), hollow=False))

    def solid(self, guide: TraceGuide, size: tuple[int, int], token: str) -> pygame.Surface:
        key = ("solid", guide.value, guide.origin, guide.scale, size, token)
        return self._cached(key, lambda: self._render(guide, size, accent(token), hollow=False))

    def hollow(self, guide: TraceGuide, size: tuple[int, int]) -> pygame.Surface:
        key = ("hollow", guide.value, guide.origin, guide.scale, size)
        return self._cached(key, lambda: self._render(guide, size, CREAM, hollow=True))

    @staticmethod
    def _render(guide: TraceGuide, size: tuple[int, int], fill, *, hollow: bool) -> pygame.Surface:
        s = SUPERSAMPLE
        big = pygame.Surface((size[0] * s, size[1] * s), pygame.SRCALPHA)
        band = guide.band * s
        outline = max(2.0 * s, band * 0.12)
        paths = [resample([(x * s, y * s) for x, y in stroke.points], max(1.0, band * 0.12)) for stroke in guide.strokes]
        for points in paths:
            _thick_path(big, points, band / 2 + outline, INK)
        for points in paths:
            _thick_path(big, points, band / 2, fill)
        if not hollow:
            light = mix(fill, (255, 255, 255), 0.38)
            # One soft highlight per numeral: a thin lighter line on the first stroke.
            first = paths[0]
            cut = max(2, len(first) // 3)
            offset = band * 0.16
            _thick_path(big, [(x - offset, y - offset) for x, y in first[:cut]], band * 0.11, light)
        else:
            # Gentle centre-line dots show the path inside the hollow numeral.
            dot = max(2.0, band * 0.07)
            for points in paths:
                for x, y in resample(points, band * 0.75)[1:-1]:
                    pygame.draw.circle(big, SAND, (int(x), int(y)), int(dot))
        return pygame.transform.smoothscale(big, size)


class TraceInk:
    """The child's ink inside the tracing box, added incrementally as they trace."""

    def __init__(self, guide: TraceGuide, size: tuple[int, int], token: str) -> None:
        self.guide = guide
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        self.color = accent(token)
        self.radius = max(2, int(guide.band * 0.40))
        self._drawn = [0.0 for _ in guide.strokes]

    def sync(self, stroke_index: int, progress: float) -> bool:
        """Draw any newly traced ink; True when the surface changed."""

        changed = False
        for index, stroke in enumerate(self.guide.strokes):
            target = stroke.length if index < stroke_index else (progress if index == stroke_index else 0.0)
            if target <= self._drawn[index] + 0.5:
                continue
            start = stroke.index_at(self._drawn[index])
            stop = stroke.index_at(target)
            for x, y in stroke.points[max(0, start - 1): stop + 1]:
                pygame.draw.circle(self.surface, self.color, (int(round(x)), int(round(y))), self.radius)
            self._drawn[index] = target
            changed = True
        return changed


class BoscoArt:
    """Own the woodland backdrops and every cached picture, pose, FX, frame and glyph."""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        resolver: Callable[[str, str], Path] = resolve_picture,
        art: ControlArt | None = None,
    ) -> None:
        self._size = (int(width), int(height))
        self._resolver = resolver
        self.art = art if art is not None else ControlArt(resolver, max_entries=96)
        self.glyphs = NumeralGlyphs()
        self.painter: ControlPainter | None = None
        self._backgrounds: dict[str, pygame.Surface] = {}
        self._frames: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._glows: dict[int, pygame.Surface] = {}

    def attach_painter(self, painter: ControlPainter) -> None:
        """Use the control kit's body recipe for frames (kit owns the painter)."""

        self.painter = painter
        self._frames.clear()

    # -- scenes ---------------------------------------------------------------------
    def background(self, season: str) -> pygame.Surface:
        """Composed woodland scene; only the current season stays resident."""

        cached = self._backgrounds.get(season)
        if cached is not None:
            return cached
        self._backgrounds.clear()
        surface = self._compose(season)
        self._backgrounds[season] = surface
        return surface

    def _compose(self, season: str) -> pygame.Surface:
        # Full-screen layers are composed through a throwaway loader so the
        # decoded 1024×600 layers are not retained in the cache.
        loader = ControlArt(self._resolver, max_entries=2)
        surface = pygame.Surface(self._size)
        surface.fill((207, 234, 247))  # theme sky until the sky layer loads
        for layer in WOODLAND_LAYERS:
            image = loader.image(f"bg.{season}.{layer}", self._size)
            if image is not None:
                if season == "woodland_pond" and layer == "ground":
                    image = self._hide_pond(image)
                surface.blit(image, (0, 0))
        loader.clear()
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        return surface

    def _hide_pond(self, ground: pygame.Surface) -> pygame.Surface:
        """Turn the pond kit into a green glade: its pond would sit under the
        signpost path, so the plain meadow grass left of it is repeated over it
        (below the hill line, where the grass is a smooth vertical gradient)."""

        width, height = ground.get_size()
        sx, sy = width / 1024.0, height / 600.0
        top = int(430 * sy)
        patch = ground.subsurface(pygame.Rect(int(30 * sx), top, int(250 * sx), height - top)).copy()
        result = ground.copy()
        for left in (280, 520, 760):
            result.blit(patch, (int(left * sx), top), pygame.Rect(0, 0, int(min(250, 790 - left) * sx), height - top))
        return result

    # -- pictures -------------------------------------------------------------------
    def picture(self, picture_id: str, size: int) -> pygame.Surface | None:
        if not picture_id:
            return None
        return self.art.image(picture_id, int(size))

    def fx(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self.art.image(asset_id, int(size))

    def hud(self, glyph: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"icon.hud.{glyph}", int(size))

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    # -- quantity frames ----------------------------------------------------------------
    def _frame_cached(self, key: tuple, build: Callable[[], pygame.Surface]) -> pygame.Surface:
        surface = self._frames.get(key)
        if surface is not None:
            self._frames.move_to_end(key)
            return surface
        surface = build()
        self._frames[key] = surface
        while len(self._frames) > MAX_FRAMES:
            self._frames.popitem(last=False)
        return surface

    def frame(self, geometry: FrameGeometry) -> pygame.Surface:
        """An empty wooden five/ten-frame (cells cream, cocoa contour)."""

        return self._frame_cached(("frame", geometry.cells, geometry.cell, geometry.vertical), lambda: self._paint_frame(geometry))

    def quantity(self, creature: str, count: int, geometry: FrameGeometry) -> pygame.Surface:
        """A frame holding ``count`` forest friends, filled row by row."""

        key = ("quantity", creature, int(count), geometry.cells, geometry.cell, geometry.vertical)

        def build() -> pygame.Surface:
            surface = self.frame(geometry).copy()
            image = self.picture(creature, geometry.item_size)
            if image is not None:
                for index in range(min(int(count), geometry.cells)):
                    surface.blit(image, image.get_rect(center=geometry.cell_center(index)))
            return surface

        return self._frame_cached(key, build)

    def _paint_frame(self, geometry: FrameGeometry) -> pygame.Surface:
        width, height = geometry.size
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        cell_side = max(6, geometry.cell - max(4, geometry.cell // 9))
        contour = max(2, geometry.cell // 22)
        if self.painter is not None:
            tray = self.painter.body(BodyShape.PANEL, (width, height), WOOD, lip=geometry.lip, contour_width=max(3, geometry.cell // 16), highlight=False)
            cell = self.painter.body(BodyShape.TILE, (cell_side, cell_side), CELL, contour_width=contour, highlight=False)
        else:
            tray = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(tray, INK, tray.get_rect(), border_radius=12)
            pygame.draw.rect(tray, WOOD, tray.get_rect().inflate(-6, -6), border_radius=10)
            cell = pygame.Surface((cell_side, cell_side), pygame.SRCALPHA)
            pygame.draw.rect(cell, INK, cell.get_rect(), border_radius=8)
            pygame.draw.rect(cell, CELL, cell.get_rect().inflate(-2 * contour, -2 * contour), border_radius=6)
        surface.blit(tray, (0, 0))
        for index in range(geometry.cells):
            surface.blit(cell, cell.get_rect(center=geometry.cell_center(index)))
        return surface

    # -- glows ----------------------------------------------------------------------
    def glow(self, diameter: int) -> pygame.Surface:
        """Soft warm halo for the speaking/hinted element (built once per size)."""

        diameter = max(8, int(diameter))
        cached = self._glows.get(diameter)
        if cached is not None:
            return cached
        if len(self._glows) >= 10:
            self._glows.clear()
        surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        radius = diameter // 2
        steps = 24
        for step in range(steps):
            r = int(radius * (1.0 - step / steps))
            alpha = int(170 * (step / steps) ** 1.25)
            pygame.draw.circle(surface, (*GLOW, alpha), (radius, radius), max(1, r))
        self._glows[diameter] = surface
        return surface

    def clear(self) -> None:
        self.art.clear()
        self.glyphs.clear()
        self._frames.clear()
        self._glows.clear()
        self._backgrounds.clear()


__all__ = [
    "BoscoArt",
    "FrameGeometry",
    "NumeralGlyphs",
    "SEASONS",
    "TraceInk",
    "accent",
    "frame_cells_for",
    "resolve_picture",
]
