"""Lifecycle, timeline and shared-kit input for La Bottega delle Misure.

One delivery is five jobs in Leo's workshop. Each job's parcels drop onto the
boards, the bench or beside the toy balance; the job card shows what to look
for (longer, taller, heavier, "measure with blocks") and the recorded prompt
says it where one exists. The child acts: taps a parcel, puts parcels on the
balance, or takes unit blocks from the crate one at a time — they lie end to
end from the start stop — and checks when the row is exactly as long as the
parcel, then counts it. Right: Leo cheers and the parcels are sent off.
Not right: Leo thinks and the idea is shown (the end line, the gap that is
still empty, the block that sticks out, the blocks counted one by one, the
balance swinging again), then the child tries again (unlimited, kind).
Feedback follows ADR 0037 and the delivery ends on the shared cast
completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
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
    from .measure_art import MeasureArt
    from .measure_audio import MeasureAudio
    from .measure_content import (
        CHECK_CENTER,
        GUIDE,
        GUIDE_HEIGHT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TILT_DEGREES,
        UNIT,
    )
    from .measure_controls import MeasureControls
    from .measure_model import Answer, Delivery, Goal, Phase, RowFit, Task, TaskKind
    from .measure_renderer import (
        DROP_SECONDS,
        EXIT_SECONDS,
        HOP_SECONDS,
        PAN_HOP_SECONDS,
        BlockHop,
        MeasureCast,
        MeasureRenderer,
        SceneMotion,
        parcel_rect,
        rows_for,
    )
    from .measure_services import EventPort, ProgressPort
else:
    from measure_art import MeasureArt
    from measure_audio import MeasureAudio
    from measure_content import (
        CHECK_CENTER,
        GUIDE,
        GUIDE_HEIGHT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TILT_DEGREES,
        UNIT,
    )
    from measure_controls import MeasureControls
    from measure_model import Answer, Delivery, Goal, Phase, RowFit, Task, TaskKind
    from measure_renderer import (
        DROP_SECONDS,
        EXIT_SECONDS,
        HOP_SECONDS,
        PAN_HOP_SECONDS,
        BlockHop,
        MeasureCast,
        MeasureRenderer,
        SceneMotion,
        parcel_rect,
        rows_for,
    )
    from measure_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
COUNT_STEP_SECONDS = 0.5
DEMO_LEAD_SECONDS = 0.9
DEMO_HOLD_SECONDS = 1.6
CELEBRATE_SECONDS = 1.1
MAX_SCHEDULED = 48
WORKSHOP_DUSK = (61, 44, 31)  # cocoa behind the completion card

_PROMPTS = {
    (TaskKind.COMPARE_LENGTH, Goal.MORE): "prompt_compare_longer",
    (TaskKind.COMPARE_LENGTH, Goal.LESS): "prompt_compare_shorter",
    (TaskKind.COMPARE_HEIGHT, Goal.MORE): "prompt_compare_taller",
    (TaskKind.COMPARE_HEIGHT, Goal.LESS): "prompt_compare_shorter_h",
    (TaskKind.MEASURE_COMPARE, Goal.MORE): "prompt_compare_longer",
    (TaskKind.MEASURE_COMPARE, Goal.LESS): "prompt_compare_shorter",
}


def prompt_cue(task: Task) -> str | None:
    """The recorded instruction for the job's current step (None = pictorial)."""

    if task.kind.lays_blocks and task.resume_phase in {Phase.ARRIVING, Phase.LAYING, Phase.COUNTING}:
        return "prompt_measure"
    return _PROMPTS.get((task.kind, task.goal))


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


class Timeline:
    """Tiny bounded scheduler for the scripted moments (arrive, demo, exit)."""

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


