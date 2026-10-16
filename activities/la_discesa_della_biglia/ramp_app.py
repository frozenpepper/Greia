"""Lifecycle, input and feedback timeline for Tito's Marble Run.

One visit is one set of four boards. On each board the child puts the tray
pieces into the shining slots (drag and drop, or tap a piece then a slot;
arrows / D-pad / stick + Space / south button move the kit focus over tray,
slots and GO), taps a placed ramp to turn it, and presses GO to watch the
marble run. Every run ends -- basket, rolled off the board, stopped, or the
time cap -- and the pieces stay where they are, with the path the marble took
left as faint dots so the child can adjust.

Feedback grammar (ADR 0037): in the basket = Tito ``pose_cheer`` + confetti +
basket wiggle + praise; a miss = Tito ``pose_think`` + dust puff, then he
demonstrates one next step (a ghost piece in its slot, a turn arrow, or a
"take it back" arrow); from the third miss on a board the demonstrated step is
also carried out. Idle for ~6 s: Tito points and the next slot glows; idle
again (or the hint button): the ghost demonstration. Never timed, never
punished; the set ends on the shared cast completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import time
from uuid import uuid4

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
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
    from .ramp_art import RunArt, Setting, setting_for
    from .ramp_audio import RampAudio
    from .ramp_content import MARBLE_RADIUS, PieceKind
    from .ramp_controls import RunControls, slot_id, tray_id
    from .ramp_engine import MarbleRun, Outcome
    from .ramp_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, BoardView
    from .ramp_model import SNAP_AFTER_MISSES, HintAction, HintPlanner, HintStep, Visit
    from .ramp_renderer import Drag, RunCast, RunMotion, RunRenderer
    from .ramp_services import EventPort, ProgressPort
else:
    from ramp_art import RunArt, Setting, setting_for
    from ramp_audio import RampAudio
    from ramp_content import MARBLE_RADIUS, PieceKind
    from ramp_controls import RunControls, slot_id, tray_id
    from ramp_engine import MarbleRun, Outcome
    from ramp_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, BoardView
    from ramp_model import SNAP_AFTER_MISSES, HintAction, HintPlanner, HintStep, Visit
    from ramp_renderer import Drag, RunCast, RunMotion, RunRenderer
    from ramp_services import EventPort, ProgressPort

CELEBRATE_SECONDS = 2.0
MISS_PAUSE_SECONDS = 0.9
SNAP_DELAY_SECONDS = 1.3
RETRY_VOICE_GAP = 8.0
CLACK_GAP = 0.07
DRAG_SLOP = 12
DROP_REACH = 40  # logical px around a slot that still counts as "on it"
MAX_SCHEDULED = 32


class AppState(StrEnum):
    BUILD = "build"
    RUNNING = "running"
    PAUSE = "pause"  # a run just ended; showing where the marble went
    CELEBRATE = "celebrate"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for scripted moments (celebrate, demonstrate)."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = [entry for entry in self._entries if entry[0] <= now]
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return bool(due)

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


@dataclass(slots=True)
class Press:
    """A pointer press on gameplay (tray tile or board slot) not yet a tap or drag."""

    target: str  # "tray" | "slot"
    index: int
    origin: tuple[int, int]


class MarbleRunActivity:
    """Coordinate the board model, physics, kit controls, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        visit: Visit,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: RampAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: RunArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.visit = visit
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.clock = clock
        self._visit_id = uuid4().hex

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else RunArt(self.kit)
        self.controls = RunControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            go_label=resources.text("btn.go"),
            on_tray=self._on_tray,
            on_slot=self._on_slot,
            on_go=self._on_go,
            on_hint=self._on_hint,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self.motion = RunMotion()
        self.timeline = Timeline(clock)
        self.setting: Setting = setting_for(visit.board_set.setting)
        self.completion: PygameCompletionScreen | None = None
        self.cast: RunCast | None = None
        self.renderer: RunRenderer | None = None
        self._cast_height = 0
        self.scene: pygame.Surface
        self.state = AppState.BUILD
        self.run_: MarbleRun | None = None
        self.trail: tuple[tuple[float, float], ...] = ()
        self.drag: Drag | None = None
        self._press: Press | None = None
        self._running = True
        self._ready_published = False
        self._activated = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._last_retry_voice = -100.0
        self._last_clack = -100.0
        self._said_go = False
        self._start_board()

    @property
    def board_state(self):
        return self.visit.state

    @property
    def view(self) -> BoardView:
        return self.controls.view

    # -- main loop ------------------------------------------------------------

    def run(self) -> int:
        # Input redraws, motion animates; the idle build screen is static.
        frames = FrameGovernor(redraw_on_input=True, keepalive_seconds=1.0)
        last = self.clock()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._surfaces.dispatch(repeat)
                now = self.clock()
                animating = self.step(min(0.1, now - last))
                last = now
                frame = frames.frame(
                    dirty=self.controls.layer.invalidation.should_draw,
                    animating=animating,
                    ambient=self.state is AppState.TERMINAL,
                )
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.progress.save(self.visit.progress)
            self.typography.clear()
        return 0

    def step(self, dt: float) -> bool:
        """Advance the run, timers and motion; return True while something moves."""

        now = self.clock()
        changed = self.timeline.run_due()
        if self.cast is not None:
            changed = self.cast.update() or changed
        self.motion.prune(now)
        if self.state is AppState.RUNNING and self.run_ is not None:
            for hit in self.run_.advance(dt):
                self._on_hit(hit.tag, now)
            if self.run_.finished:
                self._on_run_end()
        self._maybe_hint(now)
        cast_moving = self.cast is not None and self.cast.animating
        return (
            changed
            or self.state in (AppState.RUNNING, AppState.PAUSE, AppState.CELEBRATE)
            or self.motion.active(now)
            or cast_moving
            or self.drag is not None
        )

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL and self.renderer is not None:
            running = self.state in (AppState.RUNNING, AppState.PAUSE)
            self.renderer.draw(
                surface,
                self.scene,
                self.board_state,
                self.run_ if running else None,
                self.view,
                self.motion,
                self.clock(),
                trail=self.trail,
                marble_home=not running and self.state is not AppState.CELEBRATE,
                in_basket=self.state is AppState.CELEBRATE,
                drag=self.drag,
                go_rect=self.controls.go.rect,
                cast_midbottom=self.controls.screen.cast_midbottom,
            )
        self._surfaces.draw(surface)

    # -- input ------------------------------------------------------------------

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._relayout()
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self._cancel_pointer()
            return
        translated = self._input.translate(event)
        if translated is None:
            return
        if isinstance(translated, KitPointer):
            self._pointer(translated)
            return
        self._note_activity()
        if self._surfaces.dispatch(translated) is not UiEventResult.IGNORED:
            self._activated = True

    def _pointer(self, pointer: KitPointer) -> None:
        if self.state is AppState.TERMINAL:
            self._surfaces.dispatch(pointer)
            return
        phase = pointer.phase
        if phase is PointerPhase.CANCEL:
            self._cancel_pointer()
            self._surfaces.dispatch(pointer)
            return
        if phase is PointerPhase.DOWN:
            self._note_activity()
            self.controls.layer.focus_visible = False
            hit = self._gameplay_hit(pointer.position) if self.state is AppState.BUILD else None
            if hit is not None:
                self._press = Press(hit[0], hit[1], pointer.position)
                return
            self._surfaces.dispatch(pointer)
            return
        if phase is PointerPhase.MOVE:
            if self._press is not None and self.drag is None:
                dx = pointer.position[0] - self._press.origin[0]
                dy = pointer.position[1] - self._press.origin[1]
                if dx * dx + dy * dy > DRAG_SLOP * DRAG_SLOP:
                    self._start_drag(pointer.position)
            if self.drag is not None:
                self.drag.position = pointer.position
                self.drag.hover_slot = self._slot_near(pointer.position)
                return
            if self._press is None:
                self._surfaces.dispatch(pointer)
            return
        # UP
        press, self._press = self._press, None
        if self.drag is not None:
            self._drop(pointer.position)
            return
        if press is not None:
            if press.target == "tray":
                self._on_tray(press.index)
            else:
                self._on_slot(press.index)
            return
        self._surfaces.dispatch(pointer)

    def _gameplay_hit(self, position: tuple[int, int]) -> tuple[str, int] | None:
        state = self.board_state
        for index, button in enumerate(self.controls.tray):
            if button.visible and button.enabled and button.rect.collidepoint(position):
                return ("tray", index)
        for index, centre in enumerate(state.board.slots):
            if self.view.slot_rect(centre).inflate(8, 8).collidepoint(position):
                return ("slot", index)
        return None

    def _slot_near(self, position: tuple[int, int]) -> int | None:
        best: tuple[float, int] | None = None
        for index, centre in enumerate(self.board_state.board.slots):
            rect = self.view.slot_rect(centre)
            if not rect.inflate(2 * DROP_REACH, 2 * DROP_REACH).collidepoint(position):
                continue
            d = (rect.centerx - position[0]) ** 2 + (rect.centery - position[1]) ** 2
            if best is None or d < best[0]:
                best = (d, index)
        return best[1] if best is not None else None

    def _start_drag(self, position: tuple[int, int]) -> None:
        press = self._press
        state = self.board_state
        if press is None:
            return
        if press.target == "tray":
            if not state.in_tray(press.index):
                return  # a faded tile (piece already on the board) only calls it back
            piece, from_slot = press.index, None
            state.select(piece)
        else:
            occupant = state.occupant(press.index)
            if occupant is None:
                return
            piece, from_slot = occupant, press.index
        self.drag = Drag(piece, position, from_slot, self._slot_near(position))
        self._press = None
        self.audio.play("pick")
        self._sync()

    def _drop(self, position: tuple[int, int]) -> None:
        drag, self.drag = self.drag, None
        if drag is None:
            return
        state = self.board_state
        target = self._slot_near(position)
        self._activated = True
        if target is not None:
            if target != drag.from_slot:
                state.place(drag.piece, target)
                self._placed(target)
        elif drag.from_slot is not None:
            state.remove(drag.piece)
            self.audio.play("remove")
        self._sync(refocus=True)

    def _cancel_pointer(self) -> None:
        self._press = None
        if self.drag is not None:
            self.drag = None
            self._sync()

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        self._activated = False
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._handle_event(pygame.event.Event(event_type, pos=raw_pos, button=1))
        return self._activated

    def drag_to(self, raw_from: tuple[int, int], raw_to: tuple[int, int], steps: int = 6) -> bool:
        """Deliver a complete drag between physical positions (tests/tools)."""

        self._activated = False
        self._handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=raw_from, button=1))
        for index in range(1, steps + 1):
            x = raw_from[0] + (raw_to[0] - raw_from[0]) * index / steps
            y = raw_from[1] + (raw_to[1] - raw_from[1]) * index / steps
            self._handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(int(x), int(y)), rel=(0, 0), buttons=(1, 0, 0)))
        self._handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=raw_to, button=1))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press (tests/tools); returns whether something acted."""

        self._activated = False
        for event_type in (pygame.KEYDOWN, pygame.KEYUP):
            self._handle_event(pygame.event.Event(event_type, key=key, mod=0, unicode="", scancode=0))
        return self._activated

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    def _relayout(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = self._make_input()
        self._cancel_pointer()
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._prepare_board_art()
        self._sync()

    # -- board flow ---------------------------------------------------------------

    def _start_board(self) -> None:
        self.timeline.clear()
        self.motion.clear()
        self.run_ = None
        self.trail = ()
        self.drag = None
        self._press = None
        self._said_go = False
        self.state = AppState.BUILD
        self._prepare_board_art()
        assert self.cast is not None
        self.cast.reset()
        self.cast.wave()
        self._sync(refocus=True)
        self._note_activity()

    def _prepare_board_art(self) -> None:
        self.scene = self.art.compose_scene(self.visit.board, self.view, self.setting)
        height = self.controls.screen.cast_height
        if self.cast is None or height != self._cast_height:
            feedback = CastFeedback("tito", height=height, art=self.art.art, clock=self.clock)
            self.cast = RunCast(
                feedback,
                self.art.cast_pose("pose_point", height),
                self.art.cast_pose("pose_wave", height),
                self.clock,
            )
            self.renderer = RunRenderer(self.art, self.cast)
            self._cast_height = height

    def _sync(self, *, refocus: bool = False) -> None:
        editable = self.state is AppState.BUILD and self.drag is None
        self.controls.sync(self.board_state, editable=self.state is AppState.BUILD, done=self.visit.completed)
        if refocus and editable:
            self.controls.focus_default(self.board_state)

    def _on_tray(self, piece: int) -> None:
        state = self.board_state
        if self.state is not AppState.BUILD or piece >= len(state.board.pieces):
            return
        self._activated = True
        self._note_activity()
        if state.in_tray(piece):
            state.select(piece)
            self.audio.play("pick")
        else:
            state.remove(piece)  # call a piece back from the board
            self.audio.play("remove")
        self._sync()

    def _on_slot(self, slot: int) -> None:
        state = self.board_state
        if self.state is not AppState.BUILD or slot >= len(state.board.slots):
            return
        self._activated = True
        self._note_activity()
        occupant = state.occupant(slot)
        if occupant is None:
            if state.place_selected(slot) is None:
                self.motion.pops[slot] = self.clock()  # nothing left in the tray: a soft no
                self.audio.play("clack")
                return
            self._placed(slot)
            self._sync()
            if self.controls.layer.focus_visible:
                self.controls.focus_default(state)
            return
        if state.turn(occupant):
            self.motion.pops[slot] = self.clock()
            self.audio.play("turn")
        else:
            self.motion.pops[slot] = self.clock()
            self.audio.play("clack")
        self._sync()

    def _placed(self, slot: int) -> None:
        now = self.clock()
        self.motion.pops[slot] = now
        self.motion.add_fx("sparkle", self.view.slot_rect(self.board_state.board.slots[slot]).center, self.view.length(110), now)
        self.audio.play("place")

    def _on_go(self) -> None:
        if self.state is not AppState.BUILD:
            return
        self._activated = True
        self._note_activity()
        state = self.board_state
        state.summary.runs += 1
        self.run_ = state.new_run()
        self.trail = ()
        self.motion.demo = None
        self.motion.pulses.clear()
        self.state = AppState.RUNNING
        self.audio.play("go")
        if not self._said_go:
            self._said_go = True
            self.audio.say("go")
        self.events.run_started(self._visit_id, state.board.board_id, state.summary.runs)
        self._sync()

    def _on_hit(self, tag: str, now: float) -> None:
        if tag.startswith("piece:"):
            slot = int(tag.split(":", 1)[1])
            occupant = self.board_state.occupant(slot)
            if occupant is not None and self.board_state.kind(occupant) is PieceKind.BUMPER:
                self.motion.squash[slot] = now
                self.audio.play("bonk")
                return
        if now - self._last_clack >= CLACK_GAP:
            self._last_clack = now
            self.audio.play("clack")

    def _on_run_end(self) -> None:
        run = self.run_
        assert run is not None
        if run.outcome is Outcome.BASKET:
            self._board_solved()
        else:
            self._missed(run)

    def _board_solved(self) -> None:
        now = self.clock()
        state = self.board_state
        assert self.cast is not None
        self.state = AppState.CELEBRATE
        self.cast.correct()
        self.audio.play("basket")
        self.audio.say("basket")
        self.motion.wiggle = now
        basket = self.view.point(state.board.basket.x, state.board.basket.rim)
        self.motion.add_fx("confetti", (basket[0], basket[1] - self.view.length(110)), self.view.length(190), now)
        self.motion.add_fx("star_burst", (basket[0], basket[1] - self.view.length(40)), self.view.length(120), now)
        self.events.basket_hit(self._visit_id, state.board.board_id, state.summary.runs)
        self.visit.finish_board()
        self.progress.save(self.visit.progress)
        self._sync()
        self.timeline.after(CELEBRATE_SECONDS, self._after_celebration)

    def _missed(self, run: MarbleRun) -> None:
        now = self.clock()
        state = self.board_state
        assert self.cast is not None
        state.summary.misses += 1
        outcome = run.outcome or Outcome.STOPPED
        self.state = AppState.PAUSE
        self.trail = tuple(run.trail)
        self.cast.try_again()
        self.audio.play("lost" if outcome is Outcome.LOST else "stopped")
        x, y = run.drawn_position()
        if outcome is Outcome.LOST:
            y = min(y, run.basket.floor) + MARBLE_RADIUS
        self.motion.add_fx("dust_puff", self.view.point(x, y), self.view.length(110), now)
        if now - self._last_retry_voice >= RETRY_VOICE_GAP:
            self._last_retry_voice = now
            self.audio.say("retry")
        self.events.basket_missed(self._visit_id, state.board.board_id, state.summary.runs, outcome.value)
        self._sync()
        self.timeline.after(MISS_PAUSE_SECONDS, self._back_to_build)

    def _back_to_build(self) -> None:
        if self.state is not AppState.PAUSE:
            return
        self.state = AppState.BUILD
        self.run_ = None
        self._sync(refocus=self.controls.layer.focus_visible)
        self._note_activity()
        self._demonstrate(snap=self.board_state.summary.misses >= SNAP_AFTER_MISSES)

    def _after_celebration(self) -> None:
        if self.visit.complete:
            self._complete_set()
            return
        self.visit.next_board()
        self._start_board()

    def _complete_set(self) -> None:
        progress = self.visit.progress
        finished = self.setting
        set_id = self.visit.board_set.set_id
        self.visit.finish_set()
        self.progress.save(progress)
        self.events.set_completed(self._visit_id, set_id, self.visit.completed)
        self.timeline.clear()
        self.motion.clear()
        self.audio.play("fanfare")
        self.audio.say("complete")
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=finished.dusk),
            scene=CompletionScene(self.kit, character="tito", star_total=self.visit.total),
        )
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("btn.play_again"),
                achievement_count=self.visit.completed,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL

    def _restart(self) -> None:
        """Play the next set (one transaction for keyboard/controller/pointer)."""

        self._activated = True
        self._surfaces.pop_overlay()
        if self.completion is not None:
            self.completion.clear()
            self.completion = None
        self._visit_id = uuid4().hex
        self.visit.start_next_set()
        self.setting = setting_for(self.visit.board_set.setting)
        self._start_board()

    # -- hints ----------------------------------------------------------------------

    def _on_hint(self) -> None:
        if self.state is not AppState.BUILD:
            return
        self._activated = True
        self._note_activity()
        self._demonstrate(snap=False)

    def _demonstrate(self, *, snap: bool) -> None:
        """Show the single next step; on repeated misses, also carry it out."""

        if self.state is not AppState.BUILD:
            return
        now = self.clock()
        state = self.board_state
        step = HintPlanner.next_step(state)
        state.summary.hints += 1
        assert self.cast is not None
        self.cast.point(2.0)
        self.audio.play("hint")
        if step.action is HintAction.GO:
            self.motion.go_pulse = now
            self.controls.layer.focus("go")
            return
        assert step.slot is not None
        self.motion.demo = (step, now, self._demo_origin(step))
        self.motion.pulse(step.slot, now)
        if self.controls.layer.focus_visible:
            self._focus_for(step)
        if snap:
            self.timeline.after(SNAP_DELAY_SECONDS, lambda: self._snap(step))

    def _demo_origin(self, step: HintStep) -> tuple[int, int] | None:
        """Where the demonstrated piece travels from (its tray tile)."""

        if step.action is not HintAction.PLACE or step.kind is None:
            return None
        state = self.board_state
        for piece in state.tray_pieces():
            if state.kind(piece) is step.kind:
                return self.controls.tray[piece].rect.center
        return None

    def _snap(self, step: HintStep) -> None:
        if self.state is not AppState.BUILD or self.drag is not None:
            return
        if HintPlanner.apply(self.board_state, step) and step.slot is not None:
            self.motion.demo = None
            if step.action is HintAction.REMOVE:
                self.audio.play("remove")
            else:
                self._placed(step.slot)
            self._sync()
            if HintPlanner.next_step(self.board_state).action is HintAction.GO:
                self.motion.go_pulse = self.clock()

    def _focus_for(self, step: HintStep) -> None:
        state = self.board_state
        if step.action is HintAction.PLACE and step.kind is not None:
            pieces = [p for p in state.tray_pieces() if state.kind(p) is step.kind]
            if pieces and state.selected != pieces[0]:
                state.select(pieces[0])
                self._sync()
                self.controls.layer.focus(tray_id(pieces[0]))
                return
        if step.slot is not None:
            self.controls.layer.focus(slot_id(step.slot))

    def _maybe_hint(self, now: float) -> None:
        if self.state is not AppState.BUILD or self.timeline.busy or self.drag is not None:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        assert self.cast is not None
        if step == 1:
            # First nudge: Tito points and the next spot glows (no answer shown).
            plan = HintPlanner.next_step(self.board_state)
            self.cast.point(self._hints.animation_seconds(1.8))
            if plan.slot is not None:
                self.motion.pulse(plan.slot, now)
            else:
                self.motion.go_pulse = now
            self.audio.say("nudge")
            return
        self._demonstrate(snap=False)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "MarbleRunActivity", "Timeline"]
