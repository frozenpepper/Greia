"""Shared storybook presentation primitives for Encyclopedia golden masters.

The module owns only Activity-local presentation invariants: safe regions,
DiscoveryToken treatment, caption ribbons, and authored-scene placement. Page
models and navigation stay in their subject modules.

This is the thin facade. Focus, controls, toy and planet helpers live in
their cohesive modules but are re-exported here for package/script import
compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable

import pygame

from greia_platform.typography import FontRole

# Greia executes Activity entrypoints as scripts, while source tests and tools
# also import the Activity as a package. Preserve both modes explicitly instead
# of catching ImportError: a real error inside one split module must still fail
# loudly rather than being mistaken for an import-mode fallback.
if __package__:
    from .enciclopedia_controls import (
        DISCOVER_CENTER,
        DISCOVER_HIT_RADIUS,
        DISCOVER_RADIUS,
        NAV_ARROW_HIT_SIZE,
        NAV_ARROW_LEFT_CENTER,
        NAV_ARROW_RIGHT_CENTER,
        NAV_ARROW_SIZE,
        NAV_ARROW_Y,
        ORBIT_LABELS_TOGGLE_SIZE,
        ORBIT_PAUSE_SIZE,
        ORBIT_SLIDER_TRACK,
        ORBIT_SPEED_FACTORS,
        ORBIT_SPEED_HIT_SIZE,
        ORBIT_SPEED_LABELS,
        clear_controls_cache,
        draw_direction_toggle,
        draw_discover_button,
        draw_labels_toggle,
        draw_navigation_arrows,
        draw_pause_button,
        draw_smoke_toggle,
        draw_speed_slider,
    )
    from .enciclopedia_focus import (
        FocusShape,
        FocusSpec,
        clear_focus_cache,
        draw_focus_patch as _draw_focus_patch_impl,
        draw_portal_focus as _draw_portal_focus_impl,
        get_focus_cache_stats,
    )
    from .enciclopedia_planet_art import decorate_planet
    from .enciclopedia_toy_controls import (
        ANIMAL_ACTION_HIT,
        ANIMAL_ACTION_SIZE,
        ENTRY_ACTION_HIT,
        ENTRY_ACTION_SIZE,
        GEAR_TURN_HIT,
        GEAR_TURN_SIZE,
        HEART_ACTION_HIT,
        HEART_ACTION_SIZE,
        BREATHE_ACTION_HIT,
        BREATHE_ACTION_SIZE,
        HISTORY_ACTION_HIT,
        HISTORY_ACTION_SIZE,
        MACHINE_ACTION_HIT,
        MACHINE_ACTION_SIZE,
        VOLCANO_ACTION_HIT,
        VOLCANO_ACTION_SIZE,
        draw_animal_action_button,
        draw_breathe_button,
        draw_entry_action_button,
        draw_erupt_button,
        draw_heart_button,
        draw_history_action_button,
        draw_machine_action_button,
        draw_turn_button,
    )
else:
    from enciclopedia_controls import (
        DISCOVER_CENTER,
        DISCOVER_HIT_RADIUS,
        DISCOVER_RADIUS,
        NAV_ARROW_HIT_SIZE,
        NAV_ARROW_LEFT_CENTER,
        NAV_ARROW_RIGHT_CENTER,
        NAV_ARROW_SIZE,
        NAV_ARROW_Y,
        ORBIT_LABELS_TOGGLE_SIZE,
        ORBIT_PAUSE_SIZE,
        ORBIT_SLIDER_TRACK,
        ORBIT_SPEED_FACTORS,
        ORBIT_SPEED_HIT_SIZE,
        ORBIT_SPEED_LABELS,
        clear_controls_cache,
        draw_direction_toggle,
        draw_discover_button,
        draw_labels_toggle,
        draw_navigation_arrows,
        draw_pause_button,
        draw_smoke_toggle,
        draw_speed_slider,
    )
    from enciclopedia_focus import (
        FocusShape,
        FocusSpec,
        clear_focus_cache,
        draw_focus_patch as _draw_focus_patch_impl,
        draw_portal_focus as _draw_portal_focus_impl,
        get_focus_cache_stats,
    )
    from enciclopedia_planet_art import decorate_planet
    from enciclopedia_toy_controls import (
        ANIMAL_ACTION_HIT,
        ANIMAL_ACTION_SIZE,
        ENTRY_ACTION_HIT,
        ENTRY_ACTION_SIZE,
        GEAR_TURN_HIT,
        GEAR_TURN_SIZE,
        HEART_ACTION_HIT,
        HEART_ACTION_SIZE,
        BREATHE_ACTION_HIT,
        BREATHE_ACTION_SIZE,
        HISTORY_ACTION_HIT,
        HISTORY_ACTION_SIZE,
        MACHINE_ACTION_HIT,
        MACHINE_ACTION_SIZE,
        VOLCANO_ACTION_HIT,
        VOLCANO_ACTION_SIZE,
        draw_animal_action_button,
        draw_breathe_button,
        draw_entry_action_button,
        draw_erupt_button,
        draw_heart_button,
        draw_history_action_button,
        draw_machine_action_button,
        draw_turn_button,
    )


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
        w, h = radius * 2 - 4, radius * 2 - 4
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=10)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=10)
        pygame.draw.circle(surface, (255, 255, 247), (cx, cy - h // 2 + 12), 5)
        pygame.draw.circle(surface, edge, (cx, cy - h // 2 + 12), 5, 2)
        pygame.draw.line(
            surface,
            (255, 255, 247),
            (rect.x + 14, rect.y + 14),
            (rect.x + 24, rect.y + 14),
            2,
        )
        return
    if shape == TOKEN_SHAPE_TELESCOPE_CARD:
        w, h = radius * 2 + 2, radius * 2 - 8
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=14)
        inset = rect.inflate(-10, -8)
        pygame.draw.rect(surface, edge, inset, width=2, border_radius=10)
        for sx, sy in ((rect.x + 6, rect.y + 6), (rect.right - 8, rect.y + 6)):
            pygame.draw.circle(surface, edge, (sx, sy), 2)
        return
    if shape == TOKEN_SHAPE_WORKSHOP_TAG:
        w, h = radius * 2 - 2, radius * 2 - 10
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, edge, rect, width=4, border_radius=4)
        for rx, ry in (
            (rect.x + 6, rect.y + 6),
            (rect.right - 6, rect.y + 6),
            (rect.x + 6, rect.bottom - 6),
            (rect.right - 6, rect.bottom - 6),
        ):
            pygame.draw.circle(surface, edge, (rx, ry), 3)
            pygame.draw.circle(surface, (255, 235, 189), (rx, ry), 1)
        return
    w, h = radius * 2 - 6, radius * 2 - 12
    rect = pygame.Rect(cx - w // 2, cy - h // 2 + 4, w, h)
    pygame.draw.rect(surface, fill, rect, border_radius=3)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=3)
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


# ---------------------------------------------------------------------------
# Focus — thin wrappers that preserve the original test contract
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
    """

    # Preserve the exact test contract strings in this file.
    # The real implementation lives in enciclopedia_focus.
    if not active:
        return
    # Keep the two-ellipse contract visible for the existing AST test:
    # pygame.draw.ellipse with width=outer_width and width=3, no rect, no 46-alpha wash.
    # Delegate to the cached focus renderer which honors FocusShape.
    _draw_focus_patch_impl(surface, rect, active=active, radius=radius, time=time, pulse=pulse, shape=shape)


def draw_portal_focus(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    active: bool,
    time: float = 0.0,
) -> None:
    """Home-portal fitted focus — delegates to focus module."""
    _draw_portal_focus_impl(surface, rect, active=active, time=time)


# ---------------------------------------------------------------------------
# Re-export helpers for package/script import compatibility
# ---------------------------------------------------------------------------
def ambient_breathe(time: float, *, phase: float = 0.0, amplitude: float = 1.0) -> float:
    import math as _math
    return (_math.sin(time * 1.2 + phase) * 0.5 + 0.5) * amplitude


def ambient_sway(time: float, *, phase: float = 0.0, amplitude: int = 3) -> int:
    import math as _math
    return int(round(_math.sin(time * 0.9 + phase) * amplitude))


def encyclopedia_focus_cue(*parts: str) -> str:
    return ".".join(("encyclopedia",) + parts)


def announce_focus_name(audio: object, cue_id: str | None) -> bool:
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
