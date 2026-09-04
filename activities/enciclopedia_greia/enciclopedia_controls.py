"""Standard navigation and view controls for Encyclopedia.

Owns the shared chrome that appears on every section/entry page:

- left/right navigation arrows
- discover (lens) button
- orbit speed slider (stepped)
- pause / labels / smoke / direction toggles

All helpers use direct primitives where possible and a tiny bounded cache
for halos so the Acer floor does not allocate a new SRCALPHA surface every
frame. Pulse is quantized to 4 buckets.
"""

from __future__ import annotations

from collections import OrderedDict
import math

import pygame

# ---------------------------------------------------------------------------
# Cache for control halos — tiny, bounded
# ---------------------------------------------------------------------------

_CONTROL_CACHE_MAX = 20
_control_cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
_control_cache_area = 0
_CONTROL_CACHE_MAX_AREA = 900_000


def _control_cache_get(key: tuple) -> pygame.Surface | None:
    surf = _control_cache.pop(key, None)
    if surf is not None:
        _control_cache[key] = surf
        return surf
    return None


def _control_cache_put(key: tuple, surf: pygame.Surface) -> None:
    global _control_cache_area
    area = surf.get_width() * surf.get_height()
    _control_cache[key] = surf
    _control_cache_area += area
    while len(_control_cache) > _CONTROL_CACHE_MAX or _control_cache_area > _CONTROL_CACHE_MAX_AREA:
        _k, old = _control_cache.popitem(last=False)
        _control_cache_area -= old.get_width() * old.get_height()
        if _control_cache_area < 0:
            _control_cache_area = 0


def clear_controls_cache() -> None:
    global _control_cache_area
    _control_cache.clear()
    _control_cache_area = 0


def _bucket(time: float, pulse: bool) -> int:
    if not pulse:
        return 0
    return int((math.sin(time * 2.0) * 0.5 + 0.5) * 3)  # 0..3


# ---------------------------------------------------------------------------
# Constants — single source for geometry, used by pages and tests
# ---------------------------------------------------------------------------

NAV_ARROW_SIZE = 68
NAV_ARROW_HIT_SIZE = 84
NAV_ARROW_Y = 340
NAV_ARROW_LEFT_CENTER = (56, NAV_ARROW_Y)
NAV_ARROW_RIGHT_CENTER = (968, NAV_ARROW_Y)
DISCOVER_CENTER = (512, 525)
DISCOVER_RADIUS = 34
DISCOVER_HIT_RADIUS = 44

ORBIT_SPEED_LABELS = ("slow", "medium", "fast")
ORBIT_SPEED_FACTORS = (0.42, 1.0, 1.85)
ORBIT_SPEED_HIT_SIZE = (48, 48)
ORBIT_SLIDER_TRACK = pygame.Rect(0, 0, 148, 14)
ORBIT_PAUSE_SIZE = 44
ORBIT_LABELS_TOGGLE_SIZE = 44


# ---------------------------------------------------------------------------
# Navigation arrows
# ---------------------------------------------------------------------------

def draw_navigation_arrows(
    surface: pygame.Surface,
    *,
    time: float = 0.0,
    can_go_left: bool,
    can_go_right: bool,
    left_center: tuple[int, int] = NAV_ARROW_LEFT_CENTER,
    right_center: tuple[int, int] = NAV_ARROW_RIGHT_CENTER,
) -> tuple[pygame.Rect, pygame.Rect]:
    """Draw large left/right chevrons and return hit rects. Direct draw, no per-frame halo surface."""

    def _one(center: tuple[int, int], enabled: bool, direction: int) -> pygame.Rect:
        cx, cy = center
        size = NAV_ARROW_SIZE
        hit = pygame.Rect(0, 0, NAV_ARROW_HIT_SIZE, NAV_ARROW_HIT_SIZE)
        hit.center = center
        bucket = _bucket(time, enabled)
        breathe_scale = 1.0 + (bucket / 3) * 0.04 if enabled else 1.0
        w = int(size * breathe_scale)
        h = int(size * breathe_scale)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = center
        backing = (255, 242, 200) if enabled else (235, 232, 222)
        edge = (104, 78, 57) if enabled else (150, 148, 155)
        pygame.draw.rect(surface, backing, rect, border_radius=18)
        pygame.draw.rect(surface, edge, rect, width=3, border_radius=18)
        if enabled:
            # Thin halo rect — direct, not a cached surface (4px stroke is cheap)
            halo_rect = rect.inflate(12, 12)
            pygame.draw.rect(
                surface,
                (255, 220, 95, 38 + bucket * 9),
                halo_rect,
                width=4,
                border_radius=20,
            )
        chev_color = (61, 44, 31) if enabled else (125, 120, 115)
        thickness = 5
        if direction < 0:
            p1 = (cx - 8, cy)
            p2 = (cx + 6, cy - 14)
            p3 = (cx + 6, cy + 14)
        else:
            p1 = (cx + 8, cy)
            p2 = (cx - 6, cy - 14)
            p3 = (cx - 6, cy + 14)
        pygame.draw.line(surface, chev_color, p1, p2, thickness)
        pygame.draw.line(surface, chev_color, p1, p3, thickness)
        if not enabled:
            # Dim overlay — direct translucent rect, no extra surface
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s, (255, 255, 255, 88), s.get_rect(), border_radius=18)
            surface.blit(s, rect.topleft)
        return hit

    left_hit = _one(left_center, can_go_left, -1)
    right_hit = _one(right_center, can_go_right, 1)
    return left_hit, right_hit


