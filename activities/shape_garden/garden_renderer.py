"""Shape Garden — rendering helpers and bounded caches.

Owns draw helpers, text-free phrasing and image caches. The shared
shadow is decoded once, converted, and reused via a bounded LRU cache
keyed by scaled size. Sky gradient is baked once and invalidated on
viewport resize. No storage or Greia event IO; per-frame work stays
bounded.
"""

from __future__ import annotations

import math
import random

import pygame

from greia_platform.activity_ui import mix
from greia_platform.pygame_scene import PygameSceneRenderer
from greia_platform.scene import SceneDefinition, SceneNode
from greia_platform.scene_actor import SceneActorDefinition

if __package__:
    from .garden_content import (
        COLORS,
        LEAF_COLOR,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_TOP,
        STEM_COLOR,
    )
else:
    from garden_content import (
        COLORS,
        LEAF_COLOR,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_TOP,
        STEM_COLOR,
    )

_MAX_SHADOW_CACHE = 32
_MAX_SKY_CACHE = 1  # single sky surface


def _load_shared_shape_shadow() -> pygame.Surface | None:
    """Load optional semantic Greia visual once for the Activity process."""
    try:
        from greia_platform.activity_api import get_shared_visual_path

        path = get_shared_visual_path("ui.shadow.soft")
        return pygame.image.load(str(path)).convert_alpha()
    except (OSError, ValueError, pygame.error):
        return None


def _build_backdrop_scene(actor_node: SceneNode, shadow_node: SceneNode | None) -> SceneDefinition:
    nodes: list[SceneNode] = [
        SceneNode(
            node_id="hills",
            asset_id="hills.distant.01",
            rect=(0, SOIL_TOP - 220, 1024, 256),
            z=5,
            optional=True,
        ),
        SceneNode(
            node_id="cloud_large",
            asset_id="cloud.large.01",
            rect=(140, 50, 180, 72),
            z=8,
            optional=True,
        ),
        SceneNode(
            node_id="cloud_small",
            asset_id="cloud.small.01",
            rect=(700, 90, 130, 56),
            z=8,
            optional=True,
        ),
        SceneNode(
            node_id="sunlight",
            asset_id="atmosphere.sunlight_rays.01",
            rect=(624, 0, 400, 240),
            z=12,
            optional=True,
        ),
        SceneNode(
            node_id="grass_edge",
            asset_id="ground.grass_edge.01",
            rect=(0, SOIL_TOP - 125, 1024, 180),
            z=20,
            optional=True,
        ),
        SceneNode(
            node_id="left_bush",
            asset_id="bush.flowering.01",
            rect=(-20, SOIL_TOP - 65, 120, 90),
            z=25,
            optional=True,
        ),
    ]
    if shadow_node is not None:
        nodes.append(shadow_node)
    nodes.append(actor_node)
    return SceneDefinition(
        scene_id="shape_garden_backdrop",
        canvas_size=(REFERENCE_WIDTH, REFERENCE_HEIGHT),
        background=(212, 234, 248),
        nodes=tuple(nodes),
    )


def draw_soil_bed(surface: pygame.Surface, accent_color: tuple[int, int, int]) -> None:
    soil_color = mix((138, 92, 52), accent_color, 0.08)
    soil_dark = mix((112, 70, 36), accent_color, 0.08)
    pygame.draw.rect(
        surface,
        soil_color,
        (0, SOIL_TOP, REFERENCE_WIDTH, REFERENCE_HEIGHT - SOIL_TOP),
    )
    pygame.draw.rect(
        surface,
        soil_dark,
        (0, SOIL_TOP + 45, REFERENCE_WIDTH, REFERENCE_HEIGHT - SOIL_TOP - 45),
    )
    rng = random.Random(42)
    for _ in range(35):
        px = rng.randint(10, REFERENCE_WIDTH - 10)
        py = rng.randint(SOIL_TOP + 6, REFERENCE_HEIGHT - 6)
        pr = rng.randint(2, 4)
        pclr = (155, 110, 68) if rng.random() > 0.5 else (98, 58, 28)
        pygame.draw.circle(surface, pclr, (px, py), pr)


