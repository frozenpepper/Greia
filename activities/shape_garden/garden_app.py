"""Shape Garden — lifecycle coordinator.

Owns the screen/canvas/metrics/typography, model and renderer. Handles
semantic input routing, per-frame simulation and READY lifecycle (after
first flip in same loop). Domain truth lives in :mod:`garden_model`;
presentation caching lives in :mod:`garden_renderer`.
"""

from __future__ import annotations

import math
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, get_theme, mark_activity_ready
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface

if __package__:
    from .garden_content import COLORS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SOIL_TOP
    from .garden_model import GardenModel, Particle, PlacedShape
    from .garden_renderer import GardenRenderer, draw_shape, draw_sprout_stem
else:
    from garden_content import COLORS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SOIL_TOP
    from garden_model import GardenModel, Particle, PlacedShape
    from garden_renderer import GardenRenderer, draw_shape, draw_sprout_stem


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    # Legacy helper: also enforce safe_ui_rect containment used by original.
    safe = viewport.safe_ui_rect()
    return safe.x <= x < safe.right and safe.y <= y < safe.bottom


class GardenApp:
    """Coordinate Shape Garden lifecycle without owning raw drawing."""

    def __init__(self, screen: pygame.Surface | None = None) -> None:
        pygame.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.screen: pygame.Surface = screen
        self.theme = get_theme()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.renderer = GardenRenderer()
        self.model = GardenModel()
        self.clock = pygame.time.Clock()
        self.running = True
        self._ready_published = False
        self.start_time = time.monotonic()

    # -- input ------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
            self.canvas = PygameReferenceCanvas(self.screen)
            self.renderer.invalidate()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_pointer(event.pos)

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _safe_point(self.screen, screen_pos):
            return
        logical = self.canvas.pointer(screen_pos)
        if logical is None:
            return
        x, y = (int(round(logical[0])), int(round(logical[1])))
        if 0 <= x < REFERENCE_WIDTH and 0 <= y < SOIL_TOP:
            now = time.monotonic()
            color_idx = random.randrange(len(COLORS))
            self.model.add_shape(
                PlacedShape(
                    x=x,
                    y=y,
                    size=random.randint(22, 46),
                    kind=random.randrange(3),
                    color_index=color_idx,
                    spawn_time=now,
                )
            )
            self.model.trigger_reaction(now)
            c = COLORS[color_idx]
            particles: list[Particle] = []
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
            self.model.add_particles(particles)

    # -- per-frame --------------------------------------------------

    def _step_frame(self, now: float) -> None:
        self.model.update_particles(now)

    def _draw(self, now: float, elapsed: float) -> None:
        # Companion state derived from model reaction.
        if self.model.is_reacting(now):
            companion_state = "happy"
            companion_motion = "happy_hop"
        else:
            companion_state = "neutral"
            companion_motion = "idle_bounce"

        # 1. Sky gradient (baked)
        self.renderer.draw_sky(self.canvas.surface)

        # 2. Environment scene & companion
        self.renderer.draw_backdrop(
            self.canvas.surface, elapsed, companion_state, companion_motion
        )

        # 3. Soil bed
        self.renderer.draw_soil(self.canvas.surface, self.theme.accent)

        # 4. Shapes — stems, shadows, bodies
        active_shapes = self.model.active_shapes()
        for shape in active_shapes:
            draw_sprout_stem(self.canvas.surface, shape.x, shape.y, shape.size)
        for shape in active_shapes:
            self.renderer.draw_shape_shadow(self.canvas.surface, shape.x, shape.y, shape.size)
        for shape in active_shapes:
            age = now - shape.spawn_time
            scale = 1.0
            if age < 0.15:
                p = age / 0.15
                scale = 0.5 + 0.65 * math.sin(p * math.pi * 0.8)
            draw_shape(
                self.canvas.surface,
                shape.x,
                shape.y,
                shape.size,
                shape.kind,
                COLORS[shape.color_index],
                scale=scale,
            )

        # 5. Particles — drawn with fading radius
        for pt in self.model.particles:
            p_age = now - pt.birth_time
            # Lifetime already culled in update; compute visual radius.
            alpha_factor = max(0.0, 1.0 - (p_age / pt.lifetime)) if pt.lifetime > 0 else 0.0
            radius = max(2, int(round(4 * alpha_factor)))
            pygame.draw.circle(
                self.canvas.surface,
                pt.color,
                (int(round(pt.x)), int(round(pt.y))),
                radius,
            )

        self.canvas.present(clear=self.theme.background)

    # -- main loop --------------------------------------------------

    def run(self) -> int:
        while self.running and not activity_stop_requested():
            now = time.monotonic()
            elapsed = now - self.start_time
            for event in pygame.event.get():
                self.handle_event(event)
            self._step_frame(now)
            self._draw(now, elapsed)
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
            self.clock.tick(30)
        return 0


__all__ = ["GardenApp"]
