"""Lifecycle, input and feedback timeline for La Corsa delle Bacche.

One visit is three small gardens. In each, Momo waves and says "ready, go";
every berry is visible at once and the basket in the top bar shows one slot
per berry. The child steers Momo:

* arrows / D-pad / left stick: Momo walks along the path by himself, follows
  bends and stops at a junction (hold a direction to keep going); a press
  while walking is a buffered turn, the opposite direction turns him around;
* Space / south button: stop and wait (standing still is always safe);
  pressed while Momo already stands still it asks for a hint;
* tap or drag in the garden: Momo walks the shortest path there; the path
  stops in front of an awake critter (a "wait" bubble shows) -- tap again
  when the way is clear.

A berry: pop, sparkle, Momo cheers (``pose_cheer``). Walking into an awake
critter: a soft "boing", Momo bounces back one cell and thinks
(``pose_think``) -- nothing is lost, there are no lives; from the second
bump Momo shows a way to the next berry around the critters. A critter that
meets a still Momo just turns around. Sleeping hedgehogs (eyes closed) are
safe to pass. Idle for ~6 s: Momo points and the nearest berry hops; later
nudges draw a dotted trail. The last berry: a full basket, confetti and
praise; the next garden's rung follows how this one went, and after three
gardens the shared cast completion scene appears. Nothing is timed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import time
from uuid import uuid4

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
from greia_platform.input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    InteractionProfile,
    SemanticAction,
    navigation_direction,
    normalize_stick,
)
from greia_platform.localization import LocalizedResources
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
    from .corsa_art import MOMO_SHARE, Biome, CorsaArt, biome_for_garden, fruit_for
    from .corsa_audio import CorsaAudio
    from .corsa_controls import CorsaControls
    from .corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenGeometry
    from .corsa_model import DOWN, LEFT, RIGHT, UP, Direction, Garden, GardenEvent, GardenEventKind, StepResult, Visit
    from .corsa_renderer import CorsaMotion, CorsaRenderer, HintTrail, MomoCast
    from .corsa_services import EventPort, ProgressPort
else:
    from corsa_art import MOMO_SHARE, Biome, CorsaArt, biome_for_garden, fruit_for
    from corsa_audio import CorsaAudio
    from corsa_controls import CorsaControls
    from corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenGeometry
    from corsa_model import DOWN, LEFT, RIGHT, UP, Direction, Garden, GardenEvent, GardenEventKind, StepResult, Visit
    from corsa_renderer import CorsaMotion, CorsaRenderer, HintTrail, MomoCast
    from corsa_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
CELEBRATE_SECONDS = 2.0
DEMO_LEAD_SECONDS = 0.6
RETRY_VOICE_GAP = 8.0
MAX_SCHEDULED = 32
CHEER_SECONDS = 0.9

_MOVES: dict[SemanticAction, Direction] = {
    SemanticAction.MOVE_UP: UP,
    SemanticAction.MOVE_DOWN: DOWN,
    SemanticAction.MOVE_LEFT: LEFT,
    SemanticAction.MOVE_RIGHT: RIGHT,
}
_NAV_TO_MOVE: dict[SemanticAction, Direction] = {
    SemanticAction.NAV_UP: UP,
    SemanticAction.NAV_DOWN: DOWN,
    SemanticAction.NAV_LEFT: LEFT,
    SemanticAction.NAV_RIGHT: RIGHT,
}


class AppState(StrEnum):
    PLAYING = "playing"
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


class CorsaActivity:
    """Coordinate the garden model, kit HUD, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        visit: Visit,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: CorsaAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: CorsaArt | None = None,
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
        self.art = art if art is not None else CorsaArt(self.kit)
        self.controls = CorsaControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            visit.total,
            berry_icon=self.art.berry_icon,
            on_hint=self._on_hint,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self._game_input = PygameInputTranslator(InteractionProfile.DIRECTIONAL)
        self.motion = CorsaMotion()
        self.timeline = Timeline(clock)
        self.biome: Biome = biome_for_garden(0)
        self.completion: PygameCompletionScreen | None = None
        self.cast: MomoCast | None = None
        self.renderer: CorsaRenderer | None = None
        self._cast_height = 0
        self.geometry: GardenGeometry
        self.scene: pygame.Surface
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._activated = False
        self._pointer_target = None
        self._pointer_held = False
        self._held_key: Direction | None = None
        self._stick = (0.0, 0.0)
        self._stick_dir: Direction | None = None
        self._last_activity = clock()
        self._idle_hints = 0
        self._last_retry_voice = -100.0
        self._start_garden()

    @property
    def garden(self) -> Garden:
        return self.visit.garden

    # -- main loop ------------------------------------------------------------

    def run(self) -> int:
        ticker = pygame.time.Clock()
        last = self.clock()
        try:
            while self._running and not activity_stop_requested():
                for event in pygame.event.get():
                    self._handle_event(event)
                if self.state is AppState.TERMINAL:
                    repeat = self._input.poll()
                    if repeat is not None:
                        self._surfaces.dispatch(repeat)
                now = self.clock()
                self.step(min(0.05, max(0.0, now - last)))
                last = now
                self.render()
                self.canvas.present()
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
                ticker.tick(15 if self.state is AppState.TERMINAL else 30)
        finally:
            self.progress.save(self.visit.progress)
            self.typography.clear()
        return 0

    def step(self, dt: float) -> bool:
        """Advance the garden, timers and motion; return True while something moves."""

        now = self.clock()
        self.timeline.run_due()
        if self.cast is not None:
            self.cast.update()
        self.motion.prune(now)
        if self.state is not AppState.PLAYING:
            return self.state is AppState.CELEBRATE
        for event in self.garden.update(dt):
            self._on_garden_event(event)
            if self.state is not AppState.PLAYING:
                break
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        return True

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is not AppState.TERMINAL and self.renderer is not None:
            self.renderer.draw(surface, self.scene, self.garden, self.geometry, self.motion, self.clock())
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
            self._pointer_held = False
            self._release_all()
            return
        if self.state is AppState.TERMINAL:
            translated = self._input.translate(event)
            if translated is not None:
                self._activated = True
                self._surfaces.dispatch(translated)
            return
        if event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            translated = self._input.translate(event)
            if isinstance(translated, KitPointer):
                self._pointer(translated)
            return
        semantic = self._game_input.digital(event)
        if semantic is not None:
            self._on_semantic(semantic.action, semantic.edge)
            return
        axis = self._game_input.controller_axis(event)
        if axis is not None:
            self._on_stick(axis.axis, axis.value)

    def _on_semantic(self, action: SemanticAction, edge: InputEdge) -> None:
        direction = _MOVES.get(action)
        if direction is not None:
            if edge is InputEdge.PRESSED:
                self._held_key = direction
                self._steer(direction)
                self.garden.hold(direction)
            elif self._held_key == direction:
                self._held_key = None
                self.garden.hold(self._stick_dir)
            return
        if edge is not InputEdge.PRESSED:
            return
        if action is SemanticAction.PRIMARY:
            self._note_activity()
            self._activated = True
            if self.state is AppState.PLAYING and not self.garden.stop() and not self.garden.momo.moving:
                self._on_hint()
        elif action is SemanticAction.ACTIVATE:
            self._on_hint()

    def _on_stick(self, axis: ControllerAxis, value: float) -> None:
        x, y = self._stick
        if axis is ControllerAxis.LEFT_X:
            x = value
        elif axis is ControllerAxis.LEFT_Y:
            y = value
        else:
            return
        self._stick = (x, y)
        action = navigation_direction(
            normalize_stick(x, y, DEFAULT_INPUT_POLICY.stick_dead_zone), DEFAULT_INPUT_POLICY.navigation_threshold
        )
        direction = _NAV_TO_MOVE.get(action) if action is not None else None
        if direction != self._stick_dir:
            self._stick_dir = direction
            if direction is not None:
                self._steer(direction)
            self.garden.hold(direction if direction is not None else self._held_key)

    def _steer(self, direction: Direction) -> None:
        if self.state is not AppState.PLAYING:
            return
        self._note_activity()
        self._activated = True
        self._pointer_target = None
        result = self.garden.steer(direction)
        if result is StepResult.BLOCKED:
            self.motion.wall = (self.clock(), direction)
            self.audio.play("wall")

    def _release_all(self) -> None:
        self._held_key = None
        self._stick_dir = None
        self._stick = (0.0, 0.0)
        self.garden.hold(None)

    def _pointer(self, pointer: KitPointer) -> None:
        if pointer.phase is PointerPhase.DOWN:
            self._note_activity()
        result = self._surfaces.dispatch(pointer)
        if result is not UiEventResult.IGNORED or self.controls.layer.pressed_id is not None:
            self._activated = self._activated or result is not UiEventResult.IGNORED
            return
        if pointer.phase in (PointerPhase.UP, PointerPhase.CANCEL):
            self._pointer_held = False
            return
        if pointer.phase is PointerPhase.MOVE and not self._pointer_held:
            return
        if self.state is not AppState.PLAYING:
            return
        target = self.geometry.cell_at(pointer.position)
        if target is None:
            return
        if pointer.phase is PointerPhase.DOWN:
            self._pointer_held = True
            self._activated = True
            self._pointer_target = None
        if target != self._pointer_target:
            self._pointer_target = target
            self._note_activity()
            self.garden.go_to(target)

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        self._activated = False
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._handle_event(pygame.event.Event(event_type, pos=raw_pos, button=1))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press + release (tests/tools); returns whether something acted."""

        self._activated = False
        for event_type in (pygame.KEYDOWN, pygame.KEYUP):
            self._handle_event(pygame.event.Event(event_type, key=key, mod=0, unicode="", scancode=0))
        return self._activated

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._idle_hints = 0

    def _relayout(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = self._make_input()
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._prepare_art()
        self._sync_hud()

    # -- garden flow ----------------------------------------------------------------

    def _start_garden(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        self._pointer_target = None
        self.biome = biome_for_garden(self.visit.completed)
        self._prepare_art()
        assert self.cast is not None
        self.cast.reset()
        self.cast.wave()
        self.motion.intro = now
        self.audio.say("start")
        if self._held_key is not None or self._stick_dir is not None:
            self.garden.hold(self._held_key or self._stick_dir)
        self._sync_hud()
        self._note_activity()

    def _prepare_art(self) -> None:
        layout = self.garden.layout
        self.geometry = GardenGeometry.fit(layout, self.controls.area)
        self.scene = self.art.compose_scene(layout, self.geometry, self.biome)
        height = int(self.geometry.cell * MOMO_SHARE)
        if self.cast is None or height != self._cast_height:
            feedback = CastFeedback(
                "momo", height=height, art=self.art.art, idle_variant="happy", hold_seconds=CHEER_SECONDS, clock=self.clock
            )
            self.cast = MomoCast(
                feedback,
                self.art.cast_pose("pose_point", height),
                self.art.cast_pose("pose_wave", height),
                self.clock,
            )
            self.renderer = CorsaRenderer(self.art, self.cast)
            self._cast_height = height

    def _sync_hud(self) -> None:
        garden = self.garden
        picked = [fruit_for(cell) for cell in garden.basket]
        self.controls.sync(picked, garden.total, self.visit.completed, busy=self.state is not AppState.PLAYING)

    def _on_garden_event(self, event: GardenEvent) -> None:
        now = self.clock()
        center = self.geometry.center(*event.cell)
        kind = event.kind
        assert self.cast is not None
        if kind is GardenEventKind.BERRY:
            self.cast.correct()
            self.audio.play("pop")
            # The sparkle rises over Momo's head (he stands on the berry's cell).
            self.motion.add_fx("sparkle", (center[0], center[1] - self.geometry.cell * 0.7), now)
            self.motion.pulses.pop(event.cell, None)
            trail = self.motion.trail
            if trail is not None and trail.route and trail.route[-1] == event.cell:
                self.motion.trail = None
            self._sync_hud()
        elif kind is GardenEventKind.CLEARED:
            self._cleared()
        elif kind is GardenEventKind.BUMP:
            self._bumped(event)
        elif kind is GardenEventKind.WAIT:
            self.motion.bubble = now
            self.motion.pulse_critter(event.critter, now)
            self.audio.play("wait")
        elif kind is GardenEventKind.BOOP:
            self.audio.play("boop")
            self.motion.pulse_critter(event.critter, now)
        elif kind is GardenEventKind.NAP:
            self.audio.play("yawn")
        elif kind is GardenEventKind.WAKE:
            self.motion.pulse_critter(event.critter, now)

    def _bumped(self, event: GardenEvent) -> None:
        now = self.clock()
        assert self.cast is not None
        critter = self.garden.critters[event.critter]
        cr, cc = critter.position()
        mr, mc = self.garden.momo.position()
        contact = self.geometry.center((cr + mr) / 2, (cc + mc) / 2)
        self.cast.try_again()
        self.audio.play("bump")
        self.motion.add_fx("dust_puff", contact, now)
        self.motion.pulse_critter(event.critter, now)
        self._pointer_target = None
        if now - self._last_retry_voice >= RETRY_VOICE_GAP:
            self._last_retry_voice = now
            self.audio.say("retry")
        if self.garden.summary.bumps >= 2:
            # Demonstrate: a dotted way to the next berry around the critters.
            self.timeline.after(DEMO_LEAD_SECONDS, lambda: self._show_trail(avoid=True))

    def _show_trail(self, *, avoid: bool, cells: int | None = None) -> bool:
        if self.state is not AppState.PLAYING:
            return False
        route = self.garden.hint_route(avoid_critters=avoid)
        if len(route) < 2:
            return False
        if cells is not None:
            route = route[: cells + 1]
        self.motion.trail = HintTrail(tuple(route), self.clock())
        self.motion.pulse([route[-1]], self.clock())
        self.audio.play("hint")
        return True

    def _on_hint(self) -> None:
        if self.state is not AppState.PLAYING or self.garden.cleared:
            return
        self._activated = True
        self._note_activity()
        if self.motion.trail is not None:
            return  # one hint at a time; mashing never piles them up
        self.garden.summary.hints += 1
        assert self.cast is not None
        self.cast.point(1.6)
        target = self.garden.next_berry()
        if target is not None:
            self.motion.pulse([target], self.clock())
        self._show_trail(avoid=True)

    def _cleared(self) -> None:
        now = self.clock()
        assert self.cast is not None
        self.state = AppState.CELEBRATE
        self._pointer_target = None
        self.motion.trail = None
        self.cast.correct()
        self.audio.play("basket")
        self.audio.say("cleared")
        momo = self.geometry.center(*self.garden.momo.position())
        self.motion.add_fx("confetti", (momo[0], momo[1] - self.geometry.cell * 0.5), now)
        self.motion.add_fx("star_burst", momo, now)
        index = self.visit.completed + 1
        summary = self.visit.finish_garden()
        self.events.garden_cleared(self._visit_id, index, summary)
        self.progress.save(self.visit.progress)
        self._sync_hud()
        self.timeline.after(CELEBRATE_SECONDS, self._after_celebration)

    def _after_celebration(self) -> None:
        if self.visit.complete:
            self._complete_visit()
            return
        self.visit.next_garden()
        self.state = AppState.PLAYING
        self._start_garden()

    def _complete_visit(self) -> None:
        progress = self.visit.progress
        finished_biome = self.biome
        self.visit.finish_visit()
        self.progress.save(progress)
        self.events.visit_completed(self._visit_id, self.visit.completed, progress.level)
        self.timeline.clear()
        self.motion.clear()
        self.audio.play("fanfare")
        self.audio.say("complete")
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=finished_biome.dusk),
            scene=CompletionScene(self.kit, character="momo", star_total=self.visit.total),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★"),
                primary_label=self._text("btn.play_again", "↻"),
                achievement_count=self.visit.completed,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.state = AppState.TERMINAL

    def _restart(self) -> None:
        """One restart transaction regardless of keyboard/controller/pointer input."""

        self._activated = True
        self._surfaces.pop_overlay()
        if self.completion is not None:
            self.completion.clear()
            self.completion = None
        self._visit_id = uuid4().hex
        self.visit.restart()
        self.state = AppState.PLAYING
        self._start_garden()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        garden = self.garden
        if garden.momo.moving or self.timeline.busy or garden.cleared or self.motion.trail is not None:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        assert self.cast is not None
        self.cast.point(1.8)
        target = garden.next_berry()
        if target is not None:
            self.motion.pulse([target], now)
        if self._idle_hints == 1:
            self.audio.say("nudge")
            return
        # Later nudges show the way (counted for adaptation), longer each time.
        garden.summary.hints += 1
        self._show_trail(avoid=True, cells=2 + self._idle_hints if self._idle_hints < 4 else None)

    def _text(self, key: str, default: str) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key) or default
        except Exception:
            return default


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """True inside the play surface and outside the Greia protected region(s)."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "CorsaActivity", "Timeline"]
