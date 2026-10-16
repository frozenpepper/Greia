"""Lifecycle, input and feedback timeline for Bridge Builders.

One visit is one set of four crossings. On each crossing a cast friend waits
on the left bank and the picnic waits on the right. The child lifts a plank
from the tray (planks are drawn at the river's own scale: one board = one
dash of water) and stands it on a span's hinge, or stands a pillar on a river
rock (drag and drop, or tap a piece then its place; arrows / D-pad / stick +
Space / south button move the kit focus over tray, spans, rocks and GO).
Nothing on the screen says whether a choice is right: GO is the test. The
planks swing down, the friend walks across, and the bridge shows what
happened -- the picnic, or a gentle stop at the edge of a plank that falls
short (the missing dashes light up), or a thin plank bending under a heavy
pumpkin -- then the friend walks home and the planks stand up again.

Feedback grammar (ADR 0037): at the picnic = the friend's ``pose_cheer`` +
confetti + praise (just-right planks sparkle on the way); a stop = the
friend's ``pose_think`` + dust puff, then a demonstration of one next step (a
ghost plank or pillar travelling from the tray to its place); from the third
stop on a crossing the demonstrated step is also carried out. Idle for ~6 s:
the friend points and the next place glows; idle again (or the hint button):
the demonstration. Never timed, never punished; a set ends on the shared cast
completion scene.
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
    from .ponti_art import BridgeArt
    from .ponti_audio import BridgeAudio
    from .ponti_content import COMPLETION_FRIEND, PieceKind
    from .ponti_controls import BridgeControls, seat_id, spot_id, tray_id
    from .ponti_layout import BANK_TOP, CAST_HEIGHT, REFERENCE_HEIGHT, REFERENCE_WIDTH, UNIT, CrossingView
    from .ponti_model import SNAP_AFTER_MISSES, BridgeState, Failure, Fit, HintAction, HintPlanner, HintStep, Visit
    from .ponti_renderer import BridgeMotion, BridgeRenderer, Drag, TravelerCast
    from .ponti_run import BridgeRun
    from .ponti_services import EventPort, ProgressPort
else:
    from ponti_art import BridgeArt
    from ponti_audio import BridgeAudio
    from ponti_content import COMPLETION_FRIEND, PieceKind
    from ponti_controls import BridgeControls, seat_id, spot_id, tray_id
    from ponti_layout import BANK_TOP, CAST_HEIGHT, REFERENCE_HEIGHT, REFERENCE_WIDTH, UNIT, CrossingView
    from ponti_model import SNAP_AFTER_MISSES, BridgeState, Failure, Fit, HintAction, HintPlanner, HintStep, Visit
    from ponti_renderer import BridgeMotion, BridgeRenderer, Drag, TravelerCast
    from ponti_run import BridgeRun
    from ponti_services import EventPort, ProgressPort

CELEBRATE_SECONDS = 2.2
PAUSE_SECONDS = 1.4
SNAP_DELAY_SECONDS = 1.3
RETRY_VOICE_GAP = 8.0
DRAG_SLOP = 12
DROP_REACH = 36  # logical px around a target that still counts as "on it"
MAX_SCHEDULED = 32
DUSK = (52, 96, 70)


class AppState(StrEnum):
    BUILD = "build"
    RUNNING = "running"  # planks swing down, the friend walks
    PAUSE = "pause"  # the walk stopped; showing what happened
    RETURN = "return"  # the friend walks home, planks stand up
    CELEBRATE = "celebrate"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for scripted moments (celebrate, pause, snap)."""

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
    """A pointer press on gameplay not yet a tap or a drag."""

    target: str  # "tray" | "seat" | "spot"
    index: int
    origin: tuple[int, int]


