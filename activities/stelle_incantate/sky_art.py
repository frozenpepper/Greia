"""Procedural artwork for the Stelle Incantate night sky.

Everything is drawn once into cached surfaces: the backdrop is one opaque
surface rebuilt only when the logical size changes, and the reusable star
sprite keeps per-frame cost to cheap blits on Atom-class hardware.
"""

from __future__ import annotations

import math
import random
from typing import Final

import pygame


_SKY_TOP: Final[tuple[int, int, int]] = (10, 16, 46)
_SKY_BOTTOM: Final[tuple[int, int, int]] = (36, 34, 88)
_HILLS_COLOR: Final[tuple[int, int, int]] = (16, 20, 48)
_HILLS_FRONT: Final[tuple[int, int, int]] = (11, 14, 38)
_MOON_COLOR: Final[tuple[int, int, int]] = (246, 243, 224)
_MOON_CRATER: Final[tuple[int, int, int]] = (222, 218, 196)

#: Deterministic background star field (normalized positions + brightness).
_BACKGROUND_STARS: Final[tuple[tuple[float, float, int], ...]] = tuple(
    (random.Random(seed).random(), random.Random(seed + 4096).random(), 90 + seed % 120)
    for seed in range(90)
)


def build_backdrop(width: int, height: int) -> pygame.Surface:
    """Build the opaque night-sky backdrop for one logical size."""

    width = max(1, width)
    height = max(1, height)
    backdrop = pygame.Surface((width, height))

    # Vertical dusk-to-night gradient, drawn in bounded horizontal bands.
    band_height = max(2, height // 64)
    for top in range(0, height, band_height):
        progress = min(1.0, top / max(1, height - 1))
        color = tuple(
            round(top_c + (bottom_c - top_c) * progress)
            for top_c, bottom_c in zip(_SKY_TOP, _SKY_BOTTOM)
        )
        pygame.draw.rect(
            backdrop,
            color,
            pygame.Rect(0, top, width, band_height),
        )

    # Fixed distant star field.
    for nx, ny, brightness in _BACKGROUND_STARS:
        x = int(nx * width)
        y = int(ny * height * 0.82)
        size = 2 if brightness > 150 else 1
        shade = 120 + brightness // 3
        backdrop.fill((shade, shade, min(255, shade + 30)), (x, y, size, size))

    # Calm moon in the upper right.
    moon_radius = max(18, height // 22)
    moon_center = (int(width * 0.86), int(height * 0.16))
    pygame.draw.circle(backdrop, _MOON_COLOR, moon_center, moon_radius)
    pygame.draw.circle(backdrop, _MOON_CRATER, moon_center, moon_radius, width=2)
    crater_radius = max(2, moon_radius // 5)
    for dx, dy in ((-0.3, -0.2), (0.25, 0.1), (-0.05, 0.4)):
        crater = (
            int(moon_center[0] + dx * moon_radius),
            int(moon_center[1] + dy * moon_radius),
        )
        pygame.draw.circle(backdrop, _MOON_CRATER, crater, crater_radius)

    # Layered sleeping hills along the bottom.
    horizon = int(height * 0.86)
    hills = pygame.Surface((width, height - horizon), pygame.SRCALPHA)
    points_back = _hill_points(width, height - horizon, 6, 0.45, seed=7)
    pygame.draw.polygon(hills, (*_HILLS_COLOR, 255), points_back)
    backdrop.blit(hills, (0, horizon))

    front_top = int(height * 0.92)
    front = pygame.Surface((width, height - front_top), pygame.SRCALPHA)
    points_front = _hill_points(width, height - front_top, 4, 0.6, seed=13)
    pygame.draw.polygon(front, (*_HILLS_FRONT, 255), points_front)
    backdrop.blit(front, (0, front_top))

    # A few tiny pine silhouettes on the front hill line.
    tree_height = max(16, height // 22)
    for nx in (0.08, 0.16, 0.90, 0.96):
        base_x = int(nx * width)
        base_y = front_top + int(height * 0.02)
        pygame.draw.polygon(
            backdrop,
            _HILLS_FRONT,
            (
                (base_x, base_y - tree_height),
                (base_x - tree_height // 3, base_y),
                (base_x + tree_height // 3, base_y),
            ),
        )
    return backdrop


def _hill_points(
    width: int,
    hill_height: int,
    bumps: int,
    depth: float,
    *,
    seed: int,
) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    points: list[tuple[float, float]] = [(0.0, float(hill_height))]
    steps = bumps * 2
    for step in range(1, steps + 1):
        x = width * step / steps
        peak = (step % 2 == 1)
        y = hill_height - (hill_height * depth * (0.5 + 0.5 * rng.random()) if peak else hill_height * 0.15)
        points.append((x, max(2.0, y)))
    points.append((float(width), float(hill_height)))
    return [(round(x), round(y)) for x, y in points]


def build_star_sprite(radius: int, color: tuple[int, int, int] = (255, 244, 214)) -> pygame.Surface:
    """Build one soft glowing four-point star sprite with alpha halo."""

    radius = max(4, radius)
    size = radius * 4
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    center = radius * 2

    # Wide soft halo.
    halo = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(
        halo,
        (color[0], color[1], color[2], 46),
        (center, center),
        radius * 2,
    )
    pygame.draw.circle(
        halo,
        (color[0], color[1], color[2], 70),
        (center, center),
        radius + 2,
    )
    sprite.blit(halo, (0, 0))

    # Four-point sparkle cross.
    points = []
    for direction in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        points.append(
            (
                center + direction[0] * radius * 2,
                center + direction[1] * radius * 2,
            )
        )
        points.append(
            (
                center + direction[0] * radius // 2 + direction[1] * radius // 3,
                center + direction[1] * radius // 2 + direction[0] * radius // 3,
            )
        )
        points.append(
            (
                center + direction[0] * radius // 2 - direction[1] * radius // 3,
                center + direction[1] * radius // 2 - direction[0] * radius // 3,
            )
        )
    pygame.draw.polygon(sprite, color, points)
    pygame.draw.circle(sprite, (255, 255, 255), (center, center), max(2, radius // 2))
    return sprite
