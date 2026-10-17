"""Picture of Greia's protected Home chrome, painted into a Shell surface.

Why this exists. ADR 0019 requires Home to be present while an Activity is
visible, and the Activity's window is visible from the launch card onward.
The trusted chrome itself is a separate, backend-owned surface that can only
exist once the Activity session does, and it can be covered for a few
milliseconds when the Activity's window maps above it. The Shell therefore
paints a *picture* of the same Home at the same protected geometry on its
launch screen: Home is visible from the first launch frame, and the launch
card the Activity repaints carries the picture underneath the real chrome
while that chrome is raised again.

A picture is never an input surface and never replaces the trusted chrome.
The Shell answers taps on it only while its own window is on top (that is,
before the trusted chrome is shown); afterwards the backend's trusted surface
owns the protected region. Each chrome backend supplies its palette, so the
picture matches what that backend draws natively. Pure Pygame, passed in by
the caller: this module imports no display system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greia_platform.system_chrome import ActivitySystemChromeLayout

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class HomeChromePalette:
    """Colours of one backend's Home chrome."""

    window: RGB
    border: RGB
    button: RGB
    outline: RGB
    door: RGB

    @classmethod
    def from_rgb_ints(cls, **colors: int) -> "HomeChromePalette":
        return cls(**{name: _rgb(value) for name, value in colors.items()})


def paint_home_chrome_picture(
    surface: Any,
    pygame: Any,
    layout: ActivitySystemChromeLayout,
    palette: HomeChromePalette,
) -> None:
    """Paint the Home capsule, button and cottage glyph at ``layout``.

    The geometry is the arithmetic of the Legacy-X chrome window (capsule
    sized to Home plus its margin, button inset by ``width // 16``, glyph in
    48-unit design space scaled to the hit box). Back is never drawn: it
    appears with the trusted chrome when Greia's launch origin allows it.
    """

    home = layout.home_hitbox
    margin = home.x
    width = home.right + margin
    height = layout.protected_region.height
    draw = pygame.draw
    draw.rect(surface, palette.window, (0, 0, width, height), border_radius=height // 2)
    draw.rect(surface, palette.border, (0, 0, width, height), width=1, border_radius=height // 2)
    inset = max(3, home.width // 16)
    button = (
        home.x + inset,
        home.y + inset,
        max(1, home.width - inset * 2),
        max(1, home.height - inset * 2),
    )
    draw.ellipse(surface, palette.button, button)
    draw.ellipse(surface, palette.outline, button, width=3)

    cx, cy = home.x + home.width // 2, home.y + home.height // 2
    scale = min(home.width, home.height) / 48.0
    chimney = (cx + int(6 * scale), cy - int(16 * scale), max(3, int(5 * scale)), max(5, int(9 * scale)))
    draw.rect(surface, palette.outline, chimney)
    roof_base_y = cy - int(1 * scale)
    roof = (
        (cx, cy - int(14 * scale)),
        (cx + int(16 * scale), roof_base_y),
        (cx - int(16 * scale), roof_base_y),
    )
    draw.polygon(surface, palette.outline, roof)
    body_x, body_y = cx - int(12 * scale), cy - int(2 * scale)
    body_w, body_h = int(24 * scale), int(16 * scale)
    draw.rect(surface, palette.outline, (body_x, body_y, body_w, body_h))
    door_w, door_h = max(6, int(8 * scale)), max(8, int(11 * scale))
    door_x, door_y = cx - door_w // 2, body_y + body_h - door_h
    draw.rect(surface, palette.door, (door_x, door_y + door_w // 2, door_w, door_h - door_w // 2))
    draw.ellipse(surface, palette.door, (door_x, door_y, door_w, door_w))
    draw.circle(surface, palette.window, (cx, cy - int(4 * scale)), max(2, int(3.2 * scale)))


def _rgb(value: int) -> RGB:
    return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)


__all__ = ["HomeChromePalette", "paint_home_chrome_picture"]
