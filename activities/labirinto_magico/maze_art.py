"""Prepared, bounded art for Il Labirinto Magico.

The garden backdrop is a shared biome scene (``bg.meadow_day``,
``bg.woodland_autumn``, ``bg.woodland_snow``, ``bg.night_sky`` layers). The
hedge maze itself is painted once per maze onto that backdrop following the
Greia SVG recipe in code (cocoa ink contour, flat two-step foliage fill, one
highlight per hedge, a flat contact shadow) because its shape changes with
every generated maze. Everything Tito meets inside comes from the shared
library: the tent (``prop.vocab.tent``), key (``prop.everyday.key``), garden
door (``prop.vocab.door``), stars (``ui.control.star``), the firefly guide
(``creature.woodland.firefly``), arrow glyphs (``icon.hud.arrow_*``) and FX.

All scaling happens when a maze starts; drawing only blits cached surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlKit, mix

if __package__:
    from .maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, MazeGeometry
    from .maze_model import WALL, MazeLayout
else:
    from maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, MazeGeometry
    from maze_model import WALL, MazeLayout

Rgb = tuple[int, int, int]

INK: Final[Rgb] = (75, 55, 47)  # cast contour token
SHADOW: Final[Rgb] = (106, 81, 71)
CREAM: Final[Rgb] = (255, 251, 235)
GOLD: Final[Rgb] = (251, 191, 36)
FX_SIZES: Final[dict[str, float]] = {"star_burst": 2.2, "sparkle": 1.5, "dust_puff": 1.6, "confetti": 3.2}
FX_VARIANTS: Final = ("default", "frame_2", "frame_3")
ARROW_IDS: Final[dict[tuple[int, int], str]] = {
    (-1, 0): "icon.hud.arrow_up",
    (1, 0): "icon.hud.arrow_down",
    (0, -1): "icon.hud.arrow_left",
    (0, 1): "icon.hud.arrow_right",
}


@dataclass(frozen=True, slots=True)
class Biome:
    """One garden world: shared scene layers + hedge/floor colour tokens."""

    biome_id: str
    layers: tuple[str, ...]
    floor: Rgb
    floor_edge: Rgb
    hedge: Rgb
    hedge_light: Rgb
    hedge_side: Rgb
    hedge_ink: Rgb
    flecks: tuple[Rgb, ...]
    cap: Rgb | None
    dusk: Rgb  # completion backdrop


def _leaf_family(base: Rgb) -> tuple[Rgb, Rgb, Rgb]:
    """Light / shade / material contour steps from the SVG rules (§ colour)."""

    return mix(base, (255, 255, 255), 0.38), mix(base, INK, 0.24), mix(base, INK, 0.58)


_LEAF: Final[Rgb] = (89, 184, 106)
_PINE: Final[Rgb] = (64, 150, 98)
_NIGHT_LEAF: Final[Rgb] = (63, 128, 112)

BIOMES: Final[tuple[Biome, ...]] = (
    Biome(
        "meadow_day",
        ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground", "bg.meadow_day.foreground"),
        (238, 221, 186),
        (221, 197, 152),
        _LEAF,
        *_leaf_family(_LEAF),
        flecks=((244, 111, 97), (255, 251, 235), (255, 194, 52)),
        cap=None,
        dusk=(46, 92, 64),
    ),
    Biome(
        "woodland_autumn",
        ("bg.woodland_autumn.sky", "bg.woodland_autumn.far", "bg.woodland_autumn.mid", "bg.woodland_autumn.ground", "bg.woodland_autumn.foreground"),
        (240, 218, 178),
        (222, 192, 142),
        _LEAF,
        *_leaf_family(_LEAF),
        flecks=((243, 154, 56), (244, 111, 97), (255, 194, 52)),
        cap=None,
        dusk=(106, 64, 48),
    ),
    Biome(
        "woodland_snow",
        ("bg.woodland_snow.sky", "bg.woodland_snow.far", "bg.woodland_snow.mid", "bg.woodland_snow.ground", "bg.woodland_snow.foreground"),
        (222, 236, 246),
        (196, 216, 232),
        _PINE,
        *_leaf_family(_PINE),
        flecks=((255, 255, 255),),
        cap=(250, 252, 255),
        dusk=(37, 59, 89),
    ),
    Biome(
        "night_sky",
        ("bg.night_sky.sky", "bg.night_sky.stars", "bg.night_sky.far", "bg.night_sky.mid", "bg.night_sky.ground"),
        (120, 128, 170),
        (100, 108, 152),
        _NIGHT_LEAF,
        *_leaf_family(_NIGHT_LEAF),
        flecks=((255, 226, 138),),
        cap=None,
        dusk=(37, 59, 89),
    ),
)


def biome_for_visit(visits_completed: int) -> Biome:
    return BIOMES[max(0, visits_completed) % len(BIOMES)]


@dataclass(frozen=True, slots=True)
class MazeSprites:
    """Everything blitted inside one maze, scaled once for its cell size."""

    cell: int
    star: pygame.Surface
    star_small: pygame.Surface
    key: pygame.Surface | None
    door: pygame.Surface | None
    tent: pygame.Surface | None
    firefly: pygame.Surface | None
    halo: pygame.Surface
    glow: pygame.Surface
    trail: pygame.Surface
    arrows: dict[tuple[int, int], pygame.Surface | None]


class MazeArt:
    """Own every prepared surface (bounded: one backdrop, one maze, one sprite set)."""

    def __init__(self, kit: ControlKit, *, art: ControlArt | None = None, resolver=None) -> None:
        self._kit = kit
        self._resolver = resolver
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(resolver, max_entries=40)
        self._backdrop: tuple[str, pygame.Surface] | None = None
        self._sprites: MazeSprites | None = None
        self._fx: dict[tuple[str, int], tuple[pygame.Surface, ...]] = {}
        self._badges: dict[tuple[int, int], pygame.Surface] = {}

    # -- cast ----------------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image("character.tito", int(height), variant=variant)

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

    def compose_scene(self, layout: MazeLayout, geometry: MazeGeometry, biome: Biome) -> pygame.Surface:
        """Backdrop + garden panel + hedges, painted once per maze (opaque)."""

        scene = self.backdrop(biome).copy()
        HedgePainter(layout, geometry, biome).paint(scene)
        return scene

    # -- sprites -------------------------------------------------------------

    def sprites(self, cell: int) -> MazeSprites:
        cached = self._sprites
        if cached is not None and cached.cell == cell:
            return cached
        star = int(cell * 0.66)
        arrow = max(16, int(cell * 0.46))
        self._sprites = MazeSprites(
            cell=cell,
            star=self._kit.star(star),
            star_small=self._kit.star(max(12, int(cell * 0.3))),
            key=self.art.image("prop.everyday.key", int(cell * 1.0)),
            door=self.art.fit("prop.vocab.door", int(cell * 1.08)),
            tent=self.art.image("prop.vocab.tent", int(cell * 1.3)),
            firefly=self.art.image("creature.woodland.firefly", int(cell * 0.8)),
            halo=_halo(int(cell * 1.5)),
            glow=_halo(int(cell * 1.0)),
            trail=_dot(max(8, int(cell * 0.22))),
            arrows={direction: self.art.image(asset, arrow) for direction, asset in ARROW_IDS.items()},
        )
        self._badges.clear()
        return self._sprites

    def badge(self, missing: int, cell: int) -> pygame.Surface:
        """Speech bubble over a closed tent: one outline star per missing star."""

        key = (missing, cell)
        cached = self._badges.get(key)
        if cached is not None:
            return cached
        star = self._kit.star(max(18, int(cell * 0.44)), filled=False)
        pad = max(6, star.get_width() // 4)
        width = missing * star.get_width() + (missing - 1) * (pad // 2) + 2 * pad
        height = star.get_height() + pad
        body = self._kit.painter.body(BodyShape.PILL, (width, height), CREAM).copy()
        x = pad
        for _ in range(missing):
            body.blit(star, (x, pad // 2))
            x += star.get_width() + pad // 2
        if len(self._badges) > 8:
            self._badges.clear()
        self._badges[key] = body
        return body

    def fx_frames(self, name: str, cell: int) -> tuple[pygame.Surface, ...]:
        size = max(24, int(cell * FX_SIZES.get(name, 1.5)))
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


class HedgePainter:
    """Paint one generated hedge maze in the storybook recipe (code art).

    Hedge lines are merged into straight runs so a run is one rounded mass:
    all ink outlines first, then all front faces, then all tops, so joins
    between runs never show inner contour lines.
    """

    def __init__(self, layout: MazeLayout, geometry: MazeGeometry, biome: Biome) -> None:
        self.layout = layout
        self.geometry = geometry
        self.biome = biome
        seed = hash((layout.grid, layout.start, layout.goal)) & 0xFFFFFFFF
        self._rng = random.Random(seed)

    def runs(self) -> list[pygame.Rect]:
        layout, geo = self.layout, self.geometry
        rects: list[pygame.Rect] = []
        for r in range(0, layout.height, 2):
            c = 0
            while c < layout.width:
                if layout.grid[r][c] == WALL:
                    start = c
                    while c + 1 < layout.width and layout.grid[r][c + 1] == WALL:
                        c += 1
                    if c > start or self._isolated(r, c):
                        rects.append(geo.square_rect((r, start)).union(geo.square_rect((r, c))))
                c += 1
        for c in range(0, layout.width, 2):
            r = 0
            while r < layout.height:
                if layout.grid[r][c] == WALL:
                    start = r
                    while r + 1 < layout.height and layout.grid[r + 1][c] == WALL:
                        r += 1
                    if r > start:
                        rects.append(geo.square_rect((start, c)).union(geo.square_rect((r, c))))
                r += 1
        return rects

    def _joined_sideways(self, square: tuple[int, int]) -> bool:
        r, c = square
        row = self.layout.grid[r]
        return (c > 0 and row[c - 1] == WALL) or (c + 1 < len(row) and row[c + 1] == WALL)

    def _isolated(self, r: int, c: int) -> bool:
        layout = self.layout
        return all(
            not (0 <= r + dr < layout.height and 0 <= c + dc < layout.width) or layout.grid[r + dr][c + dc] != WALL
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
        )

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
        # Contact shadows of the hedges on the path.
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
            self._top_light(scene, run, radius)
        for run in runs:
            self._flecks(scene, run)

    def _top_light(self, scene: pygame.Surface, run: pygame.Rect, radius: int) -> None:
        """Second fill stop (light, upper part) plus the one highlight."""

        biome = self.biome
        gap = self.geometry.gap
        inset = max(2, gap // 8)
        # Light from the upper-left: a strip along the top of a horizontal
        # hedge and along the left of a vertical one (same thickness), so the
        # strips of joined hedges meet without seams.
        share = 0.62 if biome.cap is not None else 0.44
        band = max(2, int(gap * share))
        if run.width >= run.height:
            light = pygame.Rect(run.x + inset, run.y + inset, run.width - 2 * inset, band - inset)
        else:
            # Where a vertical hedge joins a horizontal one, the horizontal
            # hedge's strip owns the shared post, so this strip stops there.
            top = run.y + inset
            bottom = run.bottom - inset
            first, last = self.geometry.square_at((run.centerx, run.top)), self.geometry.square_at((run.centerx, run.bottom - 1))
            if first is not None and self._joined_sideways(first):
                top = self.geometry.square_rect(first).bottom
            if last is not None and self._joined_sideways(last):
                bottom = self.geometry.square_rect(last).top + inset
            light = pygame.Rect(run.x + inset, top, band - inset, bottom - top)
        if light.width > 2 and light.height > 2:
            fill = biome.cap if biome.cap is not None else biome.hedge_light
            pygame.draw.rect(scene, fill, light, border_radius=max(2, light.width // 2 if light.width < light.height else light.height // 2))
        # One soft highlight stroke inside the lit strip, near its start.
        thickness = max(2, gap // 9)
        if run.width >= run.height:
            stroke = pygame.Rect(light.x + inset, light.y + inset, max(0, min(run.width // 4, light.width - 2 * inset)), thickness)
        else:
            stroke = pygame.Rect(light.x + inset, light.y + inset, thickness, max(0, min(run.height // 4, light.height - 2 * inset)))
        if light.width > 2 and light.height > 2 and (stroke.width > 2 or stroke.height > 2):
            pygame.draw.rect(scene, mix(biome.cap or biome.hedge_light, (255, 255, 255), 0.6), stroke, border_radius=thickness)

    def _flecks(self, scene: pygame.Surface, run: pygame.Rect) -> None:
        """Small foliage accents (flowers, autumn leaves, snow, glints)."""

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
            rect = geo.square_rect(cell)
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


__all__ = ["BIOMES", "Biome", "HedgePainter", "MazeArt", "MazeSprites", "biome_for_visit"]
