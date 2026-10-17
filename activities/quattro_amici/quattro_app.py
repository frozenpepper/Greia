"""Lifecycle, turn flow and shared-kit input for Quattro Amici in Fila.

A *match* is best of three games between Flash (the child) and Leo — or
between two children sharing the device. Each game the friend whose turn it
is stands in a sunny spotlight with a happy pose while their disc hovers over
the board; Leo thinks out loud with his ``pose_think`` and then glides his
acorn to a column before dropping it, so the child can follow his move.

Feedback follows ADR 0037: a won game counts the winning row disc by disc
(chimes + sparkles), then the winner cheers (``pose_cheer``) and Leo speaks
an approved line; a lost game makes Flash think (``pose_think``) and Leo say
"let's try again"; a draw is friendly (both wave, hearts). Blocking Leo's
almost-row earns a cheer; when Leo blocks the child he points at the board.
Hints are graduated (~6 s idle -> the friend points and the disc pulses;
again -> the winning/blocking column glows) and after two lost games in a row
the useful column glows on its own. Difficulty adapts between matches
(``adapt_stage``) and Leo eases off within a session after lost games.
The match ends on the shared cast completion scene.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
import random
import time

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
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizedResources, activity_resources
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
    from .quattro_art import QuattroArt
    from .quattro_audio import QuattroAudio
    from .quattro_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WINS_FOR_MATCH,
        GameMode,
        GameStatus,
        Player,
        stage_for,
    )
    from .quattro_controls import QuattroControls
    from .quattro_layout import CAST_HEIGHT, BoardGeometry, plate_rect
    from .quattro_model import (
        DropResult,
        MatchOutcome,
        QuattroGame,
        QuattroMatch,
        adapt_stage,
        kindness_for,
        leo_brain_for,
        suggest_column,
    )
    from .quattro_renderer import WIN_STEP_SECONDS, BoardMotion, DropAnimation, FriendCast, QuattroRenderer
    from .quattro_services import (
        EventPort,
        GreiaQuattroEvents,
        GreiaQuattroProgress,
        ProgressPort,
        QuattroProgress,
    )
else:
    from quattro_art import QuattroArt
    from quattro_audio import QuattroAudio
    from quattro_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WINS_FOR_MATCH,
        GameMode,
        GameStatus,
        Player,
        stage_for,
    )
    from quattro_controls import QuattroControls
    from quattro_layout import CAST_HEIGHT, BoardGeometry, plate_rect
    from quattro_model import (
        DropResult,
        MatchOutcome,
        QuattroGame,
        QuattroMatch,
        adapt_stage,
        kindness_for,
        leo_brain_for,
        suggest_column,
    )
    from quattro_renderer import WIN_STEP_SECONDS, BoardMotion, DropAnimation, FriendCast, QuattroRenderer
    from quattro_services import (
        EventPort,
        GreiaQuattroEvents,
        GreiaQuattroProgress,
        ProgressPort,
        QuattroProgress,
    )

AUTO_HINT_SECONDS = 2.5
HINT_GLOW_SECONDS = 3.0
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at start (ADR 0037 §4b)
LEO_THINK_SECONDS = (0.7, 1.2)
GLIDE_SECONDS_PER_COLUMN = 0.12
WIN_LEAD = 0.15
CELEBRATE_HOLD = 2.4
DRAW_HOLD = 2.6
MAX_SCHEDULED = 48
SKY_NIGHT = (37, 59, 89)  # theme token "navy" behind the completion card


class Phase(StrEnum):
    TURN = "turn"  # a child may drop a disc
    LEO = "leo"  # Leo is choosing
    DROPPING = "dropping"
    CELEBRATING = "celebrating"
    BETWEEN = "between"  # the "next game" button is up
    MATCH_OVER = "match_over"


class Timeline:
    """Tiny bounded scheduler for scripted moments."""

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


def _is_safe_pointer(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Prevent Activity clicks/hover from operating under trusted Greia chrome."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom for region in viewport.protected_regions
    )


class QuattroApp:
    """Coordinate match model, shared-kit controls, art, sound and lifecycle."""

    # Class-level defaults: event routing degrades safely before wiring.
    phase: Phase = Phase.TURN
    running: bool = True
    _surfaces: SurfaceNavigator | None = None
    _dirty: bool = True
    _frames: FrameGovernor | None = None

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: QuattroAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        session_id: str | None = None,
        kit: ControlKit | None = None,
        art: QuattroArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng or random.Random()
        self.clock = clock
        self.session_id = session_id or f"{int(time.time())}-{self.rng.randrange(1_000_000):06d}"

        saved = progress.load()
        self.ladder = saved.ladder
        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else QuattroArt(self.kit.painter)
        self.match = QuattroMatch(stage_for(self.ladder.stage), saved.mode)
        self.model: QuattroGame = self.match.game
        self.geometry = BoardGeometry.for_stage(self.match.stage)
        self.art.prepare_stage(self.geometry)
        self.friends = {
            player: FriendCast(
                player,
                CastFeedback(player.cast_id, height=CAST_HEIGHT, art=self.art.art, clock=clock),
                self.art,
                clock,
            )
            for player in (Player.FLASH, Player.LEO)
        }
        self.renderer = QuattroRenderer(self.art, self.friends, clock=clock)
        self.renderer.geometry = self.geometry
        self.motion = BoardMotion()
        self.timeline = Timeline(clock)
        self.controls = QuattroControls(
            self.kit,
            self.art,
            resources,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            self.geometry,
            self.match.mode,
            on_column=self._on_column,
            on_mode=self._on_mode,
            on_next=self._on_next,
            clock=clock,
        )
        self.controls.keys.show(KEY_HINT_START_SECONDS)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _is_safe_pointer(self.screen, pos))
        self._completions: dict[str, PygameCompletionScreen] = {}
        self.completion: PygameCompletionScreen | None = None
        self.selected_col = self.geometry.cols // 2
        self.running = True
        self.ready_published = False
        self._activated = False
        self._turn_serial = 0
        self._last_activity = clock()
        self._last_step = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._losses_in_a_row = 0
        self._game_serial = 0
        self._leo_thinking_said = False
        self._pending: DropResult | None = None
        self._begin_game()

    # -- main loop ----------------------------------------------------------------

    def run(self) -> int:
        frames = self._frames = FrameGovernor()
        try:
            while self.running and not activity_stop_requested():
                self._process_events()
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                key_deadline = self.controls.keys.deadline()
                if key_deadline is not None:
                    frames.wake_at(key_deadline)
                frame = frames.frame(dirty=self._dirty, animating=animating)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.typography.clear()
            close = getattr(self.events, "close", None)
            if callable(close):
                close()  # hand queued facts to Greia (bounded) before exit
        return 0

    def step(self, dt: float | None = None) -> bool:
        """Advance timers and animation; return True while something moves."""

        now = self.clock()
        elapsed = now - self._last_step if dt is None else dt
        self._last_step = now
        elapsed = max(0.0, min(0.05, elapsed))
        if self.timeline.run_due():
            self._dirty = True
        drop = self.motion.drop
        if drop is not None:
            settled = drop.update(elapsed)
            if drop.consume_landing():
                self.audio.play_drop_clack()
            if settled:
                self.motion.drop = None
                self._after_drop()
            self._dirty = True
        for friend in self.friends.values():
            if friend.update():
                self._dirty = True
        self.motion.prune(now)
        if self.controls.keys.update():
            self._dirty = True
        self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        animating = self.motion.active(now, self.geometry) or any(f.animating for f in self.friends.values())
        return animating or self.phase is Phase.LEO

    def render(self) -> None:
        surface = self.canvas.surface
        if self.phase is Phase.MATCH_OVER and self.completion is not None:
            self._surfaces.draw(surface)
            return
        self.renderer.draw(
            surface,
            self.model,
            self.geometry,
            self.motion,
            self._wins(),
            self.selected_col,
            human_turn=self.phase is Phase.TURN,
        )
        self._surfaces.draw(surface)

    def _wins(self) -> dict[Player, int]:
        return {player: self.match.wins(player) for player in (Player.FLASH, Player.LEO)}

    # -- input ----------------------------------------------------------------------

    def _process_events(self) -> None:
        frames = self._frames
        for event in frames.events() if frames is not None else pygame.event.get():
            self._handle_event(event)
            if not self.running:
                return

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._handle_pointer_event(event)
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if self.controls.keys.observe_event(event):
            self._dirty = True
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _handle_pointer_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.MOUSEMOTION and getattr(event, "button", 1) != 1:
            return
        logical = self.canvas.pointer(event.pos) if _is_safe_pointer(self.screen, event.pos) else None
        if logical is None:
            if event.type == pygame.MOUSEBUTTONUP:
                self._kit_pointer(PointerPhase.CANCEL, (-1, -1))
            return
        x, y = logical
        if event.type == pygame.MOUSEMOTION:
            self._hover(x, y)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(x, y)
        else:
            self._handle_release(x, y)

    def _hover(self, x: float, y: float) -> None:
        if self.phase is Phase.TURN:
            col = self.renderer.get_column_at_x(self.model, x)
            if col is not None and col != self.selected_col:
                self.selected_col = col
                self.audio.play_hover()
                self._dirty = True
        self._kit_pointer(PointerPhase.MOVE, (x, y))

    def _handle_click(self, x: float, y: float) -> None:
        self._note_activity()
        if self.phase is Phase.TURN:
            col = self.renderer.get_column_at_x(self.model, x)
            if col is not None and self.controls.columns[col].contains((int(x), int(y))):
                self.selected_col = col
        self._kit_pointer(PointerPhase.DOWN, (x, y))

    def _handle_release(self, x: float, y: float) -> None:
        self._kit_pointer(PointerPhase.UP, (x, y))

    def _kit_pointer(self, phase: PointerPhase, position: tuple[float, float]) -> None:
        if self._surfaces is None:
            return
        self._dispatch(KitPointer(phase, (int(position[0]), int(position[1]))))

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        if (
            isinstance(kit_input, SemanticInputEvent)
            and kit_input.edge is InputEdge.PRESSED
            and kit_input.action in {SemanticAction.NAV_DOWN, SemanticAction.MOVE_DOWN}
            and self.phase is Phase.TURN
            and self.controls.focused_column() is not None
        ):
            # Arrow-down / D-pad down drops the disc, like Space or the south button.
            self.controls.layer.focus_visible = True
            self._on_column(self.controls.focused_column())  # type: ignore[arg-type]
            return True
        result = self._surfaces.dispatch(kit_input)
        focused = self.controls.focused_column()
        if (
            isinstance(kit_input, SemanticInputEvent)
            and focused is not None
            and focused != self.selected_col
            and self.phase is Phase.TURN
        ):
            self.selected_col = focused
            self.audio.play_hover()
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        self._activated = False
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self._handle_event(pygame.event.Event(kind, button=1, pos=raw_pos))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        self._activated = False
        self._handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))
        return self._activated

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(
            to_logical=self.canvas.pointer, is_safe=lambda pos: _is_safe_pointer(self.screen, pos)
        )
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    # -- game flow --------------------------------------------------------------------

    @property
    def vs_leo(self) -> bool:
        return self.match.mode is GameMode.VS_CPU

    def _is_human(self, player: Player) -> bool:
        return player is Player.FLASH or not self.vs_leo

    def _begin_game(self) -> None:
        self.model = self.match.game
        self.timeline.clear()
        self.motion.clear()
        for friend in self.friends.values():
            friend.reset()
        self.selected_col = self.geometry.cols // 2
        self._game_serial += 1
        starter = self.model.starter
        self.audio.say(starter.cast_id, "ready.go")
        self._leo_thinking_said = False
        # The goal of this board, after "ready, go" ("Make three/four in a row!").
        goal = {3: "make_three_in_row", 4: "make_four_in_row"}.get(self.model.stage.target)
        if goal is not None:
            self.audio.line(goal, after=True)
        self._emit(
            "quattro.game_started",
            f"game-{self._game_serial}-started",
            {"stage": self.match.stage.number, "mode": self.match.mode.value, "game": self.match.game_index + 1},
        )
        self._begin_turn()

    def _begin_turn(self) -> None:
        game = self.model
        self._turn_serial += 1
        player = game.current_player
        for who, friend in self.friends.items():
            friend.set_active(who is player)
        self.motion.show_selector = True
        self.motion.selector_since = self.clock()
        self.motion.pulse_start = None
        self.selected_col = max(0, min(self.geometry.cols - 1, self.selected_col))
        if not self._is_human(player):
            self.phase = Phase.LEO
            self._leo_move()
        else:
            self.phase = Phase.TURN
            if self.vs_leo and self.model.history:
                self.audio.line("your_turn", if_quiet=True)  # back to the child after Leo
            self._note_activity()
            if self.vs_leo and self._losses_in_a_row >= 2:
                serial = self._turn_serial
                self.timeline.after(AUTO_HINT_SECONDS, lambda: self._auto_hint(serial))
        self._sync()
        if self.phase is Phase.TURN:
            self.controls.focus_column(self.selected_col)
        self._dirty = True

    def _leo_move(self) -> None:
        game = self.model
        brain = leo_brain_for(game.stage.leo)
        choice = brain.choose(game.board, Player.LEO, self.rng, kindness_for(self._losses_in_a_row))
        if choice < 0:
            return
        think = self.rng.uniform(*LEO_THINK_SECONDS)
        glide = abs(choice - self.selected_col) * GLIDE_SECONDS_PER_COLUMN
        self.friends[Player.LEO].show("pose_think", think)
        if not self._leo_thinking_said:
            self._leo_thinking_said = True  # once per game: Flash, "Leo is thinking..."
            self.audio.line("leo_thinking", if_quiet=True)
        serial = self._turn_serial
        self.timeline.after(think, lambda: self._leo_glide(serial, choice))
        self.timeline.after(think + glide + 0.25, lambda: self._leo_drop(serial, choice))

    def _leo_glide(self, serial: int, col: int) -> None:
        if serial == self._turn_serial and self.phase is Phase.LEO:
            self.selected_col = col
            self._dirty = True

    def _leo_drop(self, serial: int, col: int) -> None:
        if serial == self._turn_serial and self.phase is Phase.LEO:
            self._execute_drop(col)

    def _on_column(self, col: int) -> None:
        if self.phase is not Phase.TURN:
            return
        self._activated = True
        self.selected_col = col
        if not self.model.can_drop(col):
            friend = self.friends[self.model.current_player]
            friend.try_again()
            self.motion.wobble_col = col
            self.motion.wobble_start = self.clock()
            self.audio.play("boop")
            self._dirty = True
            return
        self._execute_drop(col)

    def _execute_drop(self, col: int) -> bool:
        game = self.model
        result = game.drop(col)
        if not result.ok:
            return False
        self._pending = result
        target_y = self.geometry.cell_center(result.row, col)[1]
        self.motion.drop = DropAnimation(col, result.row, result.player, float(self.geometry.selector_y), float(target_y))
        self.motion.show_selector = False
        self.motion.glow_col = None
        self.phase = Phase.DROPPING
        self.audio.play_drop_slide()
        if self._is_human(result.player):
            self._emit(
                "quattro.token_dropped",
                f"game-{self._game_serial}-move-{len(game.history)}",
                {"stage": game.stage.number, "mode": self.match.mode.value, "column": col, "player": result.player.value},
            )
        self._sync()
        self._dirty = True
        return True

    def _after_drop(self) -> None:
        result = self._pending
        if result is None:
            return
        if result.status is GameStatus.WON:
            self._game_won(result)
            return
        if result.status is GameStatus.DRAW:
            self._game_draw()
            return
        if result.blocked:
            self._block_moment(result)
        self._begin_turn()

    def _block_moment(self, result: DropResult) -> None:
        now = self.clock()
        center = self.geometry.cell_center(result.row, result.col)
        if self._is_human(result.player):
            # The child filled the other friend's winning hole: celebrate the idea.
            self.friends[result.player].correct()
            self.motion.add_fx("star_burst", center, now)
            self.audio.play("pop")
            if self.vs_leo:
                self.audio.line("you_blocked_me")  # Leo, about the child's clever block
        else:
            # Leo stopped the child's row: he points at it, Flash is surprised.
            self.friends[Player.LEO].show("pose_point", 1.6)
            self.friends[Player.FLASH].show("surprised", 1.2)
            self.motion.add_fx("sparkle", center, now)
            self.audio.line("i_stopped_you")  # "I stopped you!"

    def _game_won(self, result: DropResult) -> None:
        self.phase = Phase.CELEBRATING
        self.timeline.clear()
        game = self.model
        winner = game.winner
        self.match.record_game()
        now = self.clock()
        cells = list(game.winning_cells)
        self.motion.win_cells = cells
        self.motion.win_start = now + WIN_LEAD
        self.motion.win_band = self.art.win_band(self.geometry, cells)
        for index, (row, col) in enumerate(cells):
            delay = WIN_LEAD + index * WIN_STEP_SECONDS
            self.motion.add_fx("sparkle", self.geometry.cell_center(row, col), now + delay)
            self.timeline.after(delay, lambda n=index + 1: self.audio.chime(n))
        line_done = WIN_LEAD + len(cells) * WIN_STEP_SECONDS
        self.timeline.after(line_done, lambda: self._cheer(winner))
        child_lost = self.vs_leo and winner is Player.LEO
        self._losses_in_a_row = self._losses_in_a_row + 1 if child_lost else (0 if self.vs_leo else self._losses_in_a_row)
        self._emit(
            "quattro.game_won",
            f"game-{self._game_serial}-won",
            {
                "stage": game.stage.number,
                "mode": self.match.mode.value,
                "winner": winner.value,
                "moves": len(game.history),
            },
        )
        self.timeline.after(line_done + CELEBRATE_HOLD, self._finish_game)
        self._sync()
        self._dirty = True

    def _cheer(self, winner: Player) -> None:
        now = self.clock()
        self.friends[winner].correct()
        loser = winner.opponent
        # A three-disc board names the win ("Three in a row!") instead of the
        # generic reaction, so two lines never stack on the cheer.
        three = self.model.stage.target == 3 and self.audio.line("three_in_row")
        if self.vs_leo and winner is Player.LEO:
            self.friends[loser].try_again()
            if not three:
                self.audio.say("leo", "encourage.retry")
        elif self.vs_leo:
            self.friends[loser].show("happy", 1.6)
            if not three:
                self.audio.say("leo", "praise.general")
        elif not three:
            self.audio.say(winner.cast_id, "celebrate.success")
        self.audio.play("fanfare")
        self.motion.add_fx("confetti", (self.geometry.grid.centerx, self.geometry.frame.top + 40), now)
        plate = plate_rect(winner)
        self.motion.add_fx("star_burst", plate.center, now + 0.1)
        self.motion.score_pop = (winner, now + 0.1)
        self._dirty = True

    def _game_draw(self) -> None:
        self.phase = Phase.CELEBRATING
        self.timeline.clear()
        self.match.record_game()
        now = self.clock()
        for friend in self.friends.values():
            friend.show("pose_wave", DRAW_HOLD)
        self.motion.add_fx("heart_pop", (self.geometry.grid.centerx, self.geometry.frame.top + 30), now)
        self.audio.play("pop")
        if not self.audio.line("draw"):  # "It's a draw!"
            self.audio.say("leo", "encourage.progress")
        self._emit(
            "quattro.game_draw",
            f"game-{self._game_serial}-draw",
            {"stage": self.model.stage.number, "mode": self.match.mode.value, "moves": len(self.model.history)},
        )
        self.timeline.after(DRAW_HOLD, self._finish_game)
        self._sync()
        self._dirty = True

    def _finish_game(self) -> None:
        if self.match.over:
            self._complete_match()
            return
        self.phase = Phase.BETWEEN
        for friend in self.friends.values():
            friend.set_active(False)
        self._note_activity()
        self._sync()
        self.controls.focus_default(None)
        self._dirty = True

    def _on_next(self) -> None:
        if self.phase is not Phase.BETWEEN:
            return
        self._activated = True
        self.audio.play_click()
        self.match.next_game()
        self._begin_game()

    def _on_mode(self, tool_id: str) -> None:
        mode = GameMode(tool_id)
        self._activated = True
        if mode is self.match.mode:
            return
        self.audio.play_click()
        self.progress.save(QuattroProgress(self.ladder, mode))
        self._new_match(mode)

    # -- match end ---------------------------------------------------------------------

    def _complete_match(self) -> None:
        outcome = self.match.outcome
        mode = self.match.mode
        if mode is GameMode.VS_CPU:
            self.ladder = adapt_stage(self.ladder, outcome)
        self.progress.save(QuattroProgress(self.ladder, mode))
        flash, leo = self.match.wins(Player.FLASH), self.match.wins(Player.LEO)
        self._emit(
            "quattro.match_completed",
            f"match-{self.session_id}-{self._game_serial}",
            {
                "stage": self.match.stage.number,
                "mode": mode.value,
                "outcome": outcome.value,
                "flash_wins": flash,
                "leo_wins": leo,
                "next_stage": self.ladder.stage,
            },
        )
        self.timeline.clear()
        if outcome is MatchOutcome.LEO:
            character, title_key = "leo", ("ui.match_leo" if mode is GameMode.VS_CPU else "ui.win_leo")
            stars = flash if mode is GameMode.VS_CPU else leo
        elif outcome is MatchOutcome.FLASH:
            character, title_key, stars = "flash", ("ui.match_won" if mode is GameMode.VS_CPU else "ui.win_flash"), flash
        else:
            character, title_key, stars = "flash", "ui.match_tie", max(flash, leo)
        self.audio.say(character, "celebrate.success" if outcome is not MatchOutcome.TIE else "praise.general")
        if mode is GameMode.VS_CPU and outcome is MatchOutcome.FLASH:
            self.audio.line("you_won_match", after=True)  # Leo, after Flash's cheer
        self.completion = self._completion_for(character)
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text(title_key),
                primary_label=self.resources.text("ui.play_again"),
                body_lines=(self.resources.text("ui.match_score", {"flash": flash, "leo": leo}),),
                achievement_count=stars,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._play_again))
        self.controls.progress.set_progress(len(self.match.results))
        self.phase = Phase.MATCH_OVER
        self._dirty = True

    def _completion_for(self, character: str) -> PygameCompletionScreen:
        screen = self._completions.get(character)
        if screen is None:
            screen = PygameCompletionScreen(
                self.typography,
                width=REFERENCE_WIDTH,
                height=REFERENCE_HEIGHT,
                palette=CompletionPalette(background=SKY_NIGHT),
                scene=CompletionScene(self.kit, character=character, star_total=WINS_FOR_MATCH),
            )
            self._completions[character] = screen
        return screen

    def _play_again(self) -> None:
        self._activated = True
        self._new_match(self.match.mode)

    def _new_match(self, mode: GameMode) -> None:
        if self.phase is Phase.MATCH_OVER:
            self._surfaces.pop_overlay()
            if self.completion is not None:
                self.completion.clear()
            self.completion = None
        self.match = QuattroMatch(stage_for(self.ladder.stage), mode)
        geometry = BoardGeometry.for_stage(self.match.stage)
        if geometry != self.geometry:
            self.geometry = geometry
            self.renderer.geometry = geometry
            self.art.prepare_stage(geometry)
            self.controls.set_geometry(geometry)
        self.controls.select_mode(mode)
        self._begin_game()

    # -- hints ---------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self.phase not in (Phase.TURN, Phase.BETWEEN):
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        point = self._hints.animation_seconds(1.8)
        if self.phase is Phase.BETWEEN:
            self.friends[Player.FLASH].show("pose_point", point)
            self._dirty = True
            return
        player = self.model.current_player
        self.friends[player].show("pose_point", point)
        self.motion.pulse_start = now
        if step >= 2:
            self._glow_suggestion(player, self._hints.animation_seconds(HINT_GLOW_SECONDS))
        if self._is_human(player):
            self.controls.keys.demonstrate()
        self._dirty = True

    def _auto_hint(self, serial: int) -> None:
        if serial != self._turn_serial or self.phase is not Phase.TURN:
            return
        if self._glow_suggestion(self.model.current_player):
            self.friends[self.model.current_player].show("pose_point", 1.6)

    def _glow_suggestion(self, player: Player, seconds: float = HINT_GLOW_SECONDS) -> bool:
        hint = suggest_column(self.model.board, player)
        if hint is None:
            return False
        self.motion.glow_col = hint[0]
        self.motion.glow_until = self.clock() + seconds
        self._dirty = True
        return True

    # -- presentation sync -----------------------------------------------------------------

    def _sync(self) -> None:
        phase = self.phase
        game = self.model
        player = game.current_player
        if phase is Phase.DROPPING and self._pending is not None:
            player = self._pending.player  # the banner follows the falling disc
        if phase is Phase.CELEBRATING or phase is Phase.BETWEEN:
            if game.status is GameStatus.WON:
                key = "ui.win_flash" if game.winner is Player.FLASH else "ui.win_leo"
                icon_player = game.winner
            else:
                key, icon_player = "ui.draw", player
        elif self.vs_leo and player is Player.LEO:
            key, icon_player = "ui.leo_thinking", Player.LEO
        else:
            key = "ui.turn_flash" if player is Player.FLASH else "ui.turn_leo"
            icon_player = player
        self.controls.sync(
            columns_live=phase is Phase.TURN,
            mode_live=(phase is Phase.TURN and game.board.is_empty() and self.match.game_index == 0)
            or phase is Phase.BETWEEN,
            between_games=phase is Phase.BETWEEN,
            games_played=len(self.match.results),
            banner_text=self.resources.text(key),
            banner_icon=self.art.goal_icon(icon_player, game.stage.target, 40),
        )

    def _emit(self, event_id: str, key: str, payload: dict[str, object]) -> None:
        self.events.emit(event_id, f"quattro:{self.session_id}:{key}", payload)


def build_app(
    screen: pygame.Surface,
    locale: str = "it",
    package_root: Path | None = None,
    *,
    progress: ProgressPort | None = None,
    events: EventPort | None = None,
    rng: random.Random | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> QuattroApp:
    """Construct the Activity with injected canvas, kit, art, audio and services."""

    root = package_root or Path(__file__).resolve().parent
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    # UI and spoken character voices use the SAME effective Activity language.
    resources = activity_resources(root, requested_locale=locale)
    rng = rng or random.Random()
    audio = QuattroAudio(locale=resources.context.selected.language, rng=rng)
    return QuattroApp(
        screen=screen,
        canvas=canvas,
        typography=typography,
        resources=resources,
        audio=audio,
        progress=progress if progress is not None else GreiaQuattroProgress(),
        events=events if events is not None else GreiaQuattroEvents(),
        rng=rng,
        clock=clock,
    )


__all__ = ["Phase", "QuattroApp", "Timeline", "build_app"]
