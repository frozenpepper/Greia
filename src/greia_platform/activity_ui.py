from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import pygame

from .activity_viewport import ActivityViewport
from .responsive_layout import UiRect
from .system_chrome import ActivitySystemChromeLayout
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

    Ordinary `toolbar_button()` intentionally describes a full-surface toolbar
    for non-Activity surfaces. Greia Activities should use
    `activity_toolbar_button()` / `activity_content_rect()` so essential controls
    are derived from the same platform-owned Home/Back exclusion as input.
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
        """Return full-surface toolbar geometry for non-Activity UI."""

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

    def activity_safe_rect(self) -> pygame.Rect:
        """Return the usable Activity rectangle outside trusted Home/Back chrome."""

        chrome = ActivitySystemChromeLayout.for_surface(self.width, self.height)
        top_bar_height = max(self.toolbar_height, chrome.protected_region.height)
        return pygame.Rect(0, top_bar_height, self.width, max(0, self.height - top_bar_height))

    def activity_toolbar_button(
        self,
        index: int,
        *,
        side: str = "left",
    ) -> pygame.Rect:
        """Return one Activity toolbar button inside the top bar outside platform chrome."""

        if index < 0:
            raise ValueError("button index must be non-negative")
        chrome = ActivitySystemChromeLayout.for_surface(self.width, self.height)
        protected = chrome.protected_region
        top_bar_height = max(self.toolbar_height, protected.height)
        y = max(0, (top_bar_height - self.button_size) // 2)
        step = self.button_size + self.gap
        if side == "left":
            x = protected.right + self.gap + index * step
        elif side == "right":
            x = self.width - self.margin - self.button_size - index * step
        else:
            raise ValueError("side must be left or right")
        rect = pygame.Rect(x, y, self.button_size, self.button_size)
        if (
            rect.left < 0
            or rect.top < 0
            or rect.right > self.width
            or rect.bottom > self.height
            or (
                rect.right > protected.x
                and protected.right > rect.left
                and rect.bottom > protected.y
                and protected.bottom > rect.top
            )
        ):
            raise ValueError("Activity toolbar does not fit inside safe UI region")
        return rect

    def activity_content_rect(
        self,
        *,
        top_gap: int | float = 6,
        bottom_reserve: int = 0,
    ) -> pygame.Rect:
        """Return responsive Activity content below its safe toolbar.

        `bottom_reserve` is already-scaled pixel space owned by the caller, for
        example Painting's palette tray. Essential content never extends into
        trusted system chrome or outside the real surface.
        """

        if bottom_reserve < 0:
            raise ValueError("bottom reserve must not be negative")
        chrome = ActivitySystemChromeLayout.for_surface(self.width, self.height)
        top_bar_height = max(self.toolbar_height, chrome.protected_region.height)
        top = top_bar_height + self.px(top_gap)
        bottom = self.height - self.margin - bottom_reserve
        left = self.margin
        right = self.width - self.margin
        if right <= left or bottom <= top:
            raise ValueError("Activity safe UI region is too small for requested content")
        return pygame.Rect(left, top, right - left, bottom - top)


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
    """Draw Greia's canonical cute cottage Home glyph inside a control rectangle."""

    sz = min(rect.width, rect.height)
    cx, cy = rect.centerx, rect.centery
    scale = sz / 48.0

    # Chimney on right
    chimney_x = cx + int(6 * scale)
    chimney_y = cy - int(16 * scale)
    chimney_w = max(3, int(5 * scale))
    chimney_h = max(5, int(9 * scale))
    pygame.draw.rect(
        surface,
        color,
        (chimney_x, chimney_y, chimney_w, chimney_h),
        border_radius=max(1, int(1.5 * scale)),
    )

    # Roof Triangle with overhang
    roof_top = (cx, cy - int(14 * scale))
    roof_left = (cx - int(16 * scale), cy - int(1 * scale))
    roof_right = (cx + int(16 * scale), cy - int(1 * scale))
    pygame.draw.polygon(surface, color, [roof_top, roof_left, roof_right])

    # House Body
    body_x = cx - int(12 * scale)
    body_y = cy - int(2 * scale)
    body_w = int(24 * scale)
    body_h = int(16 * scale)
    pygame.draw.rect(
        surface,
        color,
        (body_x, body_y, body_w, body_h),
        border_radius=max(2, int(3 * scale)),
    )

    # Contrast details (cutouts on colored house)
    detail_color = (255, 248, 235) if sum(color) < 450 else (61, 44, 31)

    # Cozy arched door
    door_w = max(6, int(8 * scale))
    door_h = max(8, int(11 * scale))
    door_x = cx - door_w // 2
    door_y = body_y + body_h - door_h
    pygame.draw.rect(
        surface,
        detail_color,
        (door_x, door_y, door_w, door_h),
        border_top_left_radius=door_w // 2,
        border_top_right_radius=door_w // 2,
    )

    # Door knob
    knob_x = door_x + door_w - max(2, int(2.5 * scale))
    knob_y = door_y + door_h // 2
    pygame.draw.circle(surface, color, (knob_x, knob_y), max(1, int(1.5 * scale)))

    # Round attic window
    window_r = max(2, int(3.2 * scale))
    window_center = (cx, cy - int(4 * scale))
    pygame.draw.circle(surface, detail_color, window_center, window_r)
    if window_r >= 3:
        pygame.draw.line(
            surface,
            color,
            (window_center[0] - window_r + 1, window_center[1]),
            (window_center[0] + window_r - 1, window_center[1]),
            1,
        )
        pygame.draw.line(
            surface,
            color,
            (window_center[0], window_center[1] - window_r + 1),
            (window_center[0], window_center[1] + window_r - 1),
            1,
        )


def draw_back_symbol(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    """Draw Greia's canonical chunky Back arrow glyph inside a control rectangle."""

    sz = min(rect.width, rect.height)
    cx, cy = rect.centerx, rect.centery
    scale = sz / 48.0

    # Arrow Head Points (Left-pointing rounded triangle)
    tip_x = cx - int(13 * scale)
    tip_y = cy
    top_x = cx - int(1 * scale)
    top_y = cy - int(11 * scale)
    bot_x = cx - int(1 * scale)
    bot_y = cy + int(11 * scale)

    # Arrow Shaft (chunky rectangle extending to right)
    shaft_x = cx - int(4 * scale)
    shaft_y = cy - int(5 * scale)
    shaft_w = int(16 * scale)
    shaft_h = int(10 * scale)

    corner_r = max(1, int(2.5 * scale))
    pygame.draw.rect(
        surface,
        color,
        (shaft_x, shaft_y, shaft_w, shaft_h),
        border_radius=max(2, int(3 * scale)),
    )
    pygame.draw.polygon(surface, color, [(tip_x, tip_y), (top_x, top_y), (bot_x, bot_y)])
    pygame.draw.circle(surface, color, (tip_x, tip_y), corner_r)
    pygame.draw.circle(surface, color, (top_x, top_y), corner_r)
    pygame.draw.circle(surface, color, (bot_x, bot_y), corner_r)


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


def draw_system_chrome_overlay(
    surface: pygame.Surface,
    *,
    back_available: bool = False,
    outline_color: tuple[int, int, int] = (78, 56, 40),
    fill_color: tuple[int, int, int] = (255, 252, 245),
) -> None:
    """Draw the platform-owned Home (and optional Back) button on top of any Activity frame."""
    w, h = surface.get_size()
    if w <= 0 or h <= 0:
        return
    chrome = ActivitySystemChromeLayout.for_surface(w, h, back_available=back_available)
    hb = chrome.home_hitbox
    home_rect = pygame.Rect(hb.x, hb.y, hb.width, hb.height)

    # Tactile drop shadow
    shadow_rect = home_rect.move(0, 3)
    pygame.draw.rect(
        surface,
        (203, 213, 225),
        shadow_rect,
        border_radius=max(8, home_rect.width // 3),
    )

    # Warm tactile Home button pill
    pygame.draw.rect(
        surface,
        fill_color,
        home_rect,
        border_radius=max(8, home_rect.width // 3),
    )
    # Subtle top bevel highlight
    highlight_rect = pygame.Rect(
        home_rect.x + 2,
        home_rect.y + 2,
        home_rect.width - 4,
        max(2, home_rect.height // 2),
    )
    pygame.draw.rect(
        surface,
        (255, 255, 255),
        highlight_rect,
        border_top_left_radius=max(6, home_rect.width // 3 - 2),
        border_top_right_radius=max(6, home_rect.width // 3 - 2),
    )
    # Outline
    pygame.draw.rect(
        surface,
        outline_color,
        home_rect,
        width=max(2, home_rect.width // 24),
        border_radius=max(8, home_rect.width // 3),
    )
    draw_home_symbol(surface, home_rect, outline_color)

    if chrome.back_available:
        bb = chrome.back_hitbox
        back_rect = pygame.Rect(bb.x, bb.y, bb.width, bb.height)
        back_shadow = back_rect.move(0, 3)
        pygame.draw.rect(
            surface,
            (203, 213, 225),
            back_shadow,
            border_radius=max(8, back_rect.width // 3),
        )
        pygame.draw.rect(
            surface,
            fill_color,
            back_rect,
            border_radius=max(8, back_rect.width // 3),
        )
        pygame.draw.rect(
            surface,
            outline_color,
            back_rect,
            width=max(2, back_rect.width // 24),
            border_radius=max(8, back_rect.width // 3),
        )
        draw_back_symbol(surface, back_rect, outline_color)


def draw_activity_pointer(
    surface: pygame.Surface,
    pos: tuple[int, int] | None = None,
    *,
    color: tuple[int, int, int] = (254, 202, 87),
    inner_color: tuple[int, int, int] = (255, 255, 255),
    border_color: tuple[int, int, int] = (78, 56, 40),
    radius: int = 11,
) -> None:
    """Draw Greia's high-contrast responsive pointer cursor at the mouse position."""
    if pos is None:
        if not pygame.mouse.get_focused():
            return
        pos = pygame.mouse.get_pos()
    x, y = pos
    if x <= 0 and y <= 0:
        return
    pygame.draw.circle(surface, color, pos, radius)
    pygame.draw.circle(surface, inner_color, pos, max(1, radius // 2))
    pygame.draw.circle(surface, border_color, pos, radius, max(1, radius // 5))


def is_home_clicked(surface: pygame.Surface, pos: tuple[int, int]) -> bool:
    """Return whether pos is within the platform-owned Home button hitbox."""
    w, h = surface.get_size()
    if w <= 0 or h <= 0:
        return False
    try:
        chrome = ActivitySystemChromeLayout.for_surface(w, h)
        return chrome.home_hitbox.contains(pos[0], pos[1])
    except (TypeError, ValueError):
        return False