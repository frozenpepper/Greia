"""Lifecycle, timing and input for Specchi Magici (Magic Mirrors).

Half a mosaic is laid on one side of Lilli's magic mirror. The child builds
the reflection on the glass: pick a tile from the kit (tap, or drag it), then
tap the cell where its mirror image belongs. Arrows / D-pad / left stick move
the shared kit focus ring over the same tiles and cells; Space / Enter / the
south button pick and place; Escape / the east button put a tile back.

* a tile that matches stays: it drops in with a sparkle and Lilli cheers;
* any other tile wobbles on the glass and fades (the kit has unlimited
  tiles, so nothing is lost); Lilli thinks and the picture tile it should
  mirror glows; from the second miss of a mosaic Lilli points and a see-through
  tile pulses on the right spot (she shows, the child still places it);
  retries are unlimited and there is never a failure sound;
* idle ~6 s -> Lilli points and the next picture tile to mirror glows; then
  its empty spot glows; then the right tile in the kit hops.

A finished mosaic shines along the mirror line, the tiles ripple outwards and
the next mosaic arrives. After five mosaics the shared cast completion scene
appears ("play again"); the ladder (vertical mirror -> more tiles and colours
-> turned tiles -> water mirror -> both mirrors) adapts between sets.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import math
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlArt,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitControl,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
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
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .mirror_art import MirrorArt
    from .mirror_audio import MirrorAudio
    from .mirror_controls import MirrorControls
    from .mirror_layout import LILLI_HEIGHT, LILLI_TAP_RECT, cell_at, cell_rect, tray_rects
    from .mirror_model import (
        CHALLENGE_COUNT,
        GRID_COLS,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        MirrorAxis,
        MirrorRoundFactory,
        MirrorSession,
        PlaceOutcome,
        PlaceResult,
        adapt_level,
    )
    from .mirror_renderer import (
        CELEBRATE_SECONDS,
        WOBBLE_SECONDS,
        LilliCast,
        MirrorRenderer,
        SceneMotion,
        SceneView,
        mirror_points,
    )
    from .mirror_services import EventPort, ProgressPort
else:
    from mirror_art import MirrorArt
    from mirror_audio import MirrorAudio
    from mirror_controls import MirrorControls
    from mirror_layout import LILLI_HEIGHT, LILLI_TAP_RECT, cell_at, cell_rect, tray_rects
    from mirror_model import (
        CHALLENGE_COUNT,
        GRID_COLS,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        MirrorAxis,
        MirrorRoundFactory,
        MirrorSession,
        PlaceOutcome,
        PlaceResult,
        adapt_level,
    )
    from mirror_renderer import (
        CELEBRATE_SECONDS,
        WOBBLE_SECONDS,
        LilliCast,
        MirrorRenderer,
        SceneMotion,
        SceneView,
        mirror_points,
    )
    from mirror_services import EventPort, ProgressPort

INTRO_SECONDS = 0.6
FINISH_SECONDS = CELEBRATE_SECONDS + 0.2
GLOW_SECONDS = 2.6
MAX_SCHEDULED = 48
# A press that moves less than this (logical px) before release is a tap, not a
# drag: a tapped tile stays in hand until a cell is tapped (tap-then-tap).
DRAG_THRESHOLD_PX = 14
STAGE_PLUM = (86, 58, 100)  # theme text-ink token "plum": the dark stage


class AppState(StrEnum):
    INTRO = "intro"
    PLAYING = "playing"
    CELEBRATE = "celebrate"
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

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


@dataclass(slots=True)
class _Press:
    kind: str  # "tile" | "cell" | "kit" | "other"
    index: int
    start: tuple[int, int]
    cell: tuple[int, int] | None = None
    moved: bool = False


class MirrorActivity:
    """Coordinate the mirror session, kit focus, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: MirrorAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: MirrorArt | None = None,
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
        self.factory = MirrorRoundFactory(self.rng)
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._sets_played = 0

        saved = progress.load()
        self.level = saved.level
        self._history = saved.history

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else MirrorArt(loader=ControlArt(max_entries=64))
        feedback = CastFeedback("lilli", height=LILLI_HEIGHT, art=self.art.loader, idle_variant="happy", hold_seconds=1.4, clock=clock)
        self.cast = LilliCast(feedback, self.art, clock)
        self.renderer = MirrorRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = MirrorControls(self.kit, on_tile=self._on_tile_key, on_cell=self._on_cell_key, on_listen=self._listen)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.session: MirrorSession | None = None
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.INTRO
        self.session_id = ""
        self.held: int | None = None
        self.dragging: tuple[int, int] | None = None
        self.hovered_tile: int | None = None
        self.hovered_cell: tuple[int, int] | None = None
        self._board_cell: tuple[int, int] | None = None
        self._press: _Press | None = None
        self._busy_until = 0.0
        self._intro_start = clock()
        self._last_axis: MirrorAxis | None = None
        self._running = True
        self.ready_published = False
        self._welcomed = False
        self._dirty = True
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._prompted = False
        self._corrects = 0
        self.start_set()

    # -- main loop ----------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                lively = self.step()
                frame = frames.frame(dirty=self._dirty)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                        self._welcome()
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=lively or self._input.repeating)
        finally:
            self.persist()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something moves on screen."""

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
        if self.state is AppState.TERMINAL:
            return False
        lively = (
            self.motion.active(now)
            or self.cast.animating
            or self.state in (AppState.INTRO, AppState.CELEBRATE)
            or self.dragging is not None
        )
        if lively:
            self._dirty = True
        return lively

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL and self.session is not None:
            now = self.clock()
            self.renderer.draw(surface, self._view(now), self.motion, now)
        self._surfaces.draw(surface)

    def _view(self, now: float) -> SceneView:
        session = self.session
        assert session is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        intro = 1.0
        if self.state is AppState.INTRO:
            intro = max(0.0, min(1.0, (now - self._intro_start) / INTRO_SECONDS))
        tiles = {g.cell: g.piece for g in puzzle.givens}
        tiles.update(session.placed)
        hovered_cell = self.hovered_cell
        if self.controls.layer.focus_visible:
            hovered_cell = self.controls.focused_cell()
        return SceneView(
            axis=puzzle.axis,
            picture_cells=self._picture_cells(),
            tiles=tiles,
            tray=puzzle.tray,
            tray_rects=self._tray_rects,
            held=self.held,
            dragging=self.dragging,
            hovered_tile=self.hovered_tile,
            hovered_cell=hovered_cell,
            intro=intro,
        )

    def _picture_cells(self) -> frozenset[tuple[int, int]]:
        puzzle = self.session.current_puzzle if self.session is not None else None
        if puzzle is None:
            return frozenset()
        return frozenset(
            (row, col) for row in range(GRID_ROWS) for col in range(GRID_COLS) if not puzzle.target_side((row, col))
        )

    def persist(self) -> None:
        if self.session is not None:
            self.progress.save(self.level, self.session.history)

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.held is not None or self.dragging is not None:
                self._put_back()
            else:
                self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self._put_back()
            return
        if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            self._dirty = True  # keep the platform pointer live
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen, hires=True)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.place_bar(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> None:
        if isinstance(kit_input, KitPointer):
            if kit_input.phase is not PointerPhase.MOVE:
                self._note_activity()
            if self._surfaces.overlays:
                self._surfaces.dispatch(kit_input)
            else:
                self._pointer(kit_input)
        elif isinstance(kit_input, SemanticInputEvent):
            self._note_activity()
            if (
                kit_input.action is SemanticAction.CANCEL
                and kit_input.edge is InputEdge.PRESSED
                and not self._surfaces.overlays
            ):
                self._put_back()
                if self.state is AppState.PLAYING:
                    self.controls.focus_tile(0)
            else:
                self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True

    def _pointer(self, sample: KitPointer) -> None:
        point = sample.position
        if sample.phase is PointerPhase.MOVE:
            self._hover(point)
            press = self._press
            if press is not None and press.kind == "kit":
                self.controls.layer.handle_event(sample)
                return
            if press is None:
                self.controls.layer.handle_event(sample)  # kit hover states
                return
            if (
                press.kind == "tile"
                and not press.moved
                and math.hypot(point[0] - press.start[0], point[1] - press.start[1]) > DRAG_THRESHOLD_PX
            ):
                press.moved = True
                self.held = press.index
                self.audio.play("pick")
            if press.moved:
                self.dragging = point
                self._dirty = True
            return
        if sample.phase is PointerPhase.CANCEL:
            self._press = None
            self.controls.layer.handle_event(sample)
            self._put_back()
            return
        if sample.phase is PointerPhase.DOWN:
            self.controls.layer.focus_visible = False
            self._press = self._press_at(point)
            if self._press.kind == "kit":
                self.controls.layer.handle_event(sample)
            self._dirty = True
            return
        # UP
        press, self._press = self._press, None
        if press is None:
            return
        if press.kind == "kit":
            self.controls.layer.handle_event(sample)
        elif press.moved:
            self.dragging = None
            cell = cell_at(point)
            if cell is not None and self.held is not None and self.session is not None and self.session.is_open(cell):
                self._place(self.held, cell)
            else:
                self._put_back()
        elif press.kind == "tile":
            self._pick(press.index)
        elif press.kind == "cell" and press.cell is not None:
            self._cell_tapped(press.cell)
        else:
            self._ambient_tap(point)
        self._dirty = True

    def _press_at(self, point: tuple[int, int]) -> _Press:
        target = self.controls.layer.hit(point)
        if isinstance(target, KitControl):
            return _Press("kit", -1, point)
        if self.state is AppState.PLAYING:
            tile = self._tile_at(point)
            if tile is not None:
                return _Press("tile", tile, point)
            cell = cell_at(point)
            if cell is not None:
                return _Press("cell", -1, point, cell)
        return _Press("other", -1, point)

    def _hover(self, point: tuple[int, int]) -> None:
        playing = self.state is AppState.PLAYING
        tile = self._tile_at(point) if playing else None
        cell = cell_at(point) if playing else None
        if (tile, cell) != (self.hovered_tile, self.hovered_cell):
            self.hovered_tile, self.hovered_cell = tile, cell
            self._dirty = True

    def _tile_at(self, point: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self._tray_rects):
            if rect.collidepoint(point):
                return index
        return None

    def tap(self, logical: tuple[int, int]) -> None:
        """Deliver one complete tap at a logical position (tests/tools)."""

        point = (int(logical[0]), int(logical[1]))
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 6) -> None:
        """Deliver one complete drag in logical coordinates (tests/tools)."""

        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        for step in range(1, steps + 1):
            t = step / steps
            self._dispatch(
                KitPointer(PointerPhase.MOVE, (int(start[0] + (end[0] - start[0]) * t), int(start[1] + (end[1] - start[1]) * t)))
            )
        self._dispatch(KitPointer(PointerPhase.UP, end))

    def press(self, key: int) -> None:
        """Deliver one key press through the shared navigation mapping."""

        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    def _ambient_tap(self, point: tuple[int, int]) -> None:
        """Lilli repeats the goal when tapped; a tap elsewhere puts a tile back."""

        if self.state is AppState.TERMINAL:
            return
        if LILLI_TAP_RECT.collidepoint(point):
            self._listen()
        elif self.held is not None:
            self._put_back()

    # -- picking and placing ------------------------------------------------------

    def _on_tile_key(self, index: int) -> None:
        """Keyboard/controller: pick the focused tile up, then go to the board."""

        if self._pick(index) and self.held == index:
            self.controls.focus_board(self._board_cell)

    def _on_cell_key(self, row: int, col: int) -> None:
        self._board_cell = (row, col)
        if self.state is not AppState.PLAYING:
            return
        if self.held is None:
            self._nudge_tray()
            self.controls.focus_tile(0)
            return
        held = self.held
        self._place(held, (row, col))
        if self.state is AppState.PLAYING and self.controls.layer.focus_visible:
            self.controls.focus_tile(held)

    def _pick(self, index: int) -> bool:
        puzzle = self.session.current_puzzle if self.session is not None else None
        if self.state is not AppState.PLAYING or puzzle is None or not 0 <= index < len(puzzle.tray):
            return False
        if self.held == index:
            self.held = None  # tapping the tile in hand puts it back
        else:
            self.held = index
            self.audio.play("pick")
            self.audio.shape_name(puzzle.tray[index].kind)
        self._dirty = True
        return True

    def _cell_tapped(self, cell: tuple[int, int]) -> None:
        session = self.session
        if self.state is not AppState.PLAYING or session is None:
            return
        if self.held is not None and session.is_open(cell):
            self._place(self.held, cell)
            return
        if session.piece_at(cell) is not None:
            self.motion.pokes[cell] = self.clock()
            self.audio.play("pick")
        elif self.held is None and session.is_open(cell):
            self._nudge_tray()
        self._dirty = True

    def _nudge_tray(self) -> None:
        """Empty-handed tap on the glass: the kit hops once, 'pick one first'."""

        now = self.clock()
        for index in range(len(self._tray_rects)):
            self.motion.tray_hops[index] = now + 0.05 * index

    def _put_back(self) -> None:
        self.held = None
        self.dragging = None
        self._press = None
        self._dirty = True

    def _place(self, index: int, cell: tuple[int, int]) -> None:
        session = self.session
        now = self.clock()
        if session is None or self.state is not AppState.PLAYING or now < self._busy_until:
            return
        puzzle = session.current_puzzle
        if puzzle is None or not 0 <= index < len(puzzle.tray):
            return
        piece = puzzle.tray[index]
        result = session.place(piece, cell)
        if result.outcome is PlaceOutcome.IGNORED:
            return
        self.held = None
        self.dragging = None
        self.motion.clear_hints()
        if result.correct:
            self._placed(cell, result)
        else:
            self._declined(cell, piece, result)
        self._sync_controls()
        self._dirty = True

    def _placed(self, cell: tuple[int, int], result: PlaceResult) -> None:
        now = self.clock()
        self.motion.drops[cell] = now
        self.motion.add_fx("sparkle", cell_rect(*cell).center, now + 0.15)
        self.audio.play("place")
        self._corrects += 1
        if result.puzzle_completed:
            self._celebrate(result)
            return
        self.audio.play("chime")
        self.cast.correct()
        if self._corrects % 2 == 1:
            self.audio.praise()

    def _declined(self, cell: tuple[int, int], piece, result: PlaceResult) -> None:
        session = self.session
        assert session is not None
        now = self.clock()
        self.motion.wobble = (cell, piece, now)
        self._busy_until = now + WOBBLE_SECONDS * 0.6
        self.audio.play("hum")
        self.cast.try_again()
        expected = result.focus.piece if result.focus is not None else None
        if (
            expected is not None
            and result.outcome is PlaceOutcome.WRONG_PIECE
            and (piece.kind, piece.color_index) == (expected.kind, expected.color_index)
        ):
            # The unreflected copy: the right tile, facing the wrong way.
            self.audio.say("turn_it")  # "Turn it around!"
        elif session.misses % 2 == 1:
            self.audio.say("retry_1" if result.outcome is PlaceOutcome.WRONG_CELL else "retry_2")
        focus = result.focus
        misses = session.misses
        self.timeline.after(WOBBLE_SECONDS * 0.6, lambda: self._explain(focus, misses))

    def _explain(self, focus, misses: int) -> None:
        """After a miss: the picture tile glows; from the 2nd miss Lilli shows the spot."""

        session = self.session
        if session is None or self.state is not AppState.PLAYING or focus is None:
            return
        puzzle = session.current_puzzle
        if puzzle is None or session.placed.get(focus.cell) == focus.piece:
            focus = session.next_unmatched()
            if focus is None or puzzle is None:
                return
        now = self.clock()
        source = puzzle.source_of(focus.cell)
        if source is not None:
            self.motion.glow_source(source.cell, now + self._hints.animation_seconds(GLOW_SECONDS))
        if misses >= 2:
            self.cast.point(1.8)
            self.audio.say_if_quiet("try_this_spot")  # Lilli shows the spot
            self.motion.ghost = (focus.cell, focus.piece, now + GLOW_SECONDS)
            if focus.piece in puzzle.tray:
                self.motion.tray_hops[puzzle.tray.index(focus.piece)] = now
        self._note_activity()
        self._dirty = True

    # -- set / mosaic flow ----------------------------------------------------------

    def start_set(self) -> None:
        self.timeline.clear()
        history = self.session.history if self.session is not None else self._history
        self.session = MirrorSession(self.factory.build_set(self.level), level=self.level, history=history)
        self._sets_played += 1
        self.session_id = f"{self._session_prefix}-{self._sets_played}-{self.rng.randrange(1_000_000):06d}"
        self.controls.set_progress(0)
        self._begin_mosaic()

    def _begin_mosaic(self) -> None:
        session = self.session
        assert session is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        self.motion.reset()
        self.cast.reset()
        self.held = None
        self.dragging = None
        self._press = None
        self._busy_until = 0.0
        self._prompted = False
        self._tray_rects = tray_rects(len(puzzle.tray))
        self.controls.set_tray(self._tray_rects)
        self.state = AppState.INTRO
        self._intro_start = self.clock()
        self._sync_controls()
        self.timeline.after(INTRO_SECONDS, self._play)
        self._note_activity()
        self._dirty = True

    def _play(self) -> None:
        session = self.session
        if self.state is not AppState.INTRO or session is None or session.current_puzzle is None:
            return
        self.state = AppState.PLAYING
        puzzle = session.current_puzzle
        # Wordless start: Lilli points at the mirror, the line sparkles.
        self.cast.point(1.4)
        now = self.clock()
        points = mirror_points(puzzle.axis)
        for order, point in enumerate(points[1:-1:2] if len(points) > 3 else points):
            self.motion.add_fx("sparkle", point, now + 0.12 * order)
        if self._last_axis is not None and puzzle.axis is not self._last_axis:
            self.audio.say("prompt_place")  # a new kind of mirror: say the goal again
            self._prompted = True
        elif self._last_axis is None:
            self.audio.say_if_quiet("look_mirror_line")  # the first mirror of the visit
        self._last_axis = puzzle.axis
        self._sync_controls()
        if self.controls.layer.focus_visible:
            self.controls.focus_tile(0)
        self._note_activity()
        self._dirty = True

    def _welcome(self) -> None:
        if not self._welcomed:
            self._welcomed = True
            self.audio.say("welcome")
            self._prompted = True

    def _celebrate(self, result: PlaceResult) -> None:
        session = self.session
        assert session is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        now = self.clock()
        self.state = AppState.CELEBRATE
        self.motion.celebrate = now
        for order, point in enumerate(mirror_points(puzzle.axis)):
            self.motion.add_fx("sparkle", point, now + 0.08 * order)
        self.audio.play("sparkle")
        self.cast.correct()
        milestone = session.consume_milestone()
        if milestone is not None:
            self.events.mosaic_completed(self.session_id, milestone)
        self.controls.set_progress(session.finished_count)
        self._sync_controls()
        if result.session_complete:
            self.audio.say("celebrate.success")
            self.timeline.after(FINISH_SECONDS, self._finish)
        else:
            self.audio.say("mosaic_complete")
            self.timeline.after(CELEBRATE_SECONDS, self._next_mosaic)

    def _next_mosaic(self) -> None:
        session = self.session
        if self.state is not AppState.CELEBRATE or session is None:
            return
        if session.next_puzzle():
            self._begin_mosaic()

    def _finish(self) -> None:
        session = self.session
        if session is None or self.state is not AppState.CELEBRATE:
            return
        payload = session.consume_completion()
        if payload is not None:
            self.level = adapt_level(session.level, session.history)
            self.persist()
            self.events.gallery_completed(self.session_id, payload)
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=STAGE_PLUM),
            scene=CompletionScene(self.kit, character="lilli", star_total=CHALLENGE_COUNT),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("button.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", ""),),
                achievement_count=CHALLENGE_COUNT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.state = AppState.TERMINAL
        self._sync_controls()
        self._dirty = True

    def _restart(self) -> None:
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.start_set()

    def _listen(self) -> None:
        """Replay Lilli's spoken goal (listen button, or a tap on Lilli)."""

        self.audio.say("prompt_place")
        self.cast.point(1.4)
        self._dirty = True

    # -- hints ----------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        session = self.session
        if session is None or now < self._busy_until or self.dragging is not None:
            return
        if not self._hints.is_due(now, self._last_activity):
            return
        target = session.next_unmatched()
        puzzle = session.current_puzzle
        if target is None or puzzle is None:
            return
        step = self._hints.fire(now)
        session.note_hint()
        self.cast.point(self._hints.animation_seconds(1.8))
        source = puzzle.source_of(target.cell)
        if source is not None:
            self.motion.glow_source(source.cell, now + self._hints.animation_seconds(GLOW_SECONDS))
        if step == 1 and not self._prompted:
            self.audio.say("prompt_place")
            self._prompted = True
        if step >= 2:
            self.motion.ring_target(target.cell, now + self._hints.animation_seconds(GLOW_SECONDS))
        if step >= 3 and target.piece in puzzle.tray:
            self.motion.tray_hops[puzzle.tray.index(target.piece)] = now
        self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _sync_controls(self) -> None:
        session = self.session
        playing = self.state is AppState.PLAYING
        open_cells = (
            [(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS) if session.is_open((r, c))]
            if session is not None
            else []
        )
        self.controls.sync(open_cells=open_cells, playing=playing)

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default


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


__all__ = ["AppState", "DRAG_THRESHOLD_PX", "MirrorActivity", "Timeline"]
