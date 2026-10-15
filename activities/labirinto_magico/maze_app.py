"""Lifecycle, input and feedback timeline for Il Labirinto Magico.

One visit is four short hedge mazes in one garden world. Tito waves and says
"ready, go"; the child steers him (arrows / D-pad / stick, or tap and drag in
the maze) and he walks along the corridor by himself until the next choice.
Stars must be gathered before the tent opens (its bubble shows how many are
missing), and on key mazes the garden door on the only route opens once Tito
carries the key. A star, the key or the tent: Tito cheers (``pose_cheer``) with
library FX. A dead end, the closed tent or a locked door: Tito thinks
(``pose_think``) and the firefly demonstrates the first steps of the way.
Idle for ~6 s: Tito points and the next thing to fetch pulses, then the
firefly flies ahead. The next maze's size follows how this one went, and the
visit ends on the shared cast completion scene. Nothing is ever timed.
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
    from .maze_art import Biome, MazeArt, biome_for_visit
    from .maze_audio import LabyrinthAudio
    from .maze_controls import MazeControls
    from .maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, MazeGeometry
    from .maze_model import Cell, Maze, MazeEvent, MazeEventKind, Visit, Walker, is_cell, level_spec
    from .maze_renderer import TITO_SCALE, FireflyFlight, MazeCast, MazeMotion, MazeRenderer
    from .maze_services import EventPort, ProgressPort
else:
    from maze_art import Biome, MazeArt, biome_for_visit
    from maze_audio import LabyrinthAudio
    from maze_controls import MazeControls
    from maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH, MazeGeometry
    from maze_model import Cell, Maze, MazeEvent, MazeEventKind, Visit, Walker, is_cell, level_spec
    from maze_renderer import TITO_SCALE, FireflyFlight, MazeCast, MazeMotion, MazeRenderer
    from maze_services import EventPort, ProgressPort

IDLE_HINT_SECONDS = 6.0
CELEBRATE_SECONDS = 1.9
DEMO_LEAD_SECONDS = 0.6
HINT_CELLS = 3
RETRY_VOICE_GAP = 8.0
MAX_SCHEDULED = 32

_MOVES = {
    SemanticAction.MOVE_UP: (-1, 0),
    SemanticAction.MOVE_DOWN: (1, 0),
    SemanticAction.MOVE_LEFT: (0, -1),
    SemanticAction.MOVE_RIGHT: (0, 1),
}
_NAV_TO_MOVE = {
    SemanticAction.NAV_UP: (-1, 0),
    SemanticAction.NAV_DOWN: (1, 0),
    SemanticAction.NAV_LEFT: (0, -1),
    SemanticAction.NAV_RIGHT: (0, 1),
}


class AppState(StrEnum):
    PLAYING = "playing"
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


class LabyrinthActivity:
    """Coordinate the maze model, kit HUD, art, voice and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        visit: Visit,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: LabyrinthAudio,
        progress: ProgressPort,
        events: EventPort,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: MazeArt | None = None,
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
        self.art = art if art is not None else MazeArt(self.kit)
        self.controls = MazeControls(
            self.kit, ControlLayout.for_canvas(canvas, screen.get_size()), visit.total, on_hint=self._on_hint
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        self._game_input = PygameInputTranslator(InteractionProfile.DIRECTIONAL)
        self.motion = MazeMotion()
        self.walker = Walker()
        self.timeline = Timeline(clock)
        self.biome: Biome = biome_for_visit(visit.progress.visits_completed)
        self.completion: PygameCompletionScreen | None = None
        self.cast: MazeCast | None = None
        self.renderer: MazeRenderer | None = None
        self._cast_height = 0
        self.geometry: MazeGeometry
        self.scene: pygame.Surface
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._busy = False
        self._activated = False
        self._queued: Cell | None = None
        self._pointer_target: Cell | None = None
        self._pointer_held = False
        self._stick = (0.0, 0.0)
        self._stick_dir: Cell | None = None
        self._last_activity = clock()
        self._idle_hints = 0
        self._last_retry_voice = -100.0
        self._stars_this_maze = 0
        self._start_maze()

    @property
    def maze(self) -> Maze:
        return self.visit.maze

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
                animating = self.step(min(0.05, now - last))
                last = now
                self.render()
                self.canvas.present()
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
                if self.state is AppState.TERMINAL:
                    ticker.tick(15)
                else:
                    ticker.tick(30 if animating else 20)
        finally:
            self.progress.save(self.visit.progress)
            self.typography.clear()
        return 0

    def step(self, dt: float) -> bool:
        """Advance walking, timers and motion; return True while something moves."""

        now = self.clock()
        self.timeline.run_due()
        if self.cast is not None:
            self.cast.update()
        self.motion.prune(now)
        if self.state is not AppState.PLAYING:
            return False
        for cell, last in self.walker.advance(dt):
            self._arrive(cell, last)
            if self.state is not AppState.PLAYING or self.maze.solved:
                break
        if not self.walker.moving and not self._busy:
            if self._queued is not None:
                direction, self._queued = self._queued, None
                self._move(direction)
            elif self._pointer_target is not None:
                self._follow_pointer()
            elif self._stick_dir is not None:
                self._move(self._stick_dir)
        self._maybe_hint(now)
        cast_moving = self.cast is not None and self.cast.animating
        return self.walker.moving or self.motion.active(now) or cast_moving

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING and self.renderer is not None:
            spec = level_spec(self.maze.layout.level)
            arrows = (
                spec.guide_arrows
                and not self.walker.moving
                and not self._busy
                and not self.maze.solved
                and self.motion.bump is None
            )
            self.renderer.draw(
                surface,
                self.scene,
                self.maze,
                self.walker,
                self.geometry,
                self.motion,
                self.clock(),
                show_arrows=arrows,
            )
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
        if self.state is AppState.TERMINAL:
            translated = self._input.translate(event)
            if translated is not None:
                self._surfaces.dispatch(translated)
            return
        if event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            translated = self._input.translate(event)
            if isinstance(translated, KitPointer):
                self._pointer(translated)
            return
        semantic = self._game_input.digital(event)
        if semantic is not None:
            if semantic.edge is not InputEdge.PRESSED:
                return
            direction = _MOVES.get(semantic.action)
            if direction is not None:
                self._move(direction)
            elif semantic.action in {SemanticAction.PRIMARY, SemanticAction.ACTIVATE}:
                self._on_hint()
            return
        axis = self._game_input.controller_axis(event)
        if axis is not None:
            self._on_stick(axis.axis, axis.value)

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
                self._move(direction)

    def _pointer(self, pointer: KitPointer) -> None:
        if pointer.phase is PointerPhase.DOWN:
            self._note_activity()
        result = self._surfaces.dispatch(pointer)
        if result is not UiEventResult.IGNORED or self.controls.layer.pressed_id is not None:
            return
        if pointer.phase is PointerPhase.UP or pointer.phase is PointerPhase.CANCEL:
            self._pointer_held = False
            return
        if pointer.phase is PointerPhase.MOVE and not self._pointer_held:
            return
        target = self.geometry.nearest_cell(pointer.position)
        if target is None:
            return
        if pointer.phase is PointerPhase.DOWN:
            self._pointer_held = True
            self._activated = True
        if target != self._pointer_target:
            self._pointer_target = target
            self._note_activity()
            if not self.walker.moving:
                self._follow_pointer()

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        self._activated = False
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._handle_event(pygame.event.Event(event_type, pos=raw_pos, button=1))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press (tests/tools); returns whether something acted."""

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
        self._prepare_maze_art()
        self.controls.sync(self.maze, self.visit.completed, busy=self._busy)

    # -- maze flow -----------------------------------------------------------------

    def _start_maze(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        self.walker.stop()
        self.walker.origin = self.maze.position
        self._queued = None
        self._pointer_target = None
        self._busy = False
        self._stars_this_maze = 0
        self._prepare_maze_art()
        assert self.cast is not None
        self.cast.reset()
        self.cast.wave()
        self.motion.tent_hop = now
        self.audio.say("start")
        self.controls.sync(self.maze, self.visit.completed)
        self._note_activity()

    def _prepare_maze_art(self) -> None:
        layout = self.maze.layout
        self.geometry = MazeGeometry.fit(layout, self.controls.area)
        self.scene = self.art.compose_scene(layout, self.geometry, self.biome)
        height = int(self.geometry.cell * TITO_SCALE)
        if self.cast is None or height != self._cast_height:
            feedback = CastFeedback("tito", height=height, art=self.art.art, clock=self.clock)
            self.cast = MazeCast(
                feedback,
                self.art.cast_pose("pose_point", height),
                self.art.cast_pose("pose_wave", height),
                self.clock,
            )
            self.renderer = MazeRenderer(self.art, self.cast)
            self._cast_height = height

    def _move(self, direction: Cell) -> bool:
        if self.state is not AppState.PLAYING or self._busy or self.maze.solved:
            return False
        self._note_activity()
        self._pointer_target = None
        self._activated = True
        if self.walker.moving:
            self._queued = direction  # one buffered turn, applied on arrival
            return True
        path = self.maze.route(direction)
        if path:
            self.walker.start(self.maze.position, path)
            self.audio.play("step")
            return True
        if self.maze.blocked_by_door(direction):
            self.maze.summary.locked_tries += 1
            self._door_locked()
            return True
        if self.maze.blocked_by_tent(direction):
            self.maze.summary.locked_tries += 1
            self._tent_locked()
            return True
        self.maze.summary.bumps += 1
        self.motion.bump = (self.clock(), direction)
        self.audio.play("bump")
        return True

    def _follow_pointer(self) -> None:
        target = self._pointer_target
        if target is None or self._busy or self.maze.solved:
            self._pointer_target = None
            return
        if target == self.maze.position:
            self._pointer_target = None
            return
        plan = self.maze.direction_towards(target)
        if plan is None:
            self._pointer_target = None
            # A tap on the locked door / closed tent right next to Tito is a try.
            if target == self.maze.locked_door and self.maze.door_ahead() is not None:
                self.maze.summary.locked_tries += 1
                self._door_locked()
            elif target == self.maze.layout.goal and self.maze.tent_ahead() is not None:
                self.maze.summary.locked_tries += 1
                self._tent_locked()
            return
        _, path = plan
        self.walker.start(self.maze.position, path)
        self.audio.play("step")

    def _arrive(self, cell: Cell, last: bool) -> None:
        for event in self.maze.enter(cell, final=last):
            self._on_maze_event(event)

    def _on_maze_event(self, event: MazeEvent) -> None:
        now = self.clock()
        center = self.geometry.center(*event.cell)
        kind = event.kind
        assert self.cast is not None
        if kind is MazeEventKind.STAR:
            self._stars_this_maze += 1
            self.visit.progress.stars += 1
            self.cast.correct()
            self.audio.play("star")
            self.motion.add_fx("star_burst", center, now)
            self.events.star_collected(
                self._visit_id, self.visit.completed + 1, self._stars_this_maze, self.visit.progress.stars
            )
            self.controls.sync(self.maze, self.visit.completed)
            if not self.maze.missing_stars:
                self.motion.tent_hop = now  # the tent is open now
        elif kind is MazeEventKind.KEY:
            self.cast.correct()
            self.audio.play("key")
            self.motion.add_fx("sparkle", center, now)
            if self.maze.layout.door is not None:
                self.motion.pulse([self.maze.layout.door], now)
            self.controls.sync(self.maze, self.visit.completed)
        elif kind is MazeEventKind.DOOR_OPENED:
            self.audio.play("door")
            self.motion.add_fx("dust_puff", center, now)
            self.controls.sync(self.maze, self.visit.completed)
        elif kind is MazeEventKind.DOOR_LOCKED:
            self._door_locked()
        elif kind is MazeEventKind.GOAL_LOCKED:
            self._tent_locked()
        elif kind is MazeEventKind.DEAD_END:
            self.cast.try_again()
            if self.maze.summary.dead_ends >= 2:
                self.timeline.after(DEMO_LEAD_SECONDS, lambda: self._send_firefly(HINT_CELLS))
        elif kind is MazeEventKind.SOLVED:
            self._solved()

    def _door_locked(self) -> None:
        now = self.clock()
        assert self.cast is not None
        self.cast.try_again()
        self.motion.door_rattle = now
        self.audio.play("locked")
        self._retry_voice()
        if self.maze.layout.key is not None and not self.maze.has_key:
            self.motion.pulse([self.maze.layout.key], now)
        self.timeline.after(DEMO_LEAD_SECONDS, lambda: self._send_firefly(HINT_CELLS))

    def _tent_locked(self) -> None:
        """The tent stays closed until every star is found: show which are missing."""

        now = self.clock()
        assert self.cast is not None
        self.cast.try_again()
        self.motion.tent_hop = now
        self.audio.play("locked")
        self._retry_voice()
        self.motion.pulse([*self.maze.missing_stars, self.maze.layout.goal], now)
        self.timeline.after(DEMO_LEAD_SECONDS, lambda: self._send_firefly(HINT_CELLS))

    def _retry_voice(self) -> None:
        now = self.clock()
        if now - self._last_retry_voice >= RETRY_VOICE_GAP:
            self._last_retry_voice = now
            self.audio.say("retry")

    def _send_firefly(self, cells: int) -> None:
        """Fly the first ``cells`` maze cells of the way to the next thing to fetch."""

        if self.state is not AppState.PLAYING or self.maze.solved:
            return
        route = self.maze.hint_route()
        if len(route) < 2:
            return
        count = 0
        end = len(route)
        for index, square in enumerate(route[1:], start=1):
            if is_cell(square):
                count += 1
                if count >= cells:
                    end = index + 1
                    break
        self.motion.firefly = FireflyFlight(tuple(route[:end]), self.clock())
        self.audio.play("hint")

    def _on_hint(self) -> None:
        if self.state is not AppState.PLAYING or self._busy or self.maze.solved:
            return
        self._activated = True
        self._note_activity()
        self.maze.summary.hints += 1
        assert self.cast is not None
        self.cast.point(1.6)
        self.motion.pulse([self.maze.next_target()], self.clock())
        self._send_firefly(HINT_CELLS)

    def _solved(self) -> None:
        now = self.clock()
        assert self.cast is not None
        self._busy = True
        self.walker.stop()
        self._queued = None
        self._pointer_target = None
        self.cast.correct()
        self.audio.play("tent")
        self.audio.say("solved")
        goal = self.geometry.center(*self.maze.layout.goal)
        self.motion.add_fx("confetti", (goal[0], goal[1] - self.geometry.cell * 0.4), now)
        self.motion.add_fx("star_burst", goal, now)
        self.motion.tent_hop = now
        index = self.visit.completed + 1
        summary = self.visit.finish_maze()
        self.events.maze_solved(self._visit_id, index, summary)
        self.progress.save(self.visit.progress)
        self.controls.sync(self.maze, self.visit.completed, busy=True)
        self.timeline.after(CELEBRATE_SECONDS, self._after_celebration)

    def _after_celebration(self) -> None:
        if self.visit.complete:
            self._complete_visit()
            return
        self.visit.next_maze()
        self._start_maze()

    def _complete_visit(self) -> None:
        progress = self.visit.progress
        finished_biome = self.biome
        progress.visits_completed += 1
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
            scene=CompletionScene(self.kit, character="tito", star_total=self.visit.total),
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
        """One restart transaction regardless of keyboard/controller/pointer input."""

        self._activated = True
        self._surfaces.pop_overlay()
        if self.completion is not None:
            self.completion.clear()
        self._visit_id = uuid4().hex
        self.biome = biome_for_visit(self.visit.progress.visits_completed)
        self.visit.restart()
        self.state = AppState.PLAYING
        self._start_maze()

    # -- hints ------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy or self.walker.moving or self.timeline.busy or self.maze.solved:
            return
        if now - self._last_activity < IDLE_HINT_SECONDS * (self._idle_hints + 1):
            return
        self._idle_hints += 1
        assert self.cast is not None
        self.cast.point(1.8)
        self.motion.pulse([self.maze.next_target()], now)
        if self._idle_hints == 1:
            self.audio.say("nudge")
            return
        # Later nudges show the first steps of the way (counted for adaptation).
        self.maze.summary.hints += 1
        self._send_firefly(HINT_CELLS + self._idle_hints - 2)


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["AppState", "LabyrinthActivity", "Timeline"]
