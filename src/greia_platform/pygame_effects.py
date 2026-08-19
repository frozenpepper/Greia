from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ui_core import BoundedCache
from .ui_motion import InteractionVisualState, MotionSample

_SHADOW_SURFACE_CACHE: BoundedCache[tuple[int, int, int, int], Any] = BoundedCache(128)


def clear_effects_cache() -> None:
    """Clear cached shadow surfaces."""
    _SHADOW_SURFACE_CACHE.clear()


@dataclass(frozen=True, slots=True)
class PygameDepthStyle:
    """Small reusable depth recipe for Greia Pygame surfaces."""

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


def make_rounded_shadow(size: tuple[int, int], pygame: Any, *, style: PygameDepthStyle) -> Any:
    """Create one reusable rounded shadow Surface for a size/style variant."""

    width, height = size
    if width < 1 or height < 1:
        raise ValueError("shadow size must be positive")
    key = (width, height, style.radius, style.shadow_alpha)
    cached = _SHADOW_SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    shadow = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(
        shadow,
        (0, 0, 0, style.shadow_alpha),
        shadow.get_rect(),
        border_radius=min(style.radius, width // 2, height // 2),
    )
    _SHADOW_SURFACE_CACHE[key] = shadow
    return shadow


def draw_soft_shadow(
    surface: Any,
    rect: Any,
    pygame: Any,
    *,
    style: PygameDepthStyle = PygameDepthStyle(),
    lift: float = 0.0,
    cached_shadow: Any | None = None,
) -> None:
    """Draw a rounded shadow, reusing a caller-owned cached Surface when supplied."""

    offset = max(1, int(round(style.shadow_offset + max(0.0, lift) * 2.0)))
    shadow = cached_shadow
    if shadow is None or shadow.get_size() != rect.size:
        shadow = make_rounded_shadow(rect.size, pygame, style=style)
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
    cached_shadow: Any | None = None,
) -> Any:
    """Draw Greia's standard shallow raised card and return its transformed rect."""

    target = transformed_rect(rect, motion, pygame)
    usable_shadow = cached_shadow if target.size == rect.size else None
    draw_soft_shadow(
        surface,
        target,
        pygame,
        style=style,
        lift=motion.shadow_lift,
        cached_shadow=usable_shadow,
    )
    radius = min(style.radius, target.width // 2, target.height // 2)
    pygame.draw.rect(surface, fill, target, border_radius=radius)
    width = selected_width if state.emphasized else normal_width
    pygame.draw.rect(surface, outline, target, width=max(1, width), border_radius=radius)
    return target


def make_shadowed_icon(
    icon: Any,
    pygame: Any,
    *,
    shadow_alpha: int = 58,
    shadow_offset: int = 4,
) -> Any:
    """Create one cacheable icon Surface containing a silhouette shadow."""

    width = icon.get_width() + max(0, shadow_offset)
    height = icon.get_height() + max(0, shadow_offset)
    composite = pygame.Surface((width, height), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(icon)
    shadow = mask.to_surface(
        setcolor=(0, 0, 0, shadow_alpha),
        unsetcolor=(0, 0, 0, 0),
    )
    composite.blit(shadow, (shadow_offset, shadow_offset))
    composite.blit(icon, (0, 0))
    return composite
