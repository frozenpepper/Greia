"""Planet art helpers for Encyclopedia.

Owns tiny procedural planet decoration used by the live Solar System.
For authored build-time sprites (Earth), the runtime PNG path is owned by
VisualLibrary/ build pipeline, not this module. This file only owns the
small per-frame primitive accents that keep the 8px planets readable without
requiring a full sprite sheet.

No per-frame file IO, no SVG, bounded work.
"""

from __future__ import annotations

import pygame


def decorate_planet(
    surface: pygame.Surface,
    planet_id: str,
    center: tuple[int, int],
    size: int,
    base_color: tuple[int, int, int],
    time: float = 0.0,
) -> None:
    """Add tiny recognizable markings so the Solar System reads without labels."""

    cx, cy = center
    if planet_id == "earth":
        land = (96, 168, 92)
        pygame.draw.ellipse(surface, land, (cx - 3, cy - 4, 6, 4))
        pygame.draw.ellipse(surface, land, (cx + 1, cy + 1, 4, 3))
        pygame.draw.ellipse(surface, (235, 245, 250), (cx - 4, cy - size + 1, 7, 3))
        pygame.draw.ellipse(surface, (215, 235, 245), (cx - 2, cy - 1, 4, 2))
    elif planet_id == "jupiter":
        band_dark = (170, 128, 92)
        band_light = (228, 200, 148)
        pygame.draw.ellipse(surface, band_light, (cx - size + 2, cy - 3, (size - 2) * 2, 4))
        pygame.draw.ellipse(surface, band_dark, (cx - size + 1, cy + 1, (size - 1) * 2, 3))
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
        pygame.draw.ellipse(surface, (235, 215, 165), (cx - size + 2, cy - 1, (size - 2) * 2, 2))
    elif planet_id == "mercury":
        pygame.draw.circle(surface, (130, 120, 110), (cx + 1, cy + 1), 1)
        pygame.draw.circle(surface, (150, 138, 122), (cx - 1, cy - 1), 1)
    elif planet_id == "uranus":
        pygame.draw.ellipse(surface, (125, 190, 195), (cx - 2, cy - size + 1, 4, 6))
    elif planet_id == "neptune":
        pygame.draw.ellipse(surface, (62, 92, 165), (cx - 3, cy - 1, 6, 3))
