"""App lifecycle and hybrid interaction orchestration for Officina dei Suoni."""

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
    from .sound_audio import SoundWorkshopAudio, SpeechQueue
    from .sound_content import WordItem, WorkshopMode
    from .sound_workshop_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SoundRoundFactory,
        SoundSession,
        adapt_level,
    )
    from .sound_renderer import SoundWorkshopRenderer
    from .sound_services import EventPort, ProgressPort
else:
    from sound_audio import SoundWorkshopAudio, SpeechQueue
    from sound_content import WordItem, WorkshopMode
    from sound_workshop_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SoundRoundFactory,
        SoundSession,
        adapt_level,
    )
    from sound_renderer import SoundWorkshopRenderer
    from sound_services import EventPort, ProgressPort


class AppState(StrEnum):
    PLAYING = "playing"
    WOBBLE = "wobble"
    SUCCESS_GAP = "success_gap"
    TERMINAL = "terminal"


class SoundWorkshopActivity:
    """Coordinate phoneme workshop model, speech queue, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: SoundSession,
        factory: SoundRoundFactory,
        renderer: SoundWorkshopRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: SoundWorkshopAudio,
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
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._highlight_choice: int | None = None
        self._focused_choice: int = 0

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
        if c.mode == WorkshopMode.FIND_SOUND and c.target_unit is not None:
            self.speech_queue.enqueue(c.target_unit.audio_id, delay_after=0.4)
        elif c.target_word is not None:
            self.speech_queue.enqueue(c.target_word.word_id, delay_after=0.4)

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
                return
            if self.state is AppState.TERMINAL:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._restart()
                    self._dirty = True
                return
            if self.state is AppState.PLAYING:
                if self._handle_keyboard(event.key):
                    self._dirty = True
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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_pointer(event.pos):
                self._dirty = True

    def _handle_keyboard(self, key: int) -> bool:
        current = self.session.current_challenge
        if current is None:
            return False

        num_choices = len(current.choices)
        if key in (pygame.K_LEFT, pygame.K_a):
            self._focused_choice = (self._focused_choice - 1) % num_choices
            return True
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._focused_choice = (self._focused_choice + 1) % num_choices
            return True
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            return self._select_choice(self._focused_choice)
        elif key == pygame.K_r:
            self._speak_current_challenge()
            return True
        return False

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

        # Replay or target click
        if self.renderer.replay_contains(point) or self.renderer.target_contains(point):
            self._speak_current_challenge()
            return True

        # Choice click
        choice_idx = self.renderer.choice_at(point, current)
        if choice_idx is not None:
            self._focused_choice = choice_idx
            return self._select_choice(choice_idx)

        return False

    def _select_choice(self, choice_idx: int) -> bool:
        current = self.session.current_challenge
        if current is None:
            return False

        # Audio cue for chosen item
        chosen_item = current.choices[choice_idx]
        if isinstance(chosen_item, WordItem):
            self.speech_queue.enqueue(chosen_item.word_id, delay_after=0.2)
        elif current.target_unit is not None:
            self.speech_queue.enqueue(current.target_unit.audio_id, delay_after=0.2)

        result = self.session.select_choice(choice_idx)
        return self._process_result(result, choice_idx)

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
            self.events.word_completed(self.session_id, milestone)

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
                self._focused_choice = 0
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

        highlight = self._highlight_choice if self._highlight_choice is not None else self._focused_choice
        self.renderer.draw_scene(
            self.canvas.surface,
            self.session,
            wobble_x=wobble_x,
            highlight_index=highlight,
        )

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.workshop_completed(self.session_id, payload)

        self.speech_queue.clear()
        self.audio.play_sfx("complete")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=6,
            )
        )
        self.state = AppState.TERMINAL
        self.state_started = self.clock()

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = SoundSession(challenges, level=next_level, history=self.session.history)
        self.completion.clear()
        self.state = AppState.PLAYING
        self.state_started = self.clock()
        self._focused_choice = 0
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