class BridgeActivity:
    """Coordinate the bridge model, the GO test, kit controls, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        visit: Visit,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: BridgeAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: BridgeArt | None = None,
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

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else BridgeArt(self.kit)
        self.controls = BridgeControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            go_label=resources.text("btn.go"),
            on_tray=self._on_tray,
            on_seat=self._on_seat,
            on_spot=self._on_spot,
            on_go=self._on_go,
            on_hint=self._on_hint,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self.motion = BridgeMotion()
        self.timeline = Timeline(clock)
        self.completion: PygameCompletionScreen | None = None
        self.cast: TravelerCast | None = None
        self.renderer: BridgeRenderer | None = None
        self.scene: pygame.Surface
        self.view = CrossingView(visit.crossing)
        self.state = AppState.BUILD
        self.run_: BridgeRun | None = None
        self.drag: Drag | None = None
        self._press: Press | None = None
        self._running = True
        self._ready_published = False
        self._activated = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._last_retry_voice = -100.0
        self._said_go = False
        self._start_crossing()

    @property
    def bridge(self) -> BridgeState:
        return self.visit.state

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
        """Advance the test, timers and motion; return True while something moves."""

        now = self.clock()
        changed = self.timeline.run_due()
        if self.cast is not None:
            changed = self.cast.update() or changed
        self.motion.prune(now)
        if self.state in (AppState.RUNNING, AppState.RETURN) and self.run_ is not None:
            for moment in self.run_.advance(dt):
                self._on_moment(moment, now)
        self._maybe_hint(now)
        cast_moving = self.cast is not None and self.cast.animating
        return (
            changed
            or self.state in (AppState.RUNNING, AppState.PAUSE, AppState.RETURN, AppState.CELEBRATE)
            or self.motion.active(now)
            or cast_moving
            or self.drag is not None
        )

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL and self.renderer is not None:
            self.renderer.draw(
                surface,
                self.scene,
                self.bridge,
                self.view,
                self.motion,
                self.clock(),
                run=self.run_ if self.state is not AppState.BUILD else None,
                drag=self.drag,
                targets=self._target_rects(),
                go_rect=self.controls.go.rect,
            )
        self._surfaces.draw(surface)

    def _target_rects(self) -> dict[str, pygame.Rect]:
        bridge = self.bridge
        rects = {f"seat:{span.seat}": self.view.span_band(span) for span in bridge.spans()}
        for spot in range(len(bridge.crossing.spots)):
            rects[f"spot:{spot}"] = self.view.spot_rect(spot)
        for index in range(len(bridge.crossing.pieces)):
            rects[f"tray:{index}"] = self.controls.tray[index].rect
        return rects

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
                self.drag.hover = self._drop_target(pointer.position, self.drag.piece)
                return
            if self._press is None:
                self._surfaces.dispatch(pointer)
            return
        press, self._press = self._press, None
        if self.drag is not None:
            self._drop(pointer.position)
            return
        if press is not None:
            {"tray": self._on_tray, "seat": self._on_seat, "spot": self._on_spot}[press.target](press.index)
            return
        self._surfaces.dispatch(pointer)

    def _gameplay_hit(self, position: tuple[int, int]) -> tuple[str, int] | None:
        for index, button in enumerate(self.controls.tray):
            if button.visible and button.enabled and button.rect.collidepoint(position):
                return ("tray", index)
        for spot in range(len(self.bridge.crossing.spots)):
            if self.view.spot_rect(spot).collidepoint(position):
                return ("spot", spot)
        for index, span in enumerate(self.bridge.spans()):
            if self.view.seat_rect(span).collidepoint(position):
                return ("seat", index)
        return None

    def _drop_target(self, position: tuple[int, int], piece: int) -> str | None:
        """Target id ("seat:<seat>" / "spot:<k>") the dragged piece would land on."""

        bridge = self.bridge
        best: tuple[int, str] | None = None
        if bridge.is_pillar(piece):
            candidates = [(f"spot:{k}", self.view.spot_rect(k).union(self.view.pillar_rect(k))) for k in range(len(bridge.crossing.spots))]
        else:
            candidates = [(f"seat:{span.seat}", self.view.seat_rect(span)) for span in bridge.spans()]
        for target, rect in candidates:
            if not rect.inflate(2 * DROP_REACH, 2 * DROP_REACH).collidepoint(position):
                continue
            distance = (rect.centerx - position[0]) ** 2 + (rect.centery - position[1]) ** 2
            if best is None or distance < best[0]:
                best = (distance, target)
        return best[1] if best is not None else None

    def _start_drag(self, position: tuple[int, int]) -> None:
        press = self._press
        bridge = self.bridge
        if press is None:
            return
        piece: int | None
        if press.target == "tray":
            if not bridge.in_tray(press.index):
                return  # a faded tile (piece already on the bridge) only calls it back
            piece = press.index
            bridge.select(piece)
        elif press.target == "spot":
            piece = bridge.pillar_at(press.index)
        else:
            spans = bridge.spans()
            piece = bridge.occupant(spans[press.index].seat) if press.index < len(spans) else None
        if piece is None:
            return
        self.drag = Drag(piece, position, press.target != "tray", self._drop_target(position, piece))
        self._press = None
        self.audio.play("pick")
        self._sync()

    def _drop(self, position: tuple[int, int]) -> None:
        drag, self.drag = self.drag, None
        if drag is None:
            return
        bridge = self.bridge
        target = self._drop_target(position, drag.piece)
        self._activated = True
        placed = False
        if target is not None:
            kind, _, name = target.partition(":")
            if kind == "spot":
                spot = int(name)
                current = bridge.seat_of[drag.piece]
                if current is not None:
                    bridge.remove(drag.piece)
                placed = bridge.place_pillar(drag.piece, spot)
                if not placed and current is not None:
                    self.audio.play("remove")
            else:
                if name in bridge.seats():
                    bridge.place_plank(drag.piece, name)
                    placed = True
        elif drag.from_bridge:
            bridge.remove(drag.piece)
            self.audio.play("remove")
        if placed:
            self._placed(drag.piece)
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
        self._sync()

    # -- crossing flow --------------------------------------------------------------

    def _start_crossing(self) -> None:
        self.timeline.clear()
        self.motion.clear()
        self.run_ = None
        self.drag = None
        self._press = None
        self._said_go = False
        self.state = AppState.BUILD
        crossing = self.visit.crossing
        self.view = CrossingView(crossing)
        self.controls.set_crossing(crossing)
        self.art.prepare(crossing)
        self.scene = self.art.compose_scene(crossing, self.view)
        friend = crossing.traveler
        feedback = CastFeedback(friend, height=CAST_HEIGHT, art=self.art.art, clock=self.clock)
        load = self.art.load(int(CAST_HEIGHT * 0.46)) if crossing.heavy else None
        self.cast = TravelerCast(
            feedback,
            self.art.cast_pose(friend, "pose_point", CAST_HEIGHT),
            self.art.cast_pose(friend, "pose_wave", CAST_HEIGHT),
            load,
            self.clock,
        )
        self.renderer = BridgeRenderer(self.art, self.cast, CAST_HEIGHT)
        self.audio.use_speaker(friend)
        self.cast.wave()
        self._sync(refocus=True)
        self._note_activity()

    def _sync(self, *, refocus: bool = False) -> None:
        editable = self.state is AppState.BUILD and self.drag is None
        self.controls.sync(self.bridge, self.view, editable=self.state is AppState.BUILD, done=self.visit.completed)
        if refocus and editable:
            self.controls.focus_default(self.bridge)

    def _selected_tray_piece(self) -> int | None:
        bridge = self.bridge
        selected = bridge.selected
        return selected if selected is not None and bridge.in_tray(selected) else None

    def _on_tray(self, piece: int) -> None:
        bridge = self.bridge
        if self.state is not AppState.BUILD or piece >= len(bridge.crossing.pieces):
            return
        self._activated = True
        self._note_activity()
        if bridge.in_tray(piece):
            bridge.select(piece)
            self.audio.play("pick")
        else:
            bridge.remove(piece)  # call a piece back from the bridge
            self.audio.play("remove")
        self._sync()

    def _on_seat(self, span_index: int) -> None:
        bridge = self.bridge
        spans = bridge.spans()
        if self.state is not AppState.BUILD or span_index >= len(spans):
            return
        self._activated = True
        self._note_activity()
        seat = spans[span_index].seat
        selected = self._selected_tray_piece()
        if selected is not None and not bridge.is_pillar(selected):
            bridge.place_plank(selected, seat)
            self._placed(selected)
        elif (occupant := bridge.occupant(seat)) is not None:
            bridge.remove(occupant)
            self.audio.play("remove")
        else:
            self._soft_no(selected)
            return
        self._sync()
        if self.controls.layer.focus_visible:
            self.controls.focus_default(bridge)

    def _on_spot(self, spot: int) -> None:
        bridge = self.bridge
        if self.state is not AppState.BUILD or spot >= len(bridge.crossing.spots):
            return
        self._activated = True
        self._note_activity()
        pillar = bridge.pillar_at(spot)
        selected = self._selected_tray_piece()
        if pillar is not None:
            bridge.remove(pillar)
            self.audio.play("remove")
        elif selected is not None and bridge.is_pillar(selected) and bridge.place_pillar(selected, spot):
            self._placed(selected)
        else:
            self._soft_no(selected)
            return
        self._sync()
        if self.controls.layer.focus_visible:
            self.controls.focus_default(bridge)

    def _soft_no(self, selected: int | None) -> None:
        """A gentle 'not there': show where the lifted piece can go instead."""

        now = self.clock()
        bridge = self.bridge
        self.audio.play("clack")
        if selected is not None and bridge.is_pillar(selected):
            for spot in range(len(bridge.crossing.spots)):
                self.motion.pulse(f"spot:{spot}", now)
        elif selected is not None:
            for span in bridge.spans():
                self.motion.pulse(f"seat:{span.seat}", now)
        else:
            for index in bridge.tray_pieces():
                self.motion.pulse(f"tray:{index}", now)

    def _placed(self, piece: int) -> None:
        now = self.clock()
        bridge = self.bridge
        self.motion.pops[piece] = now
        self.audio.play("place")
        where = bridge.seat_of[piece]
        if where is None:
            return
        item = bridge.piece(piece)
        if item.kind is PieceKind.PILLAR:
            centre = self.view.pillar_rect(int(where.removeprefix("spot"))).midtop
        else:
            centre = (self.view.seat_x(where) - 6, BANK_TOP - item.length * UNIT // 2)
            self.events.plank_placed(self._visit_id, bridge.crossing.crossing_id, item.length, item.strong)
        self.motion.add_fx("sparkle", centre, 96, now)

    def _on_go(self) -> None:
        if self.state is not AppState.BUILD:
            return
        self._activated = True
        self._note_activity()
        bridge = self.bridge
        bridge.summary.tests += 1
        self.run_ = BridgeRun(bridge, self.view)
        self.motion.demo = None
        self.motion.pulses.clear()
        self.motion.missing = None
        self.state = AppState.RUNNING
        self.audio.play("go")
        self.audio.play("creak")
        if not self._said_go:
            self._said_go = True
            self.audio.say("go")
        self.events.test_started(self._visit_id, bridge.crossing.crossing_id, bridge.summary.tests)
        self._sync()

    def _on_moment(self, moment: str, now: float) -> None:
        run = self.run_
        assert run is not None
        if moment == "landed":
            self.audio.play("thunk")
        elif moment.startswith("pass:"):
            plank = run.plank_for(int(moment.split(":", 1)[1]))
            if plank is not None and plank.fit is Fit.JUST_RIGHT:
                self.motion.add_fx("sparkle", ((plank.seat_x + plank.tip_x) // 2, plank.top - 26), 110, now)
                self.audio.play("sparkle")
        elif moment == "bend":
            self.audio.play("bend")
        elif moment == "arrive":
            self._crossing_solved()
        elif moment == "stop":
            self._stopped()
        elif moment == "home":
            self._back_to_build()

    def _crossing_solved(self) -> None:
        now = self.clock()
        bridge = self.bridge
        assert self.cast is not None
        self.state = AppState.CELEBRATE
        self.cast.correct()
        self.audio.play("arrive")
        self.audio.say("arrive")
        picnic = (self.view.picnic_x, BANK_TOP - 70)
        self.motion.add_fx("confetti", (picnic[0] - 30, picnic[1] - 60), 190, now)
        self.motion.add_fx("star_burst", picnic, 120, now)
        self.events.crossing_completed(self._visit_id, bridge.crossing.crossing_id, bridge.summary.tests)
        self.visit.finish_crossing()
        self.progress.save(self.visit.progress)
        self._sync()
        self.timeline.after(CELEBRATE_SECONDS, self._after_celebration)

    def _stopped(self) -> None:
        now = self.clock()
        bridge = self.bridge
        run = self.run_
        assert self.cast is not None and run is not None
        bridge.summary.misses += 1
        result = run.result
        failure = result.failure or Failure.EMPTY
        failed = result.results[result.failed_index or 0]
        self.state = AppState.PAUSE
        self.cast.try_again()
        self.audio.play("stop")
        x, y = run.traveler_midbottom()
        self.motion.add_fx("dust_puff", (x + 40, y - 10), 90, now)
        if failure is Failure.SHORT and failed.piece is not None:
            reach = failed.span.start + bridge.piece(failed.piece).length
            self.motion.missing = (reach, failed.span.end)
        elif failure is Failure.EMPTY:
            self.motion.missing = (failed.span.start, failed.span.end)
        if now - self._last_retry_voice >= RETRY_VOICE_GAP:
            self._last_retry_voice = now
            self.audio.say("retry")
        self.events.crossing_missed(self._visit_id, bridge.crossing.crossing_id, bridge.summary.tests, failure.value)
        self._sync()
        self.timeline.after(PAUSE_SECONDS, self._start_return)

    def _start_return(self) -> None:
        if self.state is not AppState.PAUSE or self.run_ is None:
            return
        self.run_.start_return()
        self.state = AppState.RETURN

    def _back_to_build(self) -> None:
        if self.state is not AppState.RETURN:
            return
        self.state = AppState.BUILD
        self.run_ = None
        self.motion.missing = None
        self._sync(refocus=self.controls.layer.focus_visible)
        self._note_activity()
        self._demonstrate(snap=self.bridge.summary.misses >= SNAP_AFTER_MISSES)

    def _after_celebration(self) -> None:
        if self.visit.complete:
            self._complete_set()
            return
        self.visit.next_crossing()
        self._start_crossing()

    def _complete_set(self) -> None:
        progress = self.visit.progress
        set_id = self.visit.crossing_set.set_id
        self.visit.finish_set()
        self.progress.save(progress)
        self.events.set_completed(self._visit_id, set_id, self.visit.completed)
        self.timeline.clear()
        self.motion.clear()
        self.audio.play("fanfare")
        self.audio.use_speaker(COMPLETION_FRIEND)
        self.audio.say("complete")
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=DUSK),
            scene=CompletionScene(self.kit, character=COMPLETION_FRIEND, star_total=self.visit.total),
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
        self._start_crossing()

    # -- hints ----------------------------------------------------------------------

    def _on_hint(self) -> None:
        if self.state is not AppState.BUILD:
            return
        self._activated = True
        self._note_activity()
        self._demonstrate(snap=False)

    @staticmethod
    def _target_key(step: HintStep) -> str | None:
        if step.action is HintAction.PLACE_PLANK and step.seat is not None:
            return f"seat:{step.seat}"
        if step.spot is not None:
            return f"spot:{step.spot}"
        return None

    def _demonstrate(self, *, snap: bool) -> None:
        """Show the single next step; on repeated stops, also carry it out."""

        if self.state is not AppState.BUILD:
            return
        now = self.clock()
        bridge = self.bridge
        step = HintPlanner.next_step(bridge)
        bridge.summary.hints += 1
        assert self.cast is not None
        self.cast.point(2.0)
        self.audio.play("hint")
        if step.action is HintAction.GO:
            self.motion.go_pulse = now
            self.controls.layer.focus("go")
            return
        piece = HintPlanner.piece_for(bridge, step)
        origin = None
        if piece is not None and bridge.in_tray(piece) and step.action is not HintAction.REMOVE_PILLAR:
            origin = self.controls.tray[piece].rect.center
        self.motion.demo = (step, now, origin)
        key = self._target_key(step)
        if key is not None:
            self.motion.pulse(key, now)
        if self.controls.layer.focus_visible:
            self._focus_for(step, piece)
        if snap:
            self.timeline.after(SNAP_DELAY_SECONDS, lambda: self._snap(step))

    def _snap(self, step: HintStep) -> None:
        if self.state is not AppState.BUILD or self.drag is not None:
            return
        piece = HintPlanner.piece_for(self.bridge, step)
        if piece is not None and HintPlanner.apply(self.bridge, step):
            self.motion.demo = None
            if step.action is HintAction.REMOVE_PILLAR:
                self.audio.play("remove")
            else:
                self._placed(piece)
            self._sync()
            if HintPlanner.next_step(self.bridge).action is HintAction.GO:
                self.motion.go_pulse = self.clock()

    def _focus_for(self, step: HintStep, piece: int | None) -> None:
        bridge = self.bridge
        if step.action is HintAction.REMOVE_PILLAR and step.spot is not None:
            self.controls.layer.focus(spot_id(step.spot))
            return
        if piece is not None and bridge.in_tray(piece) and bridge.selected != piece:
            bridge.select(piece)
            self._sync()
            self.controls.layer.focus(tray_id(piece))
            return
        if step.action is HintAction.PLACE_PILLAR and step.spot is not None:
            self.controls.layer.focus(spot_id(step.spot))
        elif step.seat is not None and step.seat in bridge.seats():
            self.controls.layer.focus(seat_id(bridge.seats().index(step.seat)))

    def _maybe_hint(self, now: float) -> None:
        if self.state is not AppState.BUILD or self.timeline.busy or self.drag is not None:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        assert self.cast is not None
        if step == 1:
            # First nudge: the friend points and the next place glows (no answer shown).
            plan = HintPlanner.next_step(self.bridge)
            self.cast.point(self._hints.animation_seconds(1.8))
            key = self._target_key(plan)
            if key is not None:
                self.motion.pulse(key, now)
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


__all__ = ["AppState", "BridgeActivity", "Timeline"]
