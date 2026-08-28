"""Shared storybook presentation primitives for Encyclopedia golden masters.

The module owns only Activity-local presentation invariants: safe regions,
DiscoveryToken treatment, caption ribbons, and authored-scene placement. Page
models and navigation stay in their subject modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
) -> None:
    """Lift an authored object without placing it inside a generic UI card."""

    if not active:
        return
    glow = pygame.Surface((rect.width + 28, rect.height + 28), pygame.SRCALPHA)
    pygame.draw.rect(
        glow,
        (255, 216, 83, 46),
        glow.get_rect(),
        border_radius=radius + 10,
    )
    pygame.draw.rect(
        glow,
        (255, 216, 83, 220),
        glow.get_rect().inflate(-7, -7),
        width=5,
        border_radius=radius,
    )
    surface.blit(glow, (rect.x - 14, rect.y - 14))


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
