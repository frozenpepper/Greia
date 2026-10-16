"""Lifecycle, timing and input for La Torre delle Forme (Shape Tower).

In Dani's playroom a paper outline stands on the workbench: a lighthouse, a
rocket, a cat ... The child fills it with wooden blocks from the kit:

* pick a block (tap it, or drag it straight onto the build); tap the block in
  hand again, press the turn button, R, or the west controller button to
  turn it a quarter; while a block is held over the build, the outline glows
  where it fits; tap or drop to put it there;
* arrows / D-pad / left stick move the shared kit focus ring over the kit,
  the build's open cells and the buttons; Space / Enter / the south button
  pick and place; Escape / the east button put a block back;
* a block that fits drops in with a wooden "tock" and Dani cheers; any other
  try wobbles and fades back (the kit never runs out, so nothing is lost),
  Dani thinks and shows what to change: "turn it" (the turn arrow pulses on
  the block), "it goes there" (the right spot glows), or the block shakes
  "not this one". From the second miss of a build Dani demonstrates: a
  see-through block glides from the kit to a right spot (the child still
  places it). Retries are unlimited; there is never a failure sound;
* idle ~6 s -> Dani points and a right spot glows; then the right kit block
  hops; then Dani demonstrates.

Nothing falls, nothing is cleared, there is no clock. A finished build
bounces from the bench up, Dani cheers and says what it is (when a shared
name clip exists) and the next outline arrives. After five builds the shared
cast completion scene appears ("build again"); the rung (slots -> turn it
-> extra blocks -> silhouette only -> two extra blocks) adapts between sets.
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
from greia_platform.input_core import InputEdge, InteractionProfile, PhysicalControl, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.pygame_input import PygameInputTranslator
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .torre_art import TorreArt
    from .torre_audio import TorreAudio
    from .torre_content import TorreSetFactory
    from .torre_controls import TorreControls
    from .torre_layout import CELL, DANI_HEIGHT, DANI_TAP_RECT, BoardFrame, tray_rects
    from .torre_model import (
        BUILDS_PER_SET,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Cell,
        PlaceOutcome,
        PlaceResult,
        Placement,
        TorreSession,
        adapt_level,
    )
    from .torre_renderer import CELEBRATE_SECONDS, WOBBLE_SECONDS, DaniCast, Glide, SceneMotion, SceneView, TorreRenderer
    from .torre_services import EventPort, ProgressPort, TorreProgress
else:
    from torre_art import TorreArt
    from torre_audio import TorreAudio
    from torre_content import TorreSetFactory
    from torre_controls import TorreControls
    from torre_layout import CELL, DANI_HEIGHT, DANI_TAP_RECT, BoardFrame, tray_rects
    from torre_model import (
        BUILDS_PER_SET,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        Cell,
        PlaceOutcome,
        PlaceResult,
        Placement,
        TorreSession,
        adapt_level,
    )
    from torre_renderer import CELEBRATE_SECONDS, WOBBLE_SECONDS, DaniCast, Glide, SceneMotion, SceneView, TorreRenderer
    from torre_services import EventPort, ProgressPort, TorreProgress

INTRO_SECONDS = 0.6
FINISH_SECONDS = CELEBRATE_SECONDS + 0.2
GLOW_SECONDS = 2.6
TURN_HINT_SECONDS = 2.6
MAX_SCHEDULED = 48
# A press that moves less than this (logical px) before release is a tap, not a
# drag: a tapped block stays in hand until the build is tapped (tap-then-tap).
DRAG_THRESHOLD_PX = 14
PLAYROOM_DUSK = (52, 84, 130)  # deep ocean ("play" Collection hue, darkened)
TURN_CONTROLS = frozenset({PhysicalControl.CONTROLLER_FACE_WEST, PhysicalControl.CONTROLLER_FACE_NORTH})


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
    kind: str  # "tile" | "board" | "kit" | "other"
    index: int
    start: tuple[int, int]
    moved: bool = False


class TorreActivity:
    """Coordinate the build session, kit focus, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: TorreAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: TorreArt | None = None,
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
        self.factory = TorreSetFactory(self.rng)
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._sets_played = 0

        saved = progress.load()
        self.level = saved.level
        self._history = saved.history
        self._builds = saved.builds
        self._stars = saved.stars
        self._first_visit = saved.builds == 0

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else TorreArt(loader=ControlArt(max_entries=64))
        feedback = CastFeedback("dani", height=DANI_HEIGHT, art=self.art.loader, idle_variant="happy", hold_seconds=1.4, clock=clock)
        self.cast = DaniCast(feedback, self.art, clock)
        self.renderer = TorreRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = TorreControls(
            self.kit, on_tile=self._on_tile_key, on_cell=self._on_cell_key, on_turn=self._turn, on_listen=self._listen
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._physical = PygameInputTranslator(InteractionProfile.NAVIGATION)
        self.controls.place_bar(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.session: TorreSession | None = None
        self.frame: BoardFrame | None = None
        self.completion: PygameCompletionScreen | None = None
        self.state = AppState.INTRO
        self.session_id = ""
        self.held: int | None = None
        self.dragging: tuple[int, int] | None = None
        self.hovered_tile: int | None = None
        self.preview: Placement | None = None
        self._pointer_at: tuple[int, int] | None = None
        self._board_cell: Cell | None = None
        self._press: _Press | None = None
        self._tray_rects: tuple[pygame.Rect, ...] = ()
        self._busy_until = 0.0
        self._intro_start = clock()
        self._running = True
        self.ready_published = False
        self._welcomed = False
        self._dirty = True
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._corrects = 0
        self.start_set()

    # -- main loop ------------------------------------------------------------------

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
        assert session is not None and self.frame is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        intro = 1.0
        if self.state is AppState.INTRO:
            intro = max(0.0, min(1.0, (now - self._intro_start) / INTRO_SECONDS))
        return SceneView(
            plan=puzzle.plan,
            style=puzzle.style,
            frame=self.frame,
            placed=session.placed,
            kit=tuple(session.kit),
            tray_rects=self._tray_rects,
            held=self.held,
            dragging=self.dragging,
            hovered_tile=self.hovered_tile,
            preview=self.preview,
            intro=intro,
        )

    def persist(self) -> None:
        history = self.session.history if self.session is not None else self._history
        self.progress.save(TorreProgress(self.level, history, self._builds, self._stars))

    # -- input ----------------------------------------------------------------------

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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._note_activity()
            self._turn()
            return
        physical = self._physical.physical_digital(event)
        if physical is not None and physical[0] in TURN_CONTROLS:
            if physical[1] is InputEdge.PRESSED:
                self._note_activity()
                self._turn()
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
        self.canvas = PygameReferenceCanvas(self.screen)
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
            self._update_preview()
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True

    def _pointer(self, sample: KitPointer) -> None:
        point = sample.position
        if sample.phase is PointerPhase.MOVE:
            self._hover(point)
            press = self._press
            if press is None or press.kind == "kit":
                self.controls.layer.handle_event(sample)  # kit hover / press states
                return
            if (
                press.kind == "tile"
                and not press.moved
                and math.hypot(point[0] - press.start[0], point[1] - press.start[1]) > DRAG_THRESHOLD_PX
            ):
                press.moved = True
                if self.held != press.index:
                    self.held = press.index
                    self.audio.play("pick")
            if press.moved:
                self.dragging = point
                self._update_preview()
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
            if self.held is not None and self.frame is not None and self.frame.near_board(point):
                self._attempt(self.held, point)
            else:
                self._put_back()
        elif press.kind == "tile":
            self._tile_tapped(press.index)
        elif press.kind == "board":
            self._board_tapped(point)
        else:
            self._ambient_tap(point)
        self._update_preview()
        self._dirty = True

    def _press_at(self, point: tuple[int, int]) -> _Press:
        target = self.controls.layer.hit(point)
        if isinstance(target, KitControl):
            return _Press("kit", -1, point)
        if self.state is AppState.PLAYING:
            tile = self._tile_at(point)
            if tile is not None:
                return _Press("tile", tile, point)
            if self.frame is not None and self.frame.near_board(point, margin=CELL // 4):
                return _Press("board", -1, point)
        return _Press("other", -1, point)

    def _hover(self, point: tuple[int, int]) -> None:
        playing = self.state is AppState.PLAYING
        tile = self._tile_at(point) if playing else None
        self._pointer_at = point
        if tile != self.hovered_tile:
            self.hovered_tile = tile
            self._dirty = True
        self._update_preview()

    def _update_preview(self) -> None:
        """Glow the outline where the block in hand would fit, under pointer/focus."""

        preview: Placement | None = None
        session, frame = self.session, self.frame
        if self.state is AppState.PLAYING and self.held is not None and session is not None and frame is not None:
            block = session.kit_block(self.held)
            if self.controls.layer.focus_visible:
                cell = self.controls.focused_cell()
                if cell is not None:
                    preview = session.best_fit(block, (cell[0] + 0.5, cell[1] + 0.5))
            else:
                point = self.dragging or self._pointer_at
                if point is not None and frame.near_board(point):
                    preview = session.best_fit(block, frame.to_cells(point))
        if preview != self.preview:
            self.preview = preview
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

    def board_point(self, placement: Placement) -> tuple[int, int]:
        """Logical centre of ``placement`` on the current build (tests/tools)."""

        assert self.frame is not None
        return self.frame.placement_rect(placement).center

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    def _ambient_tap(self, point: tuple[int, int]) -> None:
        """Dani says the goal again when tapped; a tap elsewhere puts a block back."""

        if self.state is AppState.TERMINAL:
            return
        if DANI_TAP_RECT.collidepoint(point):
            self._listen()
        elif self.held is not None:
            self._put_back()

    # -- picking, turning, placing --------------------------------------------------

    def _on_tile_key(self, index: int) -> None:
        """Keyboard/controller: pick the focused block (again = turn it), then go to the build."""

        if self.held == index:
            self._turn()
            return
        if self._pick(index):
            self.controls.focus_board(self._board_cell)
            self._update_preview()

    def _on_cell_key(self, cell: Cell) -> None:
        self._board_cell = cell
        if self.state is not AppState.PLAYING:
            return
        if self.held is None:
            self._nudge_tray()
            self.controls.focus_tile(0)
            return
        held = self.held
        assert self.frame is not None
        self._attempt(held, self.frame.cell_rect(cell).center)
        if self.state is AppState.PLAYING and self.held is None and self.controls.layer.focus_visible:
            self.controls.focus_tile(held)

    def _tile_tapped(self, index: int) -> None:
        if self.held == index:
            self._turn()
        else:
            self._pick(index)

    def _pick(self, index: int) -> bool:
        session = self.session
        if self.state is not AppState.PLAYING or session is None or not 0 <= index < len(session.kit):
            return False
        self.held = index
        self.audio.play("pick")
        self._sync_controls()
        self._dirty = True
        return True

    def _turn(self) -> None:
        """Turn the block in hand (or the focused kit block) a quarter clockwise."""

        session = self.session
        if self.state is not AppState.PLAYING or session is None:
            return
        index = self.held if self.held is not None else self.controls.focused_tile()
        if index is None or not 0 <= index < len(session.kit):
            return
        if self.held is None:
            self._pick(index)
        if session.turn(index):
            self.audio.play("turn")
            self.motion.turn_hints.pop(index, None)
        else:
            self.motion.tray_shakes[index] = self.clock()  # a square looks the same every way
        self._update_preview()
        self._dirty = True

    def _board_tapped(self, point: tuple[int, int]) -> None:
        if self.state is not AppState.PLAYING:
            return
        if self.held is not None:
            self._attempt(self.held, point)
        else:
            self._nudge_tray()

    def _nudge_tray(self) -> None:
        """Empty-handed tap on the build: the kit hops once, "pick one first"."""

        now = self.clock()
        for index in range(len(self._tray_rects)):
            self.motion.tray_hops[index] = now + 0.05 * index
        self._dirty = True

    def _put_back(self) -> None:
        self.held = None
        self.dragging = None
        self._press = None
        self.preview = None
        self._sync_controls()
        self._dirty = True

    def _attempt(self, index: int, point: tuple[int, int]) -> None:
        session, frame = self.session, self.frame
        now = self.clock()
        if session is None or frame is None or self.state is not AppState.PLAYING or now < self._busy_until:
            return
        block = session.kit_block(index)
        result = session.try_place(index, frame.to_cells(point))
        if result.outcome is PlaceOutcome.IGNORED:
            return
        self.dragging = None
        self.preview = None
        self.motion.clear_hints()
        if result.correct:
            self.held = None
            self._placed(result)
        else:
            self._declined(index, block, point, result)
        self._sync_controls()
        self._dirty = True

    def _placed(self, result: PlaceResult) -> None:
        assert result.placement is not None and self.frame is not None
        now = self.clock()
        rect = self.frame.placement_rect(result.placement)
        self.motion.drops[result.placement] = now
        self.motion.add_fx("dust_puff", (rect.centerx, rect.bottom - 8), now + 0.2)
        self.motion.add_fx("sparkle", rect.center, now + 0.15)
        self.audio.play("clack")
        self._corrects += 1
        if result.puzzle_completed:
            self._celebrate(result)
            return
        self.audio.play("chime")
        self.cast.correct()
        if self._corrects % 2 == 1:
            self.audio.say("praise.general")

    def _declined(self, index: int, block, point: tuple[int, int], result: PlaceResult) -> None:
        session = self.session
        assert session is not None
        now = self.clock()
        self.motion.wobble = (block, point, now)
        self._busy_until = now + WOBBLE_SECONDS * 0.6
        self.audio.play("hum")
        self.cast.try_again()
        if session.misses % 2 == 1:
            self.audio.say("encourage.retry")
        if result.outcome is PlaceOutcome.NO_FIT:
            # This kind belongs nowhere in the build: it shakes "not me" and goes back.
            self.motion.tray_shakes[index] = now + WOBBLE_SECONDS * 0.5
            self.held = None
        misses = session.misses
        self.timeline.after(WOBBLE_SECONDS * 0.6, lambda: self._explain(index, result.outcome, misses))

    def _explain(self, index: int, outcome: PlaceOutcome, misses: int) -> None:
        """After a miss: say what to change; from the 2nd miss Dani demonstrates."""

        session = self.session
        if session is None or self.state is not AppState.PLAYING:
            return
        now = self.clock()
        if misses >= 2:
            self._demonstrate(now)
        elif outcome is PlaceOutcome.NEEDS_TURN:
            self.motion.turn_hints[index] = now + TURN_HINT_SECONDS
        elif outcome is PlaceOutcome.WRONG_SPOT:
            spot = session.anywhere(session.kit_block(index))
            if spot is not None:
                self.motion.target_glow = (spot, now + GLOW_SECONDS)
        self._note_activity()
        self._dirty = True

    def _demonstrate(self, now: float) -> None:
        """Dani shows one right move: the block glides from the kit to its place."""

        session = self.session
        if session is None:
            return
        step = session.next_step()
        if step is None or not 0 <= step.kit_index < len(self._tray_rects):
            return
        self.cast.point(GLOW_SECONDS)
        self.motion.glide = Glide(step.placement.block, self._tray_rects[step.kit_index].center, step.placement, now)
        self.motion.tray_hops[step.kit_index] = now
        if step.needs_turn(session.kit_block(step.kit_index)):
            self.motion.turn_hints[step.kit_index] = now + TURN_HINT_SECONDS + 1.0

    # -- set / build flow -------------------------------------------------------------

    def start_set(self) -> None:
        self.timeline.clear()
        history = self.session.history if self.session is not None else self._history
        self.session = TorreSession(self.factory.build_set(self.level), level=self.level, history=history)
        self._sets_played += 1
        self.session_id = f"{self._session_prefix}-{self._sets_played}-{self.rng.randrange(1_000_000):06d}"
        self.controls.set_progress(0)
        self._begin_build()

    def _begin_build(self) -> None:
        session = self.session
        assert session is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        self.motion.reset()
        self.cast.reset()
        self.held = None
        self.dragging = None
        self.preview = None
        self._press = None
        self._busy_until = 0.0
        self.frame = BoardFrame(puzzle.plan)
        self._tray_rects = tray_rects(len(puzzle.kit))
        self.controls.set_build(self.frame, puzzle.plan.fills, self._tray_rects)
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
        # Wordless start: Dani points at the outline, which shimmers once; the
        # build's name is said when a shared name clip exists.
        now = self.clock()
        self.cast.point(1.4)
        self.motion.outline_pulse = now
        if self._welcomed:
            self.audio.noun(puzzle.plan.noun)
        if self._first_visit and session.puzzle_index == 0 and self._sets_played == 1:
            # The very first build ever: Dani shows the move once.
            self.timeline.after(1.2, lambda: self._demonstrate(self.clock()))
        self._sync_controls()
        if self.controls.layer.focus_visible:
            self.controls.focus_tile(0)
        self._note_activity()
        self._dirty = True

    def _welcome(self) -> None:
        if not self._welcomed:
            self._welcomed = True
            self.audio.say("ready.go")

    def _celebrate(self, result: PlaceResult) -> None:
        session = self.session
        assert session is not None and self.frame is not None
        puzzle = session.current_puzzle
        assert puzzle is not None
        now = self.clock()
        self.state = AppState.CELEBRATE
        self.motion.celebrate = now
        board = self.frame.rect
        self.motion.add_fx("confetti", (board.centerx, board.top + 20), now + 0.1)
        for order, placement in enumerate(session.placed):
            self.motion.add_fx("sparkle", self.frame.placement_rect(placement).center, now + 0.3 + 0.08 * order)
        self.audio.play("sparkle")
        self.cast.correct()
        self._builds += 1
        self._stars += 1
        milestone = session.consume_milestone()
        if milestone is not None:
            self.events.build_completed(self.session_id, milestone)
        self.controls.set_progress(session.finished_count)
        self._sync_controls()
        if result.session_complete:
            self.audio.say("celebrate.success")
            self.timeline.after(FINISH_SECONDS, self._finish)
        else:
            if not self.audio.noun(puzzle.plan.noun):
                self.audio.say("encourage.progress")
            self.timeline.after(CELEBRATE_SECONDS, self._next_build)

    def _next_build(self) -> None:
        session = self.session
        if self.state is not AppState.CELEBRATE or session is None:
            return
        if session.next_puzzle():
            self._begin_build()

    def _finish(self) -> None:
        session = self.session
        if session is None or self.state is not AppState.CELEBRATE:
            return
        payload = session.consume_completion()
        if payload is not None:
            self.level = adapt_level(session.level, session.history)
            self.persist()
            self.events.set_completed(self.session_id, payload)
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=PLAYROOM_DUSK),
            scene=CompletionScene(self.kit, character="dani", star_total=BUILDS_PER_SET),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("button.play_again", "↻"),
                body_lines=(self._text("victory.subtitle", ""),),
                achievement_count=BUILDS_PER_SET,
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
        """Say the goal again (listen button, or a tap on Dani): name + pointing."""

        session = self.session
        puzzle = session.current_puzzle if session is not None else None
        if puzzle is None or not self.audio.noun(puzzle.plan.noun):
            self.audio.say("ready.go")
        self.cast.point(1.4)
        self.motion.outline_pulse = self.clock()
        self._dirty = True

    # -- hints --------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        session = self.session
        if session is None or now < self._busy_until or self.dragging is not None:
            return
        if not self._hints.is_due(now, self._last_activity):
            return
        plan = session.next_step()
        if plan is None:
            return
        step = self._hints.fire(now)
        glow = self._hints.animation_seconds(GLOW_SECONDS)
        session.note_hint()
        self.cast.point(self._hints.animation_seconds(1.8))
        if step == 1:
            self.motion.target_glow = (plan.placement, now + glow)
        elif step == 2:
            self.motion.target_glow = (plan.placement, now + glow)
            self.motion.tray_hops[plan.kit_index] = now
            if plan.needs_turn(session.kit_block(plan.kit_index)):
                self.motion.turn_hints[plan.kit_index] = now + self._hints.animation_seconds(TURN_HINT_SECONDS)
        else:
            self._demonstrate(now)
        self._dirty = True

    # -- helpers ------------------------------------------------------------------------

    def _sync_controls(self) -> None:
        session = self.session
        playing = self.state is AppState.PLAYING
        open_cells = tuple(session.open_fills) if session is not None else ()
        can_turn = bool(session is not None and self.held is not None and session.kit_block(self.held).rotates)
        self.controls.sync(open_cells=open_cells, playing=playing, can_turn=can_turn)

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


__all__ = ["AppState", "DRAG_THRESHOLD_PX", "Timeline", "TorreActivity"]
