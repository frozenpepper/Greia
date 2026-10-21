"""App lifecycle, step flow and input orchestration for Tito's Number Forest.

Walk grammar (P7 §1): Tito counts a numeral's forest friends into a frame and
says the number (MEET) → the child finds the numeral among numeral tiles
(FIND) → writes it stroke by stroke (TRACE) → picks the frame holding that
many friends (SHOW) → … → two review finds → confetti and the shared
completion scene. Each written numeral becomes a signpost on the forest path.

Hints are graduated: after ~6 s of quiet Tito points, the prompt pulses and is
repeated (with the tracing hand on a TRACE step); a first wrong pick makes
Tito think — on a SHOW step he counts the picked frame aloud so the child
hears why — and from the second wrong pick the right option pulses while Tito
names or counts it. A touch away from the stroke only pulses the green start
dot. Retries are unlimited and kind; tracing never fails.
"""

from __future__ import annotations

from enum import StrEnum
import random
import time
from typing import Callable

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
from greia_platform.input_core import SemanticInputEvent
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
    from .bosco_art import SEASONS, TraceInk
    from .bosco_audio import WRITE_ZERO_CUE, BoscoAudio, SpeechQueue, ask_cue, count_cue
    from .bosco_controls import TITO_HEIGHT, ForestControls, choice_id
    from .bosco_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ForestStep,
        ForestWalk,
        StepKind,
        WalkPlanner,
        next_group,
    )
    from .bosco_renderer import BoscoRenderer, SceneState, TraceView
    from .bosco_services import BoscoProgress, EventPort, ProgressPort
    from .bosco_trace import TraceEvent, TraceTracker
else:
    from bosco_art import SEASONS, TraceInk
    from bosco_audio import WRITE_ZERO_CUE, BoscoAudio, SpeechQueue, ask_cue, count_cue
    from bosco_controls import TITO_HEIGHT, ForestControls, choice_id
    from bosco_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ForestStep,
        ForestWalk,
        StepKind,
        WalkPlanner,
        next_group,
    )
    from bosco_renderer import BoscoRenderer, SceneState, TraceView
    from bosco_services import BoscoProgress, EventPort, ProgressPort
    from bosco_trace import TraceEvent, TraceTracker


POINT_SECONDS = 2.6
SHAKE_SECONDS = 0.45
MEET_MIN_SECONDS = 2.2
MEET_BASE_SECONDS = 5.0
MEET_PER_ITEM = 1.0
MEET_OPENING_SECONDS = 4.5
CELEBRATE_MIN = 1.3
CELEBRATE_MAX = 4.5
BLOOM_HOLD = 1.9
FLIGHT_SECONDS = 0.55
BLOOM_MAX = 5.5
FINALE_SECONDS = 2.4
DEMO_SPEED = 300.0      # logical px/s of the demonstrating hand
AUTO_TRACE_SPEED = 340.0
START_PULSE_SECONDS = 1.2
SPARKLE_SECONDS = 0.7
COUNT_GAP = 0.12
DIGIT_KEYS = {getattr(pygame, f"K_{d}"): d for d in range(10)} | {getattr(pygame, f"K_KP{d}"): d for d in range(10)}


COMPLETION_PALETTE = CompletionPalette(
    background=(207, 234, 247),
    panel=(254, 243, 199),
    panel_border=(180, 83, 9),
    title=(120, 53, 15),
    body=(71, 85, 105),
    primary=(243, 154, 56),
    primary_text=(61, 44, 31),
)


class AppState(StrEnum):
    MEET = "meet"
    PLAYING = "playing"
    TRY_AGAIN = "try_again"
    CELEBRATE = "celebrate"
    BLOOM = "bloom"
    FINALE = "finale"
    TERMINAL = "terminal"


