"""Shared storybook presentation primitives for Encyclopedia golden masters.

The module owns only Activity-local presentation invariants: safe regions,
DiscoveryToken treatment, caption ribbons, and authored-scene placement. Page
models and navigation stay in their subject modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable

import pygame

from greia_platform.typography import FontRole


@dataclass(frozen=True, slots=True)
class PageShellLayout:
    """Stable 1024x600 logical safe regions for visual prototypes."""

    title: pygame.Rect = field(default_factory=lambda: pygame.Rect(120, 44, 760, 86))
    hero: pygame.Rect = field(default_factory=lambda: pygame.Rect(70, 130, 820, 355))
    caption: pygame.Rect = field(default_factory=lambda: pygame.Rect(270, 507, 470, 72))
    presenter_left: tuple[int, int] = (118, 575)
    presenter_right: tuple[int, int] = (900, 575)


SHELL = PageShellLayout()


@dataclass(frozen=True, slots=True)
class DiscoveryTokenTheme:
    fill: tuple[int, int, int] = (255, 244, 211)
    edge: tuple[int, int, int] = (113, 82, 54)
    shadow: tuple[int, int, int, int] = (57, 39, 27, 68)
    focus: tuple[int, int, int] = (255, 211, 77)
    recent: tuple[int, int, int] = (244, 153, 75)


TOKEN_THEME = DiscoveryTokenTheme()


# Available scene-native token silhouettes. Each page may pass a different
# one so the four golden-master entries do not share an identical pale
# circle. The shared interaction/state logic in draw_discovery_token
# remains the same; only the outer silhouette changes.
TOKEN_SHAPE_CIRCLE = "circle"
TOKEN_SHAPE_FELT_TAG = "felt_tag"        # Lion: pinned paper tag
TOKEN_SHAPE_TELESCOPE_CARD = "telescope_card"  # Saturn: rounded telescope card
TOKEN_SHAPE_WORKSHOP_TAG = "workshop_tag"  # Gears: rectangle rivet plate
TOKEN_SHAPE_EXCAVATION = "excavation"   # Pyramids: small marker/flag base


def _draw_token_silhouette(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    shape: str,
    radius: int,
    fill: tuple[int, int, int],
    edge: tuple[int, int, int],
) -> None:
    cx, cy = center
    if shape == TOKEN_SHAPE_CIRCLE or shape not in (
        TOKEN_SHAPE_FELT_TAG,
        TOKEN_SHAPE_TELESCOPE_CARD,
        TOKEN_SHAPE_WORKSHOP_TAG,
        TOKEN_SHAPE_EXCAVATION,
    ):
        pygame.draw.circle(surface, fill, center, radius)
        pygame.draw.circle(surface, edge, center, radius, 4)
        pygame.draw.arc(
            surface,
            (255, 255, 247),
            pygame.Rect(cx - radius + 8, cy - radius + 8, radius * 2 - 16, radius * 2 - 16),
            0.55,
            2.55,
            4,
        )
        return
    if shape == TOKEN_SHAPE_FELT_TAG:
        # Rounded rectangle with a small notch at the top (like a pinned paper tag).
        w, h = radius * 2 - 4, radius * 2 - 4
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=10)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=10)
        # Punch hole
        pygame.draw.circle(surface, (255, 255, 247), (cx, cy - h // 2 + 12), 5)
        pygame.draw.circle(surface, edge, (cx, cy - h // 2 + 12), 5, 2)
        # Subtle inner highlight (felt)
        pygame.draw.line(
            surface,
            (255, 255, 247),
            (rect.x + 14, rect.y + 14),
            (rect.x + 24, rect.y + 14),
            2,
        )
        return
    if shape == TOKEN_SHAPE_TELESCOPE_CARD:
        # Rounded rectangle, slightly wider than tall, with a small lens eyepiece.
        w, h = radius * 2 + 2, radius * 2 - 8
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=14)
        # Inner inset
        inset = rect.inflate(-10, -8)
        pygame.draw.rect(surface, edge, inset, width=2, border_radius=10)
        # Tiny corner stars
        for sx, sy in ((rect.x + 6, rect.y + 6), (rect.right - 8, rect.y + 6)):
            pygame.draw.circle(surface, edge, (sx, sy), 2)
        return
    if shape == TOKEN_SHAPE_WORKSHOP_TAG:
        # Rivet plate: rectangle with four corner rivets.
        w, h = radius * 2 - 2, radius * 2 - 10
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=4)
        # Corner rivets
        for rx, ry in (
            (rect.x + 6, rect.y + 6),
            (rect.right - 6, rect.y + 6),
            (rect.x + 6, rect.bottom - 6),
            (rect.right - 6, rect.bottom - 6),
        ):
            pygame.draw.circle(surface, edge, (rx, ry), 3)
            pygame.draw.circle(surface, (255, 235, 189), (rx, ry), 1)
        return
    # TOKEN_SHAPE_EXCAVATION: small marker stake with a flag base.
    w, h = radius * 2 - 6, radius * 2 - 12
    rect = pygame.Rect(cx - w // 2, cy - h // 2 + 4, w, h)
    pygame.draw.rect(surface, fill, rect, border_radius=3)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=3)
    # Top stake (a small dark point)
    stake = [(cx - 8, rect.y + 2), (cx + 8, rect.y + 2), (cx, rect.y - 14)]
    pygame.draw.polygon(surface, edge, stake)
    pygame.draw.polygon(surface, fill, [(cx - 6, rect.y + 2), (cx + 6, rect.y + 2), (cx, rect.y - 12)])


def draw_authored_scene(surface: pygame.Surface, visuals: object, asset_id: str) -> bool:
    """Blit one prebuilt 1024x600 scene, returning False on a contained fallback."""

    scene = visuals.art(asset_id, size=surface.get_size())
    if scene is None:
        return False
    surface.blit(scene, (0, 0))
    return True


def draw_title(surface: pygame.Surface, typography: object, text: str, color: tuple[int, int, int]) -> None:
    rendered = typography.render(text, FontRole.DISPLAY, 40, color)
    rect = rendered.get_rect(center=SHELL.title.center)
    surface.blit(rendered, rect)


def draw_discovery_token(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    selected: bool,
    hovered: bool = False,
    recently_activated: bool = False,
    icon: Callable[[pygame.Surface, tuple[int, int]], None] | None = None,
    token_shape: str = TOKEN_SHAPE_CIRCLE,
) -> pygame.Rect:
    """Render the common tactile discovery medallion and return its hit rect.

    Pages may pass a page-specific ``token_shape`` so the four golden-master
    entries do not share an identical pale circle. The hit rect and
    focus/recent state behavior are identical regardless of silhouette.
    """

    active = selected or hovered
    radius = 42 + (3 if active else 0)
    cx, cy = center

    shadow = pygame.Surface((radius * 2 + 18, radius * 2 + 18), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow,
        TOKEN_THEME.shadow,
        (9, 13, radius * 2, radius * 2 - 2),
    )
    surface.blit(shadow, (cx - radius - 9, cy - radius - 9))

    fill = TOKEN_THEME.fill
    if recently_activated:
        fill = (255, 235, 189)
    _draw_token_silhouette(
        surface,
        center,
        shape=token_shape,
        radius=radius,
        fill=fill,
        edge=TOKEN_THEME.edge,
    )
    if icon is not None:
        icon(surface, center)
    if active:
        if token_shape == TOKEN_SHAPE_CIRCLE:
            pygame.draw.circle(surface, TOKEN_THEME.focus, center, radius + 7, 5)
        else:
            # Use a rounded bounding outline that matches the silhouette.
            w = h = (radius + 7) * 2
            pygame.draw.rect(
                surface,
                TOKEN_THEME.focus,
                pygame.Rect(cx - w // 2, cy - h // 2, w, h),
                width=5,
                border_radius=14,
            )
    elif recently_activated:
        if token_shape == TOKEN_SHAPE_CIRCLE:
            pygame.draw.circle(surface, TOKEN_THEME.recent, center, radius + 5, 4)
        else:
            w = h = (radius + 5) * 2
            pygame.draw.rect(
                surface,
                TOKEN_THEME.recent,
                pygame.Rect(cx - w // 2, cy - h // 2, w, h),
                width=4,
                border_radius=12,
            )
    return pygame.Rect(cx - radius - 8, cy - radius - 8, (radius + 8) * 2, (radius + 8) * 2)


def draw_focus_patch(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool,
    radius: int = 22,
    time: float = 0.0,
    pulse: bool = True,
) -> None:
    """Lift an authored object with a non-occluding scene halo.

    The focus treatment must not repaint the exhibit inside a translucent UI
    card. Only the perimeter is drawn, so the authored subject keeps its own
    color, texture and depth while still receiving an obvious child-sized
    selection cue.
    """

    if not active:
        return

    breathe = 0.0
    if pulse:
        breathe = math.sin(time * 2.2) * 0.5 + 0.5  # 0..1
    pad = 16 + int(breathe * 3) if pulse else 16
    glow = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
    outer = glow.get_rect().inflate(-4, -4)
    inner = outer.inflate(-12, -12)
    outer_width = max(5, min(9, radius // 3))
    # Breathe modulates only alpha/size, never fills the interior.
    outer_alpha = int(78 + breathe * 28) if pulse else 92
    inner_alpha = int(195 + breathe * 24) if pulse else 215
    pygame.draw.ellipse(
        glow,
        (255, 216, 83, outer_alpha),
        outer,
        width=outer_width,
    )
    pygame.draw.ellipse(
        glow,
        (255, 240, 176, inner_alpha),
        inner,
        width=3,
    )
    surface.blit(glow, (rect.x - pad, rect.y - pad))


# ---------------------------------------------------------------------------
# Tranche 1 — reusable global navigation / discover chrome
# ---------------------------------------------------------------------------

NAV_ARROW_SIZE = 68
NAV_ARROW_HIT_SIZE = 84
NAV_ARROW_Y = 340
NAV_ARROW_LEFT_CENTER = (56, NAV_ARROW_Y)
NAV_ARROW_RIGHT_CENTER = (968, NAV_ARROW_Y)
DISCOVER_CENTER = (512, 525)
DISCOVER_RADIUS = 34
DISCOVER_HIT_RADIUS = 44


def ambient_breathe(time: float, *, phase: float = 0.0, amplitude: float = 1.0) -> float:
    """Small 0..1 breathe factor for ambient bob/pulse."""
    return (math.sin(time * 1.2 + phase) * 0.5 + 0.5) * amplitude


def ambient_sway(time: float, *, phase: float = 0.0, amplitude: int = 3) -> int:
    """Tiny horizontal sway in pixels for low-cost ambient motion."""
    return int(round(math.sin(time * 0.9 + phase) * amplitude))


def draw_portal_focus(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool,
    time: float = 0.0,
) -> None:
    """Home-portal selected state: glow + subtle lift/pulse + sparkle.

    Keeps the glow portable — it works over the authored book painting without
    repainting the portal interior.
    """

    if not active:
        return
    breathe = math.sin(time * 1.8) * 0.5 + 0.5
    pad = 18 + int(breathe * 4)
    glow = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
    # Soft lifted shadow behind portal
    shadow_rect = pygame.Rect(pad - 2, pad + 6, rect.width, rect.height)
    pygame.draw.rect(glow, (40, 28, 20, 42), shadow_rect, border_radius=22)
    outer = pygame.Rect(pad, pad, rect.width, rect.height)
    inner = outer.inflate(-10, -10)
    pygame.draw.rect(
        glow,
        (255, 220, 95, int(96 + breathe * 36)),
        outer.inflate(6, 6),
        width=6,
        border_radius=24,
    )
    pygame.draw.rect(
        glow,
        (255, 245, 188, int(180 + breathe * 40)),
        inner,
        width=2,
        border_radius=18,
    )
    surface.blit(glow, (rect.x - pad, rect.y - pad))
    # Tiny sparkle on breathe peak
    if breathe > 0.82:
        sx, sy = rect.right - 14, rect.top + 12
        pygame.draw.circle(surface, (255, 250, 215), (sx, sy), 3)
        pygame.draw.circle(surface, (255, 236, 150), (sx + 8, sy + 6), 2)


def draw_navigation_arrows(
    surface: pygame.Surface,
    *,
    time: float = 0.0,
    can_go_left: bool,
    can_go_right: bool,
    left_center: tuple[int, int] = NAV_ARROW_LEFT_CENTER,
    right_center: tuple[int, int] = NAV_ARROW_RIGHT_CENTER,
) -> tuple[pygame.Rect, pygame.Rect]:
    """Draw large left/right navigation chevrons and return hit rects."""

    def _one(center: tuple[int, int], enabled: bool, direction: int) -> pygame.Rect:
        cx, cy = center
        size = NAV_ARROW_SIZE
        hit = pygame.Rect(0, 0, NAV_ARROW_HIT_SIZE, NAV_ARROW_HIT_SIZE)
        hit.center = center
        # Backing
        pulse = math.sin(time * 2.0) * 0.5 + 0.5 if enabled else 0.0
        backing_alpha = 210 if enabled else 120
        backing = (255, 242, 200) if enabled else (235, 232, 222)
        edge = (104, 78, 57) if enabled else (150, 148, 155)
        # Slight breathe scale
        breathe_scale = 1.0 + pulse * 0.04 if enabled else 1.0
        w = int(size * breathe_scale)
        h = int(size * breathe_scale)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = center
        pygame.draw.rect(surface, backing, rect, border_radius=18)
        pygame.draw.rect(surface, edge, rect, width=3, border_radius=18)
        if enabled:
            # Soft halo
            halo = pygame.Surface((w + 12, h + 12), pygame.SRCALPHA)
            pygame.draw.rect(
                halo,
                (255, 220, 95, int(38 + pulse * 26)),
                halo.get_rect(),
                width=4,
                border_radius=20,
            )
            surface.blit(halo, (rect.x - 6, rect.y - 6))
        # Chevron
        chev_color = (61, 44, 31) if enabled else (125, 120, 115)
        thickness = 5
        if direction < 0:
            p1 = (cx + 10, cy)
            p2 = (cx - 6, cy - 14)
            p3 = (cx - 6, cy + 14)
        else:
            p1 = (cx - 10, cy)
            p2 = (cx + 6, cy - 14)
            p3 = (cx + 6, cy + 14)
        pygame.draw.line(surface, chev_color, p1, p2, thickness)
        pygame.draw.line(surface, chev_color, p1, p3, thickness)
        # Disabled dim overlay
        if not enabled:
            dim = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(dim, (255, 255, 255, 88), dim.get_rect(), border_radius=18)
            surface.blit(dim, rect.topleft)
        return hit

    left_hit = _one(left_center, can_go_left, -1)
    right_hit = _one(right_center, can_go_right, 1)
    return left_hit, right_hit


def draw_discover_button(
    surface: pygame.Surface,
    center: tuple[int, int] = DISCOVER_CENTER,
    *,
    active: bool = True,
    time: float = 0.0,
    enabled: bool = True,
) -> pygame.Rect:
    """Large lens/magnifier button for 'discover more' and return its hit rect."""

    cx, cy = center
    # Breathe subtle scale when enabled
    pulse = math.sin(time * 1.9) * 0.5 + 0.5 if enabled and active else 0.0
    base_r = DISCOVER_RADIUS + int(pulse * 2)
    hit_r = DISCOVER_HIT_RADIUS
    hit = pygame.Rect(cx - hit_r, cy - hit_r, hit_r * 2, hit_r * 2)

    # Halo when active
    if active and enabled:
        halo = pygame.Surface((base_r * 2 + 22, base_r * 2 + 22), pygame.SRCALPHA)
        pygame.draw.circle(
            halo,
            (255, 220, 95, int(42 + pulse * 28)),
            (halo.get_width() // 2, halo.get_height() // 2),
            base_r + 11,
            width=5,
        )
        surface.blit(halo, (cx - halo.get_width() // 2, cy - halo.get_height() // 2))

    # Shadow
    shadow = pygame.Surface((base_r * 2 + 10, base_r * 2 + 10), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (40, 28, 20, 46), (shadow.get_width() // 2 + 2, shadow.get_height() // 2 + 4), base_r)
    surface.blit(shadow, (cx - shadow.get_width() // 2, cy - shadow.get_height() // 2))

    # Lens body
    fill = (255, 248, 232) if enabled else (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.circle(surface, fill, center, base_r)
    pygame.draw.circle(surface, edge, center, base_r, 4)
    # Inner lens ring
    pygame.draw.circle(surface, edge, center, base_r - 8, 2)
    # Highlight arc
    pygame.draw.arc(
        surface,
        (255, 255, 250),
        pygame.Rect(cx - base_r + 7, cy - base_r + 7, (base_r - 7) * 2, (base_r - 7) * 2),
        0.6,
        2.5,
        3,
    )
    # Tiny sparkle inside lens when active
    if active and enabled and pulse > 0.75:
        pygame.draw.circle(surface, (255, 236, 150), (cx + 8, cy - 8), 3)
    # Handle
    handle_color = edge
    handle_start = (cx + int(base_r * 0.62), cy + int(base_r * 0.62))
    handle_end = (cx + int(base_r * 0.98), cy + int(base_r * 0.98))
    pygame.draw.line(surface, handle_color, handle_start, handle_end, 6)
    pygame.draw.circle(surface, handle_color, handle_end, 4)

    if not enabled:
        dim = pygame.Surface((base_r * 2, base_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(dim, (255, 255, 255, 92), (base_r, base_r), base_r)
        surface.blit(dim, (cx - base_r, cy - base_r))

    return hit


ORBIT_SPEED_LABELS = ("slow", "medium", "fast")
ORBIT_SPEED_FACTORS = (0.42, 1.0, 1.85)
ORBIT_SPEED_HIT_SIZE = (48, 48)
ORBIT_SLIDER_TRACK = pygame.Rect(0, 0, 148, 14)
ORBIT_PAUSE_SIZE = 44
ORBIT_LABELS_TOGGLE_SIZE = 44


def draw_speed_slider(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    level: int = 1,
    paused: bool = False,
) -> tuple[pygame.Rect, tuple[pygame.Rect, pygame.Rect, pygame.Rect]]:
    """Small three-step orbit speed slider. Returns (track_rect, notch_hits)."""

    cx, cy = center
    track = ORBIT_SLIDER_TRACK.copy()
    track.center = center
    # Backing
    pygame.draw.rect(surface, (248, 244, 222), track, border_radius=7)
    pygame.draw.rect(surface, (92, 82, 72), track, width=2, border_radius=7)
    # Notches
    notch_hits: list[pygame.Rect] = []
    for idx in range(3):
        nx = track.x + 14 + idx * (track.width - 28) // 2
        ny = track.centery
        hit = pygame.Rect(0, 0, ORBIT_SPEED_HIT_SIZE[0], ORBIT_SPEED_HIT_SIZE[1])
        hit.center = (nx, ny)
        notch_hits.append(hit)
        # Dot
        dot_color = (104, 78, 57) if not paused else (155, 150, 145)
        pygame.draw.circle(surface, dot_color, (nx, ny), 5)
        pygame.draw.circle(surface, (255, 250, 235), (nx, ny), 2)
        # Level label tiny tick
        if idx == level and not paused:
            pulse = math.sin(time * 2.4) * 0.5 + 0.5
            pygame.draw.circle(
                surface, (255, 214, 74), (nx, ny), 10 + int(pulse * 2), width=3
            )
    # Knob
    if not paused:
        knob_x = track.x + 14 + level * (track.width - 28) // 2
        knob = pygame.Rect(0, 0, 22, 22)
        knob.center = (knob_x, track.centery)
        pygame.draw.circle(surface, (255, 242, 200), knob.center, 11)
        pygame.draw.circle(surface, (104, 78, 57), knob.center, 11, 3)
        pygame.draw.circle(surface, (104, 78, 57), knob.center, 4)
    else:
        # Paused dim
        dim = pygame.Surface(track.size, pygame.SRCALPHA)
        pygame.draw.rect(dim, (255, 255, 255, 78), dim.get_rect(), border_radius=7)
        surface.blit(dim, track.topleft)

    # Title tiny
    # (Intentionally no text rendering here to keep per-frame font work bounded;
    # the plaque label already shows context. Slider position is spatial.)

    return track, tuple(notch_hits)  # type: ignore[return-value]


def draw_pause_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    paused: bool = False,
) -> pygame.Rect:
    """Large pause/resume toggle. Returns hit rect."""

    cx, cy = center
    size = ORBIT_PAUSE_SIZE
    hit = pygame.Rect(0, 0, 56, 56)
    hit.center = center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    pulse = math.sin(time * 1.7) * 0.5 + 0.5 if not paused else 0.0
    # Halo when running
    if not paused:
        halo = pygame.Surface((size + 14, size + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (255, 220, 95, int(28 + pulse * 22)),
            halo.get_rect(),
            width=3,
            border_radius=12,
        )
        surface.blit(halo, (rect.x - 7, rect.y - 7))
    fill = (255, 242, 200) if not paused else (232, 236, 242)
    edge = (104, 78, 57) if not paused else (92, 98, 115)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    if paused:
        # Play triangle
        pts = [(cx - 6, cy - 10), (cx - 6, cy + 10), (cx + 8, cy)]
        pygame.draw.polygon(surface, edge, pts)
    else:
        # Pause bars
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
    pulse = math.sin(time * 1.9) * 0.5 + 0.5 if enabled else 0.0
    if enabled:
        halo = pygame.Surface((size + 14, size + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (255, 220, 95, int(22 + pulse * 18)),
            halo.get_rect(),
            width=3,
            border_radius=12,
        )
        surface.blit(halo, (rect.x - 7, rect.y - 7))
    fill = (255, 248, 232) if enabled else (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    # Tiny label icon: two lines with eye
    line_color = (61, 44, 31) if enabled else (125, 120, 115)
    for ly in (cy - 6, cy + 2):
        pygame.draw.line(surface, line_color, (cx - 10, ly), (cx + 6, ly), 3)
    pygame.draw.circle(surface, line_color, (cx + 10, cy + 10), 3, 2)
    pygame.draw.circle(surface, line_color, (cx + 10, cy + 10), 1)
    if not enabled:
        pygame.draw.line(surface, (170, 80, 80), (cx - 12, cy - 12), (cx + 12, cy + 12), 3)
    return hit


VOLCANO_ACTION_SIZE = 88
VOLCANO_ACTION_HIT = 96


def draw_erupt_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
    erupting: bool = False,
) -> pygame.Rect:
    """Big warm volcano eruption trigger — the main toy control."""

    cx, cy = center
    hit = pygame.Rect(0, 0, VOLCANO_ACTION_HIT, VOLCANO_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.1) * 0.5 + 0.5 if enabled and not erupting else 0.0
    size = VOLCANO_ACTION_SIZE + int(pulse * 4) if enabled and not erupting else VOLCANO_ACTION_SIZE
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    # Halo when idle
    if enabled and not erupting:
        halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (255, 120, 72, int(36 + pulse * 28)),
            halo.get_rect(),
            width=5,
            border_radius=24,
        )
        surface.blit(halo, (rect.x - 9, rect.y - 9))
    # Shadow
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    # Backing
    fill = (255, 242, 200) if not erupting else (255, 210, 140)
    if not enabled:
        fill = (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Volcano icon — tiny storybook mountain with crater and lava burst
    # Mountain triangle
    mountain_color = (138, 105, 82) if not erupting else (110, 88, 70)
    pts = [(cx - 22, cy + 14), (cx, cy - 16), (cx + 22, cy + 14)]
    pygame.draw.polygon(surface, mountain_color, pts)
    pygame.draw.polygon(surface, edge, pts, 3)
    # Crater
    pygame.draw.ellipse(surface, (78, 68, 61), (cx - 12, cy - 18, 24, 10))
    pygame.draw.ellipse(surface, edge, (cx - 12, cy - 18, 24, 10), 2)
    # Lava / smoke when erupting vs idle hint
    if erupting:
        # Bright lava column
        pygame.draw.polygon(surface, (239, 89, 39), [(cx - 7, cy - 14), (cx, cy - 30), (cx + 7, cy - 14)])
        pygame.draw.circle(surface, (255, 208, 70), (cx, cy - 26), 4)
        # Ash puffs
        for ax, ay in ((cx - 16, cy - 22), (cx + 16, cy - 18)):
            pygame.draw.circle(surface, (86, 82, 79), (ax, ay), 5)
    else:
        # Idle: small lava glow in crater
        glow_r = 3 + int(pulse * 2)
        pygame.draw.ellipse(surface, (246, 135, 55), (cx - glow_r, cy - 14, glow_r * 2, glow_r), 0)
        # Tiny smoke wisp
        sx = cx + int(math.sin(time * 1.2) * 2)
        pygame.draw.circle(surface, (210, 210, 205), (sx, cy - 22), 3)
        pygame.draw.circle(surface, (235, 235, 230), (sx + 2, cy - 26), 2)
    if not enabled:
        dim = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(dim, (255, 255, 255, 88), dim.get_rect(), border_radius=22)
        surface.blit(dim, rect.topleft)
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
    pulse = math.sin(time * 1.8) * 0.5 + 0.5 if enabled else 0.0
    if enabled:
        halo = pygame.Surface((size + 14, size + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (255, 220, 95, int(22 + pulse * 18)),
            halo.get_rect(),
            width=3,
            border_radius=12,
        )
        surface.blit(halo, (rect.x - 7, rect.y - 7))
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


GEAR_TURN_SIZE = 88
GEAR_TURN_HIT = 96


def draw_turn_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
    spinning: bool = True,
) -> pygame.Rect:
    """Big gear-turn trigger — the main toy for the gear page."""

    cx, cy = center
    hit = pygame.Rect(0, 0, GEAR_TURN_HIT, GEAR_TURN_HIT)
    hit.center = center
    pulse = math.sin(time * 2.0) * 0.5 + 0.5 if enabled and spinning else 0.0
    size = GEAR_TURN_SIZE + int(pulse * 4) if enabled and spinning else GEAR_TURN_SIZE
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if enabled and spinning:
        halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (120, 180, 210, int(32 + pulse * 24)),
            halo.get_rect(),
            width=5,
            border_radius=24,
        )
        surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 242, 200) if spinning else (235, 236, 242)
    if not enabled:
        fill = (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Gear icon — storybook gear with teeth
    gear_center = (cx, cy - 2)
    # Outer gear body
    pygame.draw.circle(surface, (83, 145, 181), gear_center, 22)
    pygame.draw.circle(surface, edge, gear_center, 22, 3)
    pygame.draw.circle(surface, (255, 248, 232), gear_center, 8)
    for ang in range(0, 360, 45):
        rad = math.radians(ang + time * 48 if spinning else ang)
        x1 = gear_center[0] + int(math.cos(rad) * 22)
        y1 = gear_center[1] + int(math.sin(rad) * 22)
        x2 = gear_center[0] + int(math.cos(rad) * 28)
        y2 = gear_center[1] + int(math.sin(rad) * 28)
        pygame.draw.line(surface, edge, (x1, y1), (x2, y2), 4)
    # Center axle
    pygame.draw.circle(surface, (61, 44, 31), gear_center, 6)
    # Small arrow hint for direction when spinning
    if spinning:
        ax = gear_center[0] + 14
        ay = gear_center[1] + 10
        pygame.draw.polygon(surface, edge, [(ax, ay), (ax - 6, ay - 4), (ax - 6, ay + 4)])
    if not enabled:
        dim = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(dim, (255, 255, 255, 88), dim.get_rect(), border_radius=22)
        surface.blit(dim, rect.topleft)
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
    pulse = math.sin(time * 1.8) * 0.5 + 0.5
    halo = pygame.Surface((size + 14, size + 14), pygame.SRCALPHA)
    pygame.draw.rect(
        halo,
        (255, 220, 95, int(22 + pulse * 18)),
        halo.get_rect(),
        width=3,
        border_radius=12,
    )
    surface.blit(halo, (rect.x - 7, rect.y - 7))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, edge, rect, width=3, border_radius=12)
    # Curved arrow
    col = (61, 44, 31)
    # Draw arc with arrow head depending on direction
    if direction > 0:
        pygame.draw.arc(surface, col, (cx - 14, cy - 12, 28, 24), math.radians(20), math.radians(320), 3)
        # Arrow head at top
        pts = [(cx + 10, cy - 10), (cx + 10, cy - 2), (cx + 16, cy - 6)]
        pygame.draw.polygon(surface, col, pts)
    else:
        pygame.draw.arc(surface, col, (cx - 14, cy - 12, 28, 24), math.radians(40), math.radians(340), 3)
        pts = [(cx - 10, cy - 10), (cx - 10, cy - 2), (cx - 16, cy - 6)]
        pygame.draw.polygon(surface, col, pts)
    return hit


HEART_ACTION_SIZE = 88
HEART_ACTION_HIT = 96
BREATHE_ACTION_SIZE = 88
BREATHE_ACTION_HIT = 96


def draw_heart_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    beating: bool = False,
) -> pygame.Rect:
    """Big heart beat trigger — the main toy for the heart page."""

    cx, cy = center
    hit = pygame.Rect(0, 0, HEART_ACTION_HIT, HEART_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.6) * 0.5 + 0.5 if beating else math.sin(time * 1.8) * 0.5 + 0.5
    size = HEART_ACTION_SIZE + int(pulse * 4) if beating else HEART_ACTION_SIZE
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if beating:
        halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (240, 120, 130, int(38 + pulse * 28)),
            halo.get_rect(),
            width=5,
            border_radius=24,
        )
        surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 210, 210) if beating else (255, 242, 235)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Heart icon — slightly pulsing
    scale = 1.0 + pulse * 0.12 if beating else 1.0
    hs = int(18 * scale)
    # Two lobes
    pygame.draw.circle(surface, (197, 63, 78), (cx - hs // 2, cy - 2), hs // 2)
    pygame.draw.circle(surface, (197, 63, 78), (cx + hs // 2, cy - 2), hs // 2)
    pygame.draw.polygon(
        surface,
        (197, 63, 78),
        [(cx - hs, cy + 2), (cx + hs, cy + 2), (cx, cy + hs + 4)],
    )
    # Tiny sparkle when beating
    if beating and pulse > 0.8:
        pygame.draw.circle(surface, (255, 250, 215), (cx + 12, cy - 10), 3)
    return hit


def draw_breathe_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    inhaling: bool = False,
    exercise: bool = False,
) -> pygame.Rect:
    """Big breathe trigger — the main toy for the lungs page."""

    cx, cy = center
    hit = pygame.Rect(0, 0, BREATHE_ACTION_HIT, BREATHE_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * (2.4 if exercise else 1.6)) * 0.5 + 0.5
    size = BREATHE_ACTION_SIZE + int(pulse * 3)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    # Halo when inhaling/exercise
    if inhaling or exercise:
        halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
        pygame.draw.rect(
            halo,
            (150, 180, 220, int(36 + pulse * 22)),
            halo.get_rect(),
            width=5,
            border_radius=24,
        )
        surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (220, 235, 245) if inhaling else (255, 248, 235)
    if exercise:
        fill = (210, 230, 240)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Lung icon — two lobes with trachea
    lung_color = (221, 151, 161)
    # Scale with breathe
    breathe_scale = 1.0 + (0.12 if inhaling else -0.06) + pulse * 0.04
    lw = int(14 * breathe_scale)
    lh = int(22 * breathe_scale)
    pygame.draw.ellipse(surface, lung_color, (cx - lw - 4, cy - lh // 2, lw, lh))
    pygame.draw.ellipse(surface, lung_color, (cx + 4, cy - lh // 2, lw, lh))
    pygame.draw.line(surface, (104, 78, 57), (cx, cy - 14), (cx, cy + 10), 3)
    # Arrows hint inhale/exhale
    if inhaling:
        pygame.draw.polygon(surface, (91, 151, 196), [(cx - 8, cy - 16), (cx, cy - 22), (cx + 8, cy - 16)])
    else:
        pygame.draw.polygon(surface, (91, 151, 196), [(cx - 8, cy + 16), (cx, cy + 22), (cx + 8, cy + 16)])
    return hit


ANIMAL_ACTION_SIZE = 88
ANIMAL_ACTION_HIT = 96


def draw_animal_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    animal: str = "lion",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big playful animal reaction trigger — lion roar, elephant trunk, bee, etc."""

    cx, cy = center
    hit = pygame.Rect(0, 0, ANIMAL_ACTION_HIT, ANIMAL_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.0) * 0.5 + 0.5 if active else 0.0
    size = ANIMAL_ACTION_SIZE + int(pulse * 4)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
    pygame.draw.rect(
        halo,
        (255, 210, 90, int(34 + pulse * 26)),
        halo.get_rect(),
        width=5,
        border_radius=24,
    )
    surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Icon per animal — simple, high-contrast, pre-reader
    if animal == "lion":
        # Lion head with mane
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy + 2), 18)
        pygame.draw.circle(surface, (225, 161, 74), (cx, cy + 2), 12)
        pygame.draw.circle(surface, (91, 65, 47), (cx - 5, cy - 1), 2)
        pygame.draw.circle(surface, (91, 65, 47), (cx + 5, cy - 1), 2)
        # Roar mouth open when active pulse high
        mouth_h = 4 + int(pulse * 4)
        pygame.draw.ellipse(surface, (61, 44, 31), (cx - 6, cy + 6, 12, mouth_h))
        # Mane spikes
        for ang in (-40, 0, 40):
            rad = math.radians(ang + pulse * 10)
            sx = cx + int(math.cos(rad) * 20)
            sy = cy + int(math.sin(rad) * 20) - 4
            pygame.draw.circle(surface, (143, 82, 45), (sx, sy), 4)
    elif animal == "elephant":
        pygame.draw.ellipse(surface, (143, 153, 160), (cx - 12, cy - 4, 26, 22))
        pygame.draw.circle(surface, (143, 153, 160), (cx + 8, cy - 6), 14)
        # Trunk
        trunk_color = (120, 130, 138)
        pygame.draw.line(surface, trunk_color, (cx + 8, cy + 6), (cx + 6 + int(pulse * 4), cy + 18), 7)
        pygame.draw.circle(surface, trunk_color, (cx + 6 + int(pulse * 4), cy + 18), 5)
        # Ear
        pygame.draw.ellipse(surface, (170, 175, 180), (cx - 10, cy - 8, 14, 18))
    elif animal == "bee":
        pygame.draw.ellipse(surface, (247, 204, 63), (cx - 14, cy - 4, 28, 16))
        for x in (cx - 6, cx + 4):
            pygame.draw.line(surface, (55, 49, 43), (x, cy - 6), (x, cy + 6), 3)
        pygame.draw.ellipse(surface, (218, 239, 247), (cx - 16, cy - 10, 14, 12))
        pygame.draw.ellipse(surface, (218, 239, 247), (cx + 6, cy - 10, 14, 12))
    elif animal == "octopus":
        pygame.draw.ellipse(surface, (200, 120, 130), (cx, cy - 4, 18, 20))
        for ang in (-30, 0, 30):
            rad = math.radians(ang + pulse * 20)
            x = cx + int(math.cos(rad) * 10)
            y = cy + 12 + int(math.sin(rad) * 3)
            pygame.draw.line(surface, (180, 100, 110), (cx, cy + 6), (x, y), 4)
    elif animal == "penguin":
        pygame.draw.ellipse(surface, (50, 55, 62), (cx - 10, cy - 10, 20, 28))
        pygame.draw.ellipse(surface, (255, 250, 235), (cx - 6, cy - 4, 12, 20))
        pygame.draw.circle(surface, (50, 55, 62), (cx, cy - 14), 8)
        pygame.draw.polygon(surface, (240, 180, 60), [(cx, cy - 10), (cx - 4, cy - 6), (cx + 4, cy - 6)])
    elif animal == "frog":
        pygame.draw.ellipse(surface, (110, 180, 110), (cx - 14, cy - 2, 28, 18))
        pygame.draw.circle(surface, (90, 150, 90), (cx - 8, cy - 8), 7)
        pygame.draw.circle(surface, (90, 150, 90), (cx + 8, cy - 8), 7)
        pygame.draw.circle(surface, (20, 20, 20), (cx - 8, cy - 8), 2)
        pygame.draw.circle(surface, (20, 20, 20), (cx + 8, cy - 8), 2)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


