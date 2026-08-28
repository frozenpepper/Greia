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
) -> pygame.Rect:
    """Render the common tactile discovery medallion and return its hit rect."""

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
    pygame.draw.circle(surface, fill, center, radius)
    pygame.draw.circle(surface, TOKEN_THEME.edge, center, radius, 4)
    pygame.draw.arc(
        surface,
        (255, 255, 247),
        pygame.Rect(cx - radius + 8, cy - radius + 8, radius * 2 - 16, radius * 2 - 16),
        0.55,
        2.55,
        4,
    )
    if icon is not None:
        icon(surface, center)
    if active:
        pygame.draw.circle(surface, TOKEN_THEME.focus, center, radius + 7, 5)
    elif recently_activated:
        pygame.draw.circle(surface, TOKEN_THEME.recent, center, radius + 5, 4)
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