def draw_sprout_stem(surface: pygame.Surface, x: int, y: int, size: int) -> None:
    if y < 180:
        return
    bottom_y = y + size
    target_y = SOIL_TOP + 4
    if bottom_y >= target_y:
        return
    stem_width = max(3, size // 8)
    pygame.draw.line(surface, STEM_COLOR, (x, bottom_y), (x, target_y), width=stem_width)
    mid_y = (bottom_y + target_y) // 2
    leaf_w = max(6, size // 4)
    leaf_h = max(4, size // 6)
    pygame.draw.ellipse(
        surface,
        LEAF_COLOR,
        (x - leaf_w - stem_width // 2, mid_y - leaf_h, leaf_w, leaf_h),
    )
    pygame.draw.ellipse(
        surface,
        LEAF_COLOR,
        (x + stem_width // 2, mid_y - leaf_h - 2, leaf_w, leaf_h),
    )


def draw_shape(
    surface: pygame.Surface,
    x: int,
    y: int,
    size: int,
    kind: int,
    color: tuple[int, int, int],
    scale: float = 1.0,
) -> None:
    eff_size = max(4, int(round(size * scale)))
    if kind == 0:
        pygame.draw.circle(surface, color, (x, y), eff_size)
        hl = (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40))
        pygame.draw.circle(surface, hl, (x - eff_size // 3, y - eff_size // 3), max(2, eff_size // 4))
    elif kind == 1:
        rect = pygame.Rect(x - eff_size, y - eff_size, eff_size * 2, eff_size * 2)
        pygame.draw.rect(surface, color, rect, border_radius=max(4, eff_size // 4))
        hl_rect = pygame.Rect(x - eff_size + 4, y - eff_size + 4, max(4, eff_size * 2 - 8), max(3, eff_size // 3))
        hl = (min(255, color[0] + 35), min(255, color[1] + 35), min(255, color[2] + 35))
        pygame.draw.rect(surface, hl, hl_rect, border_radius=max(2, eff_size // 6))
    else:
        points = []
        for index in range(5):
            angle = math.radians(-90 + index * 72)
            points.append(
                (
                    x + int(math.cos(angle) * eff_size),
                    y + int(math.sin(angle) * eff_size),
                )
            )
        pygame.draw.polygon(surface, color, points)


class GardenRenderer:
    """Own Shape Garden presentation and bounded transient caches.

    The shared shadow is decoded/converted once. Scaled shadow variants
    are cached in a bounded LRU (≤32 entries) so per-frame shadow work
    does not re-decode or re-scale. Sky gradient is baked once onto an
    opaque surface and invalidated on viewport resize.
    """

    def __init__(self) -> None:
        self._shared_shadow = _load_shared_shape_shadow()
        self._shadow_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._shadow_order: list[tuple[int, int]] = []
        self._sky_surface: pygame.Surface | None = None
        self._scene_renderer = PygameSceneRenderer.for_activity()
        # Companion actor kept here so scene composition stays in renderer.
        self._companion_actor = SceneActorDefinition(
            actor_id="dani_companion",
            asset_id="character.dani",
            rect=(872, SOIL_TOP - 68, 96, 96),
            shadow_asset_id="shadow.contact.small.01",
            shadow_rect=(878, SOIL_TOP + 18, 84, 24),
            state="neutral",
            motion="idle_bounce",
            z=35,
        )

    # -- lifecycle --------------------------------------------------

    def invalidate(self) -> None:
        """Clear viewport-dependent caches after a VIDEORESIZE."""
        self._shadow_cache.clear()
        self._shadow_order.clear()
        self._sky_surface = None

    # -- cached resources -------------------------------------------

    def _ensure_sky(self) -> pygame.Surface:
        if self._sky_surface is not None:
            return self._sky_surface
        surface = pygame.Surface((REFERENCE_WIDTH, SOIL_TOP))
        sky_top = (212, 234, 248)
        sky_bottom = (236, 246, 240)
        for y in range(SOIL_TOP):
            ratio = y / SOIL_TOP
            r = int(sky_top[0] * (1 - ratio) + sky_bottom[0] * ratio)
            g = int(sky_top[1] * (1 - ratio) + sky_bottom[1] * ratio)
            b = int(sky_top[2] * (1 - ratio) + sky_bottom[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (REFERENCE_WIDTH, y))
        # Convert once for fast blitting; requires initialized display.
        try:
            surface = surface.convert()
        except pygame.error:
            pass
        self._sky_surface = surface
        return surface

    def _scaled_shadow(self, shadow_w: int, shadow_h: int) -> pygame.Surface | None:
        if self._shared_shadow is None:
            return None
        key = (shadow_w, shadow_h)
        cached = self._shadow_cache.get(key)
        if cached is not None:
            return cached
        try:
            scaled = pygame.transform.smoothscale(self._shared_shadow, (shadow_w, shadow_h))
        except pygame.error:
            return None
        if len(self._shadow_cache) >= _MAX_SHADOW_CACHE:
            oldest = self._shadow_order.pop(0)
            self._shadow_cache.pop(oldest, None)
        self._shadow_cache[key] = scaled
        self._shadow_order.append(key)
        return scaled

    # -- draw helpers -----------------------------------------------

    def draw_sky(self, target: pygame.Surface) -> None:
        target.blit(self._ensure_sky(), (0, 0))

    def draw_shape_shadow(self, target: pygame.Surface, x: int, y: int, size: int) -> None:
        if self._shared_shadow is None:
            return
        center_y = y + max(8, int(round(size * 0.65)))
        shadow_w = max(16, int(size * 1.8))
        shadow_h = max(8, int(size * 0.55))
        scaled = self._scaled_shadow(shadow_w, shadow_h)
        if scaled is None:
            return
        target.blit(scaled, scaled.get_rect(center=(x, center_y)))

    def draw_soil(self, target: pygame.Surface, accent_color: tuple[int, int, int]) -> None:
        draw_soil_bed(target, accent_color)

    # -- scene ------------------------------------------------------

    def draw_backdrop(
        self,
        target: pygame.Surface,
        elapsed: float,
        companion_state: str,
        companion_motion: str,
    ) -> None:
        from greia_platform.scene_actor import sample_scene_actor

        actor_sample = sample_scene_actor(
            self._companion_actor,
            elapsed_seconds=elapsed,
            motion_enabled=True,
            state=companion_state,
            motion=companion_motion,
        )
        body_node, shadow_node = actor_sample.nodes
        backdrop_scene = _build_backdrop_scene(body_node, shadow_node)
        self._scene_renderer.draw(
            backdrop_scene,
            target,
            elapsed_seconds=elapsed,
            motion_enabled=True,
            clear=False,
        )


__all__ = [
    "GardenRenderer",
    "draw_shape",
    "draw_soil_bed",
    "draw_sprout_stem",
]