# ---------------------------------------------------------------------------
# Discover (lens)
# ---------------------------------------------------------------------------

def draw_discover_button(
    surface: pygame.Surface,
    center: tuple[int, int] = DISCOVER_CENTER,
    *,
    active: bool = True,
    time: float = 0.0,
    enabled: bool = True,
) -> pygame.Rect:
    """Large lens/magnifier button for 'discover more' and return its hit rect. Direct draw."""

    cx, cy = center
    bucket = _bucket(time * 0.95, enabled and active)
    base_r = DISCOVER_RADIUS + (bucket // 2 if enabled and active else 0)
    hit_r = DISCOVER_HIT_RADIUS
    hit = pygame.Rect(cx - hit_r, cy - hit_r, hit_r * 2, hit_r * 2)

    if active and enabled:
        pygame.draw.circle(
            surface,
            (255, 220, 95, 42 + bucket * 9),
            (cx, cy),
            base_r + 11,
            width=5,
        )

    # Shadow as direct ellipse (no extra surface)
    pygame.draw.circle(surface, (40, 28, 20, 46), (cx + 2, cy + 4), base_r)

    fill = (255, 248, 232) if enabled else (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.circle(surface, fill, center, base_r)
    pygame.draw.circle(surface, edge, center, base_r, 4)
    pygame.draw.circle(surface, edge, center, base_r - 8, 2)
    pygame.draw.arc(
        surface,
        (255, 255, 250),
        pygame.Rect(cx - base_r + 7, cy - base_r + 7, (base_r - 7) * 2, (base_r - 7) * 2),
        0.6,
        2.5,
        3,
    )
    if active and enabled and bucket == 3:
        pygame.draw.circle(surface, (255, 236, 150), (cx + 8, cy - 8), 3)
    handle_start = (cx + int(base_r * 0.62), cy + int(base_r * 0.62))
    handle_end = (cx + int(base_r * 0.98), cy + int(base_r * 0.98))
    pygame.draw.line(surface, edge, handle_start, handle_end, 6)
    pygame.draw.circle(surface, edge, handle_end, 4)

    if not enabled:
        s = pygame.Surface((base_r * 2, base_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 92), (base_r, base_r), base_r)
        surface.blit(s, (cx - base_r, cy - base_r))

    return hit


# ---------------------------------------------------------------------------
# Orbit speed slider (stepped 3)
# ---------------------------------------------------------------------------

def draw_speed_slider(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    level: int = 1,
    paused: bool = False,
) -> tuple[pygame.Rect, tuple[pygame.Rect, pygame.Rect, pygame.Rect]]:
    """Small three-step orbit speed slider. Returns (track_rect, notch_hits). Direct draw."""

    cx, cy = center
    track = ORBIT_SLIDER_TRACK.copy()
    track.center = center
    pygame.draw.rect(surface, (248, 244, 222), track, border_radius=7)
    pygame.draw.rect(surface, (92, 82, 72), track, width=2, border_radius=7)
    notch_hits: list[pygame.Rect] = []
    for idx in range(3):
        nx = track.x + 14 + idx * (track.width - 28) // 2
        ny = track.centery
        hit = pygame.Rect(0, 0, ORBIT_SPEED_HIT_SIZE[0], ORBIT_SPEED_HIT_SIZE[1])
        hit.center = (nx, ny)
        notch_hits.append(hit)
        dot_color = (104, 78, 57) if not paused else (155, 150, 145)
        pygame.draw.circle(surface, dot_color, (nx, ny), 5)
        pygame.draw.circle(surface, (255, 250, 235), (nx, ny), 2)
        if idx == level and not paused:
            bucket = _bucket(time * 1.2, True)
            pygame.draw.circle(
                surface, (255, 214, 74), (nx, ny), 10 + bucket, width=3
            )
    if not paused:
        knob_x = track.x + 14 + level * (track.width - 28) // 2
        knob = pygame.Rect(0, 0, 22, 22)
        knob.center = (knob_x, track.centery)
        pygame.draw.circle(surface, (255, 242, 200), knob.center, 11)
        pygame.draw.circle(surface, (104, 78, 57), knob.center, 11, 3)
        pygame.draw.circle(surface, (104, 78, 57), knob.center, 4)
    else:
        s = pygame.Surface(track.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 255, 78), s.get_rect(), border_radius=7)
        surface.blit(s, track.topleft)

    return track, tuple(notch_hits)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------

def draw_pause_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    paused: bool = False,
) -> pygame.Rect:
    """Large pause/resume toggle. Returns hit rect. Direct draw."""

    cx, cy = center
    size = ORBIT_PAUSE_SIZE
    hit = pygame.Rect(0, 0, 56, 56)
    hit.center = center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    bucket = _bucket(time * 0.85, not paused)
    if not paused:
        pygame.draw.rect(
            surface,
            (255, 220, 95, 28 + bucket * 7),
            rect.inflate(14, 14),
            width=3,
            border_radius=12,
        )
    fill = (255, 242, 200) if not paused else (232, 236, 242)
    edge = (104, 78, 57) if not paused else (92, 98, 115)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    if paused:
        pts = [(cx - 6, cy - 10), (cx - 6, cy + 10), (cx + 8, cy)]
        pygame.draw.polygon(surface, edge, pts)
    else:
        pygame.draw.rect(surface, edge, pygame.Rect(cx - 9, cy - 10, 6, 20), border_radius=2)
        pygame.draw.rect(surface, edge, pygame.Rect(cx + 3, cy - 10, 6, 20), border_radius=2)
    return hit


