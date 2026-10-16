"""App lifecycle, listening flow and input orchestration for Officina dei Suoni.

Round grammar (P7 §1): spoken goal → listen → choose → the Sound Machine
works (cheer) → progress → finale → shared completion scene.

Hints are graduated: after ~6 s of quiet Dani points and the machine replays
its sound or word with a glow; a first wrong pick makes Dani think and
contrasts the target with the pick (the picked word, or the picked letter's
own *sound*); from the second wrong pick the right tile pulses while Dani's
machine demonstrates the answer. Retries are unlimited and always kind.

Only letter **sounds** are ever spoken here — letter names are taught by
Leo's Letter Garden.
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
    from .sound_audio import SoundWorkshopAudio, SpeechQueue
    from .sound_content import WordItem, WorkshopMode
    from .sound_controls import DANI_HEIGHT, PICTURE_SIZE, LETTER_SIZE, WorkshopControls, choice_id
    from .sound_renderer import Flight, SceneState, SoundWorkshopRenderer
    from .sound_services import EventPort, ProgressPort
    from .sound_workshop_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ChoiceStep,
        SoundRoundFactory,
        SoundSession,
        WorkshopChallenge,
        adapt_level,
    )
else:
    from sound_audio import SoundWorkshopAudio, SpeechQueue
    from sound_content import WordItem, WorkshopMode
    from sound_controls import DANI_HEIGHT, PICTURE_SIZE, LETTER_SIZE, WorkshopControls, choice_id
    from sound_renderer import Flight, SceneState, SoundWorkshopRenderer
    from sound_services import EventPort, ProgressPort
    from sound_workshop_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ChoiceStep,
        SoundRoundFactory,
        SoundSession,
        WorkshopChallenge,
        adapt_level,
    )


POINT_SECONDS = 2.6
SHAKE_SECONDS = 0.45
FLIGHT_START = 0.20
FLIGHT_END = 0.80
REVEAL_LATEST = 2.4       # first-sound stage: the letter pops out with its sound (or by then)
GEAR_SECONDS = 1.4
POP_SECONDS = 0.5
CELEBRATE_MIN = 2.2
CELEBRATE_MAX = 6.0
STEP_MIN = 1.3
STEP_MAX = 3.5
FINALE_SECONDS = 2.4

PROMPTS = {
    WorkshopMode.FIND_SOUND: "prompt_find_sound",
    WorkshopMode.INITIAL_LETTER: "prompt_first_sound",
    WorkshopMode.BUILD_WORD: "prompt_build_word",
}

# Letter keys pick a visible letter tile in the letter stages; otherwise R
# replays the machine (the R tile wins while an R tile is on screen).
_LETTER_KEYS = {getattr(pygame, f"K_{c.lower()}"): c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}


class AppState(StrEnum):
    PLAYING = "playing"
    TRY_AGAIN = "try_again"
    STEP = "step"              # one build slot filled, the next follows
    CELEBRATE = "celebrate"
    FINALE = "finale"
    TERMINAL = "terminal"


class SoundWorkshopActivity:
    """Coordinate the workshop model, speech sequence, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: SoundSession,
        factory: SoundRoundFactory,
        renderer: SoundWorkshopRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: SoundWorkshopAudio,
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
        self.progress = progress
        self.events = events
        self.audio = audio
        self.speech_queue = speech_queue
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.state = AppState.PLAYING
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
        self._picked: tuple[int, ChoiceStep, WorkshopChallenge] | None = None
        self._revealed_at: float | None = None
        self._pulse_phase = 0
        self._activated = False

        # Shared control kit (ADR 0037): learn Collection -> orange accent. The
        # kit shares the Activity's picture cache so art is decoded once.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=renderer.art.art
        )
        if renderer.cast is None:
            renderer.cast = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = WorkshopControls(
            self.kit,
            renderer.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_choice=self._on_choice,
            on_listen=self._on_listen,
            on_machine=self._on_machine,
        )
        self.controls.sync(session)
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
                background=(240, 228, 200),
                panel=(255, 251, 235),
                panel_border=(180, 83, 9),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(243, 154, 56),
                primary_text=(61, 44, 31),
            ),
            scene=CompletionScene(self.kit, character="dani", star_total=CHALLENGE_COUNT),
        )

        self._speak_intro(opening=True)

    # -- main loop ----------------------------------------------------------------
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
        if self._reveal_due(now):
            self._revealed_at = now
            changed = True
        return self._advance_state(now) or changed

    def _reveal_due(self, now: float) -> bool:
        """First-sound stage: the letter appears when the machine plays its sound."""

        if self.state is not AppState.CELEBRATE or self._picked is None or self._revealed_at is not None:
            return False
        if self._picked[2].mode is not WorkshopMode.FIND_SOUND:
            return False
        return self.speech_queue.current_tag == "horn" or now - self.state_started >= REVEAL_LATEST

    def _animating(self) -> bool:
        cast = self.renderer.cast
        return (
            self.state in {AppState.TRY_AGAIN, AppState.STEP, AppState.CELEBRATE, AppState.FINALE}
            or self.speech_queue.busy
            or self._hint_target is not None
            or (cast is not None and cast.animating)
        )

    # -- input ----------------------------------------------------------------------
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
            if self._pick_by_letter_key(event.key):
                self._dirty = True
                return
            if event.key == pygame.K_r:
                self._note_input()
                self._speak_intro(opening=False)
                self._dirty = True
                return
        translated = self._input.translate(event)
        if translated is not None and self._dispatch(translated):
            self._dirty = True

    def _pick_by_letter_key(self, key: int) -> bool:
        """Typing a capital's key picks that letter tile (letter stages only)."""

        letter = _LETTER_KEYS.get(key)
        step = self.session.current_step
        if letter is None or step is None or not step.is_letter:
            return False
        for index, choice in enumerate(step.choices):
            if choice == letter and index not in self.session.eliminated:
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
        if key == pygame.K_r or key in _LETTER_KEYS:
            self._handle_event(event)
            return self._activated or self._quiet_since != before
        translated = self._input.translate(event)
        if translated is None:
            return False
        handled = self._dispatch(translated)
        return handled or self._activated

    def _handle_terminal_pointer(self, raw_pos: tuple[int, int]) -> bool:
        if self.state is not AppState.TERMINAL:
            return False
        before = self.state
        return self._handle_pointer(raw_pos) or self.state is not before

    # -- control callbacks ------------------------------------------------------------
    def _on_listen(self) -> None:
        self._activated = True
        self._speak_intro(opening=False)

    def _on_machine(self) -> None:
        self._activated = True
        challenge = self.session.current_challenge
        if challenge is None:
            return
        queue = self.speech_queue
        queue.clear()
        if challenge.mode is WorkshopMode.FIND_SOUND:
            queue.enqueue(challenge.target_unit.audio_id, tag="horn", gap=0.35)
        else:
            assert challenge.target_word is not None
            queue.enqueue(challenge.target_word.word_id, tag="screen", gap=0.3)
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
            self._on_correct(challenge, step, index, result.session_complete)
        else:
            self._on_step(challenge, step, index)

    # -- feedback grammar ----------------------------------------------------------------
    def _on_wrong(self, challenge: WorkshopChallenge, step: ChoiceStep, index: int, errors: int) -> None:
        self.audio.play_sfx("retry")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._point_until = 0.0
        self._shake = (choice_id(index), self.clock())
        self.state = AppState.TRY_AGAIN
        self.state_started = self.clock()
        self.controls.sync(self.session)

        remaining = [i for i in range(len(step.choices)) if i not in self.session.eliminated]
        demonstrate = errors >= 2 or len(remaining) == 1
        shown = step.correct_index if demonstrate else index
        queue = self.speech_queue
        queue.clear()
        queue.enqueue("dani.retry", gap=0.35)
        if challenge.mode is WorkshopMode.FIND_SOUND:
            # "/m/ ... pig" — the target sound beside the picked (or right) word.
            queue.enqueue(step.unit.audio_id, tag="horn", gap=0.35)
            picked = step.choices[shown]
            assert isinstance(picked, WordItem)
            queue.enqueue(picked.word_id, tag=choice_id(shown), gap=0.3)
        else:
            # "/t/ ... moon" — the picked letter's own sound beside the word.
            letter = step.choices[shown]
            assert isinstance(letter, str)
            unit = self.factory.unit_for_letter(letter)
            if unit is not None:
                queue.enqueue(unit.audio_id, tag=choice_id(shown), gap=0.35)
            assert challenge.target_word is not None
            queue.enqueue(challenge.target_word.word_id, tag="screen", gap=0.3)
        self._hint_target = choice_id(step.correct_index) if demonstrate else None

    def _on_step(self, challenge: WorkshopChallenge, step: ChoiceStep, index: int) -> None:
        """A build slot was filled; the next slot of the same word follows."""

        self.audio.play_sfx("correct")
        self._point_until = 0.0
        self._hint_target = None
        self._picked = (index, step, challenge)
        queue = self.speech_queue
        queue.clear()
        queue.pause(FLIGHT_END)
        queue.enqueue(step.unit.audio_id, tag=f"slot.{step.slot}", gap=0.45)
        self.state = AppState.STEP
        self.state_started = self.clock()

    def _on_correct(self, challenge: WorkshopChallenge, step: ChoiceStep, index: int, session_complete: bool) -> None:
        self.audio.play_sfx("correct")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._point_until = 0.0
        self._hint_target = None
        self._picked = (index, step, challenge)
        self._revealed_at = None
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.word_completed(self.session_id, milestone)
        if session_complete:
            self._save_completion()

        queue = self.speech_queue
        queue.clear()
        # Speech waits for the fed item to land, then names what was made.
        queue.pause(FLIGHT_END)
        word = challenge.answer_word
        if challenge.mode is WorkshopMode.FIND_SOUND:
            # "moon ... /m/" — the letter pops out of the machine on the sound.
            queue.enqueue(word.word_id, tag="screen", gap=0.3)
            queue.enqueue(step.unit.audio_id, tag="horn", gap=0.35)
        elif challenge.mode is WorkshopMode.INITIAL_LETTER:
            queue.enqueue(step.unit.audio_id, tag=f"slot.{step.slot}", gap=0.3)
            queue.enqueue(word.word_id, tag="screen", gap=0.35)
        else:
            queue.enqueue(step.unit.audio_id, tag=f"slot.{step.slot}", gap=0.35)
            queue.enqueue(word.word_id, tag="word", gap=0.35)
        queue.enqueue("dani.praise", gap=0.2)
        self.state = AppState.CELEBRATE
        self.state_started = self.clock()

    def _speak_intro(self, *, opening: bool, hint: bool = False) -> None:
        challenge = self.session.current_challenge
        step = self.session.current_step
        if challenge is None or step is None:
            return
        queue = self.speech_queue
        queue.clear()
        prompt = PROMPTS[challenge.mode]
        if opening and self.session.challenge_index == 0:
            queue.enqueue("dani.ready", gap=0.3)
            queue.enqueue(prompt, gap=0.45)
        elif hint:
            queue.enqueue(prompt, gap=0.4)
        if challenge.mode is WorkshopMode.FIND_SOUND:
            # Sound, then every picture's name, then the sound again.
            queue.enqueue(step.unit.audio_id, tag="horn", gap=0.5)
            for index, item in enumerate(step.choices):
                if index not in self.session.eliminated and isinstance(item, WordItem):
                    queue.enqueue(item.word_id, tag=choice_id(index), gap=0.35)
            queue.enqueue(step.unit.audio_id, tag="horn", gap=0.3)
        else:
            assert challenge.target_word is not None
            queue.enqueue(challenge.target_word.word_id, tag="screen", gap=0.4)
        self._quiet_since = self.clock()

    # -- state ------------------------------------------------------------------------------
    def _advance_state(self, now: float) -> bool:
        elapsed = now - self.state_started
        changed = False
        if self.state is AppState.PLAYING:
            if (
                not self.speech_queue.busy
                and self._hints.is_due(now, self._quiet_since)
            ):
                self._give_idle_hint(now)
                changed = True
            if self._point_until and now >= self._point_until:
                self._point_until = 0.0
                changed = True
        elif self.state is AppState.TRY_AGAIN:
            if elapsed >= SHAKE_SECONDS:
                self._shake = None
                self.state = AppState.PLAYING
                self.state_started = now
                self._quiet_since = now
            changed = True
        elif self.state is AppState.STEP:
            done = elapsed >= STEP_MIN and not self.speech_queue.busy
            if done or elapsed >= STEP_MAX:
                self._after_step(now)
            changed = True
        elif self.state is AppState.CELEBRATE:
            done = elapsed >= CELEBRATE_MIN and not self.speech_queue.busy
            if done or elapsed >= CELEBRATE_MAX:
                self._after_celebration(now)
            changed = True
        elif self.state is AppState.FINALE:
            if elapsed >= FINALE_SECONDS:
                self._show_completion(now)
            changed = True
        phase = int(now * 4)
        if phase != self._pulse_phase:
            self._pulse_phase = phase
            if self._hint_target is not None or now < self._point_until or self._has_active_slot():
                changed = True
        return changed

    def _has_active_slot(self) -> bool:
        challenge = self.session.current_challenge
        return self.state is AppState.PLAYING and challenge is not None and challenge.mode is not WorkshopMode.FIND_SOUND

    def _give_idle_hint(self, now: float) -> None:
        if self.session.current_challenge is None:
            return
        self._hints.fire(now)
        self.session.record_hint()
        self._point_until = now + self._hints.animation_seconds(POINT_SECONDS)
        self._speak_intro(opening=False, hint=True)

    def _after_step(self, now: float) -> None:
        self._picked = None
        self.state = AppState.PLAYING
        self.state_started = now
        self._hints.reset(self.clock())
        self.controls.sync(self.session)
        challenge = self.session.current_challenge
        if challenge is not None and challenge.target_word is not None:
            # Re-anchor the next slot on the whole word.
            self.speech_queue.clear()
            self.speech_queue.enqueue(challenge.target_word.word_id, tag="screen", gap=0.4)
        self._quiet_since = now

    def _after_celebration(self, now: float) -> None:
        self._picked = None
        if self.session.is_complete:
            self.state = AppState.FINALE
            self.state_started = now
            self.audio.play_sfx("complete")
            self.speech_queue.clear()
            self.speech_queue.enqueue("dani.celebrate", gap=0.2)
            if self.renderer.cast is not None:
                self.renderer.cast.correct()
            self.controls.sync(self.session)
            return
        self.state = AppState.PLAYING
        self.state_started = now
        self._hints.reset(self.clock())
        self._hint_target = None
        self.controls.sync(self.session)
        self._speak_intro(opening=False)

    def _save_completion(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.workshop_completed(self.session_id, payload)

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
        self.state = AppState.TERMINAL
        self.state_started = now

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = SoundSession(challenges, level=next_level, history=self.session.history)
        self._surfaces.pop_overlay()
        self.completion.clear()
        if self.renderer.cast is not None:
            self.renderer.cast.reset()
        self.controls.sync(self.session)
        self.state = AppState.PLAYING
        self.state_started = self.clock()
        self._hints.reset(self.clock())
        self._hint_target = None
        self._activated = True
        self._speak_intro(opening=True)

    # -- drawing ------------------------------------------------------------------------------
    def scene_state(self) -> SceneState:
        now = self.clock()
        elapsed = now - self.state_started
        challenge = self.session.current_challenge
        filled = self.session.filled_slots
        active = self.session.current_step.slot if self.session.current_step is not None else None
        show_answer = reveal = False
        sparkle = flight = pop = None
        gear_frame = 0
        confetti = None

        if self.state in {AppState.CELEBRATE, AppState.STEP} and self._picked is not None:
            index, step, solved = self._picked
            challenge = solved
            active = None
            start = self.controls.choice_center(index)
            if self.state is AppState.STEP:
                filled = tuple(s for s in self.session.filled_slots if s != step.slot)
            else:
                filled = tuple(solved.slots[:-1]) if solved.mode is not WorkshopMode.FIND_SOUND else ()
            if elapsed < 0.6:
                sparkle = (start, elapsed / 0.6)
            landing = None
            if solved.mode is WorkshopMode.FIND_SOUND:
                end = self.controls.geometry.hopper
                item, start_size, end_size = step.answer, PICTURE_SIZE, 48
            else:
                assert solved.target_word is not None
                count = len(solved.target_word.label) if solved.mode is WorkshopMode.BUILD_WORD else 1
                rects = self.controls.geometry.slot_rects(count)
                slot_rect = rects[step.slot if solved.mode is WorkshopMode.BUILD_WORD else 0]
                end = slot_rect.center
                landing = slot_rect.center
                item, start_size, end_size = step.answer, LETTER_SIZE, int(slot_rect.height * 0.74)
            if FLIGHT_START <= elapsed < FLIGHT_END:
                flight = Flight(item, start, end, (elapsed - FLIGHT_START) / (FLIGHT_END - FLIGHT_START), start_size, end_size)
            if elapsed >= FLIGHT_END:
                if solved.mode is WorkshopMode.FIND_SOUND:
                    show_answer = True
                    reveal = self._revealed_at is not None
                    if reveal and now - self._revealed_at < POP_SECONDS:
                        slot = self.controls.geometry.slot_rects(1)[0]
                        pop = (slot.center, (now - self._revealed_at) / POP_SECONDS)
                else:
                    filled = (*filled, step.slot)
                    if elapsed < FLIGHT_END + POP_SECONDS and landing is not None:
                        pop = (landing, (elapsed - FLIGHT_END) / POP_SECONDS)
            if FLIGHT_END <= elapsed < FLIGHT_END + GEAR_SECONDS:
                gear_frame = int((elapsed - FLIGHT_END) * 14)
        elif self.state is AppState.FINALE:
            challenge = self.session.previous_challenge
            if challenge is not None:
                filled = challenge.slots
                show_answer = reveal = True
            active = None
            confetti = elapsed
            gear_frame = int(elapsed * 10)

        shake = None
        if self._shake is not None:
            control, started = self._shake
            t = now - started
            if t < SHAKE_SECONDS:
                shake = (control, int(9 * (1 - t / SHAKE_SECONDS) * (1 if int(t * 36) % 2 else -1)))
        hint_target = self._hint_target
        if hint_target is None and now < self._point_until:
            hint_target = "horn" if challenge is not None and challenge.mode is WorkshopMode.FIND_SOUND else "machine"
        return SceneState(
            challenge=challenge,
            filled_slots=filled,
            active_slot=active,
            show_answer_picture=show_answer,
            reveal_letter=reveal,
            speaking=self.speech_queue.current_tag,
            hint_target=hint_target,
            pulse_phase=self._pulse_phase,
            shake=shake,
            sparkle_at=sparkle,
            flight=flight,
            pop_at=pop,
            gear_frame=gear_frame,
            confetti=confetti,
            dani_pointing=now < self._point_until,
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
        if self.state in {AppState.CELEBRATE, AppState.STEP}:
            self._draw_solving_controls(surface)
            return
        if self.state is AppState.FINALE:
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
        """While the machine works the solved tiles stay put; the fed one is empty."""

        self.controls.listen.draw(surface)
        self.controls.dots.draw(surface)
        if self._picked is None:
            return
        picked, _, _ = self._picked
        flying = self.clock() - self.state_started >= FLIGHT_START
        for index, button in enumerate(self.controls.choices):
            if flying and index == picked:
                continue
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
