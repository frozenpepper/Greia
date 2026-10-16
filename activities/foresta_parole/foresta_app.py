"""App lifecycle, round flow and input orchestration for The Word Forest.

Round grammar (P7 §1): Leo says the word with its letter name while its
picture hangs on the sign ("B as Boat") → letters drop from the canopy → the
child steers the basket under the letter that starts the word → it drops in,
Leo cheers, the sign shows the word with that letter in colour → six words →
confetti and the shared completion scene.

Hints are graduated: after ~6 s without input Leo points, the sign pulses,
the right letters in the air glow and the word is said again; a wrong catch
makes Leo think, the letter bounces out and the word is repeated; after two
wrong catches (or two right letters missed) Leo demonstrates: the drops slow
down and the right letter comes next, glowing, right above the basket.
Misses never cost anything; retries are unlimited and kind.
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
from greia_platform.activity_feedback import CastFeedback
from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    InteractionProfile,
    SemanticAction,
    SemanticInputEvent,
    normalize_stick,
)
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
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .foresta_audio import ForestAudio, SpeechQueue
    from .foresta_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .foresta_controls import LEO_HEIGHT, ForestControls
    from .foresta_model import (
        Basket,
        CatchRound,
        FieldEventKind,
        ForestField,
        RoundPlanner,
        lesson_language,
        next_stage,
        stage_spec,
    )
    from .foresta_renderer import ForestRenderer, SceneState
    from .foresta_services import EventPort, ForestProgress, ProgressPort
else:
    from foresta_audio import ForestAudio, SpeechQueue  # type: ignore[no-redef]
    from foresta_content import REFERENCE_HEIGHT, REFERENCE_WIDTH  # type: ignore[no-redef]
    from foresta_controls import LEO_HEIGHT, ForestControls  # type: ignore[no-redef]
    from foresta_model import (  # type: ignore[no-redef]
        Basket,
        CatchRound,
        FieldEventKind,
        ForestField,
        RoundPlanner,
        lesson_language,
        next_stage,
        stage_spec,
    )
    from foresta_renderer import ForestRenderer, SceneState  # type: ignore[no-redef]
    from foresta_services import EventPort, ForestProgress, ProgressPort  # type: ignore[no-redef]


IDLE_HINT_SECONDS = 6.0
MAX_IDLE_HINTS = 3
POINT_SECONDS = 2.6
INTRO_MAX_SECONDS = 2.6
CAUGHT_MIN_SECONDS = 2.0
CAUGHT_MAX_SECONDS = 5.0
FINALE_SECONDS = 2.6
SPARKLE_SECONDS = 0.6
BUMP_SECONDS = 0.6
KEY_SPEED = 520.0      # logical px/s while an arrow / D-pad is held
STICK_SPEED = 600.0    # at full left-stick deflection


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
    INTRO = "intro"          # word spoken; letters start dropping shortly
    PLAYING = "playing"
    CAUGHT = "caught"        # right letter in the basket: word shown, cheer
    FINALE = "finale"
    TERMINAL = "terminal"    # shared completion scene


class ForestaApp:
    """Coordinate the catch round, speech, basket input, kit controls and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        planner: RoundPlanner,
        progress: ForestProgress,
        progress_port: ProgressPort,
        events: EventPort,
        renderer: ForestRenderer,
        typography: GreiaTypography,
        resources,
        audio: ForestAudio,
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

        self.round: CatchRound = self._new_round()
        self.state = AppState.INTRO
        self.state_started = clock()
        self._running = True
        self._ready_published = False
        self._last_tick = clock()
        self._quiet_since = clock()
        self._idle_hints = 0
        self._point_until = 0.0
        self._hint = False
        self._sparkle: tuple[tuple[int, int], float] | None = None
        self._bump: tuple[tuple[int, int], float] | None = None
        self._pulse_phase = 0
        self._activated = False
        self._held: set[SemanticAction] = set()
        self._stick_x = 0.0
        self._stick_y = 0.0
        self._revealed = False

        # Shared control kit (ADR 0037): learn Collection -> orange accent. The
        # kit shares the Activity's picture cache so art is decoded once.
        self.kit = kit if kit is not None else ControlKit(
            typography, ControlTheme.for_accent("orange"), art=renderer.art.art
        )
        renderer.kit = self.kit
        if renderer.cast is None:
            renderer.cast = CastFeedback("leo", height=LEO_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = ForestControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            task_total=self.round.total,
            on_listen=self._on_listen,
        )
        self.field = ForestField(rng, self.controls.geometry.field)
        self.basket = Basket(self.controls.geometry.field)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self._game_input = PygameInputTranslator(InteractionProfile.DIRECTIONAL)
        self.completion = self._make_completion()
        self._enter_target(opening=True)

    # -- setup helpers ----------------------------------------------------------------
    def _new_round(self) -> CatchRound:
        stage = self.progress.stage_for(self.language)
        return self.planner.build(stage, self.progress.caught_for(self.language))

    def _make_completion(self) -> PygameCompletionScreen:
        return PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=COMPLETION_PALETTE,
            scene=CompletionScene(self.kit, character="leo", star_total=self.round.total),
        )

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(
            to_logical=self.canvas.pointer,
            is_safe=lambda pos: _safe_point(self.screen, pos),
        )

    # -- main loop -------------------------------------------------------------------------
    def run(self) -> int:
        # Falling letters animate while playing; the completion scene is ambient.
        frames = FrameGovernor(redraw_on_input=True)
        while self._running and not activity_stop_requested():
            for event in frames.events():
                self._handle_event(event)
            if self.state is AppState.TERMINAL:
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
            self.tick()
            frame = frames.frame(animating=self.state is not AppState.TERMINAL, ambient=True)
            if frame is FrameKind.FULL:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            elif frame is FrameKind.POINTER:
                self.canvas.present_pointer()
            frames.wait(polling=self._input.repeating)
        self._save()
        return 0

    def tick(self) -> None:
        """Advance speech, cast, basket, falling letters and state timers."""

        now = self.clock()
        dt = max(0.0, min(0.1, now - self._last_tick))
        self._last_tick = now
        was_busy = self.speech_queue.busy
        self.speech_queue.update(dt)
        if was_busy and not self.speech_queue.busy:
            self._quiet_since = now
        cast = self.renderer.cast
        if cast is not None:
            cast.update()
        self._move_basket(dt)
        if self.state in {AppState.INTRO, AppState.PLAYING, AppState.CAUGHT}:
            for event in self.field.update(dt, self.basket.x):
                self._on_field_event(event.kind, event.letter, now)
        self._advance_state(now)

    # -- input --------------------------------------------------------------------------------
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
        if self.state is AppState.TERMINAL:
            translated = self._input.translate(event)
            if translated is not None:
                self._dispatch(translated)
            return
        if event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            translated = self._input.translate(event)
            if isinstance(translated, KitPointer):
                self._pointer(translated)
            return
        semantic = self._game_input.digital(event)
        if semantic is not None:
            self._game_action(semantic)
            return
        axis = self._game_input.controller_axis(event)
        if axis is not None:
            if axis.axis is ControllerAxis.LEFT_X:
                self._stick_x = axis.value
            elif axis.axis is ControllerAxis.LEFT_Y:
                self._stick_y = axis.value
            self._note_input()

    def _relayout(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self.field.geometry = self.controls.geometry.field
        self.basket.geometry = self.controls.geometry.field
        self.basket.x = self.basket.clamp(self.basket.x)
        self._input = self._make_input()

    def _game_action(self, semantic: SemanticInputEvent) -> None:
        action = semantic.action
        if action in {SemanticAction.MOVE_LEFT, SemanticAction.MOVE_RIGHT}:
            if semantic.edge is InputEdge.PRESSED:
                self._held.add(action)
                self.basket.goal = None
                self._note_input()
            else:
                self._held.discard(action)
            return
        if semantic.edge is not InputEdge.PRESSED:
            return
        if action in {SemanticAction.PRIMARY, SemanticAction.ACTIVATE}:
            self._note_input()
            self._on_listen()

    def _pointer(self, pointer: KitPointer) -> None:
        if pointer.phase is PointerPhase.DOWN:
            self._note_input()
        result = self._surfaces.dispatch(pointer)
        if result is not UiEventResult.IGNORED:
            return
        if self.controls.layer.pressed_id is not None:
            return  # a press that started on a control stays with the control
        if pointer.phase in {PointerPhase.DOWN, PointerPhase.MOVE} and pointer.position[1] > 0:
            if pointer.phase is PointerPhase.MOVE and abs(pointer.position[0] - self.basket.x) > 1:
                self._note_input()
            self.basket.goal = float(pointer.position[0])

    def _dispatch(self, kit_input) -> bool:
        result = self._surfaces.dispatch(kit_input)
        return result is not UiEventResult.IGNORED

    def _note_input(self) -> None:
        self._quiet_since = self.clock()

    def _move_basket(self, dt: float) -> None:
        if dt <= 0:
            return
        direction = 0
        if SemanticAction.MOVE_LEFT in self._held:
            direction -= 1
        if SemanticAction.MOVE_RIGHT in self._held:
            direction += 1
        if direction:
            self.basket.nudge(direction * KEY_SPEED * dt)
            return
        stick = normalize_stick(self._stick_x, self._stick_y, DEFAULT_INPUT_POLICY.stick_dead_zone)
        if abs(stick.x) > 0.0:
            self.basket.goal = None
            self.basket.nudge(stick.x * STICK_SPEED * dt)
            self._note_input()
            return
        self.basket.follow(dt)

    # Test/tool helpers -------------------------------------------------------------------
    def _handle_pointer(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position."""

        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        return self._pointer_tap_logical((int(logical[0]), int(logical[1])))

    def _pointer_tap_logical(self, point: tuple[int, int]) -> bool:
        """Deliver one complete tap at a logical position; True when a control fired."""

        self._activated = False
        self._pointer(KitPointer(PointerPhase.DOWN, point))
        self._pointer(KitPointer(PointerPhase.UP, point))
        return self._activated

    # -- control callbacks ------------------------------------------------------------------
    def _on_listen(self) -> None:
        self._activated = True
        if self.state in {AppState.INTRO, AppState.PLAYING}:
            self._say_prompt(clear=True)

    def _say_prompt(self, *, clear: bool) -> None:
        target = self.round.current
        if target is None:
            return
        if clear:
            self.speech_queue.clear()
        self.speech_queue.enqueue(target.card.prompt_cue, tag="prompt", gap=0.4)

    # -- falling-letter facts -----------------------------------------------------------------
    def _on_field_event(self, kind: FieldEventKind, letter, now: float) -> None:
        if self.state is not AppState.PLAYING and self.state is not AppState.INTRO:
            return
        if kind is FieldEventKind.CAUGHT_TARGET:
            self._on_caught(letter, now)
        elif kind is FieldEventKind.CAUGHT_DECOY:
            self._on_wrong(letter, now)
        elif kind is FieldEventKind.MISSED_TARGET:
            self.round.record_miss()
            self.audio.play_sfx("drop")
            if self.round.needs_guide and not self.field.guide:
                self._start_guide(now)

    def _on_wrong(self, letter, now: float) -> None:
        errors = self.round.record_wrong()
        self.audio.play_sfx("bounce")
        if self.renderer.cast is not None:
            self.renderer.cast.try_again()
        self._bump = ((int(letter.x), int(letter.y)), now)
        self._point_until = 0.0
        queue = self.speech_queue
        queue.clear()
        queue.enqueue("leo.retry", gap=0.3)
        self._say_prompt(clear=False)
        if errors >= 2 and not self.field.guide:
            self._start_guide(now)
        self._quiet_since = now

    def _start_guide(self, now: float) -> None:
        """Demonstrate: slower drops, the right letter next and glowing, Leo points."""

        self.field.set_guide(True)
        self._hint = True
        self._point_until = now + POINT_SECONDS
        if not self.speech_queue.busy:
            self._say_prompt(clear=False)

    def _on_caught(self, letter, now: float) -> None:
        card = self.round.record_caught()
        self.progress.record_catch(self.language, card.letter)
        self._save()
        self.events.letter_caught(self.session_id, self.round.done, card.letter, card.word)
        self.field.stop()
        self.field.release_all()
        self.field.set_guide(False)
        self.audio.play_sfx("catch")
        if self.renderer.cast is not None:
            self.renderer.cast.correct()
        self._sparkle = ((int(self.basket.x), int(self.controls.geometry.field.mouth_y)), now)
        self._hint = False
        self._point_until = 0.0
        self._revealed = True
        queue = self.speech_queue
        queue.clear()
        queue.enqueue(card.letter_cue, tag="letter", gap=0.2)
        queue.enqueue(card.word_cue, tag="word", gap=0.3)
        if self.round.done == self.round.total // 2:
            queue.enqueue("leo.progress", gap=0.2)
        self.controls.set_progress(self.round.done)
        self.state = AppState.CAUGHT
        self.state_started = now

    # -- targets ---------------------------------------------------------------------------------
    def _enter_target(self, *, opening: bool = False) -> None:
        now = self.clock()
        self._idle_hints = 0
        self._hint = False
        self._point_until = 0.0
        self._revealed = False
        queue = self.speech_queue
        queue.clear()
        if opening:
            queue.enqueue("leo.ready", gap=0.3)
        self._say_prompt(clear=False)
        self.state = AppState.INTRO
        self.state_started = now
        self._quiet_since = now

    def _advance_state(self, now: float) -> None:
        elapsed = now - self.state_started
        if self.state is AppState.INTRO:
            speaking_prompt = self.speech_queue.current_tag == "prompt"
            if speaking_prompt or not self.speech_queue.busy or elapsed >= INTRO_MAX_SECONDS:
                target = self.round.current
                if target is not None:
                    self.field.start(target, stage_spec(self.round.stage))
                self.state = AppState.PLAYING
                self.state_started = now
                self._quiet_since = now
        elif self.state is AppState.PLAYING:
            waiting = self.field.falling_target()
            if waiting is not None and abs(waiting.x - self.basket.x) <= self.field.geometry.basket_half:
                # Already waiting under the right letter: not idle.
                self._quiet_since = now
            if (
                not self.speech_queue.busy
                and self._idle_hints < MAX_IDLE_HINTS
                and now - self._quiet_since >= IDLE_HINT_SECONDS
            ):
                self._give_idle_hint(now)
        elif self.state is AppState.CAUGHT:
            done = elapsed >= CAUGHT_MIN_SECONDS and not self.speech_queue.busy
            if done or elapsed >= CAUGHT_MAX_SECONDS:
                self._sparkle = None
                self.round.advance()
                if self.round.is_complete:
                    self._finish_round(now)
                else:
                    self._enter_target()
        elif self.state is AppState.FINALE:
            if elapsed >= FINALE_SECONDS:
                self._show_completion(now)
        if self._sparkle is not None and now - self._sparkle[1] >= SPARKLE_SECONDS:
            self._sparkle = None
        if self._bump is not None and now - self._bump[1] >= BUMP_SECONDS:
            self._bump = None
        self._pulse_phase = int(now * 4)

    def _give_idle_hint(self, now: float) -> None:
        self._idle_hints += 1
        self.round.record_hint()
        self._point_until = now + POINT_SECONDS
        self._quiet_since = now
        self._hint = True
        for letter in self.field.falling:
            letter.glow = letter.is_target
        self._say_prompt(clear=True)

    def _finish_round(self, now: float) -> None:
        payload = self.round.consume_completion()
        if payload is not None:
            self.progress.stages[self.language] = next_stage(self.round)
            self.progress.rounds_completed += 1
            self._save()
            self.events.round_completed(self.session_id, payload)
        self.field.stop()
        self.field.release_all()
        self.state = AppState.FINALE
        self.state_started = now
        self._revealed = False
        self.audio.play_sfx("finale")
        self.speech_queue.clear()
        self.speech_queue.enqueue("leo.celebrate", gap=0.2)
        if self.renderer.cast is not None:
            self.renderer.cast.correct()

    def _save(self) -> None:
        self.progress_port.save(self.progress)

    def _show_completion(self, now: float) -> None:
        letters = "  ".join(card.letter for card in self.round.caught)
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(letters,) if letters else (),
                achievement_count=self.round.total,
            )
        )
        self._held.clear()
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
        self.controls.reset_round(self.round.total)
        self.completion = self._make_completion()
        self._activated = True
        self._enter_target(opening=True)

    # -- drawing -------------------------------------------------------------------------------
    def scene_state(self) -> SceneState:
        now = self.clock()
        target = self.round.current
        card = target.card if target is not None else None
        if self.state is AppState.FINALE:
            card = None
        sparkle = None
        if self._sparkle is not None:
            sparkle = (self._sparkle[0], (now - self._sparkle[1]) / SPARKLE_SECONDS)
        bump = None
        if self._bump is not None:
            bump = (self._bump[0], (now - self._bump[1]) / BUMP_SECONDS)
        return SceneState(
            card=card,
            letters=tuple(self.field.letters),
            basket_x=self.basket.x,
            caught=tuple(self.round.caught),
            revealed=self._revealed,
            speaking=self.speech_queue.current_tag in {"prompt", "word"},
            hint=self._hint and self.state is AppState.PLAYING,
            pulse_phase=self._pulse_phase,
            leo_pointing=now < self._point_until,
            sparkle=sparkle,
            bump=bump,
            finale=(now - self.state_started) if self.state is AppState.FINALE else None,
        )

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self._surfaces.draw(self.canvas.surface)
            return
        self.renderer.draw_scene(
            self.canvas.surface,
            self.controls.geometry,
            self.scene_state(),
            draw_controls=self._surfaces.draw,
        )


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "ForestaApp"]
