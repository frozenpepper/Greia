"""Lifecycle and pointer interaction orchestration for Specchi Magici."""

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
    from .mirror_audio import MirrorAudio
    from .mirror_model import (
        MirrorRoundFactory,
        MirrorSession,
        MosaicPuzzle,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from .mirror_renderer import MirrorRenderer
    from .mirror_services import EventPort, ProgressPort
else:
    from mirror_audio import MirrorAudio
    from mirror_model import (
        MirrorRoundFactory,
        MirrorSession,
        MosaicPuzzle,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from mirror_renderer import MirrorRenderer
    from mirror_services import EventPort, ProgressPort


class AppState(StrEnum):
    PLAYING = "playing"
    WOBBLE = "wobble"
    SHIMMER = "shimmer"
    TERMINAL = "terminal"


class MirrorActivity:
    """Coordinate symmetry puzzle model, pointer interaction, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: MirrorSession,
        factory: MirrorRoundFactory,
        renderer: MirrorRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: MirrorAudio,
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
        self._hovered_cell: tuple[int, int] | None = None
        self._hovered_tray_idx: int | None = None
        self._hovered_undo = False

        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(26, 16, 48),
                panel=(254, 243, 199),
                panel_border=(147, 51, 234),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(147, 51, 234),
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
                    self.audio.play_welcome()
            ticker.tick(30 if self.state in {AppState.WOBBLE, AppState.SHIMMER} else 20)
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
                new_cell = self.renderer.cell_at(point)
                new_tray = self.renderer.tray_item_at(point, self.session)
                new_undo = self.renderer.undo_contains(point)
                if new_cell != self._hovered_cell or new_tray != self._hovered_tray_idx or new_undo != self._hovered_undo:
                    self._hovered_cell = new_cell
                    self._hovered_tray_idx = new_tray
                    self._hovered_undo = new_undo
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

        # 0. Speech replay button / mascot click
        if self.renderer.listen_contains(point):
            self.audio.play_welcome()
            return True

        current = self.session.current_puzzle
        if current is None:
            return False

        # 1. Tray piece click
        tray_idx = self.renderer.tray_item_at(point, self.session)
        if tray_idx is not None:
            self.session.select_tray_index(tray_idx)
            self.audio.play("place")
            piece = self.session.tray[tray_idx]
            self.audio.play_shape(piece.kind)
            return True

        # 2. Undo button click
        if self.renderer.undo_contains(point):
            if self.session.undo():
                self.audio.play("place")
                return True
            return False

        # 3. Grid cell click
        cell = self.renderer.cell_at(point)
        if cell is not None and self.session.selected_tray_index is not None:
            r, c = cell
            result = self.session.place_selected_at(r, c)
            if result is not None:
                return self._process_result(result)

        return False

    def _process_result(self, result) -> bool:
        if not result.correct:
            self.audio.play_feedback(False)
            self.state = AppState.WOBBLE
            self.state_started = self.clock()
            return True

        if result.puzzle_completed:
            milestone = self.session.consume_milestone()
            if milestone is not None:
                self.events.mosaic_completed(self.session_id, milestone)

            if result.session_complete:
                self.audio.play("complete")
                self._finish_session()
            else:
                self.audio.play_mosaic_complete()
                self.state = AppState.SHIMMER
                self.state_started = self.clock()
        else:
            self.audio.play_feedback(True)
        return True

    def _advance_state(self) -> bool:
        elapsed = self.clock() - self.state_started
        if self.state == AppState.WOBBLE:
            if elapsed >= 0.28:
                self.state = AppState.PLAYING
                return True
            return True
        if self.state == AppState.SHIMMER:
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
        shimmer = False
        if self.state == AppState.WOBBLE:
            elapsed = self.clock() - self.state_started
            wobble_x = int(8 * ((1 - elapsed / 0.28) * ((int(elapsed * 40) % 2) * 2 - 1)))
        elif self.state == AppState.SHIMMER:
            shimmer = True

        self.renderer.draw_scene(
            self.canvas.surface,
            self.session,
            wobble_x=wobble_x,
            shimmer=shimmer,
            hovered_cell=self._hovered_cell,
            hovered_tray_idx=self._hovered_tray_idx,
            hovered_undo=self._hovered_undo,
        )

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.gallery_completed(self.session_id, payload)

        self.audio.play("complete")
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
        puzzles = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = MirrorSession(puzzles, level=next_level, history=self.session.history)
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
