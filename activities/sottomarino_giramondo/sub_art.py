"""Sottomarino Giramondo — bounded art owner.

The brass porthole, riveted bulkhead and cockpit instruments are the
Activity's own fantasy and stay hand-built (baked once). Creatures come from
the shared Greia library (``creature.marine.*``) resolved semantically; the
coral clump, kelp stalk, krill swarm, bubble and the octopus hugging the glass
are Activity-private renditions under ``assets/runtime`` (SVG sources beside
them). One owner decodes, crops and scales; drawing only blits.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
import math
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Viewport Porthole Geometry (Centered in the upper cockpit area)
PORTHOLE_CENTER_X = 512
PORTHOLE_CENTER_Y = 218
PORTHOLE_RADIUS = 175

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "runtime"
# Colour key for the porthole hole in the baked opaque cockpit layer.
HOLE_KEY = (255, 0, 255)

VisualResolver = Callable[[str, str], Path]

# kind -> ("shared", asset id, variant) | ("private", stem, "")
CREATURE_ART: Dict[str, Tuple[str, str, str]] = {
    "clownfish": ("shared", "creature.marine.clownfish", "default"),
    "turtle": ("shared", "creature.marine.turtle", "default"),
    "dolphin": ("shared", "creature.marine.dolphin", "default"),
    "manta": ("shared", "creature.marine.manta", "default"),
    "angler": ("shared", "creature.marine.anglerfish", "default"),
    "whale": ("shared", "creature.marine.whale", "default"),
    "shark": ("shared", "creature.marine.shark", "happy"),
    "octopus": ("private", "octopus_hug", ""),
    "coral": ("private", "coral", ""),
    "kelp": ("private", "kelp", ""),
    "krill": ("private", "krill", ""),
    "bubble": ("private", "bubble", ""),
}

# Largest dimension (px at distance z = 1, size 1.0) of each kind: the
# original cockpit's sprite scale, so creatures keep their familiar sizes.
KIND_UNIT_PX: Dict[str, float] = {
    "clownfish": 36.0,
    "turtle": 49.5,
    "dolphin": 67.5,
    "manta": 72.0,
    "angler": 45.0,
    "whale": 99.0,
    "coral": 81.0,
    "kelp": 117.0,
    "krill": 67.5,
    "bubble": 13.5,
}
# Nothing outgrows the glass as it passes close (the old sprites ballooned
# into blurry blocks that hid the view).
MAX_SPRITE_PX = 270
MIN_SPRITE_PX = 8
# Perspective sizes are quantized geometrically so a session touches a small,
# bounded set of scaled surfaces.
_SIZE_STEP = 1.08
_MAX_SCALED = 192

# Ocean colours per zone (top, bottom), as the original cockpit.
_ZONE_COLOURS = {
    "shallow": ((25, 140, 190), (15, 80, 130)),
    "twilight": ((15, 60, 110), (8, 30, 70)),
    "abyss": ((8, 15, 45), (3, 6, 20)),
}
_LIGHT_BOOST = ((45, 55, 40), (35, 45, 35))

# Instrument colours (cockpit buttons and their picture badges).
INSTRUMENT_COLOURS: Dict[str, Tuple[int, int, int]] = {
    "light": (245, 210, 60),
    "sonar": (80, 190, 225),
    "bubbles": (100, 220, 160),
    "horn": (240, 120, 70),
    "steer_left": (60, 150, 220),
    "steer_right": (60, 150, 220),
    "ahead": (65, 185, 120),
    "stop": (220, 80, 80),
    "surface": (120, 200, 235),
    "dive": (70, 120, 205),
    "action": (220, 50, 50),
}
ICON_INK = (20, 24, 32)


def _default_resolver(asset_id: str, variant: str) -> Path:
    from greia_platform.activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


def _convert(image: pygame.Surface, *, alpha: bool = True) -> pygame.Surface:
    """Convert once to the display format when a display exists."""

    if pygame.display.get_surface() is not None:
        try:
            return image.convert_alpha() if alpha else image.convert()
        except pygame.error:
            return image
    return image


def _create_cockpit_bulkhead(width: int, height: int) -> pygame.Surface:
    """Bake the opaque steel bulkhead and brass porthole rim (hole = colour key)."""

    mask = pygame.Surface((width, height))
    mask.fill((40, 52, 66))

    # Bulkhead plate seams & structural rivets on the sides
    for sx in (240, 784):
        pygame.draw.line(mask, (25, 33, 42), (sx, 0), (sx, 435), 3)
        pygame.draw.line(mask, (65, 82, 102), (sx + 2, 0), (sx + 2, 435), 1)
        for ry in range(40, 420, 50):
            for ox in (-15, 15):
                pygame.draw.circle(mask, (25, 33, 42), (sx + ox, ry + 2), 5)
                pygame.draw.circle(mask, (75, 96, 120), (sx + ox, ry), 5)
                pygame.draw.circle(mask, (130, 160, 195), (sx + ox - 1, ry - 1), 2)

    pygame.draw.circle(mask, HOLE_KEY, (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), PORTHOLE_RADIUS)

    rim_outer = PORTHOLE_RADIUS + 26
    rim_inner = PORTHOLE_RADIUS - 4
    centre = (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y)
    pygame.draw.circle(mask, (125, 85, 20), centre, rim_outer + 2, 28)
    pygame.draw.circle(mask, (218, 168, 52), centre, rim_outer, 24)
    pygame.draw.circle(mask, (140, 95, 22), centre, rim_outer + 1, 3)
    pygame.draw.circle(mask, (255, 225, 110), centre, rim_inner + 2, 3)

    for i in range(16):
        angle = i * (math.pi * 2 / 16)
        rx = PORTHOLE_CENTER_X + int((PORTHOLE_RADIUS + 13) * math.cos(angle))
        ry = PORTHOLE_CENTER_Y + int((PORTHOLE_RADIUS + 13) * math.sin(angle))
        pygame.draw.circle(mask, (90, 60, 15), (rx, ry + 1), 7)
        pygame.draw.circle(mask, (235, 190, 75), (rx, ry), 6)
        pygame.draw.circle(mask, (255, 250, 210), (rx - 2, ry - 2), 2)
    mask.set_colorkey(HOLE_KEY)
    return mask


def _create_glass_sheen() -> pygame.Surface:
    """Soft reflection arcs across the top-left of the glass (porthole-sized)."""

    size = PORTHOLE_RADIUS * 2
    sheen = pygame.Surface((size, size), pygame.SRCALPHA)
    r = PORTHOLE_RADIUS
    pygame.draw.arc(sheen, (255, 255, 255, 70), (12, 12, (r - 12) * 2, (r - 12) * 2),
                    math.radians(105), math.radians(165), 18)
    pygame.draw.arc(sheen, (255, 255, 255, 40), (25, 25, (r - 25) * 2, (r - 25) * 2),
                    math.radians(115), math.radians(155), 8)
    return sheen


def draw_instrument_icon(
    surface: pygame.Surface,
    icon_type: str,
    cx: int,
    cy: int,
    color: Tuple[int, int, int] = ICON_INK,
) -> None:
    """Bold vector symbols for the cockpit instruments (pre-reader legible)."""

    if icon_type == "light":
        pygame.draw.circle(surface, color, (cx, cy - 4), 13)
        pygame.draw.polygon(surface, color, [(cx - 10, cy), (cx + 10, cy), (cx + 6, cy + 12), (cx - 6, cy + 12)])
        pygame.draw.rect(surface, (100, 100, 100), (cx - 5, cy + 13, 10, 4), border_radius=2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 4, cy - 7), 3)
        for p1, p2 in (
            ((cx, cy - 20), (cx, cy - 26)),
            ((cx - 14, cy - 14), (cx - 20, cy - 19)),
            ((cx + 14, cy - 14), (cx + 20, cy - 19)),
            ((cx - 17, cy - 3), (cx - 23, cy - 3)),
            ((cx + 17, cy - 3), (cx + 23, cy - 3)),
        ):
            pygame.draw.line(surface, color, p1, p2, 3)
    elif icon_type == "sonar":
        pygame.draw.circle(surface, color, (cx, cy + 6), 5)
        pygame.draw.arc(surface, color, (cx - 13, cy - 7, 26, 26), 0.5, 2.64, 3)
        pygame.draw.arc(surface, color, (cx - 22, cy - 16, 44, 44), 0.5, 2.64, 3)
        pygame.draw.line(surface, color, (cx, cy + 6), (cx, cy + 18), 3)
        pygame.draw.line(surface, color, (cx - 9, cy + 18), (cx + 9, cy + 18), 3)
    elif icon_type == "bubbles":
        pygame.draw.circle(surface, color, (cx - 9, cy + 5), 11, 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 6, cy + 2), 3)
        pygame.draw.circle(surface, color, (cx + 9, cy - 5), 8, 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx + 11, cy - 7), 2)
        pygame.draw.circle(surface, color, (cx - 2, cy - 14), 5, 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 1, cy - 15), 1)
    elif icon_type == "horn":
        pygame.draw.rect(surface, color, (cx - 19, cy - 6, 9, 12), border_radius=2)
        pygame.draw.polygon(surface, color, [(cx - 10, cy - 6), (cx + 4, cy - 14), (cx + 4, cy + 14), (cx - 10, cy + 6)])
        pygame.draw.arc(surface, color, (cx + 3, cy - 9, 12, 18), -1.1, 1.1, 3)
        pygame.draw.arc(surface, color, (cx + 9, cy - 15, 18, 30), -1.1, 1.1, 3)
    elif icon_type == "steer_left":
        pygame.draw.polygon(surface, color, [
            (cx - 13, cy), (cx + 3, cy - 11), (cx + 3, cy - 4),
            (cx + 12, cy - 4), (cx + 12, cy + 4), (cx + 3, cy + 4), (cx + 3, cy + 11)])
    elif icon_type == "steer_right":
        pygame.draw.polygon(surface, color, [
            (cx + 13, cy), (cx - 3, cy - 11), (cx - 3, cy - 4),
            (cx - 12, cy - 4), (cx - 12, cy + 4), (cx - 3, cy + 4), (cx - 3, cy + 11)])
    elif icon_type == "ahead":
        pygame.draw.polygon(surface, color, [
            (cx, cy - 12), (cx + 11, cy + 3), (cx + 4, cy + 3),
            (cx + 4, cy + 11), (cx - 4, cy + 11), (cx - 4, cy + 3), (cx - 11, cy + 3)])
    elif icon_type == "dive":
        pygame.draw.polygon(surface, color, [
            (cx, cy + 12), (cx + 11, cy - 3), (cx + 4, cy - 3),
            (cx + 4, cy - 11), (cx - 4, cy - 11), (cx - 4, cy - 3), (cx - 11, cy - 3)])
    elif icon_type == "surface":
        pygame.draw.polygon(surface, color, [
            (cx, cy - 12), (cx + 11, cy + 1), (cx + 4, cy + 1),
            (cx + 4, cy + 7), (cx - 4, cy + 7), (cx - 4, cy + 1), (cx - 11, cy + 1)])
        pygame.draw.line(surface, color, (cx - 11, cy + 11), (cx + 11, cy + 11), 3)
    elif icon_type == "stop":
        pygame.draw.rect(surface, color, (cx - 9, cy - 9, 18, 18), border_radius=3)
    elif icon_type == "action":
        # The red alarm beacon dome.
        pygame.draw.circle(surface, (150, 25, 25), (cx, cy), 17)
        pygame.draw.circle(surface, (235, 60, 50), (cx, cy), 14)
        pygame.draw.line(surface, (255, 220, 220), (cx, cy - 12), (cx, cy + 12), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 5, cy - 5), 3)


class SubmarineArt:
    """Owner of every decoded/scaled surface the cockpit draws.

    Fixed working set: the baked bulkhead, glass sheen, six zone backdrops,
    one source per creature kind and a few badges/FX. Perspective sprites
    live in a hard-capped LRU (``_MAX_SCALED``). Missing art degrades to
    ``None``; the presenter then simply skips that sprite.
    """

    def __init__(self, resolver: VisualResolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else _default_resolver
        self.bulkhead = _convert(_create_cockpit_bulkhead(REFERENCE_WIDTH, REFERENCE_HEIGHT), alpha=False)
        self.bulkhead.set_colorkey(HOLE_KEY)
        self.glass_sheen = _convert(_create_glass_sheen())
        self._sources: Dict[str, Optional[pygame.Surface]] = {}
        self._scaled: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._backdrops: Dict[Tuple[str, bool], pygame.Surface] = {}
        self._badges: Dict[Tuple[str, int], pygame.Surface] = {}
        self._fx: Dict[str, list[pygame.Surface]] = {}
        for kind in CREATURE_ART:
            self._sources[kind] = self._load(kind)

    # -- decoding -----------------------------------------------------------

    def _load(self, kind: str) -> Optional[pygame.Surface]:
        source, ref, variant = CREATURE_ART[kind]
        try:
            path = ASSETS_DIR / f"{ref}.png" if source == "private" else Path(self._resolver(ref, variant))
            image = pygame.image.load(str(path))
        except Exception:
            return None
        image = _convert(image)
        bounds = image.get_bounding_rect(min_alpha=8)
        if bounds.width <= 0 or bounds.height <= 0:
            return None
        return image.subsurface(bounds).copy()

    def get_sprite(self, name: str) -> Optional[pygame.Surface]:
        """Return the cropped full-resolution source for ``name``."""

        return self._sources.get(name)

    # -- perspective sprites ------------------------------------------------

    def unit_size(self, kind: str, size_base: float, scale: float) -> int:
        """Largest dimension in px for a creature at perspective ``scale``."""

        return int(min(MAX_SPRITE_PX, max(MIN_SPRITE_PX, KIND_UNIT_PX.get(kind, 40.0) * size_base * scale)))

    def scaled(self, kind: str, longest: int, *, flip: bool = False) -> Optional[pygame.Surface]:
        """Return ``kind`` scaled so its longest side ≈ ``longest`` px (cached)."""

        source = self._sources.get(kind)
        if source is None:
            return None
        bucket = int(round(math.log(max(MIN_SPRITE_PX, longest)) / math.log(_SIZE_STEP)))
        key = (kind, bucket, flip)
        cached = self._scaled.get(key)
        if cached is not None:
            self._scaled.move_to_end(key)
            return cached
        target = _SIZE_STEP ** bucket
        w, h = source.get_size()
        factor = target / max(w, h)
        size = (max(2, int(round(w * factor))), max(2, int(round(h * factor))))
        image = pygame.transform.smoothscale(source, size)
        if flip:
            image = pygame.transform.flip(image, True, False)
        self._scaled[key] = image
        while len(self._scaled) > _MAX_SCALED:
            self._scaled.popitem(last=False)
        return image

    @property
    def scaled_count(self) -> int:
        return len(self._scaled)

    def encounter_sprite(self, kind: str, longest: int) -> Optional[pygame.Surface]:
        return self.scaled(kind, longest)

    # -- backdrops ----------------------------------------------------------

    def backdrop(self, zone: str, lights_on: bool) -> pygame.Surface:
        """Porthole-sized ocean backdrop for a zone (baked once per state)."""

        key = (zone, bool(lights_on))
        cached = self._backdrops.get(key)
        if cached is not None:
            return cached
        top, bottom = _ZONE_COLOURS.get(zone, _ZONE_COLOURS["shallow"])
        if lights_on:
            top = tuple(min(255, c + d) for c, d in zip(top, _LIGHT_BOOST[0]))
            bottom = tuple(min(255, c + d) for c, d in zip(bottom, _LIGHT_BOOST[1]))
        # The original water colour fills the glass; it deepens only gently
        # toward the bottom so the zone's mood is unchanged.
        bottom = tuple(int(t * 0.72 + b * 0.28) for t, b in zip(top, bottom))
        size = PORTHOLE_RADIUS * 2
        surface = pygame.Surface((size, size))
        for y in range(size):
            t = y / (size - 1)
            colour = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
            pygame.draw.line(surface, colour, (0, y), (size, y))
        if zone == "shallow" and not lights_on:
            rays = pygame.Surface((size, size), pygame.SRCALPHA)
            for ray in range(4):
                rx = PORTHOLE_RADIUS - 100 + ray * 70
                pygame.draw.polygon(rays, (255, 255, 220, 25),
                                    [(rx + 10, 0), (rx + 30, 0), (rx + 40, size), (rx, size)])
            surface.blit(rays, (0, 0))
        elif lights_on:
            # The floodlight's soft cone from the bottom of the glass.
            cone = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.polygon(cone, (255, 240, 170, 26),
                                [(size // 2 - 40, size), (size // 2 + 40, size), (size - 10, 0), (10, 0)])
            surface.blit(cone, (0, 0))
        surface = _convert(surface, alpha=False)
        self._backdrops[key] = surface
        return surface

    # -- badges and pictures --------------------------------------------------

    def instrument_badge(self, instrument: str, size: int) -> pygame.Surface:
        """A small rounded badge in the instrument's colour with its symbol."""

        key = (instrument, int(size))
        cached = self._badges.get(key)
        if cached is not None:
            return cached
        base = 64
        badge = pygame.Surface((base, base), pygame.SRCALPHA)
        colour = INSTRUMENT_COLOURS.get(instrument, (200, 200, 200))
        pygame.draw.rect(badge, (75, 55, 47), (0, 0, base, base), border_radius=16)
        pygame.draw.rect(badge, colour, (3, 3, base - 6, base - 6), border_radius=13)
        draw_instrument_icon(badge, instrument, base // 2, base // 2 + 2)
        if size != base:
            badge = pygame.transform.smoothscale(badge, (int(size), int(size)))
        self._badges[key] = badge
        return badge

    def picture(self, kind: str, size: int) -> Optional[pygame.Surface]:
        """A creature thumbnail fitting a ``size`` square (cached via LRU)."""

        return self.scaled(kind, size)

    def picture_row(self, parts: list[pygame.Surface], gap: int = 6) -> Optional[pygame.Surface]:
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        width = sum(p.get_width() for p in parts) + gap * (len(parts) - 1)
        height = max(p.get_height() for p in parts)
        row = pygame.Surface((width, height), pygame.SRCALPHA)
        x = 0
        for part in parts:
            row.blit(part, (x, (height - part.get_height()) // 2))
            x += part.get_width() + gap
        return row

    # -- effects ---------------------------------------------------------------

    def fx_frames(self, fx_id: str, size: int) -> list[pygame.Surface]:
        """Shared ``fx.<id>`` frames (default, frame_2, frame_3) at ``size``."""

        key = f"{fx_id}@{size}"
        cached = self._fx.get(key)
        if cached is not None:
            return cached
        frames: list[pygame.Surface] = []
        for variant in ("default", "frame_2", "frame_3"):
            try:
                image = pygame.image.load(str(self._resolver(f"fx.{fx_id}", variant)))
            except Exception:
                continue
            frames.append(pygame.transform.smoothscale(_convert(image), (size, size)))
        self._fx[key] = frames
        return frames
