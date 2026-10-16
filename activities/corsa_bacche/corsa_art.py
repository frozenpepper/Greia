"""Prepared, bounded art for La Corsa delle Bacche.

The garden backdrop is a shared biome scene (``bg.meadow_day``,
``bg.woodland_pond``, ``bg.woodland_autumn`` layers). The hedge maze itself
is painted once per garden onto that backdrop in the Greia SVG recipe in code
(cocoa ink contour, flat two-step foliage fill, one highlight per hedge, a
flat contact shadow) -- the same look as Il Labirinto Magico's hedges, so the
two garden mazes read as one family, but the code lives in this package.
Everything inside comes from the shared library: Momo (``character.momo``
poses), berries (``prop.food.{strawberry,blueberry,cherry}``), the friendly
critters (``creature.woodland.{ladybird,hedgehog}`` awake/asleep), the
"wait" glyph (``icon.hud.pause``) and FX (``fx.*``).

All scaling happens when a garden starts; drawing only blits cached surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlKit, mix

if __package__:
    from .corsa_content import CritterKind
    from .corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenGeometry
    from .corsa_model import Cell, GardenLayout
else:
    from corsa_content import CritterKind
    from corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenGeometry
    from corsa_model import Cell, GardenLayout

Rgb = tuple[int, int, int]

INK: Final[Rgb] = (75, 55, 47)  # cast contour token
SHADOW: Final[Rgb] = (106, 81, 71)
CREAM: Final[Rgb] = (255, 251, 235)
GOLD: Final[Rgb] = (251, 191, 36)
FRUITS: Final[tuple[str, ...]] = ("strawberry", "blueberry", "cherry")
FX_SIZES: Final[dict[str, float]] = {"sparkle": 1.0, "star_burst": 2.0, "dust_puff": 1.1, "confetti": 3.2}
FX_VARIANTS: Final = ("default", "frame_2", "frame_3")
BERRY_SHARE: Final = 0.66
CRITTER_SHARE: Final = 0.96
MOMO_SHARE: Final = 1.45


def fruit_for(cell: Cell) -> str:
    """Which fruit grows on a cell (stable for a layout, mixed for variety)."""

    return FRUITS[(cell[0] * 2 + cell[1]) % len(FRUITS)]


@dataclass(frozen=True, slots=True)
class Biome:
    """One garden world: shared scene layers + hedge/path colour tokens."""

    biome_id: str
    layers: tuple[str, ...]
    floor: Rgb
    floor_edge: Rgb
    hedge: Rgb
    hedge_light: Rgb
    hedge_side: Rgb
    hedge_ink: Rgb
    flecks: tuple[Rgb, ...]
    dusk: Rgb  # completion backdrop


def _leaf_family(base: Rgb) -> tuple[Rgb, Rgb, Rgb]:
    """Light / shade / material contour steps from the SVG rules (colour)."""

    return mix(base, (255, 255, 255), 0.38), mix(base, INK, 0.24), mix(base, INK, 0.58)


_LEAF: Final[Rgb] = (89, 184, 106)
_POND_LEAF: Final[Rgb] = (76, 168, 112)


def _layers(biome: str) -> tuple[str, ...]:
    return tuple(f"bg.{biome}.{layer}" for layer in ("sky", "far", "mid", "ground", "foreground"))


BIOMES: Final[tuple[Biome, ...]] = (
    Biome(
        "meadow_day",
        _layers("meadow_day"),
        (238, 221, 186),
        (221, 197, 152),
        _LEAF,
        *_leaf_family(_LEAF),
        flecks=((244, 111, 97), (255, 251, 235), (255, 194, 52)),
        dusk=(46, 92, 64),
    ),
    Biome(
        "woodland_pond",
        _layers("woodland_pond"),
        (236, 224, 192),
        (214, 198, 158),
        _POND_LEAF,
        *_leaf_family(_POND_LEAF),
        flecks=((216, 86, 131), (255, 251, 235), (148, 100, 201)),
        dusk=(37, 76, 89),
    ),
    Biome(
        "woodland_autumn",
        _layers("woodland_autumn"),
        (240, 218, 178),
        (222, 192, 142),
        _LEAF,
        *_leaf_family(_LEAF),
        flecks=((243, 154, 56), (244, 111, 97), (255, 194, 52)),
        dusk=(106, 64, 48),
    ),
)


def biome_for_garden(index: int) -> Biome:
    """Each garden of a visit has its own world (meadow, pond, autumn wood)."""

    return BIOMES[max(0, index) % len(BIOMES)]


@dataclass(frozen=True, slots=True)
class GardenSprites:
    """Everything blitted inside one garden, scaled once for its cell size."""

    cell: int
    berries: dict[str, pygame.Surface | None]
    critters: dict[tuple[CritterKind, bool], pygame.Surface | None]  # (kind, asleep)
    halo: pygame.Surface
    trail: pygame.Surface
    bubble: pygame.Surface


class CorsaArt:
    """Own every prepared surface (bounded: one backdrop, one scene, one sprite set)."""

    def __init__(self, kit: ControlKit, *, art: ControlArt | None = None, resolver=None) -> None:
        self._kit = kit
        self._resolver = resolver
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(resolver, max_entries=40)
        self._backdrop: tuple[str, pygame.Surface] | None = None
        self._sprites: GardenSprites | None = None
        self._fx: dict[tuple[str, int], tuple[pygame.Surface, ...]] = {}

    # -- cast ----------------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image("character.momo", int(height), variant=variant)

    # -- scene ---------------------------------------------------------------

    def backdrop(self, biome: Biome) -> pygame.Surface:
        if self._backdrop is not None and self._backdrop[0] == biome.biome_id:
            return self._backdrop[1]
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(biome.floor)
        # Full-screen layers are decoded through a throw-away loader so only the
        # one composed opaque backdrop stays resident (Acer RAM floor).
        loader = ControlArt(self._resolver, max_entries=1)
        for layer in biome.layers:
            image = loader.image(layer, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        self._backdrop = (biome.biome_id, surface)
        return surface

    def compose_scene(self, layout: GardenLayout, geometry: GardenGeometry, biome: Biome) -> pygame.Surface:
        """Backdrop + garden panel + hedges, painted once per garden (opaque)."""

        scene = self.backdrop(biome).copy()
        HedgePainter(layout, geometry, biome).paint(scene)
        if pygame.display.get_surface() is not None:
            scene = scene.convert()
        return scene

    # -- sprites -------------------------------------------------------------

    def sprites(self, cell: int) -> GardenSprites:
        cached = self._sprites
        if cached is not None and cached.cell == cell:
            return cached
        berry = int(cell * BERRY_SHARE)
        critter = int(cell * CRITTER_SHARE)
        critters: dict[tuple[CritterKind, bool], pygame.Surface | None] = {}
        for kind in CritterKind:
            critters[(kind, False)] = self.art.image(f"creature.woodland.{kind.value}", critter)
            critters[(kind, True)] = self.art.image(f"creature.woodland.{kind.value}", critter, variant="asleep")
        self._sprites = GardenSprites(
            cell=cell,
            berries={fruit: self.art.image(f"prop.food.{fruit}", berry) for fruit in FRUITS},
            critters=critters,
            halo=_halo(int(cell * 1.3)),
            trail=_dot(max(10, int(cell * 0.26))),
            bubble=self._bubble(max(28, int(cell * 0.52))),
        )
        return self._sprites

    def _bubble(self, size: int) -> pygame.Surface:
        """Round cream speech bubble holding the shared "pause" glyph (= wait)."""

        body = self._kit.painter.body(BodyShape.ROUND, (size, size), CREAM).copy()
        glyph = self._kit.glyph("pause", int(size * 0.7))
        if glyph is not None:
            body.blit(glyph, glyph.get_rect(center=(size // 2, size // 2)))
        return body

    def berry_icon(self, fruit: str, size: int) -> pygame.Surface | None:
        return self.art.image(f"prop.food.{fruit}", int(size))

    def fx_frames(self, name: str, cell: int) -> tuple[pygame.Surface, ...]:
        size = max(24, int(cell * FX_SIZES.get(name, 1.3)))
        key = (name, size)
        cached = self._fx.get(key)
        if cached is not None:
            return cached
        frames = tuple(
            image
            for variant in FX_VARIANTS
            if (image := self.art.image(f"fx.{name}", size, variant=variant)) is not None
        )
        if len(self._fx) > 10:
            self._fx.clear()
        self._fx[key] = frames
        return frames

    def clear(self) -> None:
        self._backdrop = None
        self._sprites = None
        self._fx.clear()
        self.art.clear()


class HedgePainter:
    """Paint one garden's hedges in the storybook recipe (code art).

    Hedge lines are merged into straight runs so a run is one rounded mass:
    all ink outlines first, then all front faces, then all tops, so joins
    between runs never show inner contour lines.
    """

    def __init__(self, layout: GardenLayout, geometry: GardenGeometry, biome: Biome) -> None:
        self.lattice = layout.lattice
        self.layout = layout
        self.geometry = geometry
        self.biome = biome
        self.height = len(self.lattice)
        self.width = len(self.lattice[0])
        seed = sum((index + 1) * ord(ch) for index, ch in enumerate("".join(self.lattice))) & 0xFFFFFFFF
        self._rng = random.Random(seed)

    def _wall(self, r: int, c: int) -> bool:
        return 0 <= r < self.height and 0 <= c < self.width and self.lattice[r][c] == "#"

    def runs(self) -> list[pygame.Rect]:
        geo = self.geometry
        rects: list[pygame.Rect] = []
        for r in range(0, self.height, 2):
            c = 0
            while c < self.width:
                if self._wall(r, c):
                    start = c
                    while c + 1 < self.width and self._wall(r, c + 1):
                        c += 1
                    if c > start or self._isolated(r, c):
                        rects.append(geo.square_rect((r, start)).union(geo.square_rect((r, c))))
                c += 1
        for c in range(0, self.width, 2):
            r = 0
            while r < self.height:
                if self._wall(r, c):
                    start = r
                    while r + 1 < self.height and self._wall(r + 1, c):
                        r += 1
                    if r > start:
                        rects.append(geo.square_rect((start, c)).union(geo.square_rect((r, c))))
                r += 1
        return rects

    def _joined_sideways(self, square: tuple[int, int]) -> bool:
        r, c = square
        return self._wall(r, c - 1) or self._wall(r, c + 1)

    def _isolated(self, r: int, c: int) -> bool:
        return not any(self._wall(r + dr, c + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))

    def paint(self, scene: pygame.Surface) -> None:
        geo, biome = self.geometry, self.biome
        gap, depth = geo.gap, geo.depth
        ink_w = max(2, int(round(gap * 0.09)))
        radius = max(3, gap // 2)
        rect = geo.rect
        panel = pygame.Rect(rect.left - gap // 2, rect.top - gap // 2, rect.width + gap, rect.height + gap + depth)

        # Garden panel: flat contact shadow, ink contour, path floor.
        overlay = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*SHADOW, 46), panel.move(0, max(4, gap // 3)), border_radius=radius + gap // 2)
        scene.blit(overlay, (0, 0))
        pygame.draw.rect(scene, INK, panel.inflate(2 * ink_w, 2 * ink_w), border_radius=radius + gap // 2 + ink_w)
        pygame.draw.rect(scene, biome.floor_edge, panel, border_radius=radius + gap // 2)
        pygame.draw.rect(scene, biome.floor, panel.inflate(-max(4, gap // 3), -max(4, gap // 3)), border_radius=radius + gap // 3)
        self._pebbles(scene)

        runs = self.runs()
        overlay.fill((0, 0, 0, 0))
        for run in runs:
            pygame.draw.rect(overlay, (*SHADOW, 40), run.move(depth // 2, depth + depth // 2), border_radius=radius)
        scene.blit(overlay, (0, 0))
        bodies = [run.union(run.move(0, depth)) for run in runs]
        for body in bodies:
            pygame.draw.rect(scene, biome.hedge_ink, body.inflate(2 * ink_w, 2 * ink_w), border_radius=radius + ink_w)
        for body in bodies:
            pygame.draw.rect(scene, biome.hedge_side, body, border_radius=radius)
        for run in runs:
            pygame.draw.rect(scene, biome.hedge, run, border_radius=radius)
        for run in runs:
            self._top_light(scene, run)
        for run in runs:
            self._flecks(scene, run)

    def _top_light(self, scene: pygame.Surface, run: pygame.Rect) -> None:
        """Second fill stop (light, upper part) plus the one highlight."""

        biome = self.biome
        gap = self.geometry.gap
        inset = max(2, gap // 8)
        band = max(2, int(gap * 0.44))
        if run.width >= run.height:
            light = pygame.Rect(run.x + inset, run.y + inset, run.width - 2 * inset, band - inset)
        else:
            # Where a vertical hedge joins a horizontal one, the horizontal
            # hedge's strip owns the shared post, so this strip stops there.
            top = run.y + inset
            bottom = run.bottom - inset
            first = self._square_at((run.centerx, run.top))
            last = self._square_at((run.centerx, run.bottom - 1))
            if first is not None and self._joined_sideways(first):
                top = self.geometry.square_rect(first).bottom
            if last is not None and self._joined_sideways(last):
                bottom = self.geometry.square_rect(last).top + inset
            light = pygame.Rect(run.x + inset, top, band - inset, bottom - top)
        if light.width > 2 and light.height > 2:
            radius = max(2, light.width // 2 if light.width < light.height else light.height // 2)
            pygame.draw.rect(scene, biome.hedge_light, light, border_radius=radius)
        thickness = max(2, gap // 9)
        if run.width >= run.height:
            stroke = pygame.Rect(light.x + inset, light.y + inset, max(0, min(run.width // 4, light.width - 2 * inset)), thickness)
        else:
            stroke = pygame.Rect(light.x + inset, light.y + inset, thickness, max(0, min(run.height // 4, light.height - 2 * inset)))
        if light.width > 2 and light.height > 2 and (stroke.width > 2 or stroke.height > 2):
            pygame.draw.rect(scene, mix(biome.hedge_light, (255, 255, 255), 0.6), stroke, border_radius=thickness)

    def _square_at(self, point: tuple[int, int]) -> tuple[int, int] | None:
        geo = self.geometry
        x, y = point
        if not (geo.xs[0] <= x < geo.xs[-1] and geo.ys[0] <= y < geo.ys[-1]):
            return None
        col = next(index for index in range(len(geo.xs) - 1) if x < geo.xs[index + 1])
        row = next(index for index in range(len(geo.ys) - 1) if y < geo.ys[index + 1])
        return (row, col)

    def _flecks(self, scene: pygame.Surface, run: pygame.Rect) -> None:
        """Small flowers in the hedges."""

        rng = self._rng
        gap = self.geometry.gap
        length = max(run.width, run.height)
        count = max(0, int(length / (gap * 3.2)))
        size = max(2, gap // 8)
        for _ in range(count):
            if rng.random() < 0.55:
                continue
            x = rng.randint(run.left + gap // 3, max(run.left + gap // 3, run.right - gap // 3))
            y = rng.randint(run.top + gap // 3, max(run.top + gap // 3, run.bottom - gap // 3))
            color = rng.choice(self.biome.flecks)
            pygame.draw.circle(scene, mix(color, INK, 0.45), (x, y), size + 1)
            pygame.draw.circle(scene, color, (x, y), size)

    def _pebbles(self, scene: pygame.Surface) -> None:
        rng = self._rng
        geo = self.geometry
        size = max(2, geo.gap // 9)
        for cell in self.layout.cells():
            if rng.random() > 0.35:
                continue
            rect = geo.cell_rect(cell)
            x = rng.randint(rect.left + size * 3, rect.right - size * 3)
            y = rng.randint(rect.top + size * 3, rect.bottom - size * 3)
            pygame.draw.ellipse(scene, self.biome.floor_edge, (x, y, size * 3, size * 2))


def _halo(size: int) -> pygame.Surface:
    """Soft warm glow disc (three flat alpha rings, no blur)."""

    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    for radius, alpha in ((center, 50), (int(center * 0.78), 70), (int(center * 0.55), 90)):
        pygame.draw.circle(surface, (255, 226, 138, alpha), (center, center), radius)
    return surface


def _dot(size: int) -> pygame.Surface:
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, (*mix(GOLD, INK, 0.35), 230), (size // 2, size // 2), size // 2)
    pygame.draw.circle(surface, (255, 236, 160, 255), (size // 2, size // 2), max(1, size // 2 - 2))
    return surface


__all__ = ["BIOMES", "Biome", "CorsaArt", "FRUITS", "GardenSprites", "HedgePainter", "biome_for_garden", "fruit_for"]
