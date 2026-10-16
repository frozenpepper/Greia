"""Prepared, bounded art for Bridge Builders.

The sky and hills are the shared ``bg.meadow_day`` layers. The river valley,
islands, planks and pillars change size with every crossing, so they are
painted in code in the Greia SVG recipe (cocoa ink contour, flat two-step
fills, one highlight per mass): grassy banks over warm
earth, a two-step river, thin tan wooden planks and thick slate stone slabs
made of one board per unit, and a sandstone pillar. The river rocks are the
shared ``prop.everyday.stone``; the picnic is ``prop.vocab.cake`` +
``prop.food.*`` on a painted blanket; the heavy load is ``prop.vocab.pumpkin``;
bursts are shared ``fx.*``; friends come from the canonical ``character.<id>``
poses.

Code-painted art is drawn at 2x and smooth-scaled once when a crossing starts
(or the screen is resized); drawing a frame only blits cached surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt, ControlKit, mix

if __package__:
    from .ponti_content import Crossing, Piece, PieceKind
    from .ponti_layout import (
        BANK_TOP,
        PILLAR_DEPTH,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        UNIT,
        WATER_TOP,
        CrossingView,
        thickness,
    )
else:
    from ponti_content import Crossing, Piece, PieceKind
    from ponti_layout import (
        BANK_TOP,
        PILLAR_DEPTH,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        UNIT,
        WATER_TOP,
        CrossingView,
        thickness,
    )

Rgb = tuple[int, int, int]
SS: Final = 2  # supersampling factor for code-painted art
ANGLE_STEP: Final = 10  # degrees between prepared drawbridge frames
STRIP: Final = 6  # px per strip of a bending plank

INK: Final[Rgb] = (75, 55, 47)
SHADOW: Final[Rgb] = (106, 81, 71)
CREAM: Final[Rgb] = (255, 246, 227)
WHITE: Final[Rgb] = (255, 255, 255)
GRASS: Final[Rgb] = (118, 188, 96)
GRASS_LIGHT: Final[Rgb] = (166, 216, 122)
EARTH: Final[Rgb] = (190, 136, 90)
EARTH_DARK: Final[Rgb] = (170, 118, 78)
WATER: Final[Rgb] = (92, 166, 224)
WATER_LIGHT: Final[Rgb] = (150, 204, 240)
WATER_INK: Final[Rgb] = (58, 114, 172)
GOLD: Final[Rgb] = (255, 206, 84)
BACKDROP_LAYERS: Final = ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid")
FX_VARIANTS: Final = ("default", "frame_2", "frame_3")


@dataclass(frozen=True, slots=True)
class PlankStyle:
    base: Rgb
    light: Rgb
    groove: Rgb
    peg: Rgb


WOOD_STYLE: Final = PlankStyle((224, 160, 96), (242, 198, 142), (176, 116, 66), (151, 100, 51))
STONE_STYLE: Final = PlankStyle((146, 158, 178), (194, 202, 216), (110, 120, 140), (226, 230, 238))
PILLAR_BASE: Final[Rgb] = (214, 184, 140)
PILLAR_LIGHT: Final[Rgb] = (234, 212, 174)


def style_for(piece: Piece) -> PlankStyle:
    return STONE_STYLE if piece.strong else WOOD_STYLE


# -- painting helpers --------------------------------------------------------------


def _scaled(big: pygame.Surface) -> pygame.Surface:
    w, h = big.get_size()
    return pygame.transform.smoothscale(big, (max(1, w // SS), max(1, h // SS)))


def paint_plank(length: int, strong: bool) -> pygame.Surface:
    """One plank lying flat: ``length`` boards, ink contour, one highlight."""

    style = STONE_STYLE if strong else WOOD_STYLE
    w, h = length * UNIT * SS, thickness(strong) * SS
    big = pygame.Surface((w, h), pygame.SRCALPHA)
    ink = 2 * SS
    radius = min(h // 2, 7 * SS)
    pygame.draw.rect(big, INK, (0, 0, w, h), border_radius=radius)
    inner = pygame.Rect(ink, ink, w - 2 * ink, h - 2 * ink)
    pygame.draw.rect(big, style.base, inner, border_radius=max(1, radius - ink))
    # Every other board a touch darker, so the boards (units) can be counted.
    alternate = mix(style.base, style.groove, 0.28)
    clip = big.get_clip()
    big.set_clip(inner)
    for board in range(1, length, 2):
        pygame.draw.rect(big, alternate, (board * UNIT * SS, 0, UNIT * SS, h))
    big.set_clip(clip)
    pygame.draw.rect(big, INK, (0, 0, w, h), width=ink, border_radius=radius)
    band = pygame.Rect(inner.x + radius, inner.y + SS, inner.width - 2 * radius, max(SS, inner.height // 4))
    pygame.draw.rect(big, style.light, band, border_radius=band.height // 2)
    for board in range(1, length):
        x = board * UNIT * SS
        pygame.draw.line(big, INK, (x, inner.top), (x, inner.bottom), SS + 1)
    peg_r = max(2, int(h * (0.13 if strong else 0.17)))
    for board in range(length):
        cx = int((board + 0.5) * UNIT * SS)
        cy = inner.centery + (SS if strong else 0)
        pygame.draw.circle(big, INK if not strong else style.groove, (cx, cy), peg_r + SS)
        pygame.draw.circle(big, style.peg, (cx, cy), peg_r)
    return _scaled(big)


def paint_pillar(*, wet: bool = True) -> pygame.Surface:
    """Sandstone pier, one unit wide; ``wet`` tints the foot under the water line."""

    w, h = UNIT * SS, PILLAR_DEPTH * SS
    big = pygame.Surface((w, h), pygame.SRCALPHA)
    ink = 2 * SS
    pygame.draw.rect(big, INK, (0, 0, w, h), border_radius=5 * SS)
    inner = pygame.Rect(ink, ink, w - 2 * ink, h - 2 * ink)
    pygame.draw.rect(big, PILLAR_BASE, inner, border_radius=4 * SS)
    pygame.draw.rect(big, PILLAR_LIGHT, (inner.x + 3 * SS, inner.y + 3 * SS, inner.width // 4, inner.height - 6 * SS), border_radius=3 * SS)
    courses = 4
    course_h = inner.height / courses
    mortar = mix(PILLAR_BASE, INK, 0.35)
    for row in range(1, courses):
        y = int(inner.y + row * course_h)
        pygame.draw.line(big, mortar, (inner.x + SS, y), (inner.right - SS, y), SS + 1)
    for row in range(courses):
        x = inner.centerx + (inner.width // 5 if row % 2 else -inner.width // 5)
        y0 = int(inner.y + row * course_h) + SS
        pygame.draw.line(big, mortar, (x, y0), (x, int(y0 + course_h) - 2 * SS), SS + 1)
    if not wet:
        return _scaled(big)
    # The foot is under water: tint it towards the river below the water line.
    water_line = (WATER_TOP - BANK_TOP) * SS
    tint = pygame.Surface((w, h - water_line), pygame.SRCALPHA)
    tint.fill((*WATER, 150))
    big.blit(tint, (0, water_line), special_flags=0)
    pygame.draw.line(big, WATER_LIGHT, (0, water_line), (w, water_line), 2 * SS)
    return _scaled(big)


def _faded(surface: pygame.Surface, alpha: int) -> pygame.Surface:
    copy = surface.copy()
    copy.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return copy


def _halo(size: tuple[int, int], color: Rgb = (255, 226, 138)) -> pygame.Surface:
    """Soft glow (three flat alpha rounded rects, no blur)."""

    w, h = size
    surface = pygame.Surface((max(2, w), max(2, h)), pygame.SRCALPHA)
    for inset, alpha in ((0, 50), (w // 12, 70), (w // 6, 95)):
        rect = pygame.Rect(0, 0, w, h).inflate(-2 * inset, -2 * inset)
        if rect.width > 2 and rect.height > 2:
            pygame.draw.rect(surface, (*color, alpha), rect, border_radius=min(rect.width, rect.height) // 2)
    return surface


def _dash(color: Rgb) -> pygame.Surface:
    """One unit mark of the measuring line across the water."""

    w, h = (UNIT - 16) * SS, 8 * SS
    big = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(big, INK, (0, 0, w, h), border_radius=h // 2)
    pygame.draw.rect(big, color, (SS * 2, SS * 2, w - SS * 4, h - SS * 4), border_radius=h // 2)
    return _scaled(big)


@dataclass(frozen=True, slots=True)
class PlankFrames:
    """One plank kind prepared for drawing: flat, upright ghost, rotations and bend strips."""

    flat: pygame.Surface
    upright_ghost: pygame.Surface
    rotations: tuple[pygame.Surface, ...]  # index = angle // ANGLE_STEP
    strips: tuple[tuple[int, pygame.Surface], ...]  # (x offset, strip) for bending


class BridgeArt:
    """Own every prepared surface (bounded: one backdrop, one scene, one kit of sprites)."""

    def __init__(self, kit: ControlKit, *, art: ControlArt | None = None, resolver=None) -> None:
        self._kit = kit
        self._resolver = resolver
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(resolver, max_entries=48)
        self._backdrop: pygame.Surface | None = None
        self._planks: dict[tuple[int, bool], PlankFrames] = {}
        self._pillar: pygame.Surface | None = None
        self._pillar_ghost: pygame.Surface | None = None
        self._post: tuple[pygame.Surface, tuple[int, int]] | None = None
        self._fx: dict[tuple[str, int], tuple[pygame.Surface, ...]] = {}
        self._icons: dict[tuple, pygame.Surface] = {}
        self.dash = _dash(CREAM)
        self.dash_missing = _dash(GOLD)

    # -- cast ------------------------------------------------------------------

    def cast_pose(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image(f"character.{character}", int(height), variant=variant)

    def load(self, height: int) -> pygame.Surface | None:
        """The heavy friend's pumpkin."""

        return self.art.image("prop.vocab.pumpkin", int(height))

    # -- scene -----------------------------------------------------------------

    def backdrop(self) -> pygame.Surface:
        if self._backdrop is not None:
            return self._backdrop
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((176, 214, 238))
        # Full-screen layers decode through a throw-away loader so only the one
        # composed opaque backdrop stays resident (Acer RAM floor).
        loader = ControlArt(self._resolver, max_entries=1)
        for layer in BACKDROP_LAYERS:
            image = loader.image(layer, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        self._backdrop = surface
        return surface

    def compose_scene(self, crossing: Crossing, view: CrossingView) -> pygame.Surface:
        """Backdrop + river valley + islands + rocks + seat posts + picnic, painted once."""

        scene = self.backdrop().copy()
        top = BANK_TOP - 70
        terrain = self._paint_terrain(crossing, view, top)
        scene.blit(terrain, (0, top))
        self._paint_rocks(scene, crossing, view)
        self._paint_front_water(scene, view)
        for seat_x in self._fixed_seat_xs(crossing, view):
            self.paint_post(scene, seat_x)
        self._paint_picnic(scene, view)
        self._paint_flowers(scene, view)
        return scene

    @staticmethod
    def _fixed_seat_xs(crossing: Crossing, view: CrossingView) -> list[int]:
        return [view.left_x] + [view.x(start + width) for start, width in crossing.islands]

    def _paint_terrain(self, crossing: Crossing, view: CrossingView, top: int) -> pygame.Surface:
        height = REFERENCE_HEIGHT - top
        big = pygame.Surface((REFERENCE_WIDTH * SS, height * SS), pygame.SRCALPHA)
        k = SS
        bank_y = (BANK_TOP - top) * k
        water_y = (WATER_TOP - top) * k
        bottom = height * k + 10
        left, right = view.left_x * k, view.right_x * k
        # River (behind the banks, between them).
        pygame.draw.rect(big, WATER, (left - 20, water_y, right - left + 40, bottom - water_y))
        pygame.draw.rect(big, WATER_LIGHT, (left - 20, water_y, right - left + 40, 16 * k))
        pygame.draw.line(big, WATER_INK, (left - 20, water_y), (right + 20, water_y), 2 * k)
        for index in range(int((right - left) / (70 * k)) + 1):
            x = left + 30 * k + index * 70 * k
            y = water_y + (34 + (index % 2) * 26) * k
            if x + 30 * k < right:
                pygame.draw.line(big, WATER_LIGHT, (x, y), (x + 30 * k, y), 3 * k)
        # Banks and islands: grass cap over warm earth, ink contour.
        masses = [
            pygame.Rect(-40 * k, bank_y, left + 40 * k, bottom - bank_y),
            pygame.Rect(right, bank_y, REFERENCE_WIDTH * k + 40 * k - right, bottom - bank_y),
        ]
        for index in range(len(crossing.islands)):
            rect = view.island_rect(index)
            masses.append(pygame.Rect(rect.x * k, bank_y, rect.width * k, bottom - bank_y))
        for mass in masses:
            self._paint_mass(big, mass, k)
        return _scaled(big)

    @staticmethod
    def _paint_mass(big: pygame.Surface, mass: pygame.Rect, k: int) -> None:
        ink = 2 * k
        radius = 12 * k
        pygame.draw.rect(big, INK, mass.inflate(2 * ink, 2 * ink), border_radius=radius)
        pygame.draw.rect(big, EARTH, mass, border_radius=radius)
        lower = pygame.Rect(mass.x, mass.y + 64 * k, mass.width, max(0, mass.height - 64 * k))
        pygame.draw.rect(big, EARTH_DARK, lower, border_bottom_left_radius=radius, border_bottom_right_radius=radius)
        # Pebbles: a few flat lighter ovals for texture (fixed pattern, no RNG).
        pebble = mix(EARTH, WHITE, 0.22)
        for index in range(max(1, mass.width // (90 * k))):
            px = mass.x + 30 * k + index * 90 * k + (index % 2) * 24 * k
            py = mass.y + (40 + (index % 3) * 26) * k
            if px + 20 * k < mass.right:
                pygame.draw.ellipse(big, pebble, (px, py, 18 * k, 9 * k))
        cap = pygame.Rect(mass.x, mass.y, mass.width, 18 * k)
        pygame.draw.rect(big, GRASS, cap, border_top_left_radius=radius, border_top_right_radius=radius)
        pygame.draw.line(big, INK, (mass.x + radius // 2, cap.bottom), (mass.right - radius // 2, cap.bottom), k + 1)
        hl = pygame.Rect(mass.x + radius, mass.y + 4 * k, max(0, mass.width - 2 * radius), 4 * k)
        if hl.width > 0:
            pygame.draw.rect(big, GRASS_LIGHT, hl, border_radius=2 * k)

    def _paint_rocks(self, scene: pygame.Surface, crossing: Crossing, view: CrossingView) -> None:
        size = (UNIT + 22, int((UNIT + 22) * 0.62))
        rock = self.art.image("prop.everyday.stone", size)
        for start in crossing.spots:
            cx = view.x(start + 0.5)
            if rock is not None:
                crop = rock.get_bounding_rect()
                scene.blit(rock, rock.get_rect(midbottom=(cx, WATER_TOP + 30 + (rock.get_height() - crop.bottom))))
            else:
                pygame.draw.ellipse(scene, (170, 174, 186), (cx - UNIT // 2, WATER_TOP - 6, UNIT, 32))

    @staticmethod
    def _paint_front_water(scene: pygame.Surface, view: CrossingView) -> None:
        """Translucent water in front of island and rock feet."""

        band = pygame.Surface((view.right_x - view.left_x, REFERENCE_HEIGHT - WATER_TOP - 22), pygame.SRCALPHA)
        band.fill((*WATER, 175))
        scene.blit(band, (view.left_x, WATER_TOP + 22))
        pygame.draw.line(scene, WATER_LIGHT, (view.left_x + 2, WATER_TOP + 22), (view.right_x - 2, WATER_TOP + 22), 2)

    def post(self) -> tuple[pygame.Surface, tuple[int, int]]:
        """Rope post + hinge bracket sprite and its offset from a seat's hinge."""

        if self._post is None:
            surface = pygame.Surface((56, 76), pygame.SRCALPHA)
            seat_x, base_y = 48, 66  # the hinge inside the sprite
            post = pygame.Rect(0, 0, 10, 56)
            post.midbottom = (seat_x - 34, base_y + 2)
            pygame.draw.rect(surface, INK, post.inflate(4, 4), border_radius=4)
            pygame.draw.rect(surface, (176, 118, 74), post, border_radius=3)
            pygame.draw.rect(surface, (212, 162, 112), (post.x + 2, post.y + 4, 3, post.height - 8), border_radius=1)
            pygame.draw.circle(surface, INK, (post.centerx, post.top), 7)
            pygame.draw.circle(surface, (176, 118, 74), (post.centerx, post.top), 5)
            bracket = pygame.Rect(seat_x - 14, base_y - 8, 14, 10)
            pygame.draw.rect(surface, INK, bracket.inflate(2, 2), border_radius=3)
            pygame.draw.rect(surface, (128, 136, 152), bracket, border_radius=3)
            self._post = (surface, (-seat_x, -base_y))
        return self._post

    def paint_post(self, target: pygame.Surface, seat_x: int, base_y: int = BANK_TOP) -> None:
        surface, (dx, dy) = self.post()
        target.blit(surface, (seat_x + dx, base_y + dy))

    @staticmethod
    def post_top(seat_x: int, base_y: int = BANK_TOP) -> tuple[int, int]:
        return (seat_x - 34, base_y - 54)

    def _paint_picnic(self, scene: pygame.Surface, view: CrossingView) -> None:
        cx = view.picnic_x
        k = SS
        w, h = 176, 30
        big = pygame.Surface((w * k + 8 * k, h * k + 8 * k), pygame.SRCALPHA)
        quad = [(4 * k + 14 * k, 4 * k), ((w - 10) * k, 4 * k), ((w + 4) * k, (h + 4) * k), (4 * k, (h + 4) * k)]
        pygame.draw.polygon(big, INK, quad)
        inner = [(x + (k * 2 if i in (0, 3) else -k * 2), y + (k * 2 if i < 2 else -k * 2)) for i, (x, y) in enumerate(quad)]
        pygame.draw.polygon(big, CREAM, inner)
        red = (230, 98, 98)
        cols, rows = 8, 2
        for row in range(rows):
            for col in range(cols):
                if (row + col) % 2:
                    continue
                t0, t1 = row / rows, (row + 1) / rows
                s0, s1 = col / cols, (col + 1) / cols

                def point(s: float, t: float) -> tuple[float, float]:
                    a = (inner[0][0] + (inner[3][0] - inner[0][0]) * t, inner[0][1] + (inner[3][1] - inner[0][1]) * t)
                    b = (inner[1][0] + (inner[2][0] - inner[1][0]) * t, inner[1][1] + (inner[2][1] - inner[1][1]) * t)
                    return (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)

                pygame.draw.polygon(big, red, [point(s0, t0), point(s1, t0), point(s1, t1), point(s0, t1)])
        blanket = _scaled(big)
        scene.blit(blanket, blanket.get_rect(midtop=(cx, BANK_TOP - 12)))
        cake = self.art.image("prop.vocab.cake", 74)
        if cake is not None:
            scene.blit(cake, cake.get_rect(midbottom=(cx + 18, BANK_TOP + 8)))
        apple = self.art.image("prop.food.apple", 42)
        if apple is not None:
            scene.blit(apple, apple.get_rect(midbottom=(cx - 46, BANK_TOP + 10)))
        berry = self.art.image("prop.food.strawberry", 34)
        if berry is not None:
            scene.blit(berry, berry.get_rect(midbottom=(cx + 70, BANK_TOP + 14)))

    def _paint_flowers(self, scene: pygame.Surface, view: CrossingView) -> None:
        flower = self.art.image("prop.nature.flower", 34)
        if flower is None:
            return
        for x in (view.left_x - 190, view.left_x - 36, view.right_x + 40, REFERENCE_WIDTH - 30):
            if 16 < x < REFERENCE_WIDTH - 10 and abs(x - view.picnic_x) > 110:
                scene.blit(flower, flower.get_rect(midbottom=(x, BANK_TOP + 6)))

    # -- pieces ------------------------------------------------------------------

    def plank(self, piece: Piece) -> PlankFrames:
        key = (piece.length, piece.strong)
        cached = self._planks.get(key)
        if cached is not None:
            return cached
        flat = paint_plank(piece.length, piece.strong)
        rotations = tuple(
            pygame.transform.rotozoom(flat, angle, 1.0) if angle else flat
            for angle in range(0, 91, ANGLE_STEP)
        )
        strips = tuple(
            (x, flat.subsurface((x, 0, min(STRIP, flat.get_width() - x), flat.get_height())))
            for x in range(0, flat.get_width(), STRIP)
        )
        frames = PlankFrames(flat, _faded(rotations[-1], 120), rotations, strips)
        if len(self._planks) >= 8:
            self._planks.clear()
        self._planks[key] = frames
        return frames

    def pillar(self) -> pygame.Surface:
        if self._pillar is None:
            self._pillar = paint_pillar()
        return self._pillar

    def pillar_ghost(self) -> pygame.Surface:
        if self._pillar_ghost is None:
            self._pillar_ghost = _faded(self.pillar(), 120)
        return self._pillar_ghost

    def prepare(self, crossing: Crossing) -> None:
        """Warm the sprites one crossing needs (so the first frame never paints)."""

        for piece in crossing.pieces:
            if piece.kind is PieceKind.PLANK:
                self.plank(piece)
            else:
                self.pillar()

    def tray_icon(self, piece: Piece, size: tuple[int, int], *, faded: bool) -> pygame.Surface:
        """Tray picture: planks at true scale (one unit = one board), pillar fitted."""

        key = (piece.signature, size, faded)
        cached = self._icons.get(key)
        if cached is not None:
            return cached
        if piece.kind is PieceKind.PLANK:
            surface = self.plank(piece).flat
        else:
            pillar = paint_pillar(wet=False)
            scale = min(1.0, size[1] / pillar.get_height())
            surface = pygame.transform.smoothscale(
                pillar, (max(1, int(pillar.get_width() * scale)), max(1, int(pillar.get_height() * scale)))
            )
        if faded:
            surface = _faded(surface, 80)
        if len(self._icons) > 24:
            self._icons.clear()
        self._icons[key] = surface
        return surface

    # -- fx / glow ---------------------------------------------------------------

    def fx_frames(self, name: str, size: int) -> tuple[pygame.Surface, ...]:
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

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("glow", size)
        cached = self._icons.get(key)
        if cached is None:
            cached = _halo(size)
            if len(self._icons) > 24:
                self._icons.clear()
            self._icons[key] = cached
        return cached


def rotate_point(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    """Rotate a point (relative to a plank hinge) up by ``angle_deg`` (screen y down)."""

    a = math.radians(angle_deg)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def rotated_center(length_px: float, thick_px: float, angle_deg: float) -> tuple[float, float]:
    """Centre of a hinged plank (lying on ``y in [-thick, 0]``) rotated up around its hinge."""

    return rotate_point(length_px / 2, -thick_px / 2, angle_deg)


__all__ = [
    "ANGLE_STEP",
    "BridgeArt",
    "PlankFrames",
    "paint_pillar",
    "paint_plank",
    "rotate_point",
    "rotated_center",
]
