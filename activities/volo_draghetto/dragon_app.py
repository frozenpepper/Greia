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
        pygame.init()
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        theme = get_theme()
        canvas = PygameReferenceCanvas(screen)

        self._start_new_round()

        running = True
        ready_published = False

        while running and not activity_stop_requested():
            dt = 1.0 / 30.0

            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if self.world.is_victory:
                            self._start_new_round()
                        else:
                            self.world.dragon.trigger_dash(4.0)
                            self.audio.play("whoosh")
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.world.is_victory:
                            self._start_new_round()
                elif event.type == pygame.MOUSEMOTION:
                    if not self.world.is_victory and _is_safe_point(screen, event.pos):
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
                        if self.world.is_victory:
                            # Play again clicked
                            self._start_new_round()
                        else:
                            # Accessory Button hit (x=580..716, y=14..58)
                            if 580 <= lx <= 716 and 14 <= ly <= 58:
                                self.world.dragon.cycle_accessory()
                                self.audio.play("pop")

            # 2. Continuous Keyboard & Controller Altitude Control
            if not self.world.is_victory:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    self.world.dragon.target_y = max(MIN_FLIGHT_Y, self.world.dragon.target_y - 9.0)
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    self.world.dragon.target_y = min(MAX_FLIGHT_Y, self.world.dragon.target_y + 9.0)

            # 3. Update World Simulation
            events = self.world.update(dt)
            for ev in events:
                if ev == "star_collected":
                    self.audio.play("star")
                elif ev == "rainbow_boost":
                    self.audio.play("whoosh")
                    self.audio.play("star")
                    try:
                        emit_activity_event("flight.star_milestone", idempotency_key=f"milestone-{time.time()}")
                    except Exception:
                        pass
                elif ev == "cloud_bounce":
                    self.audio.play("boing")
                elif ev == "round_completed":
                    self.audio.play("victory")
                    self._save_storage()
                    try:
                        emit_activity_event("flight.completed", idempotency_key=f"completed-{time.time()}")
                    except Exception:
                        pass

            # 4. Composite Frame onto Reference Canvas
            surf = canvas.surface
            if self.world.is_victory:
                # Terminal Completion Presentation
                if self._completion_screen is None:
                    self._completion_screen = PygameCompletionScreen(
                        typography=self.typography,
                        width=1024,
                        height=600,
                    )
                if not self._completion_screen.is_prepared:
                    content = CompletionContent(
                        title="VOLO COMPLETATO! 🌟",
                        primary_label="GIOCA ANCORA 🚀",
                        body_lines=(
                            "Hai raccolto tutte le 20 stelle magiche!",
                            f"Punti totali: {self.world.score}",
                        ),
                        achievement_count=1,
                    )
                    self._completion_screen.prepare(content)
                self._completion_screen.draw(surf)
            else:
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