class BoscoApp:
    """Coordinate the forest walk, speech, tracing, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        planner: WalkPlanner,
        progress: BoscoProgress,
        progress_port: ProgressPort,
        events: EventPort,
        renderer: BoscoRenderer,
        typography: GreiaTypography,
        resources,
        audio: BoscoAudio,
        speech_queue: SpeechQueue,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.planner = planner
        self.progress = progress
        self.progress_port = progress_port
        self.events = events
        self.renderer = renderer
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.speech_queue = speech_queue
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.walk = self._new_walk()
        self.season = self._season()
        self.state = AppState.MEET
        self.state_started = clock()
        self.shown_step: ForestStep | None = self.walk.step
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._last_tick = clock()
        self._quiet_since = clock()
        self._hints = IdleHintScheduler(now=self._quiet_since)
        self._point_until = 0.0
        self._hint_target: str | None = None
        self._shake: tuple[str, float] | None = None
        self._celebrating_choice: int | None = None
        self._sparkle: tuple[tuple[int, int], float] | None = None
        self._pulse_phase = 0
        self._activated = False
        self._meet_revealed = 0
        self._meet_limit = MEET_BASE_SECONDS
        # tracing
        self.tracker: TraceTracker | None = None
        self.ink: TraceInk | None = None
        self._demo: tuple[int, float, float] | None = None  # (stroke, from_progress, started)
        self._auto_trace = False
        self._start_pulse_until = 0.0
        self._flight_from: tuple[int, int] | None = None
        self._flight_started: float | None = None

        # Shared control kit (ADR 0037): learn Collection -> orange accent. The
        # kit shares the Activity's picture cache so art is decoded once.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=renderer.art.art
        )
        renderer.kit = self.kit
        renderer.art.attach_painter(self.kit.painter)
        if renderer.cast is None:
            renderer.cast = CastFeedback("tito", height=TITO_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = ForestControls(
            self.kit,
            renderer.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            task_total=self.walk.task_total,
            on_choice=self._on_choice,
            on_listen=self._on_listen,
            on_numeral=self._on_numeral,
            on_trace_key=self._on_trace_key,
        )
        renderer.controls = self.controls
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self.completion = self._make_completion()
        self._enter_step(opening="intro")

    # -- setup helpers --------------------------------------------------------------
    def _new_walk(self) -> ForestWalk:
        group = self.progress.group
        return ForestWalk(self.planner.build(group, self.progress.traced), group=group)

    def _season(self) -> str:
        return SEASONS[self.progress.rounds_completed % len(SEASONS)]

    def _make_completion(self) -> PygameCompletionScreen:
        """Shared cast completion scene sized to this walk's stars."""

        return PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=COMPLETION_PALETTE,
            scene=CompletionScene(self.kit, character="tito", star_total=self.walk.task_total),
        )

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(
            to_logical=self.canvas.pointer,
            is_safe=lambda pos: _safe_point(self.screen, pos),
        )

    # -- main loop --------------------------------------------------------------------
    def run(self) -> int:
        frames = FrameGovernor()
        while self._running and not activity_stop_requested():
            for event in frames.events():
                self._handle_event(event)
            repeat = self._input.poll()
            if repeat is not None:
                self._dispatch(repeat)
            if self.tick():
                self._dirty = True
            frame = frames.frame(dirty=self._dirty)
            if frame is FrameKind.FULL:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            elif frame is FrameKind.POINTER:
                self.canvas.present_pointer()
            frames.wait(polling=self._animating() or self._input.repeating)
        self._save()
        return 0

    def tick(self) -> bool:
        """Advance speech, cast, tracing and state timers; True when the frame changed."""

        now = self.clock()
        dt = max(0.0, min(0.1, now - self._last_tick))
        self._last_tick = now
        was_busy = self.speech_queue.busy
        changed = self.speech_queue.update(dt)
        if was_busy and not self.speech_queue.busy:
            self._quiet_since = now
        tag = self.speech_queue.current_tag
        if tag is not None and tag.startswith("item."):
            revealed = int(tag.split(".", 1)[1])
            if revealed > self._meet_revealed:
                self._meet_revealed = revealed
                self.audio.play_sfx("pop")
                changed = True
        cast = self.renderer.cast
        if cast is not None and cast.update():
            changed = True
        if self._auto_trace and self.tracker is not None and self.state is AppState.PLAYING and dt > 0:
            event = self.tracker.auto_advance(AUTO_TRACE_SPEED * dt)
            # One action press traces one stroke, then waits for the next press.
            if event in {TraceEvent.STROKE_DONE, TraceEvent.NUMERAL_DONE} or self.tracker.complete:
                self._auto_trace = False
            self._on_trace_event(event, now)
            changed = True
        if self.ink is not None and self.tracker is not None and not self.tracker.complete:
            if self.ink.sync(self.tracker.stroke_index, self.tracker.progress):
                changed = True
        return self._advance_state(now) or changed

    def _animating(self) -> bool:
        cast = self.renderer.cast
        return (
            self.state in {AppState.TRY_AGAIN, AppState.CELEBRATE, AppState.BLOOM, AppState.FINALE}
            or self.speech_queue.busy
            or self._hint_target is not None
            or self._demo is not None
            or self._auto_trace
            or (self.tracker is not None and self.tracker.dragging)
            or (cast is not None and cast.animating)
        )

    # -- input ----------------------------------------------------------------------------
    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen, hires=True)
            self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
            self._input = self._make_input()
            self._sync_controls()
            if self.tracker is not None and self.state is AppState.PLAYING:
                self._start_trace(keep_progress=True)
            self._dirty = True
            return
        if self.state not in {AppState.MEET, AppState.PLAYING, AppState.TERMINAL}:
            return
        if event.type == pygame.KEYDOWN and self.state is not AppState.TERMINAL:
            # A digit key that matches a numeral tile picks it (real numeral
            # recognition on the keyboard); R replays the spoken prompt.
            digit = DIGIT_KEYS.get(event.key)
            if digit is not None and self._typed_digit(digit):
                self._dirty = True
                return
            if event.key == pygame.K_r:
                self._note_input()
                self._replay()
                self._dirty = True
                return
        translated = self._input.translate(event)
        if translated is None:
            return
        if isinstance(translated, KitPointer) and self._trace_pointer(translated):
            self._dirty = True
            return
        if self._dispatch(translated):
            self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if self.state not in {AppState.MEET, AppState.PLAYING, AppState.TERMINAL}:
            return False
        if isinstance(kit_input, SemanticInputEvent) or (
            isinstance(kit_input, KitPointer) and kit_input.phase is PointerPhase.DOWN
        ):
            self._note_input()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def _note_input(self) -> None:
        self._quiet_since = self.clock()
        self._hints.reset(self._quiet_since)

    def _typed_digit(self, digit: int) -> bool:
        """A physical digit key picks the matching numeral tile."""

        step = self.walk.step
        if self.state is not AppState.PLAYING or step is None or not step.is_find:
            return False
        for index, value in enumerate(step.choices):
            if value == digit and index not in self.walk.eliminated:
                self._note_input()
                self._on_choice(index)
                return True
        return False

    def _trace_pointer(self, pointer: KitPointer) -> bool:
        """Route finger/pointer input on the tracing box to the tracker."""

        tracker = self.tracker
        step = self.walk.step
        if tracker is None or self.state is not AppState.PLAYING or step is None or step.kind is not StepKind.TRACE:
            return False
        box = self.controls.geometry.trace_box
        local = (pointer.position[0] - box.left, pointer.position[1] - box.top)
        if pointer.phase is PointerPhase.DOWN:
            if self.controls.layer.hit(pointer.position) is not None:
                return False
            self._note_input()
            if tracker.begin(local):
                self._demo = None
                self._auto_trace = False
                self._on_trace_event(tracker.move(local), self.clock())
            else:
                self._start_pulse_until = self.clock() + START_PULSE_SECONDS
            return True
        if pointer.phase is PointerPhase.MOVE and tracker.dragging:
            self._note_input()
            self._on_trace_event(tracker.move(local), self.clock())
            return True
        if pointer.phase in {PointerPhase.UP, PointerPhase.CANCEL} and tracker.dragging:
            tracker.end()
            return True
        return False

    # Test/tool helpers ----------------------------------------------------------------
    def _handle_pointer(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position."""

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

    def _handle_keyboard(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)
        self._activated = False
        if key == pygame.K_r or key in DIGIT_KEYS:
            before = (self.walk.step_index, self.state, self.speech_queue.busy)
            self._handle_event(event)
            return before != (self.walk.step_index, self.state, self.speech_queue.busy) or self._activated
        translated = self._input.translate(event)
        if translated is None:
            return False
        handled = self._dispatch(translated)
        return handled or self._activated

    def _drag(self, logical_points) -> None:
        """Drag a finger through logical points (tests/tools)."""

        points = [(int(x), int(y)) for x, y in logical_points]
        if not points:
            return
        if not self._trace_pointer(KitPointer(PointerPhase.DOWN, points[0])):
            return
        for point in points[1:]:
            self._trace_pointer(KitPointer(PointerPhase.MOVE, point))
        self._trace_pointer(KitPointer(PointerPhase.UP, points[-1]))

    # -- control callbacks ----------------------------------------------------------------
    def _on_listen(self) -> None:
        self._activated = True
        self._replay()

    def _on_numeral(self) -> None:
        """Tapping the big numeral on a MEET step counts its friends again."""

        self._activated = True
        step = self.walk.step
        if step is not None and step.kind is StepKind.MEET:
            self.speech_queue.clear()
            self._enqueue_meet(step)
            self.state_started = self.clock()

    def _on_trace_key(self) -> None:
        """Keyboard/controller: the current stroke traces itself ("follow the dot")."""

        self._activated = True
        if self.tracker is not None and self.state is AppState.PLAYING and not self.tracker.complete:
            self._demo = None
            self._auto_trace = True

    def _on_choice(self, index: int) -> None:
        step = self.walk.step
        if self.state is not AppState.PLAYING or step is None or not step.is_choice or index >= len(step.choices):
            return
        if index in self.walk.eliminated:
            return
        self._activated = True
        result = self.walk.select(index)
        if result.correct:
            self._on_correct(step, index)
        else:
            self._on_wrong(step, index, result.errors)

    def _replay(self) -> None:
        step = self.walk.step
        if step is None:
            return
        queue = self.speech_queue
        queue.clear()
        value = step.numeral.value
        if step.is_find:
            queue.enqueue(ask_cue(value), tag="sign", gap=0.4)
        elif step.kind is StepKind.MEET:
            self._enqueue_meet(step)
            self.state_started = self.clock()
        elif step.kind is StepKind.TRACE:
            queue.enqueue(count_cue(value), gap=0.3)
            self._start_demo(self.clock())
        elif step.kind is StepKind.SHOW:
            queue.enqueue(count_cue(value), tag="numeral", gap=0.4)

    def _enqueue_meet(self, step: ForestStep) -> None:
        """Count the friends into the frame one by one, then name the numeral."""

        self._meet_revealed = 0
        value = step.numeral.value
        for item in range(1, value + 1):
            self.speech_queue.enqueue(count_cue(item), tag=f"item.{item}", gap=COUNT_GAP)
        self.speech_queue.enqueue(count_cue(value), tag="numeral", gap=0.5)
        self._meet_limit = MEET_BASE_SECONDS + MEET_PER_ITEM * value

    def _enqueue_count(self, option: int, quantity: int) -> None:
        for item in range(1, quantity + 1):
            self.speech_queue.enqueue(count_cue(item), tag=f"count.{option}.{item}", gap=COUNT_GAP)

    # -- feedback grammar ---------------------------------------------------------------------
    def _on_wrong(self, step: ForestStep, index: int, errors: int) -> None:
        self.audio.play_sfx("retry")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._point_until = 0.0
        self._shake = (choice_id(index), self.clock())
        self.state = AppState.TRY_AGAIN
        self.state_started = self.clock()
        self._sync_controls()
        remaining = [i for i in range(len(step.choices)) if i not in self.walk.eliminated]
        demonstrate = errors >= 2 or len(remaining) == 1
        value = step.numeral.value
        correct = step.correct_index
        queue = self.speech_queue
        queue.clear()
        queue.enqueue("tito.retry", gap=0.35)
        if step.kind is StepKind.SHOW:
            if errors == 1:
                # Count the picked frame aloud so the child hears it is not N.
                self._enqueue_count(index, step.choices[index])
            if demonstrate:
                # Demonstrate: Tito counts the right frame while it pulses.
                self._hint_target = choice_id(correct)
                self._enqueue_count(correct, value)
                queue.enqueue(count_cue(value), tag=choice_id(correct), gap=0.35)
            else:
                queue.enqueue(count_cue(value), tag="numeral", gap=0.35)
        elif demonstrate:
            # Demonstrate: the right tile pulses while Tito names its numeral.
            queue.enqueue(count_cue(value), tag=choice_id(correct), gap=0.35)
            self._hint_target = choice_id(correct)
        else:
            queue.enqueue(ask_cue(value), tag="sign", gap=0.35)

    def _on_correct(self, step: ForestStep, index: int) -> None:
        self.audio.play_sfx("correct")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._point_until = 0.0
        self._hint_target = None
        self._celebrating_choice = index
        self._sparkle = (self.controls.choice_center(index), self.clock())
        queue = self.speech_queue
        queue.clear()
        queue.enqueue(count_cue(step.numeral.value), tag=choice_id(index), gap=0.3)
        if step.kind is StepKind.SHOW:
            queue.enqueue("well_done", gap=0.2)
        elif step.kind is StepKind.REVIEW and self.walk.is_complete:
            queue.enqueue("tito.praise", gap=0.2)
        self.state = AppState.CELEBRATE
        self.state_started = self.clock()
        self.controls.dots.set_progress(self.walk.tasks_done)

    def _on_trace_event(self, event: TraceEvent, now: float) -> None:
        if event is TraceEvent.STROKE_DONE:
            self.audio.play_sfx("stroke")
            assert self.tracker is not None
            end = self.tracker.guide.strokes[self.tracker.stroke_index - 1].points[-1]
            box = self.controls.geometry.trace_box
            self._sparkle = ((int(box.left + end[0]), int(box.top + end[1])), now)
            self._demo = None
            self._start_demo(now, delay=0.5)
        elif event is TraceEvent.NUMERAL_DONE:
            self._on_numeral_written(now)

    def _on_numeral_written(self, now: float) -> None:
        step = self.walk.step
        assert step is not None and self.ink is not None and self.tracker is not None
        self.ink.sync(len(self.tracker.guide.strokes), 0.0)
        value = step.numeral.value
        if self.progress.record_trace(value):
            self.events.numeral_written(self.session_id, value)
        self.walk.finish_trace()
        self._save()
        self.audio.play_sfx("bloom")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._demo = None
        self._auto_trace = False
        self._point_until = 0.0
        queue = self.speech_queue
        queue.clear()
        queue.enqueue(count_cue(value), tag="bloom", gap=0.3)
        queue.enqueue("tito.praise", gap=0.2)
        self._flight_from = self.controls.geometry.trace_box.center
        self.state = AppState.BLOOM
        self.state_started = now
        self.controls.dots.set_progress(self.walk.tasks_done)

    # -- steps ------------------------------------------------------------------------------
    def _enter_step(self, *, opening: str | None = None) -> None:
        now = self.clock()
        step = self.walk.step
        self.shown_step = step
        self._hints.reset(self.clock())
        self._hint_target = None
        self._celebrating_choice = None
        self._point_until = 0.0
        self._demo = None
        self._auto_trace = False
        self._meet_revealed = 0
        self.tracker = None
        self.ink = None
        queue = self.speech_queue
        queue.clear()
        if opening is not None:
            queue.enqueue(opening, gap=0.3)
        if step is None:
            self._sync_controls()
            return
        value = step.numeral.value
        if step.kind is StepKind.MEET:
            self.state = AppState.MEET
            self._enqueue_meet(step)
            if opening is not None:
                self._meet_limit += MEET_OPENING_SECONDS
        elif step.is_find:
            self.state = AppState.PLAYING
            index = self.walk.step_index
            if step.kind is StepKind.REVIEW and index > 0 and self.walk.steps[index - 1].kind is not StepKind.REVIEW:
                queue.enqueue("tito.progress", gap=0.3)
            queue.enqueue(ask_cue(value), tag="sign", gap=0.4)
        elif step.kind is StepKind.TRACE:
            self.state = AppState.PLAYING
            self._start_trace(keep_progress=False)
            queue.enqueue(count_cue(value), gap=0.3)
            if value == 0:
                # Owner-approved "Let's write number 0!" (silent if absent).
                queue.enqueue(WRITE_ZERO_CUE, gap=0.3)
            self._start_demo(now, delay=0.4)
        else:
            self.state = AppState.PLAYING
            queue.enqueue(count_cue(value), tag="numeral", gap=0.4)
        self.state_started = now
        self._quiet_since = now
        self._sync_controls()

    def _start_trace(self, *, keep_progress: bool) -> None:
        step = self.walk.step
        assert step is not None
        box = self.controls.geometry.trace_box
        guide = self.renderer.guide(step.numeral.value, box.size)
        old = self.tracker if keep_progress else None
        self.tracker = TraceTracker(guide)
        self.ink = TraceInk(guide, box.size, step.numeral.color)
        if old is not None and old.guide.value == guide.value:
            self.tracker.stroke_index = old.stroke_index
            self.tracker.progress = old.progress * guide.scale / max(0.001, old.guide.scale)
        self.ink.sync(self.tracker.stroke_index, self.tracker.progress)

    def _start_demo(self, now: float, *, delay: float = 0.0) -> None:
        if self.tracker is None or self.tracker.complete:
            return
        self._demo = (self.tracker.stroke_index, self.tracker.progress, now + delay)

    def _demo_point(self, now: float) -> tuple[float, float] | None:
        if self._demo is None or self.tracker is None:
            return None
        stroke_index, start, started = self._demo
        if stroke_index != self.tracker.stroke_index or now < started:
            return None
        stroke = self.tracker.stroke
        if stroke is None:
            return None
        distance = start + (now - started) * DEMO_SPEED
        if distance > stroke.length + DEMO_SPEED * 0.4:
            self._demo = None
            return None
        return stroke.point_at(distance)

    def _sync_controls(self) -> None:
        step = self.shown_step
        eliminated = self.walk.eliminated if step is self.walk.step else frozenset()
        self.controls.sync(step, eliminated=eliminated, tasks_done=self.walk.tasks_done, step_key=(id(self.walk), self.walk.step_index))

    # -- state ------------------------------------------------------------------------------
    def _advance_state(self, now: float) -> bool:
        elapsed = now - self.state_started
        changed = False
        if self.state is AppState.MEET:
            if (elapsed >= MEET_MIN_SECONDS and not self.speech_queue.busy) or elapsed >= self._meet_limit:
                self.walk.finish_meet()
                self._enter_step()
                changed = True
        elif self.state is AppState.PLAYING:
            if (
                not self.speech_queue.busy
                and self._hints.is_due(now, self._quiet_since)
                and not (self.tracker is not None and (self.tracker.dragging or self._auto_trace))
            ):
                self._give_idle_hint(now)
                changed = True
            if self._point_until and now >= self._point_until:
                self._point_until = 0.0
                changed = True
            if self._demo is not None or (self._start_pulse_until and now < self._start_pulse_until + 0.3):
                changed = True
        elif self.state is AppState.TRY_AGAIN:
            if elapsed >= SHAKE_SECONDS:
                self._shake = None
                self.state = AppState.PLAYING
                self.state_started = now
                self._quiet_since = now
            changed = True
        elif self.state is AppState.CELEBRATE:
            done = elapsed >= CELEBRATE_MIN and not self.speech_queue.busy
            if done or elapsed >= CELEBRATE_MAX:
                self._sparkle = None
                self._next_step(now)
            changed = True
        elif self.state is AppState.BLOOM:
            hold_done = elapsed >= BLOOM_HOLD and (not self.speech_queue.busy or elapsed >= BLOOM_MAX - FLIGHT_SECONDS)
            if self._flight_started is None and hold_done:
                self._flight_started = now
            if self._flight_started is not None and now - self._flight_started >= FLIGHT_SECONDS:
                self._flight_started = None
                self._next_step(now)
            changed = True
        elif self.state is AppState.FINALE:
            if elapsed >= FINALE_SECONDS:
                self._show_completion(now)
            changed = True
        phase = int(now * 4)
        if phase != self._pulse_phase:
            self._pulse_phase = phase
            if self._hint_target is not None or now < self._point_until or now < self._start_pulse_until:
                changed = True
        return changed

    def _give_idle_hint(self, now: float) -> None:
        step = self.walk.step
        if step is None:
            return
        self._hints.fire(now)
        self.walk.record_hint()
        self._point_until = now + self._hints.animation_seconds(POINT_SECONDS)
        self._quiet_since = now
        self.speech_queue.clear()
        value = step.numeral.value
        if step.kind is StepKind.TRACE:
            self._start_pulse_until = now + START_PULSE_SECONDS * 2
            self._start_demo(now, delay=0.3)
            self.speech_queue.enqueue(count_cue(value), gap=0.3)
        elif step.kind is StepKind.SHOW:
            self.speech_queue.enqueue(count_cue(value), tag="numeral", gap=0.4)
        else:
            self.speech_queue.enqueue(ask_cue(value), tag="sign", gap=0.4)

    def _next_step(self, now: float) -> None:
        self._celebrating_choice = None
        if self.walk.is_complete:
            self._finish_walk(now)
            return
        self._enter_step()

    def _finish_walk(self, now: float) -> None:
        payload = self.walk.consume_completion()
        if payload is not None:
            self.progress.group = next_group(self.walk.group, self.walk, self.planner.group_count)
            self.progress.rounds_completed += 1
            self._save()
            self.events.walk_completed(self.session_id, payload)
        self.state = AppState.FINALE
        self.state_started = now
        self.shown_step = None
        self.tracker = None
        self.ink = None
        self.audio.play_sfx("bloom")
        self.speech_queue.clear()
        self.speech_queue.enqueue("tito.celebrate", gap=0.2)
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._sync_controls()

    def _save(self) -> None:
        self.progress_port.save(self.progress)

    def _show_completion(self, now: float) -> None:
        numerals = "   ".join(str(item.value) for item in self.walk.written)
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(numerals,) if numerals else (),
                achievement_count=self.walk.task_total,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self.state_started = now

    def _restart(self) -> None:
        self.walk = self._new_walk()
        self.season = self._season()
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        self.completion.clear()
        if self.renderer.cast is not None:
            self.renderer.cast.reset()
        self.controls.reset_round(self.walk.task_total)
        self.completion = self._make_completion()
        self._activated = True
        self._enter_step(opening="tito.ready")

    # -- drawing ------------------------------------------------------------------------------
    def scene_state(self) -> SceneState:
        now = self.clock()
        elapsed = now - self.state_started
        step = self.shown_step
        trace_view = None
        if self.tracker is not None and self.ink is not None and step is not None and step.kind is StepKind.TRACE:
            trace_view = TraceView(
                guide=self.tracker.guide,
                ink=self.ink,
                stroke_index=self.tracker.stroke_index,
                head=self.tracker.head,
                progress=self.tracker.progress,
                demo_point=self._demo_point(now) if self.state is AppState.PLAYING else None,
                start_pulse=now < self._start_pulse_until,
                complete=self.tracker.complete,
            )
        bloom = flight = None
        written = self.walk.written
        if self.state is AppState.BLOOM:
            bloom = elapsed
            if self._flight_started is not None and written and self._flight_from is not None:
                t = (now - self._flight_started) / FLIGHT_SECONDS
                slot = self.controls.geometry.path_slot(len(self.walk.numerals), len(written) - 1)
                flight = (written[-1], self._flight_from, (slot.centerx - 20, slot.bottom - 40), t)
        shake = None
        if self._shake is not None:
            control, started = self._shake
            t = now - started
            if t < SHAKE_SECONDS:
                shake = (control, int(9 * (1 - t / SHAKE_SECONDS) * (1 if int(t * 36) % 2 else -1)))
        sparkle = None
        if self._sparkle is not None and now - self._sparkle[1] < SPARKLE_SECONDS:
            sparkle = (self._sparkle[0], (now - self._sparkle[1]) / SPARKLE_SECONDS)
        hint = self._hint_target
        if hint is None and now < self._point_until and step is not None:
            hint = "sign" if step.is_find else ("numeral" if step.kind in {StepKind.MEET, StepKind.SHOW} else None)
        speaking = self.speech_queue.current_tag
        counting = None
        if speaking is not None and speaking.startswith("count."):
            _, option, item = speaking.split(".")
            counting = (int(option), int(item))
        return SceneState(
            step=step,
            season=self.season,
            written=written,
            path_count=len(self.walk.numerals),
            speaking=speaking,
            hint_target=hint,
            pulse_phase=self._pulse_phase,
            shake=shake,
            tito_pointing=now < self._point_until or self.state is AppState.MEET,
            meet_revealed=self._meet_revealed,
            trace=trace_view,
            bloom=bloom,
            flight=flight,
            sparkle_at=sparkle,
            finale=elapsed if self.state is AppState.FINALE else None,
            celebrating_choice=self._celebrating_choice if self.state is AppState.CELEBRATE else None,
            counting=counting,
        )

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self._surfaces.draw(self.canvas.surface)
            return
        self.renderer.draw_scene(self.canvas.surface, self.controls.geometry, self.scene_state(), draw_controls=self._draw_controls)

    def _draw_controls(self, surface: pygame.Surface, offsets: dict[str, tuple[int, int]]) -> None:
        moved = []
        for control in self.controls.choices:
            offset = offsets.get(control.control_id)
            if offset is not None and control.visible:
                moved.append((control, control.rect))
                control.rect = control.rect.move(offset)
        try:
            self._surfaces.draw(surface)
        finally:
            for control, base in moved:
                control.rect = base


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "BoscoApp"]
