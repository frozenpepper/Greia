"""App lifecycle and pointer interaction orchestration for Festa delle Rime."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
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
    from .rhyme_audio import RhymeAudio, SpeechQueue
    from .rhyme_content import RhymeMode
    from .rhyme_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RhymeRoundFactory,
        RhymeSession,
        adapt_level,
    )
    from .rhyme_renderer import RhymeRenderer
    from .rhyme_services import EventPort, ProgressPort
else:
    from rhyme_audio import RhymeAudio, SpeechQueue
    from rhyme_content import RhymeMode
    from rhyme_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RhymeRoundFactory,
        RhymeSession,
        adapt_level,
    )
    from rhyme_renderer import RhymeRenderer
    from rhyme_services import EventPort, ProgressPort


class AppState(StrEnum):
    PLAYING = "playing"
    WOBBLE = "wobble"
    SUCCESS_GAP = "success_gap"
    TERMINAL = "terminal"


class RhymeActivity:
    """Coordinate listening game model, speech queue, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: RhymeSession,
        factory: RhymeRoundFactory,
        renderer: RhymeRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: RhymeAudio,
        speech_queue: SpeechQueue,
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
        self.speech_queue = speech_queue
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.state = AppState.PLAYING
        self.state_started = clock()
        self._highlight_choice: int | None = None
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._hovered_choice: int | None = None
        self._hovered_replay = False
        self._hovered_target = False

        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(15, 23, 42),
                panel=(254, 243, 199),
                panel_border=(2, 132, 199),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(2, 132, 199),
                primary_text=(255, 255, 255),
            ),
        )

        # Initial prompt speech
        self._speak_current_challenge()

    def run(self) -> int:
        ticker = pygame.time.Clock()
        last_t = self.clock()

        while self._running and not activity_stop_requested():
            now = self.clock()
            dt = max(0.001, now - last_t)
            last_t = now

            for event in pygame.event.get():
                self._handle_event(event)

            self.speech_queue.update(dt)

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

            ticker.tick(30 if self.state in {AppState.WOBBLE, AppState.SUCCESS_GAP} else 20)
        return 0

    def _speak_current_challenge(self) -> None:
        c = self.session.current_challenge
        if c is None:
            return
        self.speech_queue.clear()
        if c.target_item is not None:
            self.speech_queue.enqueue(c.target_item.item_id, delay_after=0.45)
        elif c.mode == RhymeMode.RHYME_ODD:
            self.speech_queue.enqueue("prompt_odd", delay_after=0.45)

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
                new_choice = self.renderer.choice_at(point, current) if current else None
                new_replay = self.renderer.replay_contains(point)
                new_target = self.renderer.target_contains(point) if (current and current.target_item) else False
                if new_choice != self._hovered_choice or new_replay != self._hovered_replay or new_target != self._hovered_target:
                    self._hovered_choice = new_choice
                    self._hovered_replay = new_replay
                    self._hovered_target = new_target
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

        # 1. Replay button or Target Lantern click
        if self.renderer.replay_contains(point) or (current.target_item is not None and self.renderer.target_contains(point)):
            self._speak_current_challenge()
            return True

        # 2. Choice Lantern click
        choice_idx = self.renderer.choice_at(point, current)
        if choice_idx is not None:
            # Play spoken word for selected choice
            choice_item = current.choices[choice_idx]
            self.speech_queue.enqueue(choice_item.item_id, delay_after=0.2)
            result = self.session.select_choice(choice_idx)
            return self._process_result(result, choice_idx)

        return False

    def _process_result(self, result, choice_idx: int) -> bool:
        if not result.correct:
            self.audio.play_sfx("retry")
            self.state = AppState.WOBBLE
            self.state_started = self.clock()
            self._highlight_choice = choice_idx
            return True

        self.audio.play_sfx("correct")
        self._highlight_choice = choice_idx

        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.match_completed(self.session_id, milestone)

        if result.session_complete:
            self._finish_session()
        else:
            self.state = AppState.SUCCESS_GAP
            self.state_started = self.clock()
        return True

    def _advance_state(self) -> bool:
        elapsed = self.clock() - self.state_started
        if self.state == AppState.WOBBLE:
            if elapsed >= 0.28:
                self.state = AppState.PLAYING
                self._highlight_choice = None
                return True
            return True
        if self.state == AppState.SUCCESS_GAP:
            if elapsed >= 0.90:
                self.state = AppState.PLAYING
                self._highlight_choice = None
                self._speak_current_challenge()
                return True
            return False
        return False

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self.completion.draw(self.canvas.surface)
            return

        wobble_x = 0
        if self.state == AppState.WOBBLE:
            elapsed = self.clock() - self.state_started
            wobble_x = int(8 * ((1 - elapsed / 0.28) * ((int(elapsed * 40) % 2) * 2 - 1)))

        self.renderer.draw_scene(
            self.canvas.surface,
            self.session,
            wobble_x=wobble_x,
            highlight_index=self._highlight_choice,
            hovered_choice_idx=self._hovered_choice,
            hovered_replay=self._hovered_replay,
            hovered_target=self._hovered_target,
        )

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.festival_completed(self.session_id, payload)

        self.speech_queue.clear()
        self.audio.play_sfx("complete")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=8,
            )
        )
        self.state = AppState.TERMINAL
        self.state_started = self.clock()

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = RhymeSession(challenges, level=next_level, history=self.session.history)
        self.completion.clear()
        self.state = AppState.PLAYING
        self.state_started = self.clock()
        self.audio.play_sfx("correct")
        self._speak_current_challenge()

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
