"""Application coordinator, event loop, and lifecycle for Colline Allegre."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Final

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
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
from greia_platform.typography import GreiaTypography

if __package__:
    from .colline_audio import CollineAudio
    from .colline_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SYSTEM_CHROME_SAFE_X,
        SYSTEM_CHROME_SAFE_Y,
    )
    from .colline_model import CollineWorld
    from .colline_renderer import CollineRenderer
else:
    from colline_audio import CollineAudio
    from colline_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SYSTEM_CHROME_SAFE_X,
        SYSTEM_CHROME_SAFE_Y,
    )
    from colline_model import CollineWorld
    from colline_renderer import CollineRenderer

STORAGE_KEY: Final[str] = "colline_allegre.progress"


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Return True if point is not within the protected system chrome region."""
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class CollineApp:
    """Main application lifecycle and event router for Colline Allegre."""

    def __init__(self, screen: pygame.Surface | None = None, locale: str = "it") -> None:
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        pygame.mouse.set_visible(True)

        self.world = CollineWorld(difficulty=2)
        self.audio = CollineAudio()
        self.typography = GreiaTypography()
        self.renderer = CollineRenderer(self.typography)

        self._resources: LocalizedResources | None = None
        self._active_locale = locale
        self._init_localization()

        self._storage: Any = None
        self._best_distance: float = 0.0
        self._total_stars: int = 0
        self._load_storage()

        self.running = True
        self.ready_published = False

        # Input state
        self.gas_active = False
        self.brake_active = False
        self.tilt_axis = 0.0
        self._touch_gas = False
        self._touch_brake = False
        self._joy_gas = False
        self._joy_brake = False
        self._joy_tilt = 0.0

    def _init_localization(self) -> None:
        pkg_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale=self._active_locale)
        try:
            profile_lang = get_profile_locale()
            context = resolve_activity_locale(profile_lang, support)
            self._resources = LocalizedResources(pkg_root, context) if context else None
            self._active_locale = context.selected.language if context else self._active_locale
        except Exception:
            pass

    def _load_storage(self) -> None:
        try:
            self._storage = get_storage()
            if self._storage is not None:
                saved = self._storage.kv_get(STORAGE_KEY, {})
                if isinstance(saved, dict):
                    self._best_distance = float(saved.get("best_distance", 0.0))
                    self._total_stars = int(saved.get("total_stars", 0))
        except Exception:
            self._storage = None

    def _save_storage(self) -> None:
        if self._storage is None:
            return
        previous_best = self._best_distance
        current_best = max(previous_best, self.world.distance_traveled)
        try:
            self._storage.kv_set(
                STORAGE_KEY,
                {
                    "best_distance": current_best,
                    "total_stars": self._total_stars + self.world.stars_collected,
                    "timestamp": time.time(),
                },
            )
        except Exception:
            return
        self._best_distance = current_best
        if current_best > previous_best:
            try:
                emit_activity_event(
                    "colline.best_distance",
                    idempotency_key=f"best-distance-{int(round(current_best * 1000.0))}",
                    payload={"distance": current_best},
                    score=current_best,
                )
            except Exception:
                pass

    def _handle_pointer_down(self, pos: tuple[int, int]) -> None:
        if not _is_safe_point(self.screen, pos):
            return
        log_pt = self.canvas.pointer(pos)
        if log_pt is None:
            return
        lx, ly = int(log_pt[0]), int(log_pt[1])

        # Never process input under top-left system chrome boundary
        if lx < SYSTEM_CHROME_SAFE_X and ly < SYSTEM_CHROME_SAFE_Y:
            return

        if self.renderer.gas_pedal_rect.collidepoint(lx, ly):
            self._touch_gas = True
        elif self.renderer.brake_pedal_rect.collidepoint(lx, ly):
            self._touch_brake = True

    def _handle_pointer_up(self, pos: tuple[int, int]) -> None:
        self._touch_gas = False
        self._touch_brake = False

    def _route_events(self, model_events: list[str]) -> None:
        veh = self.world.vehicle
        for ev in model_events:
            if ev == "colline.star_collected":
                self.audio.play("star")
                try:
                    emit_activity_event("colline.star_collected", payload={"stars": self.world.stars_collected})
                except Exception:
                    pass
            elif ev == "colline.comical_flip":
                self.audio.play("boing")
                self.renderer.emit_confetti(veh.x, veh.y, 40)
                try:
                    emit_activity_event("colline.comical_flip")
                except Exception:
                    pass
            elif ev == "colline.perfect_landing":
                self.audio.play("perfect_landing")
                self.renderer.emit_confetti(veh.x, veh.y, 25)
                try:
                    emit_activity_event("colline.perfect_landing")
                except Exception:
                    pass
            elif ev == "colline.milestone_distance":
                self.audio.play("fanfare")
                self._save_storage()
                try:
                    emit_activity_event(
                        "colline.milestone_distance",
                        payload={"milestone_m": self.world.highest_milestone},
                        idempotency_key=f"milestone-{self.world.highest_milestone}",
                    )
                except Exception:
                    pass
            elif ev == "colline.course_completed":
                self.audio.play("fanfare")
                self._save_storage()
                try:
                    emit_activity_event(
                        "colline.course_completed",
                        payload={"distance": self.world.distance_traveled, "stars": self.world.stars_collected},
                    )
                except Exception:
                    pass
            elif ev == "colline.mushroom_bounce":
                self.audio.play("boing")
                self.audio.play("whoosh")

    def run(self) -> int:
        """Main 60 FPS gameplay loop."""
        clock = pygame.time.Clock()
        last_time = time.monotonic()

        # Emit initial run_started event
        try:
            emit_activity_event("colline.run_started", idempotency_key=f"run-{time.time()}")
        except Exception:
            pass

        while self.running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, max(0.001, now - last_time))
            last_time = now

            # Process input events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key in (pygame.K_r, pygame.K_F5):
                        self.world.reset()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.canvas = PygameReferenceCanvas(self.screen)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_pointer_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_pointer_up(event.pos)
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:
                        self._joy_gas = True
                    elif event.button in (1, 2):
                        self._joy_brake = True
                elif event.type == pygame.JOYBUTTONUP:
                    if event.button == 0:
                        self._joy_gas = False
                    elif event.button in (1, 2):
                        self._joy_brake = False
                elif event.type == pygame.JOYAXISMOTION:
                    if event.axis == 0:
                        self._joy_tilt = event.value if abs(event.value) > 0.2 else 0.0
                    elif event.axis == 5:
                        self._joy_gas = event.value > 0.2
                    elif event.axis == 4:
                        self._joy_brake = event.value > 0.2

            # Continuous Keyboard & Gamepad evaluation
            keys = pygame.key.get_pressed()
            key_gas = (
                keys[pygame.K_RIGHT]
                or keys[pygame.K_UP]
                or keys[pygame.K_SPACE]
                or keys[pygame.K_d]
                or keys[pygame.K_w]
                or keys[pygame.K_RETURN]
            )
            key_brake = keys[pygame.K_LEFT] or keys[pygame.K_DOWN] or keys[pygame.K_s] or keys[pygame.K_a]

            # Mid-air tilt keys
            tilt_val = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                tilt_val -= 1.0
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                tilt_val += 1.0
            if abs(self._joy_tilt) > 0.1:
                tilt_val += self._joy_tilt

            throttle = 1.0 if (key_gas or self._touch_gas or self._joy_gas) else 0.0
            brake = 1.0 if (key_brake or self._touch_brake or self._joy_brake) else 0.0

            self.renderer.gas_pressed = throttle > 0.0
            self.renderer.brake_pressed = brake > 0.0

            # Advance 2D physics simulation
            events = self.world.step(dt, throttle=throttle, brake=brake, tilt=tilt_val)
            self._route_events(events)

            # Render scene onto 1024x600 reference canvas
            self.renderer.render(self.canvas.surface, self.world, dt)

            # Present canvas to physical display
            self.canvas.present()
            pygame.display.flip()

            # Mark activity ready after first frame is safely on screen
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True

            clock.tick(60)

        # Cleanup on exit
        self._save_storage()
        self.audio.stop_all()
        self.typography.clear()
        return 0


def build_app(screen: pygame.Surface | None = None, locale: str = "it") -> CollineApp:
    return CollineApp(screen=screen, locale=locale)