def draw_labels_toggle(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
) -> pygame.Rect:
    """Toggle for orbit/plaque labels. Returns hit rect."""

    cx, cy = center
    size = ORBIT_LABELS_TOGGLE_SIZE
    hit = pygame.Rect(0, 0, 56, 56)
    hit.center = center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    bucket = _bucket(time * 0.95, enabled)
    if enabled:
        pygame.draw.rect(
            surface,
            (255, 220, 95, 22 + bucket * 6),
            rect.inflate(14, 14),
            width=3,
            border_radius=12,
        )
    fill = (255, 248, 232) if enabled else (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    line_color = (61, 44, 31) if enabled else (125, 120, 115)
    for ly in (cy - 6, cy + 2):
        pygame.draw.line(surface, line_color, (cx - 10, ly), (cx + 6, ly), 3)
    pygame.draw.circle(surface, line_color, (cx + 10, cy + 10), 3, 2)
    pygame.draw.circle(surface, line_color, (cx + 10, cy + 10), 1)
    if not enabled:
        pygame.draw.line(surface, (170, 80, 80), (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
    return hit


def draw_smoke_toggle(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
) -> pygame.Rect:
    """Toggle for volcano smoke — cloud icon."""

    cx, cy = center
    size = 44
    hit = pygame.Rect(0, 0, 56, 56)
    hit.center = center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    bucket = _bucket(time * 0.9, enabled)
    if enabled:
        pygame.draw.rect(
            surface,
            (255, 220, 95, 22 + bucket * 6),
            rect.inflate(14, 14),
            width=3,
            border_radius=12,
        )
    fill = (255, 248, 232) if enabled else (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    cloud = (61, 44, 31) if enabled else (125, 120, 115)
    pygame.draw.circle(surface, cloud, (cx - 6, cy + 4), 7)
    pygame.draw.circle(surface, cloud, (cx + 2, cy - 3), 8)
    pygame.draw.circle(surface, cloud, (cx + 8, cy + 4), 6)
    pygame.draw.ellipse(surface, fill, (cx - 10, cy + 6, 20, 6))
    if not enabled:
        pygame.draw.line(surface, (170, 80, 80), (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
    return hit


def draw_direction_toggle(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    direction: float = 1.0,
) -> pygame.Rect:
    """Toggle for gear direction — circular arrow."""

    cx, cy = center
    size = 44
    hit = pygame.Rect(0, 0, 56, 56)
    hit.center = center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    bucket = _bucket(time * 0.9, True)
    pygame.draw.rect(
        surface,
        (255, 220, 95, 22 + bucket * 6),
        rect.inflate(14, 14),
        width=3,
        border_radius=12,
    )
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    col = (61, 44, 31)
    if direction > 0:
        pygame.draw.arc(surface, col, (cx - 14, cy - 12, 28, 24), math.radians(20), math.radians(320), 3)
        pts = [(cx + 10, cy - 10), (cx + 10, cy - 2), (cx + 16, cy - 6)]
        pygame.draw.polygon(surface, col, pts)
    else:
        pygame.draw.arc(surface, col, (cx - 14, cy - 12, 28, 24), math.radians(40), math.radians(340), 3)
        pts = [(cx - 10, cy - 10), (cx - 10, cy - 2), (cx - 16, cy - 6)]
        pygame.draw.polygon(surface, col, pts)
    return hit