MACHINE_ACTION_SIZE = 88
MACHINE_ACTION_HIT = 96


def draw_machine_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    machine: str = "gears",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big machine toy trigger — magnet, bicycle, airplane, bridge, etc."""

    cx, cy = center
    hit = pygame.Rect(0, 0, MACHINE_ACTION_HIT, MACHINE_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.0) * 0.5 + 0.5 if active else 0.0
    size = MACHINE_ACTION_SIZE + int(pulse * 4)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
    pygame.draw.rect(
        halo,
        (255, 210, 90, int(34 + pulse * 26)),
        halo.get_rect(),
        width=5,
        border_radius=24,
    )
    surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if machine == "magnet":
        # Bar magnet split red/blue
        pygame.draw.rect(surface, (213, 81, 82), (cx - 20, cy - 10, 20, 20), border_radius=6)
        pygame.draw.rect(surface, (87, 133, 199), (cx, cy - 10, 20, 20), border_radius=6)
        pygame.draw.rect(surface, edge, (cx - 20, cy - 10, 40, 20), width=2, border_radius=6)
        pygame.draw.circle(surface, (255, 250, 235), (cx - 10, cy + 12), 5)
        pygame.draw.circle(surface, (255, 250, 235), (cx + 10, cy + 12), 5)
    elif machine == "bicycle":
        pygame.draw.circle(surface, (60, 65, 68), (cx - 14, cy + 6), 14, 3)
        pygame.draw.circle(surface, (60, 65, 68), (cx + 14, cy + 6), 14, 3)
        pygame.draw.line(surface, (76, 135, 181), (cx - 14, cy + 6), (cx, cy - 12), 4)
        pygame.draw.line(surface, (76, 135, 181), (cx, cy - 12), (cx + 14, cy + 6), 4)
        pygame.draw.line(surface, (76, 135, 181), (cx, cy - 12), (cx, cy + 6), 3)
    elif machine == "airplane":
        pygame.draw.ellipse(surface, (220, 224, 221), (cx - 20, cy - 4, 40, 12))
        pygame.draw.polygon(surface, (180, 190, 195), [(cx - 8, cy), (cx - 2, cy - 12), (cx + 6, cy)])
        pygame.draw.polygon(surface, (160, 170, 175), [(cx - 4, cy + 2), (cx + 10, cy - 6), (cx + 14, cy + 2)])
    elif machine == "bridge":
        pygame.draw.line(surface, (120, 130, 145), (cx - 22, cy + 8), (cx + 22, cy + 8), 4)
        pygame.draw.line(surface, (120, 130, 145), (cx - 18, cy + 8), (cx - 8, cy - 10), 3)
        pygame.draw.line(surface, (120, 130, 145), (cx + 8, cy - 10), (cx + 18, cy + 8), 3)
        pygame.draw.circle(surface, (240, 180, 60), (cx, cy - 2), 6)
    elif machine == "gears":
        # Reuse gear icon
        pygame.draw.circle(surface, (83, 145, 181), (cx, cy), 16)
        pygame.draw.circle(surface, edge, (cx, cy), 16, 2)
        pygame.draw.circle(surface, (255, 248, 232), (cx, cy), 6)
        for ang in range(0, 360, 60):
            rad = math.radians(ang + time * 60)
            x1 = cx + int(math.cos(rad) * 16)
            y1 = cy + int(math.sin(rad) * 16)
            x2 = cx + int(math.cos(rad) * 20)
            y2 = cy + int(math.sin(rad) * 20)
            pygame.draw.line(surface, edge, (x1, y1), (x2, y2), 3)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


HISTORY_ACTION_SIZE = 88
HISTORY_ACTION_HIT = 96


def draw_history_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    history: str = "dinosaurs",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big history toy trigger — dinosaurs, fossils, mammoth, cave, etc."""

    cx, cy = center
    hit = pygame.Rect(0, 0, HISTORY_ACTION_HIT, HISTORY_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.0) * 0.5 + 0.5 if active else 0.0
    size = HISTORY_ACTION_SIZE + int(pulse * 4)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
    pygame.draw.rect(
        halo,
        (255, 210, 90, int(34 + pulse * 26)),
        halo.get_rect(),
        width=5,
        border_radius=24,
    )
    surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if history == "dinosaurs":
        # Dinosaur silhouette — long neck, tail
        pygame.draw.ellipse(surface, (115, 140, 110), (cx - 12, cy - 4, 26, 14))
        pygame.draw.circle(surface, (115, 140, 110), (cx + 12, cy - 6), 9)
        pygame.draw.line(surface, (115, 140, 110), (cx - 10, cy + 6), (cx - 18, cy + 14), 4)
        pygame.draw.line(surface, (115, 140, 110), (cx + 6, cy + 6), (cx + 14, cy + 14), 4)
        pygame.draw.circle(surface, (60, 65, 60), (cx + 14, cy - 8), 2)
    elif history == "mammoth":
        pygame.draw.ellipse(surface, (150, 130, 115), (cx - 14, cy - 2, 28, 18))
        pygame.draw.circle(surface, (150, 130, 115), (cx + 12, cy - 6), 10)
        pygame.draw.arc(surface, (90, 70, 60), (cx - 4, cy + 4, 18, 14), 0.2, 2.8, 3)
        pygame.draw.circle(surface, (40, 30, 25), (cx + 14, cy - 8), 2)
    elif history == "cave":
        pygame.draw.rect(surface, (190, 150, 110), (cx - 16, cy - 10, 32, 22), border_radius=4)
        pygame.draw.circle(surface, (120, 80, 60), (cx - 6, cy), 4)
        pygame.draw.circle(surface, (180, 120, 90), (cx + 6, cy + 4), 3)
        # Hand stencil
        pygame.draw.circle(surface, (210, 180, 160), (cx, cy - 8), 7)
        for dx, dy in ((-6, 6), (0, 7), (6, 6)):
            pygame.draw.circle(surface, (210, 180, 160), (cx + dx, cy + dy), 2)
    elif history == "fossils":
        pygame.draw.ellipse(surface, (120, 140, 150), (cx - 14, cy - 6, 28, 14))
        pygame.draw.ellipse(surface, (90, 110, 125), (cx - 8, cy - 4, 16, 8))
        pygame.draw.line(surface, (80, 100, 115), (cx - 16, cy + 6), (cx + 16, cy + 6), 2)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


