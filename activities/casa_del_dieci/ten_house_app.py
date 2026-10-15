"""Lifecycle and semantic input orchestration for La Casa del Dieci."""

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
    from .ten_house_audio import TenHouseAudio
    from .ten_house_controls import TenHouseControls
    from .ten_house_model import (
        OperationMode,
        TenHouseChallenge,
        TenHouseRoundFactory,
        TenHouseSession,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from .ten_house_renderer import DANI_HEIGHT, TenHouseRenderer
    from .ten_house_services import EventPort, ProgressPort
else:
    from ten_house_audio import TenHouseAudio
    from ten_house_controls import TenHouseControls
    from ten_house_model import (
        OperationMode,
        TenHouseChallenge,
        TenHouseRoundFactory,
        TenHouseSession,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        adapt_level,
    )
    from ten_house_renderer import DANI_HEIGHT, TenHouseRenderer
    from ten_house_services import EventPort, ProgressPort


class AppState(StrEnum):
    PLAYING = "playing"
    WOBBLE = "wobble"
    CELEBRATION = "celebration"
    TRANSITION = "transition"
    TERMINAL = "terminal"


class TenHouseActivity:
    """Coordinate domain model, shared-kit input/controls, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        session: TenHouseSession,
        factory: TenHouseRoundFactory,
        renderer: TenHouseRenderer,
        typography: GreiaTypography,
        resources,
        progress: ProgressPort,
        events: EventPort,
        audio: TenHouseAudio,
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
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.state = AppState.PLAYING
        self.state_started = clock()
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._spoken_challenge_id: str | None = None

        # Shared control kit (ADR 0037): learn Collection -> orange accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("orange"))
        if renderer.cast is None:
            renderer.cast = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        self.controls = TenHouseControls(
            self.kit,
            resources,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            on_room=self._on_room,
            on_choice=self._on_choice,
            on_confirm=self._perform_confirm,
            on_replay=self._replay_prompt,
        )
        self.controls.sync(session)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(
            to_logical=self._to_logical,
            is_safe=lambda pos: _safe_point(self.screen, pos),
        )
        self._activated = False

        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(
                background=(24, 36, 64),
                panel=(254, 243, 199),
                panel_border=(180, 83, 9),
                title=(120, 53, 15),
                body=(71, 85, 105),
                primary=(34, 197, 94),
                primary_text=(255, 255, 255),
            ),
            scene=CompletionScene(self.kit, character="dani", star_total=6),
        )

    def _get_prompt_cue(self, challenge: TenHouseChallenge) -> str:
        if challenge.mode == OperationMode.COMPOSE:
            return f"prompt_compose_{challenge.target}"
        elif challenge.mode == OperationMode.ADD:
            return "prompt_add"
        elif challenge.mode == OperationMode.TAKE_AWAY:
            return "prompt_take_away"
        elif challenge.mode == OperationMode.MISSING_PART:
            return "prompt_missing_part"
        return "prompt_compose_1"

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)
            repeat = self._input.poll()
            if repeat is not None:
                self._dispatch(repeat)
            if self._advance_state():
                self._dirty = True
            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            animating = self.state in {AppState.WOBBLE, AppState.CELEBRATION, AppState.TRANSITION}
            ticker.tick(30 if animating or self.renderer.cast.animating else 20)
        return 0

    # -- input ------------------------------------------------------------

    def _to_logical(self, position: tuple[int, int]) -> tuple[float, float] | None:
        return self.canvas.pointer(position)

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
            self._dirty = True
            return
        if self.state not in {AppState.PLAYING, AppState.TERMINAL}:
            return
        translated = self._input.translate(event)
        if translated is not None and self._dispatch(translated):
            self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        """Route one kit input through the SurfaceNavigator; True if handled."""

        if self.state not in {AppState.PLAYING, AppState.TERMINAL}:
            return False
        result = self._surfaces.dispatch(kit_input)
        if self.state is AppState.PLAYING:
            self.controls.mirror_focus(self.session)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

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
        """Deliver one key press through the shared navigation mapping."""

        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key))
        if translated is None:
            return False
        return self._dispatch(translated)

    def _handle_terminal_pointer(self, raw_pos: tuple[int, int]) -> bool:
        if self.state is not AppState.TERMINAL:
            return False
        before = self.state
        if not self._handle_pointer(raw_pos) and self.state is before:
            return False
        return True

    # -- control callbacks --------------------------------------------------

    def _on_room(self, index: int) -> None:
        current = self.session.current_challenge
        if current is None or current.mode != OperationMode.COMPOSE:
            return
        if self.session.toggle_room(index):
            self.audio.play("toggle")
            self.session.focused_room = index
            self.session.focus_in_choices = False
            self.controls.sync(self.session)
            self._activated = True

    def _on_choice(self, index: int) -> None:
        current = self.session.current_challenge
        if current is None or current.mode == OperationMode.COMPOSE:
            return
        self._activated = self._perform_choice(current.choice_values[index])

    def _replay_prompt(self) -> None:
        current = self.session.current_challenge
        if current is not None:
            self.audio.play_speech(self._get_prompt_cue(current))
            self._activated = True

    def _perform_confirm(self) -> bool:
        result = self.session.confirm_compose()
        self._activated = True
        return self._process_result(result)

    def _perform_choice(self, value: int) -> bool:
        result = self.session.choose(value)
        return self._process_result(result)

    def _process_result(self, result) -> bool:
        if not result.correct:
            self.audio.play_feedback(False)
            self.renderer.cast.try_again()
            self.state = AppState.WOBBLE
            self.state_started = self.clock()
            return True

        self.audio.play_feedback(True)
        self.renderer.cast.correct()
        milestone = self.session.consume_milestone()
        if milestone is not None:
            self.events.room_completed(self.session_id, milestone)

        if result.session_complete:
            self._finish_session()
        else:
            self.controls.sync(self.session)
            self.state = AppState.CELEBRATION
            self.state_started = self.clock()
        return True

    # -- state ----------------------------------------------------------------

    def _advance_state(self) -> bool:
        current = self.session.current_challenge
        if current is not None and current.challenge_id != self._spoken_challenge_id:
            self._spoken_challenge_id = current.challenge_id
            cue = self._get_prompt_cue(current)
            self.audio.play_speech(cue)

        changed = self.renderer.cast.update() if self.renderer.cast is not None else False
        elapsed = self.clock() - self.state_started
        if self.state == AppState.WOBBLE:
            if elapsed >= 0.35:
                self.state = AppState.PLAYING
                self.controls.sync(self.session)
            return True
        if self.state == AppState.CELEBRATION:
            if elapsed >= 0.55:
                self.state = AppState.TRANSITION
                self.state_started = self.clock()
            return True
        if self.state == AppState.TRANSITION:
            if elapsed >= 0.20:
                self.state = AppState.PLAYING
                self.controls.sync(self.session)
                return True
            return changed
        return changed

    def _render(self) -> None:
        if self.state is AppState.TERMINAL:
            self._surfaces.draw(self.canvas.surface)
            return

        wobble_x = 0
        highlight_rooms = False
        is_celebrating = self.state == AppState.CELEBRATION
        if self.state == AppState.WOBBLE:
            elapsed = self.clock() - self.state_started
            wobble_x = int(8 * ((1 - elapsed / 0.35) * ((int(elapsed * 40) % 2) * 2 - 1)))
            highlight_rooms = True

        hovered = self.controls.layer.hovered_id or ""
        hovered_room = int(hovered.split(".", 1)[1]) if hovered.startswith("room.") else None
        surface = self.canvas.surface
        self.renderer.draw_scene(
            surface,
            self.session,
            highlight_rooms=highlight_rooms,
            hovered_room=hovered_room,
            is_celebrating=is_celebrating,
        )
        shaking = self.controls.wobble_target() if wobble_x else None
        if shaking is not None:
            base = shaking.rect
            shaking.rect = base.move(wobble_x, 0)
            self._surfaces.draw(surface)
            shaking.rect = base
        else:
            self._surfaces.draw(surface)

    def _finish_session(self) -> None:
        payload = self.session.consume_completion()
        if payload is not None:
            next_level = adapt_level(self.session.level, self.session.history)
            self.progress.save(next_level, self.session.history)
            self.events.house_completed(self.session_id, payload)

        self.audio.play("complete")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=6,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL
        self.state_started = self.clock()

    def _restart(self) -> None:
        next_level = adapt_level(self.session.level, self.session.history)
        challenges = self.factory.build_set(next_level)
        self.session_id = f"{self.session_id.rsplit('-', 1)[0]}-{self.rng.randrange(1_000_000):06d}"
        self.session = TenHouseSession(challenges, level=next_level, history=self.session.history)
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.renderer.cast.reset()
        self.controls.sync(self.session)
        self.state = AppState.PLAYING
        self.state_started = self.clock()
        self.audio.play("correct")
        self._activated = True


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True
