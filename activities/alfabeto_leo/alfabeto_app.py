"""App lifecycle, step flow and input orchestration for L'Alfabeto di Leo.

Round grammar (P7 §1): Leo says the letter with its picture (MEET) → the child
finds it among letter tiles (FIND) → traces it stroke by stroke (TRACE) → it
blooms and is planted in the garden → … → two review finds → confetti and the
shared completion scene.

Hints are graduated: after ~6 s of quiet Leo points and the question (or the
tracing demonstration) is repeated; a first wrong tile makes Leo think and asks
again; from the second wrong tile the right one pulses while Leo names it. A
touch away from the stroke only pulses the green start dot. Retries are
unlimited and kind; tracing never fails.
"""

from __future__ import annotations

from enum import StrEnum
import random
import time
from typing import Callable

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
    from .alfabeto_art import TraceInk
    from .alfabeto_audio import AlfabetoAudio, SpeechQueue, ask_cue, letter_cue
    from .alfabeto_controls import LEO_HEIGHT, GardenControls, choice_id
    from .alfabeto_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GardenPlanner,
        GardenRound,
        GardenStep,
        StepKind,
        get_letter_catalogue,
        lesson_language,
        next_group,
    )
    from .alfabeto_renderer import AlfabetoRenderer, SceneState, TraceView
    from .alfabeto_services import AlfabetoProgress, EventPort, ProgressPort
    from .alfabeto_trace import TraceEvent, TraceTracker
else:
    from alfabeto_art import TraceInk
    from alfabeto_audio import AlfabetoAudio, SpeechQueue, ask_cue, letter_cue
    from alfabeto_controls import LEO_HEIGHT, GardenControls, choice_id
    from alfabeto_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GardenPlanner,
        GardenRound,
        GardenStep,
        StepKind,
        get_letter_catalogue,
        lesson_language,
        next_group,
    )
    from alfabeto_renderer import AlfabetoRenderer, SceneState, TraceView
    from alfabeto_services import AlfabetoProgress, EventPort, ProgressPort
    from alfabeto_trace import TraceEvent, TraceTracker


IDLE_HINT_SECONDS = 6.0
MAX_IDLE_HINTS = 3
POINT_SECONDS = 2.6
SHAKE_SECONDS = 0.45
MEET_MIN_SECONDS = 2.2
MEET_MAX_SECONDS = 7.0
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


