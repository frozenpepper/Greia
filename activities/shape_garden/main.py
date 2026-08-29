from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_shared_visual_path,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, mix
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_scene import PygameSceneRenderer
from greia_platform.scene import (
    SceneDefinition,
    SceneNode,
)
from greia_platform.scene_actor import (
    SceneActorDefinition,
    sample_scene_actor,
)

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
SOIL_TOP = 530

COLORS = (
    (247, 93, 89),   # Tomato Red
    (255, 190, 46),  # Sunflower Yellow
    (80, 188, 112),  # Meadow Green
    (67, 150, 222),  # Sky Blue
    (168, 105, 214), # Lilac Purple
)

STEM_COLOR = (74, 158, 88)
LEAF_COLOR = (102, 186, 115)


@dataclass(slots=True)
class PlacedShape:
    x: int
    y: int
    size: int
    kind: int
    color_index: int
    spawn_time: float


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    birth_time: float
    lifetime: float


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    safe = activity_viewport_for_surface(surface).safe_ui_rect()
    x, y = position
    return safe.x <= x < safe.right and safe.y <= y < safe.bottom


def _load_shared_shape_shadow() -> pygame.Surface | None:
    """Load optional semantic Greia visual once for the Activity process."""
    try:
        path = get_shared_visual_path("ui.shadow.soft")
        return pygame.image.load(str(path)).convert_alpha()
    except (OSError, ValueError, pygame.error):
        return None


