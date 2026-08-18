from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import pygame

from .ui_core import BoundedCache
from .ui_preferences import InterfaceSize

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
_ICON_CACHE: BoundedCache[tuple[str, int], pygame.Surface] = BoundedCache(64)


@dataclass(frozen=True, slots=True)
class ChildUiMetrics:
    """Cheap responsive geometry for child-sized Pygame controls.

    1024×600 remains the reference authoring scale, not a physical-screen
    requirement. The active child's semantic interface-size preference is
    composed into this shared metric, so first-party Activity authors still
    author one layout rather than maintaining compact/normal/large variants.
    Growth is capped on very large displays and the constrained-screen floor is
    preserved.
    """

    width: int
    height: int
    scale: float
    margin: int
    toolbar_height: int
    button_size: int
    gap: int
    radius: int

    @classmethod
    def for_size(cls, width: int, height: int) -> "ChildUiMetrics":
        if width <= 0 or height <= 0:
            raise ValueError("surface dimensions must be positive")
        viewport_scale = max(
            0.5,
            min(1.7, width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT),
        )
        try:
            preference = InterfaceSize(
                os.environ.get("GREIA_INTERFACE_SIZE", InterfaceSize.NORMAL.value)
            )
        except ValueError:
            preference = InterfaceSize.NORMAL
        scale = max(0.5, min(1.9, viewport_scale * preference.scale))
        px = lambda value: max(1, int(round(value * scale)))
        return cls(width, height, scale, px(18), px(78), px(58), px(12), px(16))

    def px(self, value: int | float) -> int:
        return max(1, int(round(float(value) * self.scale)))

    def toolbar_button(self, index: int, *, side: str = "left") -> pygame.Rect:
        if index < 0:
            raise ValueError("button index must be non-negative")
        y = self.margin + max(0, (self.toolbar_height - self.button_size) // 2)
        step = self.button_size + self.gap
        if side == "left":
            x = self.margin + index * step
        elif side == "right":
            x = self.width - self.margin - self.button_size - index * step
        else:
            raise ValueError("side must be left or right")
        return pygame.Rect(x, y, self.button_size, self.button_size)


def load_icon(path: str | Path, size: int) -> pygame.Surface:
    """Load and scale one icon variant through the shared hard-bounded cache."""

    if size <= 0:
        raise ValueError("icon size must be positive")
    key = (str(Path(path)), int(size))
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    image = pygame.image.load(key[0]).convert_alpha()
    if image.get_width() != size or image.get_height() != size:
        image = pygame.transform.smoothscale(image, (size, size))
    _ICON_CACHE[key] = image
    return image


def clear_icon_cache() -> None:
    """Drop renderer-specific cached icon surfaces after display teardown/change."""

    _ICON_CACHE.clear()


def draw_icon_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int],
    icon: pygame.Surface | None = None,
    selected: bool = False,
    outline: tuple[int, int, int] | None = None,
) -> None:
    """Draw a lightweight icon button directly onto its owning surface."""

    radius = max(8, min(rect.width, rect.height) // 4)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if selected:
        border = outline if outline is not None else (255, 255, 255)
        pygame.draw.rect(
            surface,
            border,
            rect,
            width=max(3, rect.width // 18),
            border_radius=radius,
        )
    if icon is not None:
        surface.blit(icon, icon.get_rect(center=rect.center))


def draw_plus_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    cx, cy = rect.center
    span = max(8, rect.width // 4)
    width = max(4, rect.width // 12)
    pygame.draw.line(surface, color, (cx - span, cy), (cx + span, cy), width)
    pygame.draw.line(surface, color, (cx, cy - span), (cx, cy + span), width)


def draw_grid_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    size = max(7, rect.width // 6)
    gap = max(5, rect.width // 10)
    total = size * 2 + gap
    left = rect.centerx - total // 2
    top = rect.centery - total // 2
    for row in range(2):
        for col in range(2):
            pygame.draw.rect(
                surface,
                color,
                (
                    left + col * (size + gap),
                    top + row * (size + gap),
                    size,
                    size,
                ),
                border_radius=max(2, size // 4),
            )


def draw_undo_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    cx, cy = rect.center
    radius = max(10, rect.width // 4)
    arc_rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
    pygame.draw.arc(surface, color, arc_rect, 0.4, 4.5, max(4, rect.width // 12))
    tip = (cx - radius + 2, cy - radius // 3)
    pygame.draw.polygon(
        surface,
        color,
        [
            tip,
            (tip[0] + radius // 2, tip[1] - radius // 3),
            (tip[0] + radius // 2, tip[1] + radius // 3),
        ],
    )


def draw_eraser_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    width = max(18, rect.width // 2)
    height = max(12, rect.height // 3)
    eraser = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(
        eraser,
        color,
        eraser.get_rect(),
        border_radius=max(3, height // 4),
    )
    rotated = pygame.transform.rotate(eraser, -28)
    surface.blit(rotated, rotated.get_rect(center=rect.center))


def draw_home_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    """Draw Greia's canonical simple Home glyph inside a control rectangle."""

    span = max(12, min(rect.width, rect.height) // 3)
    roof_y = rect.centery - span // 2
    left = rect.centerx - span
    right = rect.centerx + span
    wall_top = rect.centery
    bottom = rect.centery + span
    stroke = max(3, min(rect.width, rect.height) // 12)
    pygame.draw.lines(
        surface,
        color,
        False,
        [(left, wall_top), (rect.centerx, roof_y), (right, wall_top)],
        stroke,
    )
    body = pygame.Rect(left + stroke, wall_top - stroke // 2, span * 2 - stroke * 2, bottom - wall_top)
    pygame.draw.rect(surface, color, body, width=stroke, border_radius=max(2, stroke))
    door_width = max(stroke * 2, body.width // 4)
    door = pygame.Rect(
        rect.centerx - door_width // 2,
        body.bottom - max(stroke * 2, body.height // 2),
        door_width,
        max(stroke * 2, body.height // 2),
    )
    pygame.draw.rect(surface, color, door, width=stroke, border_radius=max(1, stroke // 2))


def draw_back_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    """Draw Greia's canonical Back glyph; this is Greia navigation, not browser history."""

    span = max(12, min(rect.width, rect.height) // 3)
    stroke = max(3, min(rect.width, rect.height) // 12)
    tip = (rect.centerx - span, rect.centery)
    tail = (rect.centerx + span, rect.centery)
    pygame.draw.line(surface, color, tip, tail, stroke)
    pygame.draw.lines(
        surface,
        color,
        False,
        [
            (rect.centerx - span // 3, rect.centery - span * 2 // 3),
            tip,
            (rect.centerx - span // 3, rect.centery + span * 2 // 3),
        ],
        stroke,
    )


def mix(
    color: tuple[int, int, int],
    other: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(
        max(
            0,
            min(
                255,
                int(round(channel * (1.0 - amount) + target * amount)),
            ),
        )
        for channel, target in zip(color, other)
    )
