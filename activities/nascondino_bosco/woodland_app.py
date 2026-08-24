"""Activity application lifecycle and event coordination for Nascondino nel Bosco."""

from __future__ import annotations

import time
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_storage,
    get_ui_preferences,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionPalette,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography

try:
    from woodland_art import WoodlandArtLibrary
    from woodland_audio import WoodlandAudio
    from woodland_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        WoodlandGameState,
    )
    from woodland_renderer import WoodlandRenderer
except ImportError:
    from .woodland_art import WoodlandArtLibrary
    from .woodland_audio import WoodlandAudio
    from .woodland_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        WoodlandGameState,
    )
    from .woodland_renderer import WoodlandRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Verify input point does not collide with protected platform UI regions."""
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class WoodlandApp:
    """Orchestrates state, presentation, terminal victory, and Greia lifecycle."""

    def __init__(
        self,
        screen: pygame.Surface,
        resources: LocalizedResources,
        typography: GreiaTypography | None = None,
        audio: WoodlandAudio | None = None,
    ) -> None:
        self.screen = screen
        self.resources = resources
        self.typography = typography or GreiaTypography()
        self.audio = audio or WoodlandAudio()
        self.art = WoodlandArtLibrary()
        self.renderer = WoodlandRenderer(self.art, self.typography, self.resources)
        self.canvas = PygameReferenceCanvas(screen)
        self.storage = get_storage()

        # Load persisted stars
        saved_data = self.storage.kv_get(STORAGE_KEY) if self.storage else {}
        if not isinstance(saved_data, dict):
            saved_data = {}
        total_stars = saved_data.get("stars", 0)

        self.state = WoodlandGameState(total_stars=total_stars)
        self.state.start_round()

        # Terminal victory screen owner
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(25, 38, 48),
                panel=(255, 252, 245),
                panel_border=(234, 179, 8),
                title=(180, 83, 9),
                body=(71, 85, 105),
                primary=(34, 197, 94),
                primary_text=(255, 255, 255),
            ),
        )
        self._running = True
        self._ready_published = False

    def run(self) -> int:
        """Main loop executing at smooth, regulated 30 FPS."""
        clock = pygame.time.Clock()
        previous_time = time.monotonic()
        dirty = True

        while self._running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - previous_time))
            previous_time = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.get_surface() or self.screen
                    self.canvas = PygameReferenceCanvas(self.screen)
                    dirty = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._handle_click(event.pos):
                        dirty = True

            if not self.state.is_victory:
                self.state.update_animations(dt)
                dirty = True

            if dirty:
                if self.state.is_victory:
                    content = CompletionContent(
                        title=self.resources.text("victory.title"),
                        primary_label=self.resources.text("btn.play_again"),
                        body_lines=(self.resources.text("victory.subtitle"),),
                        achievement_count=self.state.found_count,
                    )
                    self.completion.prepare(content)
                    self.completion.draw(self.canvas.surface)
                else:
                    ui_prefs = get_ui_preferences()
                    self.renderer.draw_active_game(
                        self.canvas.surface,
                        self.state,
                        ui_prefs.interface_size,
                        t_now=now,
                    )

                self.canvas.present()
                pygame.display.flip()
                dirty = False

                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True

            clock.tick(30 if not self.state.is_victory else 25)

        return 0

    def _handle_click(self, raw_pos: tuple[int, int]) -> bool:
        """Dispatch child clicks cleanly to spots or completion controls."""
        if is_home_clicked(self.screen, raw_pos):
            self._running = False
            return False

        if not _is_safe_point(self.screen, raw_pos):
            return False

        ptr = self.canvas.pointer(raw_pos)
        if ptr is None:
            return False
        mx, my = int(ptr[0]), int(ptr[1])

        if self.state.is_victory:
            # Check Play Again hit target
            if self.completion.primary_contains((mx, my)):
                self.audio.play("pop")
                self.state.start_round()
                return True
            return False

        # Check spot interactions
        for spot in self.state.spots:
            if spot.contains(mx, my):
                was_target, animal_id = self.state.inspect_spot(spot.spot_id)
                if animal_id is not None:
                    self.audio.play("rustle")
                    self.audio.play("pop")

                    if was_target:
                        # Save progress & emit milestone
                        if self.storage:
                            self.storage.kv_set(STORAGE_KEY, {"stars": self.state.total_stars})
                        try:
                            emit_activity_event(
                                "woodland.animal_found",
                                {"animal": animal_id, "stars": self.state.total_stars},
                            )
                        except Exception:
                            pass

                        if self.state.is_victory:
                            self.audio.play("win")
                            try:
                                emit_activity_event(
                                    "woodland.round_completed",
                                    {"stars": self.state.total_stars},
                                )
                            except Exception:
                                pass
                return True

        return False
