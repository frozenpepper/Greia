"""Lifecycle, timing and shared-kit input for Wonder Match.

A visit starts on Lilli's album shelf: the child picks one of five sticker
albums by its pictures. A board is a classic pairs memory game (2x2 -> 3x2 ->
4x3 -> 4x4, adapted from recent boards). Turning over two cards that match
plays a chime, speaks the picture's name when an approved recording exists,
makes Lilli cheer and sends the picture as a sticker to its well on the album
page, which keeps filling across visits. A miss is never a failure: the two
cards wiggle, stay visible for a moment while Lilli thinks, and turn back.
After a long streak of misses Lilli points and peeks one pair face up for a
moment. Idle for ~6 s, Lilli points and the waiting card glows. There is no
timer, no score and no move counter; a finished board ends on the shared
cast completion scene (again / albums).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .memory_art import MemoryArt, Side
    from .memory_audio import MemoryAudio
    from .memory_content import ALBUMS, LEVELS, MAX_LEVEL, REFERENCE_HEIGHT, REFERENCE_WIDTH, Album, album_by_id
    from .memory_controls import MemoryControls
    from .memory_layout import LILLI_HEIGHT, BoardLayout, PickerLayout
    from .memory_model import (
        HISTORY_LIMIT,
        BoardResult,
        CardState,
        FlipResult,
        MemoryBoard,
        StickerBook,
        adapt_level,
        choose_subjects,
        peek_threshold,
    )
    from .memory_render import FLIGHT_SECONDS, FLIP_SECONDS, BoardMotion, Flight, LilliCast, MemoryRenderer
    from .memory_services import EventPort, ProgressPort
else:
    from memory_art import MemoryArt, Side
    from memory_audio import MemoryAudio
    from memory_content import ALBUMS, LEVELS, MAX_LEVEL, REFERENCE_HEIGHT, REFERENCE_WIDTH, Album, album_by_id
    from memory_controls import MemoryControls
    from memory_layout import LILLI_HEIGHT, BoardLayout, PickerLayout
    from memory_model import (
        HISTORY_LIMIT,
        BoardResult,
        CardState,
        FlipResult,
        MemoryBoard,
        StickerBook,
        adapt_level,
        choose_subjects,
        peek_threshold,
    )
    from memory_render import FLIGHT_SECONDS, FLIP_SECONDS, BoardMotion, Flight, LilliCast, MemoryRenderer
    from memory_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
MATCH_LEAD = FLIP_SECONDS + 0.12
STICKER_DELAY = 0.95
MISS_LOOK = FLIP_SECONDS + 0.3
MISS_HOLD = 1.25
PEEK_SHOW = 1.6
COMPLETE_DELAY = 1.1
HINT_GLOW = 1.6
MAX_SCHEDULED = 64
NAVY = (37, 59, 89)


class AppState(StrEnum):
    PICKER = "picker"
    PLAYING = "playing"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for the scripted moments."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = [entry for entry in self._entries if entry[0] <= now]
        if not due:
            return False
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return True

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class MemoryApp:
    """Coordinate albums, the board model, kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: MemoryAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: MemoryArt | None = None,
        session_prefix: str | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._boards_played = 0
        self.session_id = self._new_session_id()

        saved = progress.load()
        self.level = saved.level
        self.album: Album = album_by_id(saved.album_id)
        self.book = StickerBook(saved.stickers)
        self.history: list[BoardResult] = list(saved.history)

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else MemoryArt(self.kit.painter)
        feedback = CastFeedback("lilli", height=LILLI_HEIGHT, art=self.art.loader, clock=clock)
        self.cast = LilliCast(feedback, self.art, clock)
        self.renderer = MemoryRenderer(self.art, self.cast, clock)
        self.motion = BoardMotion()
        self.timeline = Timeline(clock)
        self.controls = MemoryControls(
            self.kit,
            self.art,
            on_card=self._on_card,
            on_album=self._on_album,
            on_albums=self._open_picker,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(canvas, screen.get_size())
        self.board: MemoryBoard | None = None
        self.layout: BoardLayout | None = None
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.PICKER
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._idle_hints = 0
        self._open_picker()

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        ticker = pygame.time.Clock()
        try:
            while self._running and not activity_stop_requested():
                for event in pygame.event.get():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                if self._dirty or animating:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                ticker.tick(30 if animating else 15)
        finally:
            self.persist()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.motion.prune(now)
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        cards = len(self.board.cards) if self.board is not None else 0
        return (self.state is AppState.PLAYING and self.motion.active(now, cards)) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PICKER:
            self.renderer.draw_picker(surface)
            self._surfaces.draw(surface)
        elif self.state is AppState.PLAYING and self.board is not None and self.layout is not None:
            self.renderer.draw_board(surface, self.album, self.board, self.layout, self.book, self.motion)
            self._surfaces.draw(surface)
        else:
            self._surfaces.draw(surface)

    def persist(self) -> None:
        self.progress.save(self.level, self.album.album_id, self.book, self.history)

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        if self.state is AppState.PICKER:
            self._show_picker_controls()
        elif self.board is not None:
            self.layout = self._board_layout()
            self.controls.relayout_board(self.layout, self.album, self.board)
            self.controls.sync(self.board)
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, logical: tuple[int, int]) -> bool:
        """Deliver one complete tap at a logical position (tests/tools)."""

        point = (int(logical[0]), int(logical[1]))
        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        self._activated = False
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._dispatch(translated)
        return self._activated

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._idle_hints = 0

    # -- album shelf ------------------------------------------------------------

    def _open_picker(self) -> None:
        self._activated = True
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.timeline.clear()
        self.motion.clear()
        self.audio.stop_speech()
        self.board = None
        self.layout = None
        self.state = AppState.PICKER
        self.cast.reset()
        self.cast.waving = True
        self._busy = False
        self._show_picker_controls()
        self.persist()
        self._note_activity()
        self._dirty = True

    def _show_picker_controls(self) -> None:
        layout = PickerLayout.build(len(ALBUMS), self._layout_source.protected)
        self.controls.show_picker(layout, self.book, self.album.album_id)

    def _on_album(self, album_id: str) -> None:
        if self.state is not AppState.PICKER:
            return
        self._activated = True
        self.album = album_by_id(album_id)
        self._start_board()

    # -- board flow ---------------------------------------------------------------

    def _board_layout(self) -> BoardLayout:
        button = self._layout_source.control_height(68, maximum=84)
        return BoardLayout.build(LEVELS[self.level], self._layout_source.protected, album_button_size=button)

    def _start_board(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        self.cast.waving = False
        self.cast.reset()
        spec = LEVELS[max(0, min(MAX_LEVEL, self.level))]
        subjects = choose_subjects(self.album, spec.pairs, self.book, self.rng)
        self.board = MemoryBoard(subjects, self.rng)
        self.layout = self._board_layout()
        self.audio.prepare_names(subjects)
        self.controls.show_board(self.layout, self.album, self.board)
        self.state = AppState.PLAYING
        self.session_id = self._new_session_id()
        self.motion.deal_start = now
        deal = 0.045 * len(self.board.cards) + 0.25
        self._busy = True
        self.timeline.after(deal, self._end_busy)
        self.audio.play("whoosh")
        self.audio.lilli("ready.go")
        self.cast.point(1.4)
        self._note_activity()
        self._dirty = True

    def _end_busy(self) -> None:
        self._busy = False
        self._note_activity()
        self._dirty = True

    def _on_card(self, index: int) -> None:
        board = self.board
        if board is None or self.state is not AppState.PLAYING or self._busy:
            return
        outcome = board.flip(index)
        if outcome.result is FlipResult.IGNORED:
            return
        self._activated = True
        now = self.clock()
        self.motion.turn(index, now, Side.BACK, Side.FACE)
        self.motion.halos.pop(index, None)
        self.audio.play("flip")
        if outcome.result is FlipResult.MATCH:
            self.timeline.after(MATCH_LEAD, lambda: self._celebrate(outcome.first, outcome.second, outcome.subject_id))
        elif outcome.result is FlipResult.MISS:
            self.timeline.after(MISS_LOOK, lambda: self._miss(outcome.first, outcome.second))
            self.timeline.after(MISS_HOLD, self._cover_miss)
        self._dirty = True

    def _celebrate(self, first: int, second: int, subject_id: str) -> None:
        board = self.board
        layout = self.layout
        if board is None or layout is None:
            return
        now = self.clock()
        for index in (first, second):
            self.motion.halos[index] = (now, now + STICKER_DELAY)
            rect = layout.cards[index]
            self.motion.add_fx("sparkle", (rect.right - rect.width // 5, rect.top + rect.height // 5), now)
        self.audio.play("match")
        if not self.audio.say_name(subject_id) and board.matched % 2 == 1:
            self.audio.lilli("praise.general")
        self.cast.correct()
        self.events.pair_found(self.session_id, {"pairs": board.matched, "total": board.pairs, "album": self.album.album_id})
        self.book.add(self.album.album_id, subject_id)
        self.motion.incoming.add(subject_id)
        self.timeline.after(STICKER_DELAY, lambda: self._send_stickers(first, second, subject_id))
        self.controls.sync(board)
        self._dirty = True

    def _send_stickers(self, first: int, second: int, subject_id: str) -> None:
        layout = self.layout
        if layout is None:
            return
        now = self.clock()
        well = layout.wells[self.album.subject_ids.index(subject_id)]
        asset_id = self.album.subject(subject_id).asset_id
        for order, index in enumerate((first, second)):
            self.motion.gone.add(index)
            self.motion.flights.append(Flight(now + order * 0.08, layout.cards[index].center, well.center, asset_id))
        self.audio.play("whoosh")
        self.timeline.after(FLIGHT_SECONDS + 0.1, lambda: self._land(subject_id, well.center))
        self._dirty = True

    def _land(self, subject_id: str, centre: tuple[int, int]) -> None:
        now = self.clock()
        self.motion.incoming.discard(subject_id)
        self.motion.pops[subject_id] = now
        self.motion.add_fx("star_burst", centre, now)
        self.audio.play("pop")
        board = self.board
        if board is not None and board.complete and not self.motion.incoming:
            self._busy = True
            self.timeline.after(COMPLETE_DELAY, self._complete_board)
        self._dirty = True

    def _miss(self, first: int, second: int) -> None:
        board = self.board
        if board is None:
            return
        now = self.clock()
        self.motion.wobbles[first] = now
        self.motion.wobbles[second] = now
        self.audio.play("miss")
        self.cast.try_again()
        if board.miss_streak and board.miss_streak % 3 == 0:
            self.audio.lilli("encourage.retry")
        self._dirty = True

    def _cover_miss(self) -> None:
        board = self.board
        if board is None:
            return
        now = self.clock()
        for index in board.cover_miss():
            self.motion.turn(index, now, Side.FACE, Side.BACK)
        self.audio.play("unflip")
        if board.miss_streak >= peek_threshold(board.pairs):
            self.timeline.after(FLIP_SECONDS + 0.2, self._peek)
            self._busy = True
        self._note_activity()
        self._dirty = True

    def _peek(self) -> None:
        """Lilli shows one pair for a moment after a long run of misses."""

        board = self.board
        layout = self.layout
        if board is None or layout is None:
            self._busy = False
            return
        pair = board.peek_pair(self.rng)
        board.reset_streak()
        if pair is None:
            self._busy = False
            return
        now = self.clock()
        self._busy = True
        for index in pair:
            self.motion.peek.add(index)
            self.motion.turn(index, now, Side.BACK, Side.FACE)
            self.motion.halos[index] = (now, now + PEEK_SHOW)
        self.cast.point(PEEK_SHOW + 0.4)
        self.audio.play("peek")
        self.audio.lilli("encourage.progress")
        self.timeline.after(PEEK_SHOW, lambda: self._end_peek(pair))
        self._dirty = True

    def _end_peek(self, pair: tuple[int, int]) -> None:
        now = self.clock()
        for index in pair:
            self.motion.peek.discard(index)
            self.motion.turn(index, now, Side.FACE, Side.BACK)
        self.audio.play("unflip")
        self.timeline.after(FLIP_SECONDS, self._end_busy)
        self._dirty = True

    def _complete_board(self) -> None:
        board = self.board
        if board is None or self.state is not AppState.PLAYING:
            return
        result = BoardResult(self.level, board.pairs, board.misses)
        self.history = (self.history + [result])[-HISTORY_LIMIT:]
        played_level = self.level
        self.level = adapt_level(self.level, self.history)
        self.persist()
        self.events.game_completed(
            self.session_id,
            {
                "pairs": board.pairs,
                "misses": board.misses,
                "level": played_level + 1,
                "album": self.album.album_id,
                "stickers": self.book.count(self.album.album_id),
            },
        )
        self.audio.play("fanfare")
        self.audio.lilli("celebrate.success")
        self.cast.correct()
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NAVY),
            scene=CompletionScene(self.kit, character="lilli", star_total=board.pairs, secondary_glyph="page"),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("button.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", "★"),),
                achievement_count=board.pairs,
                secondary_label=self._text("button.albums", "▦"),
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart, on_secondary=self._open_picker))
        self.timeline.clear()
        self.state = AppState.TERMINAL
        self._busy = False
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self._start_board()

    # -- hints ----------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        board = self.board
        layout = self.layout
        if board is None or layout is None or self._busy or board.pending_miss is not None:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        self.cast.point(1.8)
        if board.open_index is not None:
            target = board.open_index  # "find its twin": the waiting card glows
            self.motion.halos[target] = (now, now + HINT_GLOW)
        else:
            focused = self.controls.focused_card()
            down = [i for i, card in enumerate(board.cards) if card.state is CardState.DOWN]
            if not down:
                return
            target = focused if focused in down else self.rng.choice(down)
            self.motion.wobbles[target] = now
            self.motion.halos[target] = (now, now + HINT_GLOW)
        self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default

    def _new_session_id(self) -> str:
        self._boards_played += 1
        return f"{self._session_prefix}-{self._boards_played}-{self.rng.randrange(1_000_000):06d}"


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """True inside the play surface and outside the Greia protected region(s)."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "MemoryApp", "Timeline"]