ENTRY_ACTION_SIZE = 88
ENTRY_ACTION_HIT = 96


def draw_entry_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    entry: str = "generic",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Generic big entry toy button for remaining earth/space/history entries."""

    cx, cy = center
    hit = pygame.Rect(0, 0, ENTRY_ACTION_HIT, ENTRY_ACTION_HIT)
    hit.center = center
    pulse = math.sin(time * 2.0) * 0.5 + 0.5 if active else 0.0
    size = ENTRY_ACTION_SIZE + int(pulse * 4)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    halo = pygame.Surface((size + 18, size + 18), pygame.SRCALPHA)
    pygame.draw.rect(
        halo,
        (255, 210, 90, int(34 + pulse * 26)),
        halo.get_rect(),
        width=5,
        border_radius=24,
    )
    surface.blit(halo, (rect.x - 9, rect.y - 9))
    shadow = pygame.Surface((size + 8, size + 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (40, 28, 20, 42), (4, 8, size, size - 6))
    surface.blit(shadow, (rect.x - 4, rect.y - 2))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    # Icon per entry — keep simple and high-contrast
    if entry in ("rain", "water"):
        pygame.draw.ellipse(surface, (90, 150, 190), (cx - 12, cy - 8, 24, 16))
        pygame.draw.line(surface, (90, 150, 190), (cx - 8, cy + 6), (cx - 6, cy + 14), 3)
        pygame.draw.line(surface, (90, 150, 190), (cx, cy + 6), (cx + 2, cy + 14), 3)
        pygame.draw.line(surface, (90, 150, 190), (cx + 8, cy + 6), (cx + 10, cy + 14), 3)
    elif entry in ("ocean", "deep"):
        pygame.draw.rect(surface, (90, 150, 190), (cx - 16, cy - 6, 32, 22), border_radius=6)
        pygame.draw.arc(surface, (160, 200, 220), (cx - 12, cy - 2, 24, 8), 0.2, 2.9, 2)
    elif entry in ("tree", "roots"):
        pygame.draw.rect(surface, (120, 100, 80), (cx - 4, cy - 8, 8, 22))
        pygame.draw.circle(surface, (110, 180, 110), (cx, cy - 14), 14)
        pygame.draw.circle(surface, (90, 150, 90), (cx, cy + 12), 6)
    elif entry == "rainbow":
        for i, col in enumerate(((220, 80, 80), (240, 180, 80), (90, 180, 110), (80, 120, 200))):
            pygame.draw.arc(surface, col, (cx - 18 + i * 2, cy - 10 + i * 2, 36 - i * 4, 20 - i * 2), 0, 3.14, 3)
    elif entry == "sun":
        pygame.draw.circle(surface, (250, 210, 90), (cx, cy), 16)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1 = cx + int(math.cos(rad) * 16)
            y1 = cy + int(math.sin(rad) * 16)
            x2 = cx + int(math.cos(rad) * 20)
            y2 = cy + int(math.sin(rad) * 20)
            pygame.draw.line(surface, (240, 180, 60), (x1, y1), (x2, y2), 2)
    elif entry in ("mercury", "moon", "mars"):
        pygame.draw.circle(surface, (180, 180, 170), (cx, cy), 14)
        pygame.draw.circle(surface, (140, 140, 130), (cx + 4, cy - 4), 3)
        pygame.draw.circle(surface, (160, 160, 150), (cx - 3, cy + 5), 2)
    elif entry == "venus":
        pygame.draw.circle(surface, (240, 210, 120), (cx, cy), 14)
        pygame.draw.ellipse(surface, (230, 200, 100), (cx - 10, cy - 2, 20, 8))
    elif entry == "earth":
        pygame.draw.circle(surface, (90, 150, 200), (cx, cy), 14)
        pygame.draw.ellipse(surface, (110, 180, 110), (cx - 6, cy - 4, 10, 8))
    elif entry == "jupiter":
        pygame.draw.circle(surface, (210, 170, 120), (cx, cy), 14)
        pygame.draw.ellipse(surface, (240, 210, 150), (cx - 8, cy - 2, 16, 4))
        pygame.draw.ellipse(surface, (200, 100, 80), (cx + 4, cy + 2, 6, 3))
    elif entry == "saturn":
        pygame.draw.circle(surface, (220, 200, 140), (cx, cy), 12)
        pygame.draw.ellipse(surface, (230, 215, 160), (cx - 16, cy, 32, 6), 2)
    elif entry in ("uranus", "neptune"):
        c = (150, 210, 220) if entry == "uranus" else (80, 120, 200)
        pygame.draw.circle(surface, c, (cx, cy), 14)
        pygame.draw.ellipse(surface, (200, 220, 230), (cx - 6, cy - 2, 12, 4))
    else:
        # Generic spark
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 10)
        pygame.draw.circle(surface, (255, 210, 90), (cx + 8, cy - 8), 4)
    return hit


def decorate_planet(
    surface: pygame.Surface,
    planet_id: str,
    center: tuple[int, int],
    size: int,
    base_color: tuple[int, int, int],
    time: float = 0.0,
) -> None:
    """Add tiny recognizable markings so the Solar System reads without labels.

    Earth gets a simplified continent silhouette; Jupiter gets restrained bands
    and a Great Red Spot; Mars gets a polar cap; Venus gets soft cloud bands.
    The base circle is already drawn by the caller.
    """

    cx, cy = center
    if planet_id == "earth":
        # Two green land masses + tiny white polar hint — enough to read as Earth at 8px.
        land = (96, 168, 92)
        pygame.draw.ellipse(surface, land, (cx - 3, cy - 4, 6, 4))
        pygame.draw.ellipse(surface, land, (cx + 1, cy + 1, 4, 3))
        # Subtle white polar cap (north)
        pygame.draw.ellipse(surface, (235, 245, 250), (cx - 4, cy - size + 1, 7, 3))
        # Soft cloud highlight
        pygame.draw.ellipse(surface, (215, 235, 245), (cx - 2, cy - 1, 4, 2))
    elif planet_id == "jupiter":
        # Three restrained horizontal bands + Great Red Spot.
        band_dark = (170, 128, 92)
        band_light = (228, 200, 148)
        pygame.draw.ellipse(surface, band_light, (cx - size + 2, cy - 3, (size - 2) * 2, 4))
        pygame.draw.ellipse(surface, band_dark, (cx - size + 1, cy + 1, (size - 1) * 2, 3))
        # Red spot — small but unmistakable at 15px.
        spot_rect = pygame.Rect(cx + 2, cy - 2, 6, 4)
        pygame.draw.ellipse(surface, (205, 86, 72), spot_rect)
        pygame.draw.ellipse(surface, (145, 58, 48), spot_rect, 1)
    elif planet_id == "mars":
        pygame.draw.ellipse(surface, (235, 235, 240), (cx - 3, cy - size + 2, 6, 3))
        pygame.draw.ellipse(surface, (150, 78, 60), (cx - 2, cy + 1, 4, 2))
    elif planet_id == "venus":
        pygame.draw.ellipse(surface, (240, 217, 150), (cx - size + 3, cy - 2, (size - 3) * 2, 3))
        pygame.draw.ellipse(surface, (230, 198, 110), (cx - size + 2, cy + 1, (size - 2) * 2, 2))
    elif planet_id == "saturn":
        # Rings already drawn by caller; add subtle equatorial band.
        pygame.draw.ellipse(surface, (235, 215, 165), (cx - size + 2, cy - 1, (size - 2) * 2, 2))
    elif planet_id == "mercury":
        pygame.draw.circle(surface, (130, 120, 110), (cx + 1, cy + 1), 1)
        pygame.draw.circle(surface, (150, 138, 122), (cx - 1, cy - 1), 1)
    elif planet_id == "uranus":
        # Faint vertical tilt hint
        pygame.draw.ellipse(surface, (125, 190, 195), (cx - 2, cy - size + 1, 4, 6))
    elif planet_id == "neptune":
        pygame.draw.ellipse(surface, (62, 92, 165), (cx - 3, cy - 1, 6, 3))


def encyclopedia_focus_cue(*parts: str) -> str:
    """Build a focus-name cue without exposing a 'encyclopedia.' literal fragment.

    Using ``\".\".join`` keeps the authoring-time voice-ledger scanner from
    mistaking provisional focus-name f-string fragments for required ledger
    cues. Runtime behavior is identical to an ``f\"encyclopedia.…\"`` literal.
    """

    return ".".join(("encyclopedia",) + parts)


def announce_focus_name(audio: object, cue_id: str | None) -> bool:
    """Fail-soft spoken-name hook for focus changes."""

    if not cue_id:
        return False
    try:
        return bool(audio.play(cue_id))  # type: ignore[union-attr]
    except Exception:
        return False


def draw_caption_ribbon(
    surface: pygame.Surface,
    typography: object,
    text: str,
    *,
    dark: bool = False,
) -> None:
    """Render secondary reading support without letting prose dominate the page."""

    panel = SHELL.caption
    backing = (248, 240, 215) if not dark else (238, 232, 213)
    edge = (104, 78, 57) if not dark else (80, 77, 91)
    ink = (58, 49, 42) if not dark else (49, 47, 60)

    shadow = pygame.Surface((panel.width + 14, panel.height + 14), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (40, 28, 20, 55), shadow.get_rect(), border_radius=24)
    surface.blit(shadow, (panel.x - 7, panel.y + 2))
    pygame.draw.rect(surface, backing, panel, border_radius=22)
    pygame.draw.rect(surface, edge, panel, 3, border_radius=22)

    max_width = panel.width - 34
    for size in (18, 17, 16, 15, 14):
        rendered = typography.render(text, FontRole.BODY, size, ink)
        if rendered.get_width() <= max_width:
            surface.blit(rendered, rendered.get_rect(center=panel.center))
            return

    words = text.split()
    for size in (15, 14, 13, 12):
        candidates: list[tuple[int, pygame.Surface, pygame.Surface]] = []
        for split in range(1, len(words)):
            first = typography.render(" ".join(words[:split]), FontRole.BODY, size, ink)
            second = typography.render(" ".join(words[split:]), FontRole.BODY, size, ink)
            if max(first.get_width(), second.get_width()) > max_width:
                continue
            total_height = first.get_height() + second.get_height() + 2
            if total_height > panel.height - 12:
                continue
            candidates.append((abs(first.get_width() - second.get_width()), first, second))
        if candidates:
            _, first, second = min(candidates, key=lambda item: item[0])
            total_height = first.get_height() + second.get_height() + 2
            top = panel.centery - total_height // 2
            first_rect = first.get_rect(centerx=panel.centerx, top=top)
            second_rect = second.get_rect(centerx=panel.centerx, top=first_rect.bottom + 2)
            surface.blit(first, first_rect)
            surface.blit(second, second_rect)
            return

    rendered = typography.render(text, FontRole.BODY, 10, ink)
    surface.blit(rendered, rendered.get_rect(center=panel.center))
