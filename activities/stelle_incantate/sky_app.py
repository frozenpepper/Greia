"""Main application and interaction loop for Stelle Incantate."""

from __future__ import annotations

import time
from uuid import uuid4

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
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

if __package__:
    from .sky_audio import SkyAudio
    from .sky_model import SkySession
    from .sky_renderer import (
        CELEBRATE_SECONDS,
        NEXT_BUTTON_RECT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SkyRenderer,
    )
    from .sky_services import GreiaSkyEvents, GreiaSkyStorage
else:
    from sky_audio import SkyAudio
    from sky_model import SkySession
    from sky_renderer import (
        CELEBRATE_SECONDS,
        NEXT_BUTTON_RECT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SkyRenderer,
    )
    from sky_services import GreiaSkyEvents, GreiaSkyStorage


class AppState:
    PLAYING = "playing"
    CELEBRATE = "celebrate"
    TERMINAL = "terminal"


class SkyActivity:
    """Connect-the-stars constellation Activity hosted by Leo the owl."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: SkyRenderer,
        audio: SkyAudio,
        events: GreiaSkyEvents,
        storage: GreiaSkyStorage,
        resources: LocalizedResources,
        *,
        session_id: str | None = None,
        clock=time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.renderer = renderer
        self.audio = audio
        self.events = events
        self.storage = storage
        self.resources = resources
        self.session_id = session_id or f"sky-{uuid4().hex}"
        self.clock = clock

        self.completion = PygameCompletionScreen(
            typography=renderer.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(13, 18, 48),
                panel=(253, 250, 240),
                panel_border=(234, 179, 8),
                title=(180, 83, 9),
                body=(71, 85, 105),
                primary=(34, 197, 94),
                primary_text=(255, 255, 255),
                achievement=(234, 179, 8),
                achievement_inner=(254, 240, 138),
            ),
        )

        self.session = SkySession(completed_ids=storage.load_completed())
        self._state = AppState.PLAYING
        self._state_started = self.clock()
        self._running = True
        self._ready_published = False

        self._line_started = self.clock()
        self._line_progress = 1.0
        self._wrong_star: int | None = None
        self._wrong_started = 0.0
        self._fact_text: str | None = None
        self._fact_opened_for: str | None = None
        self._hovered_next = False
        self.selected_star_index = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)
            self._render()
            self.canvas.present()
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
            ticker.tick(30)
        return 0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
            return
        if event.type == pygame.MOUSEMOTION:
            logical = self.canvas.pointer(event.pos)
            if logical is not None and self._state == AppState.CELEBRATE:
                point = (int(logical[0]), int(logical[1]))
                self._hovered_next = NEXT_BUTTON_RECT.collidepoint(point)
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and not getattr(event, "touch", False)):
            self._handle_raw_pointer(event.pos)
        elif event.type == pygame.FINGERDOWN:
            width, height = self.screen.get_size()
            self._handle_raw_pointer((int(event.x * width), int(event.y * height)))

    def _handle_raw_pointer(self, screen_point: tuple[int, int]) -> None:
        if not self._point_in_activity_viewport(screen_point):
            return
        logical = self.canvas.pointer(screen_point)
        if logical is not None:
            self._handle_pointer_click((int(logical[0]), int(logical[1])))

    def _handle_keydown(self, key: int) -> None:
        """Navigation is visible and all activations use existing gameplay actions."""
        if self._state == AppState.TERMINAL:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self._restart()
            return
        if key == pygame.K_f:
            self._open_fact()
            return
        if self._state == AppState.CELEBRATE:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                # Do not skip the constellation celebration before Next appears.
                if self.clock() - self._state_started >= 1.0:
                    self._advance()
            return
        if key in (pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN):
            step = -1 if key in (pygame.K_LEFT, pygame.K_UP) else 1
            self.selected_star_index = (
                self.selected_star_index + step
            ) % self.session.current.star_count
        elif pygame.K_1 <= key <= pygame.K_9:
            index = key - pygame.K_1
            if index < self.session.current.star_count:
                self.selected_star_index = index
                self._tap_star(index)
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self._tap_star(self.selected_star_index)

    def _point_in_activity_viewport(self, raw_pos: tuple[int, int]) -> bool:
        viewport = activity_viewport_for_surface(self.screen)
        x, y = raw_pos
        if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
            return False
        for protected in viewport.protected_regions:
            if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
                return False
        return True

    def _handle_pointer_click(self, point: tuple[int, int]) -> None:
        if self._state == AppState.TERMINAL:
            if self.completion.primary_contains(point):
                self._restart()
            return
        if self._state == AppState.CELEBRATE:
            if NEXT_BUTTON_RECT.collidepoint(point):
                self._advance()
                return
            if self.renderer.fact_button_contains(point):
                self._open_fact()
            return
        # Playing.
        if self.renderer.fact_button_contains(point):
            self._open_fact()
            return
        star_index = self.renderer.star_at(self.session.current, point)
        if star_index is not None:
            self.selected_star_index = star_index
            self._tap_star(star_index)

    # ------------------------------------------------------------------
    # Gameplay transitions
    # ------------------------------------------------------------------

    def _tap_star(self, star_index: int) -> None:
        round_state = self.session.current
        if star_index >= round_state.star_count:
            return
        if round_state.connect(star_index):
            self.audio.play_note(star_index)
            if not round_state.is_complete:
                self.selected_star_index = round_state.next_star
            self._line_started = self.clock()
            self._line_progress = 0.0
            if round_state.is_complete:
                self._begin_celebration()
        else:
            self._wrong_star = star_index
            self._wrong_started = self.clock()
            self.audio.play("wrong")

    def _begin_celebration(self) -> None:
        constellation_id = self.session.record_completion()
        self.storage.save_completed(sorted(self.session.completed_ids))
        self.events.constellation_completed(
            self.session_id,
            constellation_id,
            self.session.current.star_count,
        )
        self.audio.play("complete")
        self._fact_opened_for = None
        self._state = AppState.CELEBRATE
        self._state_started = self.clock()

    def _advance(self) -> None:
        if self.session.all_complete:
            self._begin_terminal()
            return
        self.session.advance()
        self.selected_star_index = 0
        self._state = AppState.PLAYING
        self._state_started = self.clock()
        self._fact_text = None
        self._wrong_star = None
        self._line_progress = 1.0

    def _open_fact(self) -> None:
        constellation_id = self.session.current.constellation.constellation_id
        fact_key = self.session.current.constellation.fact_key
        try:
            fact = self.resources.text(fact_key)
        except Exception:
            fact = None
        if not fact:
            return
        self._fact_text = fact
        # Leo speaks the reviewed fact when the localized voice asset exists;
        # the procedural chirp is the fail-soft fallback, never a substitute
        # impersonation.
        try:
            cue = self.resources.audio_cue(fact_key, allow_fallback=False)
        except Exception:
            cue = None
        if cue is not None and self.audio.play_voice_cue(cue.path):
            pass
        else:
            self.audio.play("fact")
        if self._fact_opened_for != constellation_id:
            self._fact_opened_for = constellation_id
            self.events.fact_opened(self.session_id, constellation_id)

    def _begin_terminal(self) -> None:
        self.audio.play("victory")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=len(self.session.order),
            )
        )
        self._state = AppState.TERMINAL
        self._state_started = self.clock()

    def _restart(self) -> None:
        self.session_id = f"sky-{uuid4().hex}"
        self.session = SkySession(completed_ids=self.storage.load_completed())
        self.selected_star_index = 0
        self.completion.clear()
        self._state = AppState.PLAYING
        self._state_started = self.clock()
        self._fact_text = None
        self._fact_opened_for = None
        self._wrong_star = None
        self.audio.play_note(0)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self) -> None:
        now = self.clock()
        state_age = now - self._state_started

        if self._line_progress < 1.0:
            self._line_progress = min(1.0, (now - self._line_started) / 0.28)
        wrong_age = now - self._wrong_started
        if self._wrong_star is not None and wrong_age > 0.6:
            self._wrong_star = None

        if self._state == AppState.TERMINAL:
            self.completion.draw(self.canvas.surface)
            return

        round_state = self.session.current
        celebrating = self._state == AppState.CELEBRATE
        show_next = celebrating and state_age > 1.0
        name_text = None
        if celebrating:
            try:
                name_text = self.resources.text(round_state.constellation.name_key)
            except Exception:
                name_text = None

        self.renderer.draw_scene(
            self.canvas.surface,
            round_state,
            now=now,
            line_progress=self._line_progress,
            wrong_star=self._wrong_star,
            wrong_age=wrong_age,
            celebrating=celebrating,
            fact_text=self._fact_text,
            leo_happy=celebrating,
            name_text=name_text,
            show_next=show_next,
            hovered_next=self._hovered_next,
        )
        if self._state == AppState.PLAYING:
            cx, cy = self.renderer.star_center(round_state, self.selected_star_index)
            pygame.draw.circle(self.canvas.surface, (15, 23, 42), (cx, cy), 30, 7)
            pygame.draw.circle(self.canvas.surface, (56, 189, 248), (cx, cy), 30, 4)