def _build_backdrop_scene(actor_node: SceneNode, shadow_node: SceneNode | None) -> SceneDefinition:
    nodes: list[SceneNode] = [
        # 1. Distant Rolling Hills
        SceneNode(
            node_id="hills",
            asset_id="hills.distant.01",
            rect=(0, SOIL_TOP - 220, 1024, 256),
            z=5,
            optional=True,
        ),
        # 2. Soft Ambient Clouds
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
        # 3. Soft Sunlight Rays
        SceneNode(
            node_id="sunlight",
            asset_id="atmosphere.sunlight_rays.01",
            rect=(624, 0, 400, 240),
            z=12,
            optional=True,
        ),
        # 4. Modular Grass Boundary
        SceneNode(
            node_id="grass_edge",
            asset_id="ground.grass_edge.01",
            rect=(0, SOIL_TOP - 125, 1024, 180),
            z=20,
            optional=True,
        ),
        # 5. Botanical Corner Framing
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

    # Subtle soil texture pebbles
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


def draw_shape_shadow(
    surface: pygame.Surface,
    shadow: pygame.Surface | None,
    x: int,
    y: int,
    size: int,
) -> None:
    if shadow is None:
        return
    center_y = y + max(8, int(round(size * 0.65)))
    shadow_w = max(16, int(size * 1.8))
    shadow_h = max(8, int(size * 0.55))
    scaled_sh = pygame.transform.smoothscale(shadow, (shadow_w, shadow_h))
    surface.blit(scaled_sh, scaled_sh.get_rect(center=(x, center_y)))


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


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    renderer = PygameSceneRenderer.for_activity()
    shared_shape_shadow = _load_shared_shape_shadow()

    companion_actor = SceneActorDefinition(
        actor_id="dani_companion",
        asset_id="character.dani",
        rect=(872, SOIL_TOP - 68, 96, 96),
        shadow_asset_id="shadow.contact.small.01",
        shadow_rect=(878, SOIL_TOP + 18, 84, 24),
        state="neutral",
        motion="idle_bounce",
        z=35,
    )

    shapes: list[PlacedShape] = []
    particles: list[Particle] = []
    running = True
    ready_published = False
    start_time = time.monotonic()
    reaction_until = 0.0

    while running and not activity_stop_requested():
        now = time.monotonic()
        elapsed = now - start_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if not _safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                x, y = (int(round(logical[0])), int(round(logical[1])))
                if 0 <= x < REFERENCE_WIDTH and 0 <= y < SOIL_TOP:
                    color_idx = random.randrange(len(COLORS))
                    shapes.append(
                        PlacedShape(
                            x=x,
                            y=y,
                            size=random.randint(22, 46),
                            kind=random.randrange(3),
                            color_index=color_idx,
                            spawn_time=now,
                        )
                    )
                    # Trigger Dani companion delight reaction
                    reaction_until = now + 0.85

                    # Spawn playful sparkle particles
                    c = COLORS[color_idx]
                    for _ in range(5):
                        angle = random.uniform(0, math.tau)
                        spd = random.uniform(20.0, 60.0)
                        particles.append(
                            Particle(
                                x=float(x),
                                y=float(y),
                                vx=math.cos(angle) * spd,
                                vy=math.sin(angle) * spd - 30.0,
                                color=c,
                                birth_time=now,
                                lifetime=random.uniform(0.35, 0.65),
                            )
                        )

        # Determine companion state
        if now < reaction_until:
            companion_state = "happy"
            companion_motion = "happy_hop"
        else:
            companion_state = "neutral"
            companion_motion = "idle_bounce"

        actor_sample = sample_scene_actor(
            companion_actor,
            elapsed_seconds=elapsed,
            motion_enabled=True,
            state=companion_state,
            motion=companion_motion,
        )

        body_node, shadow_node = actor_sample.nodes
        backdrop_scene = _build_backdrop_scene(body_node, shadow_node)

        # 1. Sky Gradient Background
        sky_top = (212, 234, 248)
        sky_bottom = (236, 246, 240)
        for y in range(SOIL_TOP):
            ratio = y / SOIL_TOP
            r = int(sky_top[0] * (1 - ratio) + sky_bottom[0] * ratio)
            g = int(sky_top[1] * (1 - ratio) + sky_bottom[1] * ratio)
            b = int(sky_top[2] * (1 - ratio) + sky_bottom[2] * ratio)
            pygame.draw.line(canvas.surface, (r, g, b), (0, y), (REFERENCE_WIDTH, y))

        # 2. Draw Environment Scene & Companion
        renderer.draw(
            backdrop_scene,
            canvas.surface,
            elapsed_seconds=elapsed,
            motion_enabled=True,
            clear=False,
        )

        # 3. Rich Soil Bed
        draw_soil_bed(canvas.surface, theme.accent)

        # 4. Placed Shape Stems & Grounding
        active_shapes = shapes[-120:]
        for shape in active_shapes:
            draw_sprout_stem(canvas.surface, shape.x, shape.y, shape.size)

        for shape in active_shapes:
            draw_shape_shadow(
                canvas.surface,
                shared_shape_shadow,
                shape.x,
                shape.y,
                shape.size,
            )

        for shape in active_shapes:
            # Subtle growth spawn pulse
            age = now - shape.spawn_time
            scale = 1.0
            if age < 0.15:
                # 0.0 -> 0.15s: pop scale from 0.5 to 1.15 to 1.0
                p = age / 0.15
                scale = 0.5 + 0.65 * math.sin(p * math.pi * 0.8)

            draw_shape(
                canvas.surface,
                shape.x,
                shape.y,
                shape.size,
                shape.kind,
                COLORS[shape.color_index],
                scale=scale,
            )

        # 5. Active particles
        surviving_particles: list[Particle] = []
        dt = 1.0 / 30.0
        for pt in particles:
            p_age = now - pt.birth_time
            if p_age < pt.lifetime:
                pt.x += pt.vx * dt
                pt.y += pt.vy * dt
                pt.vy += 45.0 * dt  # Gentle gravity
                alpha_factor = max(0.0, 1.0 - (p_age / pt.lifetime))
                radius = max(2, int(round(4 * alpha_factor)))
                pygame.draw.circle(
                    canvas.surface,
                    pt.color,
                    (int(round(pt.x)), int(round(pt.y))),
                    radius,
                )
                surviving_particles.append(pt)
        particles = surviving_particles[-30:]

        canvas.present(clear=theme.background)
        pygame.display.flip()
        if not ready_published:
            mark_activity_ready()
            ready_published = True
        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
