"""Main application coordinator and event loop for Corsa delle Bacche."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Final

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_theme,
    mark_activity_ready,
)
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)

try:
    from corsa_audio import CorsaAudio
    from corsa_content import (
        COLOR_BG_GARDEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Direction,
    )
    from corsa_model import CorsaModel
    from corsa_renderer import CorsaRenderer
except ImportError:
    from .corsa_audio import CorsaAudio
    from .corsa_content import (
        COLOR_BG_GARDEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Direction,
    )
    from .corsa_model import CorsaModel
    from .corsa_renderer import CorsaRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Return True if position is within bounds and outside protected Greia system chrome."""
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class CorsaApp:
    """Coordinates lifecycle, input routing, simulation, and presentation."""

    def __init__(self, screen: pygame.Surface | None = None, locale: str = "it") -> None:
        if screen is None:
            if not pygame.get_init():
                pygame.init()
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode(
                    (REFERENCE_WIDTH, REFERENCE_HEIGHT),
                    pygame.RESIZABLE,
                )

        self.screen: pygame.Surface = screen
        self.canvas: PygameReferenceCanvas = PygameReferenceCanvas(self.screen)
        pygame.mouse.set_visible(True)

        self.model: CorsaModel = CorsaModel()
        self.renderer: CorsaRenderer = CorsaRenderer()
        self.audio: CorsaAudio = CorsaAudio()

        self._active_locale: str = locale
        self._resources: LocalizedResources | None = None
        self._init_localization(locale)

        self.running: bool = True
        self.ready_published: bool = False
        self._level_clear_timer: float = 0.0

    def _init_localization(self, preferred_locale: str) -> None:
        pkg_root = Path(__file__).parent
        try:
            support = ActivityLocaleSupport.load(pkg_root / "locales")
            self._resources = support.resources_for(preferred_locale)
        except Exception:
            self._resources = None

    def run(self) -> int:
        """Main game loop ticking at 60 FPS."""
        clock = pygame.time.Clock()
        self.running = True
        last_time = time.monotonic()

        while self.running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, max(0.001, now - last_time))
            last_time = now

            # 1. Event Routing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.model.request_direction(Direction.UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.model.request_direction(Direction.DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.model.request_direction(Direction.LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.model.request_direction(Direction.RIGHT)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        if self.model.level_complete:
                            self.model.next_level()
                            self._level_clear_timer = 0.0
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.canvas = PygameReferenceCanvas(self.screen)
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                    if pygame.mouse.get_pressed()[0]:
                        self._handle_pointer_motion(event.pos)
                elif event.type == pygame.JOYHATMOTION:
                    hx, hy = event.value
                    if hy == 1:
                        self.model.request_direction(Direction.UP)
                    elif hy == -1:
                        self.model.request_direction(Direction.DOWN)
                    elif hx == -1:
                        self.model.request_direction(Direction.LEFT)
                    elif hx == 1:
                        self.model.request_direction(Direction.RIGHT)
                elif event.type == pygame.JOYAXISMOTION:
                    if event.axis == 0:  # X axis
                        if event.value < -0.5:
                            self.model.request_direction(Direction.LEFT)
                        elif event.value > 0.5:
                            self.model.request_direction(Direction.RIGHT)
                    elif event.axis == 1:  # Y axis
                        if event.value < -0.5:
                            self.model.request_direction(Direction.UP)
                        elif event.value > 0.5:
                            self.model.request_direction(Direction.DOWN)

            # Continuous Keyboard Steering
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.model.request_direction(Direction.UP)
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.model.request_direction(Direction.DOWN)
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.model.request_direction(Direction.LEFT)
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.model.request_direction(Direction.RIGHT)

            # 2. Advance Simulation
            events = self.model.update(dt)
            for ev in events:
                if ev == "pop":
                    self.audio.play("pop")
                    try:
                        emit_activity_event("berry.collected")
                    except Exception:
                        pass
                elif ev == "chime":
                    self.audio.play("chime")
                elif ev == "star_fanfare":
                    self.audio.play("star_fanfare")
                    try:
                        emit_activity_event("rainbow_star.activated")
                    except Exception:
                        pass
                elif ev == "dizzy_squeak":
                    self.audio.play("dizzy_squeak")
                    try:
                        emit_activity_event("critter.gentle_rescue")
                    except Exception:
                        pass
                elif ev == "bounce":
                    self.audio.play("bounce")
                elif ev == "apple_munch":
                    self.audio.play("apple_munch")
                elif ev == "level_clear":
                    self.audio.play("level_clear")
                    self._level_clear_timer = 0.0
                    try:
                        emit_activity_event("maze.level_completed")
                    except Exception:
                        pass

            # 3. Handle Level Progression Delay
            if self.model.level_complete:
                self._level_clear_timer += dt
                if self._level_clear_timer >= 2.2:
                    self.model.next_level()
                    self._level_clear_timer = 0.0

            # 4. Render Frame onto Reference Canvas
            self.renderer.render(self.canvas.surface, self.model, dt)

            # 5. Present Canvas to Physical Screen
            self.canvas.present(clear=COLOR_BG_GARDEN)
            pygame.display.flip()

            # Mark ready after first display flip
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True

            clock.tick(60)

        pygame.quit()
        return 0

    def _handle_pointer_motion(self, pos: tuple[int, int]) -> None:
        """Route mouse click/drag or touch swipe towards target cell relative to Momo."""
        if not _is_safe_point(self.screen, pos):
            return
        logical = self.canvas.pointer(pos)
        if logical is None:
            return

        lx, ly = logical
        dx = lx - self.model.player.x
        dy = ly - self.model.player.y

        # Dead-zone around Momo to avoid jitters
        if math_hypot := (dx * dx + dy * dy):
            if math_hypot < 100:  # < 10px radius
                return

        if abs(dx) > abs(dy):
            self.model.request_direction(Direction.RIGHT if dx > 0 else Direction.LEFT)
        else:
            self.model.request_direction(Direction.DOWN if dy > 0 else Direction.UP)


def build_app(screen: pygame.Surface | None = None, locale: str = "it") -> CorsaApp:
    """Factory function for CorsaApp."""
    return CorsaApp(screen=screen, locale=locale)