class BottegaActivity:
    """Coordinate the job model, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        delivery: Delivery,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: MeasureAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: MeasureArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.delivery = delivery
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.clock = clock
        self._delivery_id = uuid4().hex

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        self.art = art if art is not None else MeasureArt(self.kit.painter)
        feedback = CastFeedback(GUIDE, height=GUIDE_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = MeasureCast(feedback, self.art.cast_pose(GUIDE, "pose_point", GUIDE_HEIGHT), clock)
        self.renderer = MeasureRenderer(self.art, self.cast, clock=clock)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = MeasureControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            delivery.total_jobs,
            on_parcel=self._on_parcel,
            on_crate=self._on_crate,
            on_row=self._on_row,
            on_check=self._on_check,
            on_count=self._on_count,
            on_listen=self._on_listen,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=WORKSHOP_DUSK),
            scene=CompletionScene(self.kit, character=GUIDE, star_total=delivery.total_jobs),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._idle_hints = 0
        self._start_job()

    @property
    def task(self) -> Task:
        return self.delivery.current

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                frame = frames.frame(dirty=self._dirty, animating=animating)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.progress.save(self.delivery.progress)
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers and motion; return True while something moves."""

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
        return self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.task, self.motion)
        self._surfaces.draw(surface)

    # -- input --------------------------------------------------------------------

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
            self._input = PygameControlInput(
                to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos)
            )
            self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
            self._dirty = True
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
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

    def _sync(self, *, refocus: bool = False) -> None:
        self.controls.sync(self.task, refocus=refocus, busy=self._busy)
        self._dirty = True

    # -- job flow -------------------------------------------------------------------

    def _start_job(self) -> None:
        task = self.task
        now = self.clock()
        self.timeline.clear()
        self.motion.clear(now)
        self.motion.sign_hop = now
        if task.kind is TaskKind.WEIGH:
            self.art.preload_beam()
        self.controls.bind_task(task)
        self.controls.set_progress(self.delivery.completed)
        self.cast.reset()
        self._busy = True
        self._sync(refocus=True)
        self.timeline.after(DROP_SECONDS + 0.1, self._arrived)
        self._note_activity()

    def _arrived(self) -> None:
        task = self.task
        task.arrived()
        self._busy = False
        self._sync(refocus=True)
        self.audio.say(prompt_cue(task))
        self.cast.point(1.6)
        self.motion.sign_hop = self.clock()
        self._note_activity()

    def _on_listen(self) -> None:
        if self.state is not AppState.PLAYING:
            return
        self._activated = True
        self.motion.sign_hop = self.clock()
        self.audio.say(prompt_cue(self.task))
        self._dirty = True

    # -- weighing --------------------------------------------------------------------

    def _on_parcel(self, parcel_id: int) -> None:
        task = self.task
        if task.phase is Phase.LOADING:
            if not task.load(parcel_id):
                return
            self._activated = True
            now = self.clock()
            self.motion.pan_hops[parcel_id] = now
            self.audio.play("pop")
            self._busy = True
            self._sync()
            self.timeline.after(PAN_HOP_SECONDS, self._landed_on_pan)
            return
        if task.phase is not Phase.PICKING:
            return
        self._activated = True
        result = task.pick(parcel_id)
        if result is Answer.CORRECT:
            self._celebrate(lit=parcel_id)
        elif result is Answer.WRONG:
            self._demonstrate_pick(parcel_id)

    def _landed_on_pan(self) -> None:
        task = self.task
        now = self.clock()
        self.motion.swing(task.tilt() * TILT_DEGREES, now)
        self.audio.play("creak")
        self._busy = False
        self._sync(refocus=True)
        if task.all_on_pans:
            self.motion.sign_hop = now
            self.cast.point(1.2)
        self._note_activity()

    # -- laying blocks ----------------------------------------------------------------

    def _on_crate(self, row: int) -> None:
        task = self.task
        if task.phase is not Phase.LAYING:
            return
        self._activated = True
        now = self.clock()
        if not task.add_block(row):
            self.motion.crate_pulses[row] = now
            self.audio.play("boop")
            self._dirty = True
            return
        place = task.rows[row] - 1
        self.motion.clear_marks()
        self.motion.hops[(row, place)] = BlockHop(now, row, place, True)
        self.motion.crate_pulses[row] = now
        self.timeline.after(HOP_SECONDS, lambda r=row, p=place: self._block_landed(r, p))
        self.audio.play("take")
        self._sync()

    def _block_landed(self, row: int, place: int) -> None:
        if self.task.rows[row] <= place:
            return  # taken back before it landed
        self.motion.pops[(row, place)] = self.clock()
        self.audio.play("clack")
        self.audio.chime(place + 1)
        self._dirty = True

    def _on_row(self, row: int) -> None:
        task = self.task
        if task.phase is not Phase.LAYING or not task.take_block(row):
            return
        self._activated = True
        place = task.rows[row]
        self.motion.clear_marks()
        self.motion.pops.pop((row, place), None)
        self.motion.hops[(row, place)] = BlockHop(self.clock(), row, place, False)
        self.audio.play("take")
        self._sync()

    def _on_check(self) -> None:
        task = self.task
        result = task.check()
        if result is Answer.IGNORED:
            return
        self._activated = True
        self.motion.clear_marks()
        if result is Answer.CORRECT:
            self._blocks_fit()
        else:
            self._demonstrate_fit()

    def _blocks_fit(self) -> None:
        """The rows match the parcels: a small cheer, then count or compare."""

        task = self.task
        now = self.clock()
        self.cast.correct()
        self.audio.play("pop")
        for index, row in enumerate(rows_for(task)):
            x, y, w, h = row.block_rect(task.rows[index] - 1)
            self.motion.add_fx("sparkle", (x + w, y + h // 2), now)
        self._busy = True
        self._sync()
        self.timeline.after(0.7, self._next_step)

    def _next_step(self) -> None:
        self._busy = False
        self._sync(refocus=True)
        self.motion.sign_hop = self.clock()
        self.audio.say(prompt_cue(self.task))
        self._note_activity()

    def _on_count(self, index: int) -> None:
        value = self.controls.choice_value(index)
        if value is None:
            return
        task = self.task
        result = task.choose_count(value)
        if result is Answer.IGNORED:
            return
        self._activated = True
        if result is Answer.CORRECT:
            self._celebrate(lit=0)
        else:
            self._demonstrate_count()

    # -- feedback -------------------------------------------------------------------------

    def _celebrate(self, *, lit: int) -> None:
        task = self.task
        now = self.clock()
        self._busy = True
        self.timeline.clear()
        self.cast.correct()
        self.audio.play("chime_5")
        self.audio.praise()
        self.motion.lit = lit
        rect = parcel_rect(task, task.parcels[lit], degrees=self.motion.angle(now))
        self.motion.add_fx("check_pop", rect.midtop, now)
        self.motion.add_fx("star_burst", rect.center, now)
        self.motion.add_fx("confetti", (rect.centerx, max(140, rect.top - 60)), now)
        self._sync()
        self.timeline.after(CELEBRATE_SECONDS, self._send_off)

    def _send_off(self) -> None:
        self.motion.exit_started = self.clock()
        self.audio.play("whoosh")
        self.timeline.after(EXIT_SECONDS, self._finish_job)
        self._dirty = True

    def _try_again(self) -> None:
        self._busy = True
        self.cast.try_again()
        self.audio.encourage()
        self._sync()

    def _demonstrate_fit(self) -> None:
        """Show each row's end line and the gap still empty or the block too many."""

        self._try_again()
        self.timeline.after(DEMO_LEAD_SECONDS, self._show_fit_marks)
        self.timeline.after(DEMO_LEAD_SECONDS + DEMO_HOLD_SECONDS, self._finish_demo)

    def _show_fit_marks(self) -> None:
        task = self.task
        now = self.clock()
        self.motion.marks_started = now
        rows = rows_for(task)
        for index, fit in enumerate(task.last_fits):
            if fit is RowFit.SHORT:
                self.motion.missing[index] = task.missing(index)
            elif fit is RowFit.LONG:
                self.motion.extra[index] = task.extra(index)
        # The end line of the first row that does not fit.
        for index, fit in enumerate(task.last_fits):
            if fit is not RowFit.EXACT:
                row = rows[index]
                end = row.stop_x + task.parcels[index].units * UNIT
                self.motion.guide_x = end
                self.motion.guide_span = (row.top - 96, row.top + 84)
                break
        self.audio.play("boop")
        self._dirty = True

    def _demonstrate_count(self) -> None:
        """Count the laid blocks one by one (badges + rising chimes)."""

        task = self.task
        self._try_again()
        for place in range(task.rows[0]):
            self.timeline.after(
                DEMO_LEAD_SECONDS + COUNT_STEP_SECONDS * place, lambda p=place: self._count_badge(0, p, p + 1)
            )
        total = DEMO_LEAD_SECONDS + COUNT_STEP_SECONDS * task.rows[0] + 0.3
        self.timeline.after(total, self._finish_demo)

    def _count_badge(self, row: int, place: int, number: int) -> None:
        now = self.clock()
        # A row's last number stays up a little longer: it is the measurement.
        hold = 1.2 if place == self.task.rows[row] - 1 else 0.0
        self.motion.badges[(row, place)] = (now + hold, number)
        self.motion.pops[(row, place)] = now
        self.audio.chime(number)
        self._dirty = True

    def _demonstrate_pick(self, parcel_id: int) -> None:
        task = self.task
        now = self.clock()
        self.motion.wobble = (parcel_id, now)
        self._try_again()
        lead = DEMO_LEAD_SECONDS
        if task.kind is TaskKind.MEASURE_COMPARE:
            # Count both rows side by side: the longer row keeps counting alone.
            longest = max(task.rows)
            for place in range(longest):
                for row in range(len(task.rows)):
                    if place < task.rows[row]:
                        self.timeline.after(
                            lead + COUNT_STEP_SECONDS * place, lambda r=row, p=place: self._count_badge(r, p, p + 1)
                        )
            self.timeline.after(lead + COUNT_STEP_SECONDS * longest + 0.4, self._finish_demo)
            return
        if task.kind is TaskKind.WEIGH:
            self.timeline.after(lead, self._reweigh)
        else:
            self.timeline.after(lead, self._show_compare_marks)
        self.timeline.after(lead + DEMO_HOLD_SECONDS, self._finish_demo)

    def _reweigh(self) -> None:
        """The balance swings again and settles: the heavy side goes down."""

        now = self.clock()
        task = self.task
        self.motion.swing(task.tilt() * TILT_DEGREES, now, start=-task.tilt() * TILT_DEGREES * 0.6)
        self.motion.pulses[task.target_id] = now  # the right parcel hops
        self.audio.play("creak")
        self._dirty = True

    def _show_compare_marks(self) -> None:
        """Lengths: a line at the shorter parcel's end; heights: at its top."""

        task = self.task
        now = self.clock()
        shorter = min(task.parcels, key=lambda parcel: parcel.units)
        rect = parcel_rect(task, shorter)
        others = [parcel_rect(task, parcel) for parcel in task.parcels]
        if task.kind is TaskKind.COMPARE_HEIGHT:
            self.motion.guide_y = rect.top
            self.motion.guide_span = (min(r.left for r in others) - 30, max(r.right for r in others) + 30)
        else:
            self.motion.guide_x = rect.right
            self.motion.guide_span = (min(r.top for r in others) - 40, max(r.bottom for r in others) + 10)
        self.motion.marks_started = now
        self.motion.pulses[task.target_id] = now  # the right parcel hops
        self.audio.play("boop")
        self._dirty = True

    def _finish_demo(self) -> None:
        self.task.finish_demonstration()
        self._busy = False
        self._sync(refocus=True)
        self._note_activity()

    def _finish_job(self) -> None:
        index = self.delivery.completed + 1
        summary = self.delivery.finish_job()
        self.events.parcel_completed(self._delivery_id, index, summary)
        self.progress.save(self.delivery.progress)
        self.controls.set_progress(self.delivery.completed)
        if self.delivery.complete:
            self._complete_delivery()
            return
        self.delivery.next_job()
        self._start_job()

    def _complete_delivery(self) -> None:
        self.delivery.progress.deliveries_completed += 1
        self.progress.save(self.delivery.progress)
        self.events.delivery_completed(self._delivery_id, self.delivery.completed, self.delivery.stage)
        self.timeline.clear()
        self.motion.clear(self.clock() - 10.0)
        self.audio.play("fanfare")
        self.audio.praise()
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                achievement_count=self.delivery.total_jobs,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        """One restart transaction regardless of keyboard/controller/pointer input."""

        self._activated = True
        self._surfaces.pop_overlay()
        self.completion.clear()
        self._delivery_id = uuid4().hex
        self.delivery.restart()
        self.state = AppState.PLAYING
        self._start_job()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        task = self.task
        if (
            self._busy
            or self.timeline.busy
            or task.phase
            not in {
                Phase.LOADING,
                Phase.LAYING,
                Phase.COUNTING,
                Phase.PICKING,
            }
        ):
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        self.cast.point(1.8)
        self.motion.sign_hop = now
        if self._idle_hints == 1:
            task.note_hint()
            self.audio.say(prompt_cue(task))
            self._dirty = True
            return
        # Later hints show where to act, never which answer is right.
        if task.phase is Phase.LOADING:
            for parcel in task.parcels:
                if not task.on_pan[parcel.parcel_id]:
                    self.motion.pulses[parcel.parcel_id] = now
                    break
        elif task.phase is Phase.LAYING:
            empty = [index for index, count in enumerate(task.rows) if count == 0]
            if empty:
                self.motion.crate_pulses[empty[0]] = now
            else:
                self.motion.add_fx("sparkle", CHECK_CENTER, now)
        elif task.phase is Phase.PICKING:
            for parcel in task.parcels:
                self.motion.pulses[parcel.parcel_id] = now
        self._dirty = True


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "BottegaActivity", "Timeline", "prompt_cue"]
