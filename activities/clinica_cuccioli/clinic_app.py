from __future__ import annotations

import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import is_home_clicked
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface

from clinic_audio import ClinicAudioPort
from clinic_model import ClinicSession, TreatmentResult
from clinic_renderer import ClinicRenderer, TABLE_RECT
from clinic_services import ClinicEventPort, ClinicProgressPort


class ClinicActivity:
    """Coordinate Clinic lifecycle without owning domain, rendering or IO details.

    Dependencies are injected so gameplay/event/persistence behavior can be tested
    independently and so future runtime presentation changes do not fork the game
    rules. The class owns only the event-loop lifecycle and cross-service sequencing.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: ClinicSession,
        renderer: ClinicRenderer,
        audio: ClinicAudioPort,
        progress: ClinicProgressPort,
        events: ClinicEventPort,
    ) -> None:
        self._screen = screen
        self._canvas = canvas
        self._session = session
        self._renderer = renderer
        self._audio = audio
        self._progress = progress
        self._events = events
        self._running = True
        self._ready_published = False

    def run(self) -> int:
        clock = pygame.time.Clock()
        previous_time = time.monotonic()
        dirty = True

        while self._running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.0, now - previous_time))
            previous_time = now

            for event in pygame.event.get():
                dirty = self._handle_event(event) or dirty

            if not self._session.is_victory:
                # The thought bubble has a small continuous bob while treating a
                # patient, so the active scene remains intentionally animated.
                dirty = True
                self._renderer.update(dt)

            if dirty:
                self._renderer.render(self._canvas.surface, self._session, now)
                self._canvas.present()
                pygame.display.flip()
                dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True

            # 30 Hz while animated; 25 Hz polling at a frozen victory screen keeps
            # worst-case input latency at about 40 ms without repainting unchanged pixels.
            clock.tick(30 if not self._session.is_victory else 25)

        return 0

    def _handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            self._running = False
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return False
        if event.type == pygame.VIDEORESIZE:
            self._screen = pygame.display.get_surface() or self._screen
            self._canvas = PygameReferenceCanvas(self._screen)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_pointer(event.pos)
        return False

    def _handle_pointer(self, screen_position: tuple[int, int]) -> bool:
        if is_home_clicked(self._screen, screen_position):
            self._running = False
            return False
        if not _is_safe_point(self._screen, screen_position):
            return False

        pointer = self._canvas.pointer(screen_position)
        if pointer is None:
            return False
        point = (int(pointer[0]), int(pointer[1]))

        if self._session.is_victory:
            if self._renderer.play_again_contains(point):
                self._session.restart()
                self._renderer.reset_transients()
                return True
            return False

        tool_id = self._renderer.tool_at(point)
        if tool_id is not None:
            result = self._session.use_tool(tool_id)
            # Preserve the playful sound on every palette selection, including a
            # wrong choice; only successful treatment publishes progression facts.
            self._audio.play(tool_id)
            if result.applied:
                self._finish_treatment(result, TABLE_RECT.center)
            return True

        if self._renderer.patient_contains(point) and self._session.next_needed is not None:
            result = self._session.use_selected_tool()
            if result.applied:
                self._audio.play(result.tool_id)
                self._finish_treatment(result, point)
                return True
        return False

    def _finish_treatment(
        self,
        result: TreatmentResult,
        effect_origin: tuple[int, int],
    ) -> None:
        self._renderer.celebrate(result.tool_id, effect_origin)
        self._events.treatment_applied(result)
        if not result.patient_healed:
            return
        self._audio.play("win")
        self._progress.save_stars(result.total_stars)
        self._events.patient_healed(result)


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Reject Activity input in Greia's protected system-chrome regions."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )
