from __future__ import annotations

import math
from pathlib import Path
import random
from typing import Any

import pygame

ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

_IMAGE_CACHE: dict[str, pygame.Surface | None] = {}
_SCALE_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_FLIP_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_PORTAL_FRAMES_CACHE: dict[int, list[pygame.Surface]] = {}
_PARTICLE_SURF_CACHE: dict[tuple[int, int, int, int], pygame.Surface] = {}


def load_asset_surface(filename: str) -> pygame.Surface | None:
    if filename not in _IMAGE_CACHE:
        p = ASSETS_DIR / filename
        if p.exists():
            try:
                _IMAGE_CACHE[filename] = pygame.image.load(str(p)).convert_alpha()
            except Exception:
                _IMAGE_CACHE[filename] = None
        else:
            _IMAGE_CACHE[filename] = None
    return _IMAGE_CACHE[filename]


def get_scaled_asset(filename: str, width: int, height: int) -> pygame.Surface | None:
    width = max(1, int(width))
    height = max(1, int(height))
    key = (filename, width, height)
    if key not in _SCALE_CACHE:
        orig = load_asset_surface(filename)
        if orig is not None:
            _SCALE_CACHE[key] = pygame.transform.smoothscale(orig, (width, height))
        else:
            _SCALE_CACHE[key] = None
    return _SCALE_CACHE[key]


def get_flipped_asset(filename: str, width: int, height: int) -> pygame.Surface | None:
    width = max(1, int(width))
    height = max(1, int(height))
    key = (filename, width, height)
    if key not in _FLIP_CACHE:
        base = get_scaled_asset(filename, width, height)
        if base is not None:
            _FLIP_CACHE[key] = pygame.transform.flip(base, True, False)
        else:
            _FLIP_CACHE[key] = None
    return _FLIP_CACHE[key]


def get_portal_rotation_frames(size: int, num_frames: int = 16) -> list[pygame.Surface]:
    size = max(16, int(size))
    if size not in _PORTAL_FRAMES_CACHE:
        base = get_scaled_asset("portal_goal.png", size, size)
        frames: list[pygame.Surface] = []
        if base is not None:
            for i in range(num_frames):
                angle = (360.0 / num_frames) * i
                rot = pygame.transform.rotate(base, angle)
                frames.append(rot)
        else:
            # Procedural fallback frames
            for i in range(num_frames):
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(surf, (168, 85, 247), (size // 2, size // 2), size // 2)
                pygame.draw.circle(surf, (254, 240, 138), (size // 2, size // 2), size // 3)
                frames.append(surf)
        _PORTAL_FRAMES_CACHE[size] = frames
    return _PORTAL_FRAMES_CACHE[size]


def get_particle_surface(color: tuple[int, int, int], alpha: int, radius: int) -> pygame.Surface:
    alpha = max(0, min(255, int(alpha)))
    radius = max(1, int(radius))
    key = (*color, alpha, radius)
    if key not in _PARTICLE_SURF_CACHE:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius)
        _PARTICLE_SURF_CACHE[key] = surf
    return _PARTICLE_SURF_CACHE[key]


class MazeArt:
    @staticmethod
    def bake_static_maze(
        grid: list[list[int]],
        biome: dict[str, Any],
        cs: int,
        maze_w: int,
        maze_h: int,
    ) -> pygame.Surface:
        """Bake the entire static maze grid and wall shadows into an opaque surface."""
        surf_w = maze_w * cs
        surf_h = maze_h * cs
        surf = pygame.Surface((surf_w, surf_h))
        surf.fill(biome["bg"])

        for r in range(maze_h):
            for c in range(maze_w):
                rx = c * cs
                ry = r * cs
                cell_rect = pygame.Rect(rx, ry, cs, cs)

                if grid[r][c] == 1:
                    # 3D Wall Shadow & Body
                    pygame.draw.rect(surf, biome["wall_shadow"], cell_rect)
                    margin = max(1, cs // 10)
                    wall_inner = pygame.Rect(
                        rx + margin,
                        ry + margin,
                        max(2, cs - margin * 2),
                        max(2, cs - margin * 2),
                    )
                    pygame.draw.rect(
                        surf,
                        biome["wall"],
                        wall_inner,
                        border_radius=max(1, cs // 6),
                    )
                    top_h = max(1, cs // 4)
                    if cs >= 8:
                        pygame.draw.rect(
                            surf,
                            biome["wall_top"],
                            (
                                rx + margin + 1,
                                ry + margin + 1,
                                max(2, cs - (margin + 1) * 2),
                                top_h,
                            ),
                            border_radius=max(1, cs // 8),
                        )
                else:
                    # Open corridor floor
                    pygame.draw.rect(surf, biome["path"], cell_rect)
                    if cs >= 12:
                        dot_r = max(1, cs // 10)
                        pygame.draw.circle(
                            surf,
                            biome["bg"],
                            (rx + cs // 2, ry + cs // 2),
                            dot_r,
                        )

        return surf

    @staticmethod
    def init_ambient_particles(width: int, height: int, count: int = 15) -> list[dict[str, Any]]:
        particles: list[dict[str, Any]] = []
        for _ in range(count):
            particles.append({
                "x": random.uniform(20, width - 20),
                "y": random.uniform(20, height - 20),
                "vx": random.uniform(-0.4, 0.4),
                "vy": random.uniform(-0.5, -0.1),
                "size": random.randint(2, 4),
                "alpha": random.choice([80, 120, 160]),
            })
        return particles

    @staticmethod
    def update_ambient_particles(
        particles: list[dict[str, Any]],
        width: int,
        height: int,
    ) -> None:
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < 10:
                p["y"] = height - 10
                p["x"] = random.uniform(20, width - 20)
            elif p["x"] < 10:
                p["x"] = width - 10
            elif p["x"] > width - 10:
                p["x"] = 10

    @staticmethod
    def create_star_burst(x: float, y: float, color: tuple[int, int, int] = (254, 240, 138), count: int = 10) -> list[dict[str, Any]]:
        burst: list[dict[str, Any]] = []
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1.5, 4.0)
            burst.append({
                "x": x,
                "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "color": color,
                "size": random.uniform(4, 8),
            })
        return burst

    @staticmethod
    def update_celebration_particles(particles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        surviving: list[dict[str, Any]] = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["size"] = max(0.0, p["size"] - 0.25)
            if p["size"] > 1.0:
                surviving.append(p)
        return surviving
