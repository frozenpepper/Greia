"""App lifecycle, speech flow and input orchestration for Leo's Syllable Train.

Round grammar (P7 §1): a train arrives with one wagon per beat → spoken goal →
clap / choose → the train reads (cheer) → it leaves → progress dots → finale →
shared completion scene.

* Italian / Spanish / (staged) French: the word is said; the child claps its
  beats on the drum (each clap couples a beat and says that syllable), then
  builds every wagon (vowel after the given consonant, or whole syllable
  tiles); the train reads "LU… NA… luna!".
* English: the train asks for N beats (drum beats light its wagons); the child
  chooses the picture whose word fits, then claps its beats onto the wagons.

Hints are graduated: after ~6 s of quiet Leo points and the goal is replayed
with a pulse; a first wrong pick makes Leo think and contrasts the pick with
the target; from the second wrong pick the right tile pulses while it is
demonstrated. Retries are unlimited and always kind.
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
    from .sillabe_audio import CLAP_PROMPT_CUE, SFX_PREFIX, SillabeAudio, SpeechQueue
    from .sillabe_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WORD_DONE_CUES,
        ReadingMethod,
        TrainWord,
        syllable_cue,
    )
    from .sillabe_controls import (
        LEO_HEIGHT,
        PICTURE_SIZE,
        TILE_TEXT_SIZE,
        WAGON_FACE,
        TrainControls,
        TrainLayout,
        choice_id,
    )
    from .sillabe_model import (
        CHALLENGE_COUNT,
        ChoiceStep,
        Phase,
        StepKind,
        TrainChallenge,
        TrainRoundFactory,
        TrainSession,
        adapt_level,
    )
    from .sillabe_renderer import Flight, SceneState, SillabeRenderer
    from .sillabe_services import EventPort, ProgressPort
else:
    from sillabe_audio import CLAP_PROMPT_CUE, SFX_PREFIX, SillabeAudio, SpeechQueue
    from sillabe_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WORD_DONE_CUES,
        ReadingMethod,
        TrainWord,
        syllable_cue,
    )
    from sillabe_controls import (
        LEO_HEIGHT,
        PICTURE_SIZE,
        TILE_TEXT_SIZE,
        WAGON_FACE,
        TrainControls,
        TrainLayout,
        choice_id,
    )
    from sillabe_model import (
        CHALLENGE_COUNT,
        ChoiceStep,
        Phase,
        StepKind,
        TrainChallenge,
        TrainRoundFactory,
        TrainSession,
        adapt_level,
    )
    from sillabe_renderer import Flight, SceneState, SillabeRenderer
    from sillabe_services import EventPort, ProgressPort


POINT_SECONDS = 2.6
SHAKE_SECONDS = 0.45
ARRIVE_SECONDS = 1.1
DEPART_SECONDS = 1.3
TRAIN_TRAVEL = 860
FLIGHT_START = 0.15
FLIGHT_END = 0.70
POP_SECONDS = 0.5
RING_SECONDS = 0.5
STEP_MIN = 1.2
STEP_MAX = 3.5
BLEND_MIN = 2.0
BLEND_MAX = 8.0
FINALE_SECONDS = 2.4
WHEEL_STRIDE = 9  # px of travel per wheel frame

_VOWEL_KEYS = {getattr(pygame, f"K_{c.lower()}"): c for c in "AEIOU"}


class AppState(StrEnum):
    ARRIVE = "arrive"
    PLAYING = "playing"
    TRY_AGAIN = "try_again"
    STEP = "step"          # a wagon was built / a picture chosen; the next part follows
    CLAPPED = "clapped"    # all beats clapped on a building train; the word is said
    BLEND = "blend"        # the train reads the word; Leo cheers
    DEPART = "depart"
    FINALE = "finale"
    TERMINAL = "terminal"


class SillabeActivity:
    """Coordinate the train model, speech sequence, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: TrainSession,
        factory: TrainRoundFactory,
        renderer: SillabeRenderer,
        typography: GreiaTypography,
        resources,
        locale: str,
        progress: ProgressPort,
        events: EventPort,
        audio: SillabeAudio,
        speech_queue: SpeechQueue,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.session = session
        self.factory = factory
        self.renderer = renderer
        self.typography = typography
        self.resources = resources
        self.language = locale.replace("_", "-").split("-", 1)[0].lower()
        self.progress = progress
        self.events = events
        self.audio = audio
        self.speech_queue = speech_queue
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.state = AppState.ARRIVE
        self.state_started = clock()
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._last_tick = clock()
        self._quiet_since = clock()
        self._hints = IdleHintScheduler(now=self._quiet_since)
        self._point_until = 0.0
        self._hint_target: str | None = None
        self._shake: tuple[str, float] | None = None
        self._picked: tuple[int, ChoiceStep] | None = None
        self._ring: tuple[int, float] | None = None
        self._display: TrainChallenge | None = session.current_challenge
        self._pulse_phase = 0
        self._pulse_due = False  # a decorative pulse step is due (ambient frame)
        self._activated = False
        self._opening = True

        # Shared control kit (ADR 0037): learn Collection -> orange accent. The
        # kit shares the Activity's picture cache so art is decoded once.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=renderer.art.art
        )
        if renderer.cast is None:
            renderer.cast = CastFeedback("leo", height=LEO_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = TrainControls(
            self.kit,
            renderer.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_choice=self._on_choice,
            on_listen=self._on_listen,
            on_sign=self._on_sign,
            on_drum=self._on_drum,
        )
        self.controls.sync(session, interactive=False)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(
            to_logical=self.canvas.pointer,
            is_safe=lambda pos: _safe_point(self.screen, pos),
        )
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(217, 242, 208),
                panel=(255, 251, 235),
                panel_border=(180, 83, 9),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(243, 154, 56),
                primary_text=(61, 44, 31),
            ),
            scene=CompletionScene(self.kit, character="leo", star_total=CHALLENGE_COUNT),
        )
        self.audio.play_sfx("whistle")

    @property
    def method(self) -> ReadingMethod:
        return self.factory.method

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
            frame = frames.frame(dirty=self._dirty, ambient=self._pulse_due)
            self._pulse_due = False
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
        return 0

    def tick(self) -> bool:
        """Advance speech, cast and state timers; True when the frame changed."""

        now = self.clock()
        dt = max(0.0, now - self._last_tick)
        self._last_tick = now
        was_busy = self.speech_queue.busy
        changed = self.speech_queue.update(dt)
        if was_busy and not self.speech_queue.busy:
            self._quiet_since = now
        cast = self.renderer.cast
        if cast is not None and cast.update():
            changed = True
        if self._ring is not None and now - self._ring[1] >= RING_SECONDS:
            self._ring = None
            changed = True
        return self._advance_state(now) or changed or self._ring is not None

    def _animating(self) -> bool:
        cast = self.renderer.cast
        return (
            self.state is not AppState.PLAYING and self.state is not AppState.TERMINAL
            or self.speech_queue.busy
            or self._hint_target is not None
            or self._ring is not None
            or (cast is not None and cast.animating)
        )

    # -- input --------------------------------------------------------------------------
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
            self._input = PygameControlInput(
                to_logical=self.canvas.pointer,
                is_safe=lambda pos: _safe_point(self.screen, pos),
            )
            self._dirty = True
            return
        if self.state not in {AppState.PLAYING, AppState.TERMINAL}:
            return
        if event.type == pygame.KEYDOWN and self.state is AppState.PLAYING:
            if self._pick_by_vowel_key(event.key):
                self._dirty = True
                return
            if event.key == pygame.K_r:
                self._note_input()
                self._speak_goal(hint=False)
                self._dirty = True
                return
        translated = self._input.translate(event)
        if translated is not None and self._dispatch(translated):
            self._dirty = True

    def _pick_by_vowel_key(self, key: int) -> bool:
        """Typing a vowel picks that vowel tile (vowel steps only)."""

        vowel = _VOWEL_KEYS.get(key)
        step = self.session.current_step
        if vowel is None or step is None or step.kind is not StepKind.VOWEL:
            return False
        for index, choice in enumerate(step.choices):
            if choice == vowel and index not in self.session.eliminated:
                self._note_input()
                self.controls.layer.focus(choice_id(index))
                self._on_choice(index)
                return True
        return False

    def _dispatch(self, kit_input) -> bool:
        if self.state not in {AppState.PLAYING, AppState.TERMINAL}:
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

    def _handle_pointer(self, raw_pos: tuple[int, int]) -> bool:
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

    def _handle_keyboard(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping (tests/tools)."""

        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)
        self._activated = False
        before = self._quiet_since
        if key == pygame.K_r or key in _VOWEL_KEYS:
            self._handle_event(event)
            if self._activated or self._quiet_since != before:
                return True
            if key == pygame.K_r:
                return False
        translated = self._input.translate(event)
        if translated is None:
            return False
        handled = self._dispatch(translated)
        return handled or self._activated

    # -- control callbacks ------------------------------------------------------------------
    def _on_listen(self) -> None:
        self._activated = True
        self._speak_goal(hint=False)

    def _on_sign(self) -> None:
        self._activated = True
        challenge = self.session.current_challenge
        if challenge is None:
            return
        self.speech_queue.clear()
        if self.method is ReadingMethod.BEATS and self.session.phase is Phase.CHOOSE:
            self._enqueue_train_beats(challenge.wagons)
        else:
            self.speech_queue.enqueue(challenge.word.audio_id, tag="sign", gap=0.3)
        self._quiet_since = self.clock()

    def _on_drum(self) -> None:
        if self.state is not AppState.PLAYING:
            return
        challenge = self.session.current_challenge
        result = self.session.clap()
        if result is None or challenge is None:
            return
        self._activated = True
        self._hint_target = None
        self._point_until = 0.0
        self.audio.play_sfx("drum")
        self._ring = (result.beat, self.clock())
        if challenge.clap_first:
            # Each beat says its syllable; clips queue so fast claps never cut.
            if not self.speech_queue.busy or self.speech_queue.current_tag in {None, "sign"}:
                self.speech_queue.clear()
            self.speech_queue.enqueue(
                syllable_cue(challenge.word.syllables[result.beat]), tag=f"wagon.{result.beat}", gap=0.15
            )
        if result.clap_completed and challenge.clap_first:
            self.speech_queue.enqueue(challenge.word.audio_id, tag="train", gap=0.4)
            self._go(AppState.CLAPPED)
            self.controls.sync(self.session, interactive=False)
        elif result.challenge_completed:
            self._on_challenge_done(challenge, result.session_complete)
        self._quiet_since = self.clock()

    def _on_choice(self, index: int) -> None:
        challenge = self.session.current_challenge
        step = self.session.current_step
        if self.state is not AppState.PLAYING or challenge is None or step is None:
            return
        if index >= len(step.choices) or index in self.session.eliminated:
            return
        self._activated = True
        result = self.session.select_choice(index)
        if not result.correct:
            self._on_wrong(challenge, step, index, result.errors)
        elif result.challenge_completed:
            self._picked = (index, step)
            self._on_challenge_done(challenge, result.session_complete)
        else:
            self._on_step(challenge, step, index)

    # -- feedback grammar ----------------------------------------------------------------
    def _on_wrong(self, challenge: TrainChallenge, step: ChoiceStep, index: int, errors: int) -> None:
        self.audio.play_sfx("retry")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._point_until = 0.0
        self._shake = (choice_id(index), self.clock())
        self._go(AppState.TRY_AGAIN)
        self.controls.sync(self.session)

        remaining = [i for i in range(len(step.choices)) if i not in self.session.eliminated]
        demonstrate = errors >= 2 or len(remaining) == 1
        queue = self.speech_queue
        queue.clear()
        queue.enqueue("leo.retry", gap=0.35)
        if step.kind is StepKind.PICTURE:
            # "pizza: DUM DUM" — the picked word's beats, then the right one's.
            shown = step.correct_index if demonstrate else index
            word = step.choices[shown]
            assert isinstance(word, TrainWord)
            queue.enqueue(word.audio_id, tag=choice_id(shown), gap=0.3)
            for beat in range(word.beats):
                queue.enqueue(f"{SFX_PREFIX}drum", tag=f"beat.{beat}", gap=0.12)
        else:
            # "LA … LU" — what the pick would make, then the wagon's syllable.
            if not demonstrate:
                queue.enqueue(syllable_cue(step.syllable_for(index)), tag=choice_id(index), gap=0.35)
            queue.enqueue(syllable_cue(step.target_syllable), tag=f"wagon.{step.wagon}", gap=0.3)
            if demonstrate:
                queue.enqueue(syllable_cue(step.target_syllable), tag=choice_id(step.correct_index), gap=0.3)
        self._hint_target = choice_id(step.correct_index) if demonstrate else None

    def _on_step(self, challenge: TrainChallenge, step: ChoiceStep, index: int) -> None:
        """A wagon was built (or the beats picture chosen); the next part follows."""

        self.audio.play_sfx("correct")
        self._point_until = 0.0
        self._hint_target = None
        self._picked = (index, step)
        queue = self.speech_queue
        queue.clear()
        queue.pause(FLIGHT_END)
        if step.kind is StepKind.PICTURE:
            if self.renderer.cast is not None:
                self.renderer.cast.correct()
            queue.enqueue(challenge.word.audio_id, tag="sign", gap=0.4)
        else:
            queue.enqueue(syllable_cue(step.target_syllable), tag=f"wagon.{step.wagon}", gap=0.4)
        self._go(AppState.STEP)

    def _on_challenge_done(self, challenge: TrainChallenge, session_complete: bool) -> None:
        """The whole word is on the train: it reads it aloud and Leo cheers."""

        self.audio.play_sfx("correct")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._point_until = 0.0
        self._hint_target = None
        self._display = challenge
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.word_completed(self.session_id, milestone)
        if session_complete:
            self._save_completion()
        queue = self.speech_queue
        queue.clear()
        if challenge.clap_first:
            step = challenge.steps[-1]
            queue.pause(FLIGHT_END)
            queue.enqueue(syllable_cue(step.target_syllable), tag=f"wagon.{step.wagon}", gap=0.5)
            # The train reads: "LU … NA … luna!"
            for index, syllable in enumerate(challenge.word.syllables):
                queue.enqueue(syllable_cue(syllable), tag=f"wagon.{index}", gap=0.25)
            queue.enqueue(challenge.word.audio_id, tag="train", gap=0.4)
            if self.session.challenge_index == 1:
                queue.enqueue(WORD_DONE_CUES.get(self.language, "word_complete"), gap=0.3)
        else:
            queue.pause(0.25)
            queue.enqueue(challenge.word.audio_id, tag="train", gap=0.4)
        queue.enqueue("leo.praise", gap=0.2)
        self._go(AppState.BLEND)

    def _speak_goal(self, *, hint: bool) -> None:
        """Say (again) what the current part of the round asks for."""

        challenge = self.session.current_challenge
        if challenge is None:
            return
        queue = self.speech_queue
        queue.clear()
        phase = self.session.phase
        step = self.session.current_step
        opening = self._opening
        self._opening = False
        if opening and self.session.challenge_index == 0:
            queue.enqueue("leo.ready", gap=0.3)
        if phase is Phase.CLAP:
            if self.session.challenge_index == 0 and not hint:
                queue.enqueue(CLAP_PROMPT_CUE, gap=0.3)  # the drum's job, first word only
            queue.enqueue(challenge.word.audio_id, tag="sign", gap=0.4)
            if hint and challenge.clap_first:
                # Model the beats once, in the word's own syllables.
                for index, syllable in enumerate(challenge.word.syllables):
                    queue.enqueue(syllable_cue(syllable), tag=f"wagon.{index}", gap=0.2)
        elif step is not None and step.kind is StepKind.PICTURE:
            self._enqueue_train_beats(challenge.wagons)
            if challenge.level < 3 or hint:
                for index, word in enumerate(step.choices):
                    if index not in self.session.eliminated and isinstance(word, TrainWord):
                        queue.enqueue(word.audio_id, tag=choice_id(index), gap=0.3)
        elif step is not None:
            if self.session.challenge_index == 0 and self.session.step_index == 0 and not hint:
                queue.enqueue("instruction_build", gap=0.35)
            if hint:
                queue.enqueue(challenge.word.audio_id, tag="sign", gap=0.35)
            queue.enqueue(syllable_cue(step.target_syllable), tag=f"wagon.{step.wagon}", gap=0.3)
        self._quiet_since = self.clock()

    def _enqueue_train_beats(self, wagons: int) -> None:
        for beat in range(wagons):
            self.speech_queue.enqueue(f"{SFX_PREFIX}drum", tag=f"beat.{beat}", gap=0.18)
        self.speech_queue.pause(0.25)

    # -- state ----------------------------------------------------------------------------
    def _go(self, state: AppState) -> None:
        self.state = state
        self.state_started = self.clock()

    def _advance_state(self, now: float) -> bool:
        elapsed = now - self.state_started
        changed = False
        state = self.state
        if state is AppState.ARRIVE:
            if elapsed >= ARRIVE_SECONDS:
                self._begin_playing(now, speak=True)
            changed = True
        elif state is AppState.PLAYING:
            if (
                not self.speech_queue.busy
                and self._hints.is_due(now, self._quiet_since)
            ):
                self._give_idle_hint(now)
                changed = True
            if self._point_until and now >= self._point_until:
                self._point_until = 0.0
                changed = True
        elif state is AppState.TRY_AGAIN:
            if elapsed >= SHAKE_SECONDS:
                self._shake = None
                self._go(AppState.PLAYING)
                self._quiet_since = now
            changed = True
        elif state in {AppState.STEP, AppState.CLAPPED}:
            done = elapsed >= STEP_MIN and not self.speech_queue.busy
            if done or elapsed >= STEP_MAX:
                self._picked = None
                self._begin_playing(now, speak=True)
            changed = True
        elif state is AppState.BLEND:
            done = elapsed >= BLEND_MIN and not self.speech_queue.busy
            if done or elapsed >= BLEND_MAX:
                self._picked = None
                self.audio.play_sfx("whistle")
                self._go(AppState.DEPART)
            changed = True
        elif state is AppState.DEPART:
            if elapsed >= DEPART_SECONDS:
                self._after_departure(now)
            changed = True
        elif state is AppState.FINALE:
            if elapsed >= FINALE_SECONDS:
                self._show_completion(now)
            changed = True
        phase = int(now * 4)
        if phase != self._pulse_phase:
            self._pulse_phase = phase
            if now < self._point_until:
                changed = True  # Leo's hint is essential motion (and short)
            elif self._hint_target is not None or self._has_pulsing_target():
                # Pulsing wagon/hint glows are decoration: ambient frames, which
                # the frame governor freezes once the child has been idle.
                self._pulse_due = True
        return changed

    def _has_pulsing_target(self) -> bool:
        if self.state is not AppState.PLAYING:
            return False
        step = self.session.current_step
        return self.session.phase is Phase.CLAP or (step is not None and step.wagon is not None)

    def _begin_playing(self, now: float, *, speak: bool) -> None:
        self._go(AppState.PLAYING)
        self._hints.reset(self.clock())
        self._hint_target = None
        self._display = self.session.current_challenge
        self.controls.sync(self.session)
        if speak:
            self._speak_goal(hint=False)
        self._quiet_since = now

    def _give_idle_hint(self, now: float) -> None:
        if self.session.current_challenge is None:
            return
        self._hints.fire(now)
        self.session.record_hint()
        self._point_until = now + self._hints.animation_seconds(POINT_SECONDS)
        self._speak_goal(hint=True)

    def _after_departure(self, now: float) -> None:
        if self.session.is_complete:
            self._go(AppState.FINALE)
            self.audio.play_sfx("complete")
            self.speech_queue.clear()
            self.speech_queue.enqueue("leo.celebrate", gap=0.2)
            if self.renderer.cast is not None:
                self.renderer.cast.correct()
            self.controls.sync(self.session, interactive=False)
            return
        self._display = self.session.current_challenge
        self.audio.play_sfx("whistle")
        self._go(AppState.ARRIVE)
        self.controls.sync(self.session, interactive=False)

    def _save_completion(self) -> None:
        payload = self.session.consume_completion()
        if payload is None:
            return
        next_level = adapt_level(self.session.level, self.session.history)
        self.progress.save(next_level, self.session.history, words=CHALLENGE_COUNT, stars=CHALLENGE_COUNT)
        self.events.train_completed(self.session_id, payload)

    def _show_completion(self, now: float) -> None:
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=CHALLENGE_COUNT,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self._go(AppState.TERMINAL)

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = TrainSession(challenges, level=next_level, history=self.session.history)
        self._surfaces.pop_overlay()
        self.completion.clear()
        if self.renderer.cast is not None:
            self.renderer.cast.reset()
        self._display = self.session.current_challenge
        self._opening = True
        self._activated = True
        self._hint_target = None
        self.speech_queue.clear()
        self.audio.play_sfx("whistle")
        self._go(AppState.ARRIVE)
        self.controls.sync(self.session, interactive=False)

    # -- drawing --------------------------------------------------------------------------
    def scene_state(self) -> SceneState:
        now = self.clock()
        elapsed = now - self.state_started
        challenge = self._display
        session = self.session
        same = challenge is not None and challenge is session.current_challenge
        step = session.current_step if same else None
        built = session.built_wagons if same else ()
        claps = session.claps if same else 0
        solved = challenge is not None and not same
        if solved:
            built = tuple(range(challenge.wagons))
            claps = challenge.wagons
        active = step.wagon if step is not None and self.state in {AppState.PLAYING, AppState.TRY_AGAIN} else None

        offset = 0
        if self.state is AppState.ARRIVE:
            t = min(1.0, elapsed / ARRIVE_SECONDS)
            offset = -int(TRAIN_TRAVEL * (1 - t) ** 2)
        elif self.state is AppState.DEPART:
            t = min(1.0, elapsed / DEPART_SECONDS)
            offset = int(TRAIN_TRAVEL * t * t)
        wheel_frame = abs(offset) // WHEEL_STRIDE

        sign_picture = True
        if challenge is not None and challenge.method is ReadingMethod.BEATS and not solved:
            # The beats train hides its word until the right picture is chosen.
            sign_picture = session.phase is Phase.CLAP and same
            if self.state is AppState.STEP:
                sign_picture = elapsed >= FLIGHT_END

        sparkle = flight = pop = None
        if self._picked is not None and self.state in {AppState.STEP, AppState.BLEND} and challenge is not None:
            index, picked_step = self._picked
            start = self.controls.choice_center(index)
            if elapsed < 0.6:
                sparkle = (start, elapsed / 0.6)
            if picked_step.kind is StepKind.PICTURE:
                end = self.controls.geometry.sign_face.center
                item, start_size, end_size = picked_step.answer, PICTURE_SIZE, 100
            else:
                wagons, _ = TrainLayout.train_rects(challenge.wagons)
                end = WAGON_FACE.move(wagons[picked_step.wagon].topleft).center
                item, start_size, end_size = picked_step.answer, TILE_TEXT_SIZE, TILE_TEXT_SIZE
                if picked_step.kind is StepKind.VOWEL:
                    end = (end[0] + 22, end[1])
                if elapsed < FLIGHT_END:
                    built = tuple(w for w in built if w != picked_step.wagon)
            if FLIGHT_START <= elapsed < FLIGHT_END:
                flight = Flight(item, start, end, (elapsed - FLIGHT_START) / (FLIGHT_END - FLIGHT_START), start_size, end_size)
            elif FLIGHT_END <= elapsed < FLIGHT_END + POP_SECONDS:
                pop = (end, (elapsed - FLIGHT_END) / POP_SECONDS)
            if picked_step.kind is not StepKind.PICTURE and elapsed < FLIGHT_END:
                # Keep the wagon showing its consonant while the vowel flies in.
                active = picked_step.wagon
                step = picked_step

        shake = None
        if self._shake is not None:
            control, started = self._shake
            t = now - started
            if t < SHAKE_SECONDS:
                shake = (control, int(9 * (1 - t / SHAKE_SECONDS) * (1 if int(t * 36) % 2 else -1)))
        hint_target = self._hint_target
        if hint_target is None and now < self._point_until:
            hint_target = "drum" if session.phase is Phase.CLAP else "sign"
        if hint_target is None and self.state is AppState.PLAYING and session.phase is Phase.CLAP:
            hint_target = "drum"
        ring = None
        if self._ring is not None:
            ring = (self._ring[0], (now - self._ring[1]) / RING_SECONDS)
        confetti = elapsed if self.state is AppState.FINALE else None
        return SceneState(
            challenge=challenge,
            step=step if step is not None else (self._picked[1] if self._picked else None),
            built=built,
            claps=claps,
            active_wagon=active,
            train_offset=offset,
            wheel_frame=wheel_frame,
            sign_picture=sign_picture,
            speaking=self.speech_queue.current_tag,
            hint_target=hint_target,
            pulse_phase=self._pulse_phase,
            shake=shake,
            sparkle_at=sparkle,
            flight=flight,
            pop_at=pop,
            beat_ring=ring,
            confetti=confetti,
            leo_pointing=now < self._point_until,
        )

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self._surfaces.draw(self.canvas.surface)
            return
        self.renderer.draw_scene(
            self.canvas.surface,
            self.controls.geometry,
            self.scene_state(),
            draw_controls=self._draw_controls,
        )

    def _draw_controls(self, surface: pygame.Surface, offsets: dict[str, tuple[int, int]]) -> None:
        if self.state in {AppState.STEP, AppState.BLEND} and self._picked is not None:
            self._draw_solving_controls(surface)
            return
        if self.state is not AppState.PLAYING and self.state is not AppState.TRY_AGAIN:
            self.controls.listen.draw(surface)
            self.controls.dots.draw(surface)
            return
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

    def _draw_solving_controls(self, surface: pygame.Surface) -> None:
        """While a pick flies to its wagon / the board, the other tiles stay put."""

        self.controls.listen.draw(surface)
        self.controls.dots.draw(surface)
        if self._picked is None or self.clock() - self.state_started >= FLIGHT_END + POP_SECONDS:
            return
        picked, _ = self._picked
        flying = self.clock() - self.state_started >= FLIGHT_START
        for index, button in enumerate(self.controls.choices):
            if button.visible and not (flying and index == picked):
                button.draw(surface)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "SillabeActivity"]