class AlfabetoApp:
    """Coordinate the garden round, speech, tracing, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        planner: GardenPlanner,
        progress: AlfabetoProgress,
        progress_port: ProgressPort,
        events: EventPort,
        renderer: AlfabetoRenderer,
        typography: GreiaTypography,
        resources,
        audio: AlfabetoAudio,
        speech_queue: SpeechQueue,
        locale: str,
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
        self.language = lesson_language(locale)
        self.rng = rng
        self.session_id = session_id
        self.clock = clock
        self._alphabet = {item.char for item in get_letter_catalogue(self.language)}

        self.round = self._new_round()
        self.state = AppState.MEET
        self.state_started = clock()
        self.shown_step: GardenStep | None = self.round.step
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._last_tick = clock()
        self._quiet_since = clock()
        self._idle_hints = 0
        self._point_until = 0.0
        self._hint_target: str | None = None
        self._shake: tuple[str, float] | None = None
        self._celebrating_choice: int | None = None
        self._sparkle: tuple[tuple[int, int], float] | None = None
        self._pulse_phase = 0
        self._activated = False
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
        if renderer.cast is None:
            renderer.cast = CastFeedback("leo", height=LEO_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = GardenControls(
            self.kit,
            renderer.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            task_total=self.round.task_total,
            on_choice=self._on_choice,
            on_listen=self._on_listen,
            on_letter=self._on_letter,
            on_trace_key=self._on_trace_key,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self.completion = self._make_completion()
        self._enter_step(opening=True)

    # -- setup helpers --------------------------------------------------------------
    def _new_round(self) -> GardenRound:
        group = self.progress.group_for(self.language)
        return GardenRound(self.planner.build(group, self.progress.traced), group=group)

    def _make_completion(self) -> PygameCompletionScreen:
        """Shared cast completion scene sized to this round's stars."""

        return PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=COMPLETION_PALETTE,
            scene=CompletionScene(self.kit, character="leo", star_total=self.round.task_total),
        )

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(
            to_logical=self.canvas.pointer,
            is_safe=lambda pos: _safe_point(self.screen, pos),
        )

    # -- main loop --------------------------------------------------------------------
    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)
            repeat = self._input.poll()
            if repeat is not None:
                self._dispatch(repeat)
            if self.tick():
                self._dirty = True
            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            ticker.tick(30 if self._animating() else 20)
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
        cast = self.renderer.cast
        if cast is not None and cast.update():
            changed = True
        if self._auto_trace and self.tracker is not None and self.state is AppState.PLAYING and dt > 0:
            event = self.tracker.auto_advance(AUTO_TRACE_SPEED * dt)
            # One action press traces one stroke, then waits for the next press.
            if event in {TraceEvent.STROKE_DONE, TraceEvent.LETTER_DONE} or self.tracker.complete:
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
            self.canvas = PygameReferenceCanvas(self.screen)
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
            # A letter key that matches a tile picks it (real keyboard letter
            # recognition); otherwise R replays the spoken prompt.
            if pygame.K_a <= event.key <= pygame.K_z and self._typed_letter(chr(ord("A") + event.key - pygame.K_a)):
                self._dirty = True
                return
            if event.key == pygame.K_r:
                self._note_input()
                self._replay()
                self._dirty = True
                return
        if event.type == pygame.TEXTINPUT and event.text.upper() == "Ñ" and self._typed_letter("Ñ"):
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

    def _typed_letter(self, char: str) -> bool:
        """A physical letter key picks the matching tile (real letter recognition)."""

        step = self.round.step
        if self.state is not AppState.PLAYING or step is None or not step.is_find:
            return False
        for index, item in enumerate(step.choices):
            if item.char == char and index not in self.round.eliminated:
                self._note_input()
                self._on_choice(index)
                return True
        return False

    def _trace_pointer(self, pointer: KitPointer) -> bool:
        """Route finger/pointer input on the tracing box to the tracker."""

        tracker = self.tracker
        step = self.round.step
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
        if key == pygame.K_r or pygame.K_a <= key <= pygame.K_z:
            before = (self.round.step_index, self.state, self.speech_queue.busy)
            self._handle_event(event)
            return before != (self.round.step_index, self.state, self.speech_queue.busy) or self._activated
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

    def _on_letter(self) -> None:
        self._activated = True
        step = self.round.step
        if step is not None and step.kind is StepKind.MEET:
            self.speech_queue.clear()
            self.speech_queue.enqueue(letter_cue(step.letter.char), tag="letter", gap=0.4)

    def _on_trace_key(self) -> None:
        """Keyboard/controller: the current stroke traces itself ("follow the dot")."""

        self._activated = True
        if self.tracker is not None and self.state is AppState.PLAYING and not self.tracker.complete:
            self._demo = None
            self._auto_trace = True

    def _on_choice(self, index: int) -> None:
        step = self.round.step
        if self.state is not AppState.PLAYING or step is None or not step.is_find or index >= len(step.choices):
            return
        self._activated = True
        result = self.round.select(index)
        if result.correct:
            self._on_correct(step, index)
        else:
            self._on_wrong(step, index, result.errors)

    def _replay(self) -> None:
        step = self.round.step
        if step is None:
            return
        queue = self.speech_queue
        queue.clear()
        if step.is_find:
            queue.enqueue(ask_cue(step.letter.char), gap=0.4)
        elif step.kind is StepKind.MEET:
            queue.enqueue(letter_cue(step.letter.char), tag="letter", gap=0.4)
        elif step.kind is StepKind.TRACE:
            queue.enqueue(letter_cue(step.letter.char), gap=0.3)
            self._start_demo(self.clock())

    # -- feedback grammar ---------------------------------------------------------------------
    def _on_wrong(self, step: GardenStep, index: int, errors: int) -> None:
        self.audio.play_sfx("retry")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._point_until = 0.0
        self._shake = (choice_id(index), self.clock())
        self.state = AppState.TRY_AGAIN
        self.state_started = self.clock()
        self._sync_controls()
        remaining = [i for i in range(len(step.choices)) if i not in self.round.eliminated]
        demonstrate = errors >= 2 or len(remaining) == 1
        queue = self.speech_queue
        queue.clear()
        queue.enqueue("leo.retry", gap=0.35)
        if demonstrate:
            # Demonstrate: the right tile pulses while Leo names its letter.
            queue.enqueue(letter_cue(step.letter.char), tag=choice_id(step.correct_index), gap=0.35)
            self._hint_target = choice_id(step.correct_index)
        else:
            queue.enqueue(ask_cue(step.letter.char), gap=0.35)

    def _on_correct(self, step: GardenStep, index: int) -> None:
        self.audio.play_sfx("correct")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._point_until = 0.0
        self._hint_target = None
        self._celebrating_choice = index
        self._sparkle = (self.controls.choice_center(index), self.clock())
        queue = self.speech_queue
        queue.clear()
        queue.enqueue(letter_cue(step.letter.char), tag=choice_id(index), gap=0.3)
        if step.kind is StepKind.REVIEW and self.round.is_complete:
            queue.enqueue("leo.praise", gap=0.2)
        self.state = AppState.CELEBRATE
        self.state_started = self.clock()
        self.controls.dots.set_progress(self.round.tasks_done)

    def _on_trace_event(self, event: TraceEvent, now: float) -> None:
        if event is TraceEvent.STROKE_DONE:
            self.audio.play_sfx("stroke")
            assert self.tracker is not None
            end = self.tracker.guide.strokes[self.tracker.stroke_index - 1].points[-1]
            box = self.controls.geometry.trace_box
            self._sparkle = ((int(box.left + end[0]), int(box.top + end[1])), now)
            self._demo = None
            self._start_demo(now, delay=0.5)
        elif event is TraceEvent.LETTER_DONE:
            self._on_letter_traced(now)

    def _on_letter_traced(self, now: float) -> None:
        step = self.round.step
        assert step is not None and self.ink is not None and self.tracker is not None
        self.ink.sync(len(self.tracker.guide.strokes), 0.0)
        char = step.letter.char
        had_all = self._alphabet <= set(self.progress.traced)
        if self.progress.record_trace(char):
            self.events.letter_learned(self.session_id, char)
        if not had_all and self._alphabet <= set(self.progress.traced):
            self.events.alphabet_completed(self.session_id, len(self._alphabet))
        self.round.finish_trace()
        self._save()
        self.audio.play_sfx("bloom")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._demo = None
        self._auto_trace = False
        self._point_until = 0.0
        queue = self.speech_queue
        queue.clear()
        queue.enqueue(letter_cue(char), tag="bloom", gap=0.3)
        queue.enqueue("leo.praise", gap=0.2)
        self._flight_from = self.controls.geometry.trace_box.center
        self.state = AppState.BLOOM
        self.state_started = now
        self.controls.dots.set_progress(self.round.tasks_done)

    # -- steps ------------------------------------------------------------------------------
    def _enter_step(self, *, opening: bool = False) -> None:
        now = self.clock()
        step = self.round.step
        self.shown_step = step
        self._idle_hints = 0
        self._hint_target = None
        self._celebrating_choice = None
        self._point_until = 0.0
        self._demo = None
        self._auto_trace = False
        self.tracker = None
        self.ink = None
        queue = self.speech_queue
        queue.clear()
        if opening:
            queue.enqueue("leo.ready", gap=0.3)
        if step is None:
            self._sync_controls()
            return
        if step.kind is StepKind.MEET:
            self.state = AppState.MEET
            queue.enqueue(letter_cue(step.letter.char), tag="letter", gap=0.5)
        elif step.is_find:
            self.state = AppState.PLAYING
            first_review = step.kind is StepKind.REVIEW and self.round.steps[self.round.step_index - 1].kind is not StepKind.REVIEW
            if first_review:
                queue.enqueue("leo.progress", gap=0.3)
            queue.enqueue(ask_cue(step.letter.char), gap=0.4)
        else:
            self.state = AppState.PLAYING
            self._start_trace(keep_progress=False)
            queue.enqueue(letter_cue(step.letter.char), gap=0.3)
            self._start_demo(now, delay=0.4)
        self.state_started = now
        self._quiet_since = now
        self._sync_controls()

    def _start_trace(self, *, keep_progress: bool) -> None:
        step = self.round.step
        assert step is not None
        box = self.controls.geometry.trace_box
        guide = self.renderer.guide(step.letter.char, box.size)
        old = self.tracker if keep_progress else None
        self.tracker = TraceTracker(guide)
        self.ink = TraceInk(guide, box.size, step.letter.color)
        if old is not None and old.guide.char == guide.char:
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
        eliminated = self.round.eliminated if step is self.round.step else frozenset()
        self.controls.sync(step, eliminated=eliminated, tasks_done=self.round.tasks_done, step_key=(id(self.round), self.round.step_index))

    # -- state ------------------------------------------------------------------------------
    def _advance_state(self, now: float) -> bool:
        elapsed = now - self.state_started
        changed = False
        if self.state is AppState.MEET:
            if (elapsed >= MEET_MIN_SECONDS and not self.speech_queue.busy) or elapsed >= MEET_MAX_SECONDS:
                self.round.finish_meet()
                self._enter_step()
                changed = True
        elif self.state is AppState.PLAYING:
            if (
                not self.speech_queue.busy
                and self._idle_hints < MAX_IDLE_HINTS
                and now - self._quiet_since >= IDLE_HINT_SECONDS
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
        step = self.round.step
        if step is None:
            return
        self._idle_hints += 1
        self.round.record_hint()
        self._point_until = now + POINT_SECONDS
        self._quiet_since = now
        if step.kind is StepKind.TRACE:
            self._start_pulse_until = now + START_PULSE_SECONDS * 2
            self._start_demo(now, delay=0.3)
            self.speech_queue.clear()
            self.speech_queue.enqueue(letter_cue(step.letter.char), gap=0.3)
        else:
            self.speech_queue.clear()
            self.speech_queue.enqueue(ask_cue(step.letter.char), gap=0.4)

    def _next_step(self, now: float) -> None:
        self._celebrating_choice = None
        if self.round.is_complete:
            self._finish_round(now)
            return
        self._enter_step()

    def _finish_round(self, now: float) -> None:
        payload = self.round.consume_completion()
        if payload is not None:
            self.progress.groups[self.language] = next_group(self.round.group, self.round, self.planner.group_count)
            self.progress.rounds_completed += 1
            self._save()
            self.events.garden_completed(self.session_id, payload)
        self.state = AppState.FINALE
        self.state_started = now
        self.shown_step = None
        self.tracker = None
        self.ink = None
        self.audio.play_sfx("bloom")
        self.speech_queue.clear()
        self.speech_queue.enqueue("leo.celebrate", gap=0.2)
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._sync_controls()

    def _save(self) -> None:
        self.progress_port.save(self.progress)

    def _show_completion(self, now: float) -> None:
        letters = "  ".join(item.char for item in self.round.planted)
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(letters,) if letters else (),
                achievement_count=self.round.task_total,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self.state_started = now

    def _restart(self) -> None:
        self.round = self._new_round()
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self._surfaces.pop_overlay()
        self.completion.clear()
        if self.renderer.cast is not None:
            self.renderer.cast.reset()
        self.controls.reset_round(self.round.task_total)
        self.completion = self._make_completion()
        self._activated = True
        self._enter_step(opening=True)

    # -- drawing ------------------------------------------------------------------------------
    def scene_state(self) -> SceneState:
        now = self.clock()
        elapsed = now - self.state_started
        step = self.shown_step
        picture = ""
        if step is not None:
            picture = step.letter.picture_for(self.language)
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
        planted = self.round.planted
        if self.state is AppState.BLOOM:
            bloom = elapsed
            if self._flight_started is not None and planted and self._flight_from is not None:
                t = (now - self._flight_started) / FLIGHT_SECONDS
                slot = self.controls.geometry.garden_slot(len(self.round.letters), len(planted) - 1)
                flight = (planted[-1], self._flight_from, (slot.centerx - 22, slot.bottom - 40), t)
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
        if hint is None and now < self._point_until and step is not None and step.kind is StepKind.MEET:
            hint = "letter"
        return SceneState(
            step=step,
            picture=picture,
            planted=planted,
            garden_count=len(self.round.letters),
            speaking=self.speech_queue.current_tag,
            hint_target=hint,
            pulse_phase=self._pulse_phase,
            shake=shake,
            leo_pointing=now < self._point_until or self.state is AppState.MEET,
            trace=trace_view,
            bloom=bloom,
            flight=flight,
            sparkle_at=sparkle,
            finale=elapsed if self.state is AppState.FINALE else None,
            celebrating_choice=self._celebrating_choice if self.state is AppState.CELEBRATE else None,
            bouquet=(
                tuple((item, item.picture_for(self.language)) for item in planted)
                if self.state is AppState.FINALE
                else ()
            ),
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


__all__ = ["AlfabetoApp", "AppState"]
