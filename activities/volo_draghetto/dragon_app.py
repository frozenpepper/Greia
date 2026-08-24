"""Application coordinator, event loop, and lifecycle for Il Volo del Draghetto."""

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
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import (
    CompletionContent,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography

try:
    from dragon_art import DragonArtLibrary
    from dragon_audio import DragonAudio
    from dragon_model import (
        FlightWorldState,
        MIN_FLIGHT_Y,
        MAX_FLIGHT_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from dragon_renderer import DragonRenderer
except ImportError:
    from .dragon_art import DragonArtLibrary
    from .dragon_audio import DragonAudio
    from .dragon_model import (
        FlightWorldState,
        MIN_FLIGHT_Y,
        MAX_FLIGHT_Y,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .dragon_renderer import DragonRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class DragonFlightApp:
    """Main application coordinator for Il Volo del Draghetto."""

    def __init__(self) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.FULLSCREEN)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        pygame.mouse.set_visible(False)

        self.world = FlightWorldState()
        self.art = DragonArtLibrary()
        self.audio = DragonAudio()
        self.typography = GreiaTypography()
        self.renderer = DragonRenderer(self.art, self.typography)

        self._resources: LocalizedResources | None = None
        self._active_locale = "it"
        self._init_localization()

        self._storage: Any = None
        self._load_storage()

        self._completion_screen: PygameCompletionScreen | None = None

    def _init_localization(self) -> None:
        pkg_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        try:
            profile_lang = get_profile_locale()
            context = resolve_activity_locale(profile_lang, support)
            self._resources = LocalizedResources(pkg_root, context) if context else None
            self._active_locale = context.selected.language if context else "it"
        except Exception:
            self._active_locale = "it"

    def _load_storage(self) -> None:
        try:
            self._storage = get_storage()
            if self._storage is not None:
                saved = self._storage.kv_get(STORAGE_KEY, {})
                if isinstance(saved, dict):
                    self.world.score = int(saved.get("score", 0))
                    self.world.total_stars = int(saved.get("stars", 0))
        except Exception:
            self._storage = None

    def _save_storage(self) -> None:
        if self._storage is not None:
            try:
                self._storage.kv_set(
                    STORAGE_KEY,
                    {
                        "score": self.world.score,
                        "stars": self.world.total_stars,
                        "timestamp": time.time(),
                    },
                )
            except Exception:
                pass

    def _start_new_round(self) -> None:
        self.world.start_flight()
        self._completion_screen = None

    def run(self) -> int:
        """Run the main application lifecycle loop."""
        screen = self.screen
        canvas = self.canvas
        clock = pygame.time.Clock()
        theme = get_theme()

        self._start_new_round()

        running = True
        ready_published = False
        previous_time = time.monotonic()

        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - previous_time))
            previous_time = now

            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.world.dragon.move_altitude(-24.0)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.world.dragon.move_altitude(24.0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.world.dragon.trigger_dash(3.5)
                        self.audio.play("whoosh")
                    elif event.key in (pygame.K_TAB, pygame.K_l):
                        self.world.dragon.cycle_accessory()
                        self.audio.play("pop")
                elif event.type == pygame.MOUSEMOTION:
                    if _is_safe_point(screen, event.pos):
                        plog = canvas.pointer(event.pos)
                        if plog is not None:
                            self.world.dragon.target_y = max(MIN_FLIGHT_Y, min(MAX_FLIGHT_Y, plog[1]))
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.get_surface() or screen
                    canvas = PygameReferenceCanvas(screen)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if is_home_clicked(screen, event.pos):
                        running = False
                        continue
                    if not _is_safe_point(screen, event.pos):
                        continue
                    logical = canvas.pointer(event.pos)
                    if logical is not None:
                        lx, ly = logical
                        # Accessory Button hit (x=580..716, y=14..58)
                        if 580 <= lx <= 716 and 14 <= ly <= 58:
                            self.world.dragon.cycle_accessory()
                            self.audio.play("pop")
                        else:
                            # Click anywhere in flight triggers a dash burst!
                            self.world.dragon.trigger_dash(3.0)
                            self.audio.play("whoosh")

            # 2. Continuous Keyboard & Controller Altitude Control
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.world.dragon.move_altitude(-12.0)
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.world.dragon.move_altitude(12.0)

            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.world.dragon.trigger_dash(2.0)

            # 3. Update World Simulation
            events = self.world.update(dt)
            for ev in events:
                if ev == "star_collected":
                    self.audio.play("star")
                elif ev == "star_milestone":
                    self.audio.play("star")
                    self.audio.play("victory")
                    self._save_storage()
                    try:
                        emit_activity_event("flight.star_milestone", idempotency_key=f"milestone-{time.time()}")
                    except Exception:
                        pass
                elif ev == "rainbow_boost":
                    self.audio.play("whoosh")
                    self.audio.play("star")
                elif ev == "cloud_bounce":
                    self.audio.play("boing")

            # 4. Composite Frame onto Reference Canvas
            surf = canvas.surface
            feedback_msg = ""
            if self.world.feedback_text_key and self._resources:
                feedback_msg = self._resources.text(self.world.feedback_text_key)
            self.renderer.render_world(surf, self.world, feedback_msg)

            # 5. Present Canvas to Screen
            canvas.present(clear=theme.background)
            pygame.display.flip()

            if not ready_published:
                mark_activity_ready()
                ready_published = True

            clock.tick(30)

        self._save_storage()
        pygame.quit()
        return 0
