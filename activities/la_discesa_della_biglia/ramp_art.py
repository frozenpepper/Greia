"""Prepared, bounded art for Tito's Marble Run.

The setting is a shared biome scene: the garden (``bg.meadow_day`` layers) or
the playroom (``bg.indoor_room.wall_playroom`` + a floor). The wooden board,
its fixed shelves, the marble tube, the movable ramps and funnels, the basket
and the marble change shape with every board, so they are painted in code in
the Greia SVG recipe (cocoa ink contour, flat two-step fill, one highlight per
mass, flat contact shadows), matching the Activity icon: orange pegged ramps,
a raspberry marble, a leaf-green basket (funnels are grape so they stand
out on the ocean-accent kit tiles). The bumper is the shared wooden block
``prop.blocks.cylinder`` (coral); the slots are the shared dashed block slot
``prop.blocks.rectangle`` (slot); bursts are shared ``fx.*``; Tito comes from
the canonical ``character.tito`` poses.

Everything is painted at 2x and smooth-scaled once when a board starts (or
the screen is resized); drawing a frame only blits cached surfaces.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Final

import pygame

from greia_platform.activity_controls import ControlArt, ControlKit, mix

if __package__:
    from .ramp_content import (
        BASKET_DEPTH,
        BASKET_INNER,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        BUMPER_HALF_HEIGHT,
        BUMPER_RADIUS,
        MARBLE_RADIUS,
        PLANK_RADIUS,
        SLOT_HEIGHT,
        SLOT_WIDTH,
        Board,
        Capsule,
        Facing,
        PieceKind,
        piece_capsules,
    )
    from .ramp_layout import FRAME, REFERENCE_HEIGHT, REFERENCE_WIDTH, BoardView
else:
    from ramp_content import (
        BASKET_DEPTH,
        BASKET_INNER,
        BOARD_HEIGHT,
        BOARD_WIDTH,
        BUMPER_HALF_HEIGHT,
        BUMPER_RADIUS,
        MARBLE_RADIUS,
        PLANK_RADIUS,
        SLOT_HEIGHT,
        SLOT_WIDTH,
        Board,
        Capsule,
        Facing,
        PieceKind,
        piece_capsules,
    )
    from ramp_layout import FRAME, REFERENCE_HEIGHT, REFERENCE_WIDTH, BoardView

Rgb = tuple[int, int, int]
SS: Final = 2  # supersampling factor for code-painted art

INK: Final[Rgb] = (75, 55, 47)
SHADOW: Final[Rgb] = (106, 81, 71)
CREAM: Final[Rgb] = (255, 246, 227)
WHITE: Final[Rgb] = (255, 255, 255)


@dataclass(frozen=True, slots=True)
class PlankStyle:
    """Fill steps for one family of planks (base, light highlight, end pegs)."""

    base: Rgb
    light: Rgb
    peg: Rgb | None
    ink: Rgb = INK


RAMP_STYLE: Final = PlankStyle((243, 154, 56), (247, 189, 126), (151, 100, 51))
FUNNEL_STYLE: Final = PlankStyle((155, 109, 214), (196, 168, 236), (104, 70, 160))
SHELF_STYLE: Final = PlankStyle((176, 118, 74), (212, 162, 112), (196, 198, 206))
TUBE_STYLE: Final = PlankStyle((74, 145, 216), (137, 184, 230), None)
BASKET_GREEN: Final[Rgb] = (89, 184, 106)
BASKET_RIM: Final[Rgb] = (147, 209, 158)
BASKET_INK: Final[Rgb] = (81, 113, 74)
MARBLE_LIGHT: Final[Rgb] = (230, 145, 174)
MARBLE_BASE: Final[Rgb] = (216, 86, 131)
MARBLE_INK: Final[Rgb] = (138, 69, 85)
MARBLE_SWIRL: Final[Rgb] = (251, 225, 234)
MARBLE_FRAMES: Final = 16
FX_VARIANTS: Final = ("default", "frame_2", "frame_3")


@dataclass(frozen=True, slots=True)
class Setting:
    """One place the board stands in: shared scene layers + a dusk colour."""

    setting_id: str
    layers: tuple[str, ...]
    dusk: Rgb
    board_wood: Rgb


SETTINGS: Final[dict[str, Setting]] = {
    "garden": Setting(
        "garden",
        ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground", "bg.meadow_day.foreground"),
        (46, 92, 64),
        (226, 170, 104),
    ),
    "playroom": Setting(
        "playroom",
        ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood"),
        (64, 72, 112),
        (222, 160, 96),
    ),
}


@dataclass(frozen=True, slots=True)
class Sprite:
    """A prepared surface plus where its anchor (board-unit origin) sits in it."""

    surface: pygame.Surface
    anchor: tuple[int, int]

    def blit(self, target: pygame.Surface, at: tuple[int, int]) -> None:
        target.blit(self.surface, (at[0] - self.anchor[0], at[1] - self.anchor[1]))


# -- low-level painting ------------------------------------------------------------


def _capsule_poly(a: tuple[float, float], b: tuple[float, float], width: float) -> list[tuple[float, float]]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return []
    nx, ny = -dy / length * width, dx / length * width
    return [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]


def _thick(surface: pygame.Surface, color, a, b, width: float) -> None:
    """Round-capped thick segment (polygon body + two discs)."""

    poly = _capsule_poly(a, b, width)
    if poly:
        pygame.draw.polygon(surface, color, poly)
    pygame.draw.circle(surface, color, (round(a[0]), round(a[1])), max(1, round(width)))
    pygame.draw.circle(surface, color, (round(b[0]), round(b[1])), max(1, round(width)))


def paint_planks(
    capsules: Sequence[Capsule],
    style: PlankStyle,
    scale: float,
    origin: tuple[float, float],
    *,
    pegs: bool = True,
) -> Sprite:
    """Paint wooden planks (capsules in board units) as one anti-aliased sprite.

    ``origin`` is the board-unit point that becomes the sprite anchor.
    """

    ink_w = max(1.6, 2.2 / max(0.4, scale))  # ~2 px contour at any scale (board units)
    pad = max(c.radius for c in capsules) + ink_w + 2
    min_x = min(min(c.a[0], c.b[0]) for c in capsules) - pad
    max_x = max(max(c.a[0], c.b[0]) for c in capsules) + pad
    min_y = min(min(c.a[1], c.b[1]) for c in capsules) - pad
    max_y = max(max(c.a[1], c.b[1]) for c in capsules) + pad
    k = scale * SS
    width = max(2, int(math.ceil((max_x - min_x) * k)))
    height = max(2, int(math.ceil((max_y - min_y) * k)))
    big = pygame.Surface((width, height), pygame.SRCALPHA)

    def p(point: tuple[float, float]) -> tuple[float, float]:
        return ((point[0] - min_x) * k, (point[1] - min_y) * k)

    for c in capsules:
        _thick(big, style.ink, p(c.a), p(c.b), (c.radius + ink_w) * k)
    for c in capsules:
        _thick(big, style.base, p(c.a), p(c.b), c.radius * k)
    for c in capsules:
        dx, dy = c.b[0] - c.a[0], c.b[1] - c.a[1]
        length = math.hypot(dx, dy)
        if length < c.radius * 2:
            # A round peg: one highlight dot towards the upper left.
            centre = p(c.a)
            pygame.draw.circle(big, style.light, (centre[0] - c.radius * k * 0.3, centre[1] - c.radius * k * 0.3), c.radius * k * 0.38)
            continue
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        if ny > 0:  # the "up" normal points towards smaller y
            nx, ny = -nx, -ny
        offset = c.radius * 0.42
        trim = c.radius * 1.2
        a = (c.a[0] + ux * trim + nx * offset, c.a[1] + uy * trim + ny * offset)
        b = (c.b[0] - ux * trim + nx * offset, c.b[1] - uy * trim + ny * offset)
        _thick(big, style.light, p(a), p(b), c.radius * 0.28 * k)
    if pegs and style.peg is not None:
        for c in capsules:
            if math.hypot(c.b[0] - c.a[0], c.b[1] - c.a[1]) < c.radius * 2:
                continue
            for end in (c.a, c.b):
                centre = p(end)
                pygame.draw.circle(big, style.ink, centre, c.radius * k * 0.62 + ink_w * k * 0.7)
                pygame.draw.circle(big, style.peg, centre, c.radius * k * 0.62)
    surface = pygame.transform.smoothscale(big, (max(1, width // SS), max(1, height // SS)))
    anchor = (int(round((origin[0] - min_x) * scale)), int(round((origin[1] - min_y) * scale)))
    return Sprite(surface, anchor)


def _halo(size: tuple[int, int], color: Rgb = (255, 226, 138)) -> pygame.Surface:
    """Soft glow (three flat alpha rounded rects, no blur)."""

    w, h = size
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    for inset, alpha in ((0, 50), (w // 12, 70), (w // 6, 95)):
        rect = pygame.Rect(0, 0, w, h).inflate(-2 * inset, -2 * inset)
        if rect.width > 2 and rect.height > 2:
            pygame.draw.rect(surface, (*color, alpha), rect, border_radius=min(rect.width, rect.height) // 2)
    return surface


def _shine(size: tuple[int, int]) -> pygame.Surface:
    """The resting look of an empty slot: a warm, quiet sunny patch."""

    w, h = size
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    radius = min(w, h) // 3
    pygame.draw.rect(surface, (255, 214, 120, 70), (0, 0, w, h), border_radius=radius)
    pygame.draw.rect(surface, (255, 236, 170, 90), (w // 10, h // 6, w - w // 5, h - h // 3), border_radius=radius)
    return surface


def _shadow(sprite: Sprite) -> Sprite:
    """Flat contact shadow of a piece on the board (its silhouette, soft cocoa)."""

    mask = pygame.mask.from_surface(sprite.surface, 40)
    silhouette = mask.to_surface(setcolor=(*SHADOW, 46), unsetcolor=(0, 0, 0, 0))
    return Sprite(silhouette, sprite.anchor)


def _faded(surface: pygame.Surface, alpha: int) -> pygame.Surface:
    copy = surface.copy()
    copy.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return copy


@dataclass(frozen=True, slots=True)
class BoardSprites:
    """Everything blitted on the board, scaled once for one board scale."""

    scale: float
    marble: tuple[pygame.Surface, ...]
    marble_shadow: pygame.Surface
    trail: pygame.Surface
    ramp: dict[Facing, Sprite]
    ramp_ghost: dict[Facing, Sprite]
    funnel: Sprite
    funnel_ghost: Sprite
    bumper: Sprite | None
    bumper_ghost: Sprite | None
    slot: pygame.Surface | None
    slot_shine: pygame.Surface
    slot_glow: pygame.Surface
    basket_back: Sprite
    basket_front: Sprite
    shadows: dict[tuple[PieceKind, Facing], Sprite]
    shadow_offset: tuple[int, int]

    def shadow(self, kind: PieceKind, facing: Facing) -> Sprite | None:
        return self.shadows.get((kind, facing if kind is PieceKind.RAMP else Facing.RIGHT))

    def piece(self, kind: PieceKind, facing: Facing, *, ghost: bool = False) -> Sprite | None:
        if kind is PieceKind.RAMP:
            return (self.ramp_ghost if ghost else self.ramp)[facing]
        if kind is PieceKind.FUNNEL:
            return self.funnel_ghost if ghost else self.funnel
        return self.bumper_ghost if ghost else self.bumper


class RunArt:
    """Own every prepared surface (bounded: one backdrop, one scene, one sprite set)."""

    def __init__(self, kit: ControlKit, *, art: ControlArt | None = None, resolver=None) -> None:
        self._kit = kit
        self._resolver = resolver
        # Content art gets its own bounded cache so it never evicts kit glyphs.
        self.art = art if art is not None else ControlArt(resolver, max_entries=40)
        self._backdrop: tuple[str, pygame.Surface] | None = None
        self._sprites: BoardSprites | None = None
        self._fx: dict[tuple[str, int], tuple[pygame.Surface, ...]] = {}
        self._icons: dict[tuple, pygame.Surface] = {}

    # -- cast ------------------------------------------------------------------

    def cast_pose(self, variant: str, height: int) -> pygame.Surface | None:
        return self.art.image("character.tito", int(height), variant=variant)

    # -- scene -----------------------------------------------------------------

    def backdrop(self, setting: Setting) -> pygame.Surface:
        if self._backdrop is not None and self._backdrop[0] == setting.setting_id:
            return self._backdrop[1]
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(setting.dusk)
        # Full-screen layers decode through a throw-away loader so only the one
        # composed opaque backdrop stays resident (Acer RAM floor).
        loader = ControlArt(self._resolver, max_entries=1)
        for layer in setting.layers:
            image = loader.image(layer, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        self._backdrop = (setting.setting_id, surface)
        return surface

    def compose_scene(self, board: Board, view: BoardView, setting: Setting) -> pygame.Surface:
        """Backdrop + wooden board + fixed shelves + marble tube, painted once (opaque)."""

        scene = self.backdrop(setting).copy()
        self._paint_board(scene, view, setting)
        if board.shelves:
            shelves = [Capsule(s.a, s.b, PLANK_RADIUS, 0.0, "shelf") for s in board.shelves]
            sprite = paint_planks(shelves, SHELF_STYLE, view.scale, (0.0, 0.0))
            ox, oy = view.point(0.0, 0.0)
            _shadow(sprite).blit(scene, (ox + view.length(4), oy + view.length(6)))
            sprite.blit(scene, (ox, oy))
        self._paint_tube(scene, board, view)
        return scene

    def _paint_board(self, scene: pygame.Surface, view: BoardView, setting: Setting) -> None:
        frame = view.frame
        face = view.face
        radius = FRAME + 6
        overlay = pygame.Surface(scene.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*SHADOW, 60), frame.move(6, 8), border_radius=radius)
        scene.blit(overlay, (0, 0))
        wood = setting.board_wood
        pygame.draw.rect(scene, INK, frame.inflate(4, 4), border_radius=radius + 2)
        pygame.draw.rect(scene, mix(wood, INK, 0.18), frame, border_radius=radius)
        top = pygame.Rect(frame.x, frame.y, frame.width, frame.height - FRAME // 2)
        pygame.draw.rect(scene, wood, top, border_radius=radius)
        pygame.draw.rect(scene, mix(wood, WHITE, 0.42), (frame.x + radius, frame.y + 3, frame.width // 3, 3), border_radius=2)
        pygame.draw.rect(scene, INK, face.inflate(4, 4), border_radius=8)
        pygame.draw.rect(scene, CREAM, face, border_radius=7)
        # Pegboard holes: a quiet grid that makes the board read as a toy.
        hole = mix(CREAM, (196, 160, 120), 0.32)
        step = 40.0
        r = max(1, view.length(2.6))
        y = step / 2
        while y < BOARD_HEIGHT:
            x = step / 2
            while x < BOARD_WIDTH:
                pygame.draw.circle(scene, hole, view.point(x, y), r)
                x += step
            y += step

    def _paint_tube(self, scene: pygame.Surface, board: Board, view: BoardView) -> None:
        sx, sy = board.start.x, board.start.y
        width = MARBLE_RADIUS + 7
        bottom = sy - MARBLE_RADIUS * 0.2
        tube = [Capsule((sx, -20.0), (sx, bottom), width, 0.0, "tube")]
        sprite = paint_planks(tube, TUBE_STYLE, view.scale, (0.0, 0.0), pegs=False)
        clip = scene.get_clip()
        scene.set_clip(view.face)
        sprite.blit(scene, view.point(0.0, 0.0))
        scene.set_clip(clip)
        # A darker mouth so the marble reads as waiting inside the tube.
        mouth = pygame.Rect(0, 0, view.length(width * 1.5), view.length(8))
        mouth.center = view.point(sx, bottom)
        pygame.draw.ellipse(scene, INK, mouth.inflate(4, 4))
        pygame.draw.ellipse(scene, mix(TUBE_STYLE.base, INK, 0.55), mouth)

    # -- sprites ---------------------------------------------------------------

    def sprites(self, view: BoardView) -> BoardSprites:
        cached = self._sprites
        if cached is not None and abs(cached.scale - view.scale) < 1e-6:
            return cached
        scale = view.scale
        ramps = {
            facing: paint_planks(piece_capsules(PieceKind.RAMP, facing, (0.0, 0.0), "x"), RAMP_STYLE, scale, (0.0, 0.0))
            for facing in Facing
        }
        funnel = paint_planks(
            piece_capsules(PieceKind.FUNNEL, Facing.RIGHT, (0.0, 0.0), "x"), FUNNEL_STYLE, scale, (0.0, 0.0)
        )
        bumper = self._bumper_sprite(scale)
        slot_size = (view.length(SLOT_WIDTH), view.length(SLOT_HEIGHT))
        slot = self.art.image("prop.blocks.rectangle", slot_size, variant="slot")
        self._sprites = BoardSprites(
            scale=scale,
            marble=self._marble_frames(scale),
            marble_shadow=self._marble_shadow(scale),
            trail=self._trail_dot(scale),
            ramp=ramps,
            ramp_ghost={facing: Sprite(_faded(sprite.surface, 130), sprite.anchor) for facing, sprite in ramps.items()},
            funnel=funnel,
            funnel_ghost=Sprite(_faded(funnel.surface, 130), funnel.anchor),
            bumper=bumper,
            bumper_ghost=Sprite(_faded(bumper.surface, 130), bumper.anchor) if bumper is not None else None,
            slot=_faded(slot, 235) if slot is not None else None,
            slot_shine=_shine(slot_size),
            slot_glow=_halo((slot_size[0] + view.length(36), slot_size[1] + view.length(36))),
            basket_back=self._basket(scale, front=False),
            basket_front=self._basket(scale, front=True),
            shadows={
                **{(PieceKind.RAMP, facing): _shadow(sprite) for facing, sprite in ramps.items()},
                (PieceKind.FUNNEL, Facing.RIGHT): _shadow(funnel),
                **({(PieceKind.BUMPER, Facing.RIGHT): _shadow(bumper)} if bumper is not None else {}),
            },
            shadow_offset=(view.length(4), view.length(6)),
        )
        return self._sprites

    def _bumper_sprite(self, scale: float) -> Sprite | None:
        width = max(4, int(round(BUMPER_RADIUS * 2 * scale)))
        height = max(4, int(round((BUMPER_HALF_HEIGHT + BUMPER_RADIUS) * 2 * scale)))
        source = self.art.image("prop.blocks.cylinder", 256, variant="coral")
        if source is None:
            capsules = piece_capsules(PieceKind.BUMPER, Facing.RIGHT, (0.0, 0.0), "x")
            return paint_planks(capsules, PlankStyle((244, 111, 97), (249, 167, 156), None), scale, (0.0, 0.0), pegs=False)
        crop = source.subsurface(source.get_bounding_rect()).copy()
        surface = pygame.transform.smoothscale(crop, (width, height))
        return Sprite(surface, (width // 2, height // 2))

    def _marble_frames(self, scale: float) -> tuple[pygame.Surface, ...]:
        r = MARBLE_RADIUS * scale * SS
        size = int(math.ceil(2 * r + 6 * SS))
        c = size / 2
        ink = max(2.0, 2.2 * SS)
        frames: list[pygame.Surface] = []
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(base, MARBLE_INK, (c, c), r + ink)
        pygame.draw.circle(base, MARBLE_BASE, (c, c), r)
        # Second fill stop: a lighter upper-left disc (flat, no gradient tools).
        pygame.draw.circle(base, MARBLE_LIGHT, (c - r * 0.18, c - r * 0.2), r * 0.74)
        for index in range(MARBLE_FRAMES):
            frame = base.copy()
            angle = index * (2 * math.pi / MARBLE_FRAMES)
            outer: list[tuple[float, float]] = []
            inner: list[tuple[float, float]] = []
            for step in range(9):
                t = angle + step * (math.radians(110) / 8)
                outer.append((c + math.cos(t) * r * 0.78, c + math.sin(t) * r * 0.78))
                inner.append((c + math.cos(t) * r * 0.54, c + math.sin(t) * r * 0.54))
            pygame.draw.polygon(frame, MARBLE_SWIRL, outer + inner[::-1])
            # The one highlight stays put (the light does not roll with the marble).
            hl = pygame.Rect(0, 0, r * 0.62, r * 0.42)
            hl.center = (round(c - r * 0.38), round(c - r * 0.46))
            pygame.draw.ellipse(frame, WHITE, hl)
            frames.append(pygame.transform.smoothscale(frame, (size // SS, size // SS)))
        return tuple(frames)

    @staticmethod
    def _marble_shadow(scale: float) -> pygame.Surface:
        w = max(4, int(MARBLE_RADIUS * 2.0 * scale))
        h = max(2, int(MARBLE_RADIUS * 0.5 * scale))
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (*SHADOW, 50), surface.get_rect())
        return surface

    @staticmethod
    def _trail_dot(scale: float) -> pygame.Surface:
        size = max(4, int(round(8 * scale)))
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*MARBLE_BASE, 120), (size / 2, size / 2), size / 2)
        return surface

    @staticmethod
    def _basket(scale: float, *, front: bool) -> Sprite:
        """Leaf-green basket (icon recipe); the front holds the rim band and lower body."""

        k = scale * SS
        half_top = BASKET_INNER / 2 + 14
        half_bottom = BASKET_INNER / 2 - 2
        depth = BASKET_DEPTH
        pad = 10
        width = int(math.ceil((half_top * 2 + 2 * pad) * k))
        height = int(math.ceil((depth + 2 * pad) * k))
        big = pygame.Surface((width, height), pygame.SRCALPHA)
        cx = width / 2
        top = pad * k
        bottom = (pad + depth) * k
        ink = 2.4 * SS
        body = [
            (cx - half_top * k, top + 6 * k),
            (cx + half_top * k, top + 6 * k),
            (cx + half_bottom * k, bottom),
            (cx - half_bottom * k, bottom),
        ]
        body_top = top + (22 * k if front else 6 * k)
        clip = pygame.Rect(0, int(body_top), width, height)
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(layer, BASKET_INK, body, width=0)
        inset = [
            (cx - (half_top - 3) * k, top + 8 * k),
            (cx + (half_top - 3) * k, top + 8 * k),
            (cx + (half_bottom - 2.5) * k, bottom - 3 * k),
            (cx - (half_bottom - 2.5) * k, bottom - 3 * k),
        ]
        pygame.draw.polygon(layer, BASKET_GREEN if front else mix(BASKET_GREEN, INK, 0.32), inset)
        if front:
            # Weave: one band and two staves (the icon's basket).
            band_y = top + depth * 0.62 * k
            pygame.draw.line(layer, BASKET_INK, (cx - half_top * 0.92 * k, band_y), (cx + half_top * 0.92 * k, band_y), max(2, int(ink * 0.8)))
            for sign in (-1, 1):
                pygame.draw.line(
                    layer,
                    BASKET_INK,
                    (cx + sign * half_top * 0.36 * k, top + 26 * k),
                    (cx + sign * half_bottom * 0.3 * k, bottom - 3 * k),
                    max(2, int(ink * 0.8)),
                )
        big.blit(layer, clip.topleft, clip)
        if front:
            rim = pygame.Rect(0, 0, int((half_top * 2 + 12) * k), int(13 * k))
            rim.center = (int(cx), int(top + 6 * k))
            pygame.draw.rect(big, BASKET_INK, rim.inflate(ink * 2, ink * 2), border_radius=rim.height)
            pygame.draw.rect(big, BASKET_RIM, rim, border_radius=rim.height)
            hl = pygame.Rect(rim.x + rim.height, rim.y + 2 * SS, rim.width // 3, max(2, rim.height // 4))
            pygame.draw.rect(big, mix(BASKET_RIM, WHITE, 0.6), hl, border_radius=hl.height)
        surface = pygame.transform.smoothscale(big, (max(1, width // SS), max(1, height // SS)))
        # Anchor: basket centre x at the floor line.
        return Sprite(surface, (surface.get_width() // 2, int(round((pad + depth) * scale))))

    # -- tray icons --------------------------------------------------------------

    def tray_icon(self, kind: PieceKind, facing: Facing, size: tuple[int, int], *, faded: bool) -> pygame.Surface:
        key = (kind, facing if kind is PieceKind.RAMP else Facing.RIGHT, size, faded)
        cached = self._icons.get(key)
        if cached is not None:
            return cached
        width, height = size
        capsules = piece_capsules(kind, facing, (0.0, 0.0), "x")
        reach = max(c.radius for c in capsules) + 3
        extent_w = max(max(c.a[0], c.b[0]) for c in capsules) - min(min(c.a[0], c.b[0]) for c in capsules) + 2 * reach
        extent_h = max(max(c.a[1], c.b[1]) for c in capsules) - min(min(c.a[1], c.b[1]) for c in capsules) + 2 * reach
        scale = min(width / extent_w, height / extent_h)
        if kind is PieceKind.BUMPER:
            sprite = self._bumper_sprite(scale)
        else:
            style = RAMP_STYLE if kind is PieceKind.RAMP else FUNNEL_STYLE
            sprite = paint_planks(capsules, style, scale, (0.0, 0.0))
        surface = sprite.surface if sprite is not None else pygame.Surface((1, 1), pygame.SRCALPHA)
        if faded:
            surface = _faded(surface, 80)
        if len(self._icons) > 24:
            self._icons.clear()
        self._icons[key] = surface
        return surface

    # -- fx ----------------------------------------------------------------------

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
        cached = self._icons.get(key)  # type: ignore[arg-type]
        if cached is None:
            cached = _halo(size)
            self._icons[key] = cached  # type: ignore[index]
        return cached


def setting_for(board_set_setting: str) -> Setting:
    return SETTINGS.get(board_set_setting, SETTINGS["garden"])


__all__ = [
    "BoardSprites",
    "MARBLE_FRAMES",
    "RunArt",
    "SETTINGS",
    "Setting",
    "Sprite",
    "paint_planks",
    "setting_for",
]
