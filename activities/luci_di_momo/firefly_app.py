"""Lifecycle and semantic input orchestration for Luci di Momo."""

from __future__ import annotations

from enum import StrEnum
import random
import time
from typing import Callable

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import is_home_clicked
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import CompletionContent, CompletionPalette, PygameCompletionScreen
from greia_platform.typography import GreiaTypography

if __package__:
    from .firefly_audio import FireflyAudio
    from .firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH, adapt_level
    from .firefly_renderer import FireflyRenderer
    from .firefly_services import EventPort, ProgressPort
else:
    from firefly_audio import FireflyAudio
    from firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH, adapt_level
    from firefly_renderer import FireflyRenderer
    from firefly_services import EventPort, ProgressPort


class PresentationPhase(StrEnum):
    READY = "ready"
    REVEAL = "reveal"
    CHOOSE = "choose"
    HINT = "hint"
    TERMINAL = "terminal"


class FireflyActivity:
    """Coordinate domain state, bounded animation, Greia lifecycle, and adapters."""

    HINT_STEP_MS = 240

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: FireflySession,
        factory: FireflyRoundFactory,
        renderer: FireflyRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: FireflyAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.session = session
        self.factory = factory
        self.renderer = renderer
        self.typography = typography
        self.resources = resources
        self.progress = progress
        self.events = events
        self.audio = audio
        self.rng = rng
        self.session_id = session_id
        self.clock = clock
        self.phase = PresentationPhase.READY
        self.phase_started = clock()
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._hovered_start = False
        self._hovered_choice: int | None = None
        self._hovered_replay = False
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(31, 47, 79), panel=(255, 250, 232), panel_border=(236, 192, 83),
                title=(124, 76, 38), body=(73, 83, 103), primary=(74, 160, 108),
                primary_text=(255, 255, 255),
            ),
        )

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)
            if self._advance_timed_phase():
                self._dirty = True
            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
                    self.audio.play_welcome()
            ticker.tick(30 if self.phase in {PresentationPhase.REVEAL, PresentationPhase.HINT} else 20)
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._dirty = True
            return
        if event.type == pygame.MOUSEMOTION:
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                current = self.session.current_round
                new_start = self.renderer.start_contains(point) if self.phase is PresentationPhase.READY else False
                new_choice = self.renderer.choice_at(point, current) if (current and self.phase is PresentationPhase.CHOOSE) else None
                new_replay = self.renderer.replay_contains(point) if self.phase is PresentationPhase.CHOOSE else False
                if (
                    new_start != self._hovered_start
                    or new_choice != self._hovered_choice
                    or new_replay != self._hovered_replay
                ):
                    self._hovered_start = new_start
                    self._hovered_choice = new_choice
                    self._hovered_replay = new_replay
                    self._dirty = True
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_pointer(event.pos):
                self._dirty = True

    def _handle_pointer(self, raw_pos: tuple[int, int]) -> bool:
        if is_home_clicked(self.screen, raw_pos):
            self._running = False
            return False
        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        point = (int(logical[0]), int(logical[1]))

        # Speech replay / mascot click
        if self.renderer.listen_contains(point):
            if self.phase is PresentationPhase.CHOOSE:
                self.audio.play_prompt_choose()
            else:
                self.audio.play_welcome()
            return True

        if self.phase is PresentationPhase.TERMINAL:
            if self.completion.primary_contains(point):
                self._restart()
                return True
            return False

        current = self.session.current_round
        if current is None:
            return False

        if self.phase is PresentationPhase.READY:
            if self.renderer.start_contains(point):
                self.phase = PresentationPhase.REVEAL
                self.phase_started = self.clock()
                self.audio.play("reveal")
                return True
            return False

        if self.phase is not PresentationPhase.CHOOSE:
            return False

        if self.renderer.replay_contains(point):
            self.session.mark_replay()
            self.phase = PresentationPhase.REVEAL
            self.phase_started = self.clock()
            self.audio.play("reveal")
            return True

        value = self.renderer.choice_at(point, current)
        if value is None:
            return False
        result = self.session.choose(value)
        if not result.correct:
            self.audio.play_feedback(False)
            self.phase = PresentationPhase.HINT
            self.phase_started = self.clock()
            return True

        self.audio.play_count(current.quantity)
        self.audio.play_feedback(True)
        if result.session_complete:
            self._finish_session()
        else:
            self.phase = PresentationPhase.READY
            self.phase_started = self.clock()
        return True

    def _advance_timed_phase(self) -> bool:
        current = self.session.current_round
        if current is None:
            return False
        elapsed_ms = int((self.clock() - self.phase_started) * 1000)
        if self.phase is PresentationPhase.REVEAL:
            if elapsed_ms >= current.reveal_ms:
                self.phase = PresentationPhase.CHOOSE
                self.audio.play_prompt_choose()
                return True
            return False
        if self.phase is PresentationPhase.HINT:
            total = current.quantity * self.HINT_STEP_MS + 360
            if elapsed_ms >= total:
                self.phase = PresentationPhase.CHOOSE
                self._last_hint_step = None
                return True
            step = min(current.quantity, 1 + elapsed_ms // self.HINT_STEP_MS)
            if getattr(self, "_last_hint_step", None) != step:
                self._last_hint_step = step
                return True
            return False
        return False

    def _render(self) -> None:
        if self.phase is PresentationPhase.TERMINAL:
            self.completion.draw(self.canvas.surface)
            return
        current = self.session.current_round
        if current is None:
            return
        total_rounds = len(self.session.rounds)
        if self.phase is PresentationPhase.READY:
            self.renderer.draw_ready(
                self.canvas.surface,
                current,
                round_index=self.session.round_index,
                total_rounds=total_rounds,
                hovered_start=self._hovered_start,
            )
            return
        if self.phase is PresentationPhase.CHOOSE:
            self.renderer.draw_choices(
                self.canvas.surface,
                current,
                round_index=self.session.round_index,
                total_rounds=total_rounds,
                hovered_value=self._hovered_choice,
                hovered_replay=self._hovered_replay,
            )
            return
        visible_count = None
        if self.phase is PresentationPhase.HINT:
            elapsed_ms = int((self.clock() - self.phase_started) * 1000)
            visible_count = min(current.quantity, 1 + elapsed_ms // self.HINT_STEP_MS)
        self.renderer.draw_reveal(
            self.canvas.surface,
            current,
            level=self.session.level,
            round_index=self.session.round_index,
            total_rounds=total_rounds,
            visible_count=visible_count,
        )

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.garden_completed(self.session_id, payload)
        self.audio.play_garden_complete()
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=5,
            )
        )
        self.phase = PresentationPhase.TERMINAL
        self.phase_started = self.clock()

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        rounds = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = FireflySession(rounds, level=next_level, history=self.session.history)
        self.completion.clear()
        self.phase = PresentationPhase.READY
        self.phase_started = self.clock()
        self.audio.play_welcome()


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True
