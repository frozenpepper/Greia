"""Focus rendering for Encyclopedia — explicit shape contract, bounded cache.

This module owns the focus halo contract that `faa46ec4` left generic.

- `FocusShape` makes shape intent explicit; pages must choose, not receive an
  arbitrary ellipse because a hotspot happens to be a Rect.
- `FocusSpec` carries the chosen shape + geometry.
- `FocusRenderer` owns a small bounded cache of pre-rendered halo surfaces so
  shared chrome does not allocate a new SRCALPHA surface every frame.

The public helpers `draw_focus_patch` and `draw_portal_focus` preserve the
previous call sites but now honor `FocusSpec` and use direct primitives or
cached surfaces instead of per-frame allocations.

Visual rule (review §1):
- circular planets -> FocusShape.CIRCLE
- Home portals / rectangular exhibits / cards -> FocusShape.ROUNDED_RECT
- irregular artwork -> caller supplies fitted bounds as rounded_rect
- never an ellipse simply because the hotspot is a Rect
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import math
from enum import StrEnum

import pygame


class FocusShape(StrEnum):
    CIRCLE = "circle"
    ROUNDED_RECT = "rounded_rect"


@dataclass(frozen=True, slots=True)
class FocusSpec:
    shape: FocusShape
    rect: pygame.Rect
    radius: int = 16
    time: float = 0.0
    pulse: bool = True


# Tuned to the Acer floor: small cache, quantized pulse, bounded area.
_FOCUS_CACHE_MAX_ENTRIES = 24
_FOCUS_CACHE_MAX_AREA = 1_200_000  # ~ a few 200x200 halos


class _BoundedSurfaceCache:
    def __init__(self, max_entries: int = _FOCUS_CACHE_MAX_ENTRIES, max_area: int = _FOCUS_CACHE_MAX_AREA) -> None:
        self._entries: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._area = 0
        self._max_entries = max_entries
        self._max_area = max_area
        self.hits = 0
        self.misses = 0

    def get(self, key: tuple) -> pygame.Surface | None:
        surf = self._entries.pop(key, None)
        if surf is not None:
            self._entries[key] = surf
            self.hits += 1
            return surf
        self.misses += 1
        return None

    def put(self, key: tuple, surf: pygame.Surface) -> None:
        area = surf.get_width() * surf.get_height()
        self._entries[key] = surf
        self._area += area
        # Evict oldest until under bounds
        while len(self._entries) > self._max_entries or self._area > self._max_area:
            _k, old = self._entries.popitem(last=False)
            self._area -= old.get_width() * old.get_height()
            if self._area < 0:
                self._area = 0

    def clear(self) -> None:
        self._entries.clear()
        self._area = 0


_focus_cache = _BoundedSurfaceCache()


def _quantize_pulse(time: float, pulse: bool) -> int:
    if not pulse:
        return 0
    # 4 buckets is enough for breathe to read, small cache
    breathe = math.sin(time * 2.2) * 0.5 + 0.5
    return int(breathe * 3)  # 0..3


def _outer_alpha_for_bucket(bucket: int, pulse: bool) -> int:
    if not pulse:
        return 92
    # maps 0..3 -> 78, 88, 98, 106 approx
    return 78 + bucket * 10 if bucket < 3 else 106


def _inner_alpha_for_bucket(bucket: int, pulse: bool) -> int:
    if not pulse:
        return 215
    return 195 + bucket * 8


def _pad_for_bucket(bucket: int, pulse: bool) -> int:
    return 16 + bucket if pulse else 16


def clear_focus_cache() -> None:
    _focus_cache.clear()


def get_focus_cache_stats() -> tuple[int, int, int]:
    return (len(_focus_cache._entries), _focus_cache._area, _focus_cache.hits + _focus_cache.misses)


# ---------------------------------------------------------------------------
# Public: portal focus (Home) — fitted rounded rect, not ellipse
# ---------------------------------------------------------------------------

def draw_portal_focus(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool,
    time: float = 0.0,
) -> None:
    """Home-portal selected state: glow + subtle lift/pulse + sparkle.

    Uses a fitted rounded_rect, not an ellipse, because portals are
    rectangular exhibits. Keeps the glow portable over the authored book.
    """

    if not active:
        return
    bucket = _quantize_pulse(time * 0.82, True)  # slightly slower breathe for portal
    # Direct draw where possible; halo is a single rect outline, not a full
    # per-frame surface. Only the outer glow uses a cached halo.
    pad = 18 + bucket
    # Cache key for outer glow
    key = ("portal", rect.width, rect.height, bucket)
    glow = _focus_cache.get(key)
    if glow is None:
        glow = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
        shadow_rect = pygame.Rect(pad - 2, pad + 6, rect.width, rect.height)
        pygame.draw.rect(glow, (40, 28, 20, 42), shadow_rect, border_radius=22)
        outer = pygame.Rect(pad, pad, rect.width, rect.height)
        inner = outer.inflate(-10, -10)
        pygame.draw.rect(
            glow,
            (255, 220, 95, 96 + bucket * 12),
            outer.inflate(6, 6),
            width=6,
            border_radius=24,
        )
        pygame.draw.rect(
            glow,
            (255, 245, 188, 180 + bucket * 13),
            inner,
            width=2,
            border_radius=18,
        )
        _focus_cache.put(key, glow)
    surface.blit(glow, (rect.x - pad, rect.y - pad))
    # Tiny sparkle on peak — direct draw, no surface
    if bucket == 3:
        sx, sy = rect.right - 14, rect.top + 12
        pygame.draw.circle(surface, (255, 250, 215), (sx, sy), 3)
        pygame.draw.circle(surface, (255, 236, 150), (sx + 8, sy + 6), 2)


# ---------------------------------------------------------------------------
# Public: generic focus patch — explicit shape contract
# ---------------------------------------------------------------------------

def draw_focus_patch(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool,
    radius: int = 22,
    time: float = 0.0,
    pulse: bool = True,
    shape: FocusShape | str = FocusShape.ROUNDED_RECT,
) -> None:
    """Lift an authored object with a non-occluding scene halo.

    The focus treatment must not repaint the exhibit inside a translucent UI
    card. Only the perimeter is drawn, so the authored subject keeps its own
    color, texture and depth while still receiving an obvious child-sized
    selection cue.

    Shape contract:
    - FocusShape.CIRCLE for truly circular targets (planets, sun, moon)
    - FocusShape.ROUNDED_RECT for portals, cards, rectangular exhibits
    - Caller supplies fitted rect; this helper will not invent an ellipse
      simply because a hotspot is a Rect.
    """

    if not active:
        return

    # Normalize shape
    if isinstance(shape, str):
        try:
            shape = FocusShape(shape)
        except ValueError:
            shape = FocusShape.ROUNDED_RECT

    bucket = _quantize_pulse(time, pulse)
    pad = _pad_for_bucket(bucket, pulse)

    if shape is FocusShape.CIRCLE:
        # Circular halo — draw two stroked circles directly, no per-frame surface.
        # Use quantized alpha for breathe without surface churn.
        outer_alpha = _outer_alpha_for_bucket(bucket, pulse)
        inner_alpha = _inner_alpha_for_bucket(bucket, pulse)
        # Compute fitted circle from rect (use smallest side)
        cx, cy = rect.center
        r = min(rect.width, rect.height) // 2 + pad - 4
        outer_width = max(5, min(9, radius // 3))
        # Direct circles
        pygame.draw.circle(surface, (255, 216, 83, outer_alpha), (cx, cy), r, width=outer_width)
        pygame.draw.circle(surface, (255, 240, 176, inner_alpha), (cx, cy), r - 6, width=3)
        return

    # Rounded-rect halo — use cached glow surface for the two rect outlines.
    # Key includes rect size + bucket + radius bucket
    key = ("rounded_rect", rect.width, rect.height, radius, bucket)
    glow = _focus_cache.get(key)
    if glow is None:
        glow = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
        outer = glow.get_rect().inflate(-4, -4)
        inner = outer.inflate(-12, -12)
        outer_width = max(5, min(9, radius // 3))
        pygame.draw.rect(
            glow,
            (255, 216, 83, _outer_alpha_for_bucket(bucket, pulse)),
            outer,
            width=outer_width,
            border_radius=radius,
        )
        pygame.draw.rect(
            glow,
            (255, 240, 176, _inner_alpha_for_bucket(bucket, pulse)),
            inner,
            width=3,
            border_radius=max(8, radius - 4),
        )
        _focus_cache.put(key, glow)
    surface.blit(glow, (rect.x - pad, rect.y - pad))
