"""App lifecycle, listening flow and input orchestration for Festa delle Rime.

Round grammar (P7 §1): spoken goal → listen → choose → celebrate → progress →
festival finale → shared completion scene. Hints are graduated: after ~6 s of
quiet Leo points and the words are replayed with a glow; a first wrong pick
makes Leo think and replays the target beside the picked word so the child can
hear they do not rhyme; from the second wrong pick the right picture pulses
while Leo says the rhyming pair. Retries are unlimited and always kind.
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
    from .rhyme_audio import RhymeAudio, SpeechQueue
    from .rhyme_content import RhymeMode
    from .rhyme_controls import LEO_HEIGHT, RhymeControls, choice_id
    from .rhyme_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RhymeChallenge,
        RhymeRoundFactory,
        RhymeSession,
        adapt_level,
    )
    from .rhyme_renderer import RhymeRenderer, SceneState
    from .rhyme_services import EventPort, ProgressPort
else:
    from rhyme_audio import RhymeAudio, SpeechQueue
    from rhyme_content import RhymeMode
    from rhyme_controls import LEO_HEIGHT, RhymeControls, choice_id
    from rhyme_model import (
        CHALLENGE_COUNT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        RhymeChallenge,
        RhymeRoundFactory,
        RhymeSession,
        adapt_level,
    )
    from rhyme_renderer import RhymeRenderer, SceneState
    from rhyme_services import EventPort, ProgressPort


POINT_SECONDS = 2.6
SHAKE_SECONDS = 0.45
FLIGHT_START = 0.30
FLIGHT_END = 1.00
CELEBRATE_MIN = 1.55
CELEBRATE_MAX = 5.0
FINALE_SECONDS = 2.6


class AppState(StrEnum):
    PLAYING = "playing"
    TRY_AGAIN = "try_again"
    CELEBRATE = "celebrate"
    FINALE = "finale"
    TERMINAL = "terminal"


class RhymeActivity:
    """Coordinate the listening model, speech sequence, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: RhymeSession,
        factory: RhymeRoundFactory,
        renderer: RhymeRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: RhymeAudio,
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
        self._celebrated_index: int | None = None
        self._pulse_phase = 0
        self._activated = False

        # Shared control kit (ADR 0037): learn Collection -> orange accent. The
        # kit shares the Activity's picture cache so art is decoded once.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=renderer.art.art
        )
        if renderer.cast is None:
            renderer.cast = CastFeedback("leo", height=LEO_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = RhymeControls(
            self.kit,
            renderer.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_choice=self._on_choice,
            on_listen=self._on_listen,
            on_target=self._on_target,
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
                background=(37, 59, 89),
                panel=(254, 243, 199),
                panel_border=(180, 83, 9),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(243, 154, 56),
                primary_text=(61, 44, 31),
            ),
            scene=CompletionScene(self.kit, character="leo", star_total=CHALLENGE_COUNT),
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
        return self._advance_state(now) or changed

    def _animating(self) -> bool:
        cast = self.renderer.cast
        return (
            self.state in {AppState.TRY_AGAIN, AppState.CELEBRATE, AppState.FINALE}
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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.state is AppState.PLAYING:
            self._note_input()
            self._speak_intro(opening=False)
            self._dirty = True
            return
        translated = self._input.translate(event)
        if translated is not None and self._dispatch(translated):
            self._dirty = True

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
        if key == pygame.K_r:
            before = self._quiet_since
            self._handle_event(event)
            return self._quiet_since != before or self.speech_queue.busy
        translated = self._input.translate(event)
        if translated is None:
            return False
        self._activated = False
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

    def _on_target(self) -> None:
        self._activated = True
        challenge = self.session.current_challenge
        if challenge is None:
            return
        if challenge.target_item is None:
            self._speak_intro(opening=False)
            return
        self.speech_queue.clear()
        self.speech_queue.enqueue(challenge.target_item.item_id, tag="target", gap=0.3)

    def _on_choice(self, index: int) -> None:
        challenge = self.session.current_challenge
        if self.state is not AppState.PLAYING or challenge is None or index >= len(challenge.choices):
            return
        self._activated = True
        result = self.session.select_choice(index)
        if result.correct:
            self._on_correct(challenge, index, result.session_complete)
        else:
            self._on_wrong(challenge, index, result.errors)

    # -- feedback grammar ----------------------------------------------------------------
    def _on_wrong(self, challenge: RhymeChallenge, index: int, errors: int) -> None:
        self.audio.play_sfx("retry")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._point_until = 0.0
        self._shake = (choice_id(index), self.clock())
        self.state = AppState.TRY_AGAIN
        self.state_started = self.clock()
        self.controls.sync(self.session)

        queue = self.speech_queue
        queue.clear()
        queue.enqueue("leo.retry", gap=0.35)
        remaining = [i for i in range(len(challenge.choices)) if i not in self.session.eliminated]
        demonstrate = errors >= 2 or len(remaining) == 1
        if challenge.mode is RhymeMode.RHYME_ODD:
            rhymers = [i for i in range(len(challenge.choices)) if i != challenge.correct_index]
            for i in rhymers:
                queue.enqueue(challenge.choices[i].item_id, tag=choice_id(i), gap=0.3)
            if demonstrate:
                queue.enqueue(challenge.answer.item_id, tag=choice_id(challenge.correct_index), gap=0.3)
        else:
            assert challenge.target_item is not None
            if demonstrate:
                queue.enqueue("listen_end_of_word", gap=0.3)  # then the model pair
            queue.enqueue(challenge.target_item.item_id, tag="target", gap=0.35)
            if demonstrate:
                queue.enqueue(challenge.answer.item_id, tag=choice_id(challenge.correct_index), gap=0.3)
            else:
                queue.enqueue(challenge.choices[index].item_id, tag=choice_id(index), gap=0.3)
                queue.enqueue("do_they_rhyme", gap=0.3)  # the child compares the pair
        self._hint_target = choice_id(challenge.correct_index) if demonstrate else None

    def _on_correct(self, challenge: RhymeChallenge, index: int, session_complete: bool) -> None:
        self.audio.play_sfx("correct")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._point_until = 0.0
        self._hint_target = None
        self._celebrated_index = index
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.match_completed(self.session_id, milestone)
        if session_complete:
            self._save_completion()

        queue = self.speech_queue
        queue.clear()
        if challenge.mode is RhymeMode.RHYME_ODD:
            for i in range(len(challenge.choices)):
                if i != challenge.correct_index:
                    queue.enqueue(challenge.choices[i].item_id, tag=choice_id(i), gap=0.25)
        else:
            assert challenge.target_item is not None
            queue.enqueue(challenge.target_item.item_id, tag="target", gap=0.25)
            queue.enqueue(challenge.answer.item_id, tag=choice_id(index), gap=0.3)
        queue.enqueue("praise_rhyme", gap=0.2)
        self.state = AppState.CELEBRATE
        self.state_started = self.clock()

    def _speak_intro(self, *, opening: bool, hint: bool = False) -> None:
        challenge = self.session.current_challenge
        if challenge is None:
            return
        queue = self.speech_queue
        queue.clear()
        odd = challenge.mode is RhymeMode.RHYME_ODD
        if opening and self.session.challenge_index == 0:
            queue.enqueue("leo.ready", gap=0.3)
            queue.enqueue("prompt_odd" if odd else "prompt_rhyme", gap=0.45)
        elif hint:
            queue.enqueue("prompt_odd" if odd else "prompt_find_rhyme", gap=0.4)
        if challenge.target_item is not None:
            queue.enqueue(challenge.target_item.item_id, tag="target", gap=0.6)
        for index, item in enumerate(challenge.choices):
            if index not in self.session.eliminated:
                queue.enqueue(item.item_id, tag=choice_id(index), gap=0.35)
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
            if self._hint_target is not None or now < self._point_until:
                changed = True
        return changed

    def _give_idle_hint(self, now: float) -> None:
        challenge = self.session.current_challenge
        if challenge is None:
            return
        self._hints.fire(now)
        self.session.record_hint()
        self._point_until = now + self._hints.animation_seconds(POINT_SECONDS)
        self._speak_intro(opening=False, hint=True)

    def _after_celebration(self, now: float) -> None:
        self._celebrated_index = None
        if self.session.is_complete:
            self.state = AppState.FINALE
            self.state_started = now
            self.audio.play_sfx("complete")
            self.speech_queue.clear()
            self.speech_queue.enqueue("leo.celebrate", gap=0.2)
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
            self.events.festival_completed(self.session_id, payload)

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
        self.session = RhymeSession(challenges, level=next_level, history=self.session.history)
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
        found = self.session.found
        sparkle = flight = burst = fireworks = None
        if self.state is AppState.CELEBRATE and self._celebrated_index is not None and found:
            start = self.controls.choice_center(self._celebrated_index)
            slot_index = len(found) - 1
            slot = self.controls.geometry.slots[slot_index]
            if elapsed < 0.6:
                sparkle = (start, elapsed / 0.6)
            if elapsed < FLIGHT_END:
                found = found[:-1]
                if elapsed >= FLIGHT_START:
                    t = (elapsed - FLIGHT_START) / (FLIGHT_END - FLIGHT_START)
                    flight = (self.session.found[-1], start, slot.center, t)
            elif elapsed < FLIGHT_END + 0.5:
                burst = (slot_index, (elapsed - FLIGHT_END) / 0.5)
        if self.state is AppState.FINALE:
            fireworks = elapsed
        challenge = self.session.current_challenge
        if self.state is AppState.CELEBRATE and self._celebrated_index is not None:
            challenge = self._previous_challenge()
        shake = None
        if self._shake is not None:
            control, started = self._shake
            t = now - started
            if t < SHAKE_SECONDS:
                shake = (control, int(9 * (1 - t / SHAKE_SECONDS) * (1 if int(t * 36) % 2 else -1)))
        return SceneState(
            challenge=challenge,
            found=found,
            speaking=self.speech_queue.current_tag,
            hint_target=self._hint_target if self._hint_target else ("target" if now < self._point_until else None),
            pulse_phase=self._pulse_phase,
            shake=shake,
            sparkle_at=sparkle,
            flight=flight,
            burst_slot=burst,
            fireworks=fireworks,
            leo_pointing=now < self._point_until,
        )

    def _previous_challenge(self) -> RhymeChallenge | None:
        return self.session.previous_challenge

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
        if self.state is AppState.CELEBRATE:
            self._draw_celebration_controls(surface)
            return
        if self.state is AppState.FINALE:
            self.controls.listen.draw(surface)
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

    def _draw_celebration_controls(self, surface: pygame.Surface) -> None:
        """During the celebration the solved tiles stay put; the found one is empty."""

        self.controls.listen.draw(surface)
        challenge = self._previous_challenge()
        if challenge is None:
            return
        flying = self.clock() - self.state_started >= FLIGHT_START
        for index, button in enumerate(self.controls.choices[: len(challenge.choices)]):
            if flying and index == self._celebrated_index:
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
