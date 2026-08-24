"""Lifecycle and pointer interaction orchestration for La Bottega delle Misure."""

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
    from .measure_audio import MeasureAudio
    from .measure_model import (
        MeasureChallenge,
        MeasureMode,
        MeasureRoundFactory,
        MeasureSession,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from .measure_renderer import MeasureRenderer
    from .measure_services import EventPort, ProgressPort
else:
    from measure_audio import MeasureAudio
    from measure_model import (
        MeasureChallenge,
        MeasureMode,
        MeasureRoundFactory,
        MeasureSession,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from measure_renderer import MeasureRenderer
    from measure_services import EventPort, ProgressPort


class AppState(StrEnum):
    PLAYING = "playing"
    WOBBLE = "wobble"
    TRANSITION = "transition"
    TERMINAL = "terminal"


class BottegaActivity:
    """Coordinate measurement domain model, pointer interaction, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: MeasureSession,
        factory: MeasureRoundFactory,
        renderer: MeasureRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: MeasureAudio,
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

        self.state = AppState.PLAYING
        self.state_started = clock()
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._hovered_item: str | None = None
        self._hovered_choice_idx: int | None = None

        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(40, 32, 28),
                panel=(254, 243, 199),
                panel_border=(180, 83, 9),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(34, 197, 94),
                primary_text=(255, 255, 255),
            ),
        )

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)
            if self._advance_state():
                self._dirty = True
            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            ticker.tick(30 if self.state in {AppState.WOBBLE, AppState.TRANSITION} else 20)
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

        if self.state is AppState.TERMINAL:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_terminal_pointer(event.pos):
                    self._dirty = True
            return

        if self.state is not AppState.PLAYING:
            return

        if event.type == pygame.MOUSEMOTION:
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                current = self.session.current_challenge
                new_item = self.renderer.item_at(point, current) if current else None
                new_choice = self.renderer.choice_index_at(point, current) if current else None
                if new_item != self._hovered_item or new_choice != self._hovered_choice_idx:
                    self._hovered_item = new_item
                    self._hovered_choice_idx = new_choice
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

        current = self.session.current_challenge
        if current is None:
            return False

        # 1. Parcel item click in COMPARE / ORDER modes
        if current.mode in {MeasureMode.COMPARE, MeasureMode.ORDER}:
            item_id = self.renderer.item_at(point, current)
            if item_id is not None:
                self.audio.play("snap")
                result = self.session.select_item(item_id)
                if result is not None:
                    return self._process_result(result)
                return True

        # 2. Number choice click in MEASURE / SHELF modes
        if current.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            val = self.renderer.choice_at(point, current)
            if val is not None:
                result = self.session.select_answer_value(val)
                return self._process_result(result)

        return False

    def _process_result(self, result) -> bool:
        if not result.correct:
            self.audio.play("retry")
            self.state = AppState.WOBBLE
            self.state_started = self.clock()
            return True

        self.audio.play("correct")
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.parcel_completed(self.session_id, milestone)

        if result.session_complete:
            self._finish_session()
        else:
            self.state = AppState.TRANSITION
            self.state_started = self.clock()
        return True

    def _advance_state(self) -> bool:
        elapsed = self.clock() - self.state_started
        if self.state == AppState.WOBBLE:
            if elapsed >= 0.28:
                self.state = AppState.PLAYING
                return True
            return True
        if self.state == AppState.TRANSITION:
            if elapsed >= 0.35:
                self.state = AppState.PLAYING
                return True
            return False
        return False

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self.completion.draw(self.canvas.surface)
            return

        wobble_x = 0
        show_baseline = False
        if self.state == AppState.WOBBLE:
            elapsed = self.clock() - self.state_started
            wobble_x = int(8 * ((1 - elapsed / 0.28) * ((int(elapsed * 40) % 2) * 2 - 1)))
            show_baseline = True

        self.renderer.draw_scene(
            self.canvas.surface,
            self.session,
            wobble_x=wobble_x,
            show_baseline=show_baseline,
            hovered_item_id=self._hovered_item,
            hovered_choice_idx=self._hovered_choice_idx,
        )

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.delivery_completed(self.session_id, payload)

        self.audio.play("complete")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=5,
            )
        )
        self.state = AppState.TERMINAL
        self.state_started = self.clock()

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = MeasureSession(challenges, level=next_level, history=self.session.history)
        self.completion.clear()
        self.state = AppState.PLAYING
        self.state_started = self.clock()
        self.audio.play("correct")

    def _handle_terminal_pointer(self, raw_pos: tuple[int, int]) -> bool:
        if is_home_clicked(self.screen, raw_pos):
            self._running = False
            return False
        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        point = (int(logical[0]), int(logical[1]))
        if self.completion.primary_contains(point):
            self._restart()
            return True
        return False


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True
