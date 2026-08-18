from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ui_motion import InteractionVisualState, MotionSample


@dataclass(frozen=True, slots=True)
class PygameDepthStyle:
    """Small reusable depth recipe for Greia Pygame surfaces.

    The implementation intentionally uses direct primitive drawing and at most
    one tiny temporary shadow surface per draw. It is not a scene graph or a
    compositor and remains suitable for the 1024x600 legacy reference floor.
    """

    shadow_offset: int = 5
    shadow_alpha: int = 52
    radius: int = 24

    def __post_init__(self) -> None:
        if self.shadow_offset < 0:
            raise ValueError("shadow_offset must be non-negative")
        if not 0 <= self.shadow_alpha <= 255:
            raise ValueError("shadow_alpha must be between 0 and 255")
        if self.radius < 0:
            raise ValueError("radius must be non-negative")


def transformed_rect(rect: Any, motion: MotionSample, pygame: Any) -> Any:
    """Return an integer Pygame Rect after one bounded scale/translation sample."""

    width = max(1, int(round(rect.width * motion.scale)))
    height = max(1, int(round(rect.height * motion.scale)))
    transformed = pygame.Rect(0, 0, width, height)
    transformed.center = (
        int(round(rect.centerx + motion.offset_x)),
        int(round(rect.centery + motion.offset_y)),
    )
    return transformed


def draw_soft_shadow(
    surface: Any,
    rect: Any,
    pygame: Any,
    *,
    style: PygameDepthStyle = PygameDepthStyle(),
    lift: float = 0.0,
) -> None:
    """Draw a cheap translucent rounded shadow without blurring the whole screen."""

    offset = max(1, int(round(style.shadow_offset + max(0.0, lift) * 2.0)))
    shadow_rect = pygame.Rect(0, 0, rect.width, rect.height)
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(
        shadow,
        (0, 0, 0, style.shadow_alpha),
        shadow_rect,
        border_radius=min(style.radius, rect.width // 2, rect.height // 2),
    )
    surface.blit(shadow, (rect.left + offset, rect.top + offset))


def draw_raised_panel(
    surface: Any,
    rect: Any,
    pygame: Any,
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    state: InteractionVisualState = InteractionVisualState(),
    motion: MotionSample = MotionSample(),
    style: PygameDepthStyle = PygameDepthStyle(),
    selected_width: int = 7,
    normal_width: int = 3,
) -> Any:
    """Draw Greia's standard shallow raised card and return its transformed rect."""

    target = transformed_rect(rect, motion, pygame)
    draw_soft_shadow(surface, target, pygame, style=style, lift=motion.shadow_lift)
    radius = min(style.radius, target.width // 2, target.height // 2)
    pygame.draw.rect(surface, fill, target, border_radius=radius)
    width = selected_width if state.emphasized else normal_width
    pygame.draw.rect(surface, outline, target, width=max(1, width), border_radius=radius)
    return target


def draw_shadowed_icon(
    surface: Any,
    icon: Any,
    center: tuple[int, int],
    pygame: Any,
    *,
    shadow_alpha: int = 58,
    shadow_offset: int = 4,
) -> None:
    """Give a transparent icon a small silhouette shadow and then draw it."""

    alpha = icon.get_alpha()
    mask = pygame.mask.from_surface(icon)
    shadow = mask.to_surface(setcolor=(0, 0, 0, shadow_alpha), unsetcolor=(0, 0, 0, 0))
    shadow.set_alpha(shadow_alpha)
    rect = icon.get_rect(center=center)
    surface.blit(shadow, (rect.left + shadow_offset, rect.top + shadow_offset))
    surface.blit(icon, rect)
    if alpha is not None:
        icon.set_alpha(alpha)
