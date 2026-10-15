"""Main application loop, lifecycle, and event routing for Quattro Amici in Fila.

Coordinates Pygame ReferenceCanvas, platform lifecycle markers, input routing
(mouse, keyboard, controller), gravity animation, and CPU opponent timing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from greia_platform.activity_api import activity_stop_requested, emit_activity_event, mark_activity_ready
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .quattro_audio import QuattroAudio
    from .quattro_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GameMode,
        GameStatus,
        Player,
    )
    from .quattro_model import QuattroModel
    from .quattro_renderer import DropAnimation, QuattroRenderer
else:
    from quattro_audio import QuattroAudio
    from quattro_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GameMode,
        GameStatus,
        Player,
    )
    from quattro_model import QuattroModel
    from quattro_renderer import DropAnimation, QuattroRenderer


def _is_safe_pointer(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Prevent Activity clicks/hover from operating under trusted Greia chrome."""
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    if any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    ):
        return False
    return True


@dataclass
class QuattroApp:
    """Greia Activity app orchestrating model, presentation, audio, and input."""
    screen: pygame.Surface
    canvas: PygameReferenceCanvas
    renderer: QuattroRenderer
    typography: GreiaTypography
    resources: LocalizedResources
    audio: QuattroAudio
    model: QuattroModel
    selected_col: int = 2
    active_drop: DropAnimation | None = None
    cpu_thinking: bool = False
    cpu_think_timer: float = 0.0
    ready_published: bool = False
    running: bool = True
    last_clack_row: int = -1
    game_sequence: int = 0

    def run(self) -> int:
        """Execute the 60 FPS Activity loop."""
        clock = pygame.time.Clock()
        last_time = time.monotonic()
        self._emit_game_started()

        while self.running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.05, now - last_time)
            last_time = now

            self._process_events()
            self._update(dt)
            self._draw()

            # Present through reference canvas to physical display
            self.canvas.present()
            pygame.display.flip()

            # Signal readiness on the very first presented frame
            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True

            clock.tick(60)

        return 0

    def _process_events(self) -> None:
        """Route input events from keyboard, mouse, and gamepads."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            elif event.type == pygame.MOUSEMOTION:
                if not _is_safe_pointer(self.screen, event.pos):
                    continue
                logical_pos = self.canvas.pointer(event.pos)
                if logical_pos is not None:
                    col = self.renderer.get_column_at_x(self.model, logical_pos[0])
                    if col is not None and col != self.selected_col:
                        self.selected_col = col
                        self.audio.play_hover()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not _is_safe_pointer(self.screen, event.pos):
                    continue
                logical_pos = self.canvas.pointer(event.pos)
                if logical_pos is not None:
                    self._handle_click(logical_pos[0], logical_pos[1])

            elif event.type == pygame.JOYHATMOTION:
                hat_x, _ = event.value
                if hat_x < 0:
                    self._move_selection(-1)
                elif hat_x > 0:
                    self._move_selection(1)

            elif event.type == pygame.JOYBUTTONDOWN:
                # Button 0 = South button (A/Cross)
                if event.button == 0:
                    self._try_drop(self.selected_col)

    def _handle_keydown(self, key: int) -> None:
        """Keyboard input mapping."""
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._move_selection(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._move_selection(1)
        elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_DOWN, pygame.K_s):
            self._try_drop(self.selected_col)
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            diff = key - pygame.K_0
            self._switch_difficulty(diff)
        elif key == pygame.K_m:
            self._toggle_mode()
        elif key == pygame.K_r:
            self._restart_game()

    def _move_selection(self, delta: int) -> None:
        """Move column selector left or right with wrap/clamping."""
        new_col = max(0, min(self.model.board.cols - 1, self.selected_col + delta))
        if new_col != self.selected_col:
            self.selected_col = new_col
            self.audio.play_hover()

    def _handle_click(self, x: float, y: float) -> None:
        """Process clicks on buttons and board columns."""
        # 1. Level buttons (1 to 4) near top right
        btn_y = 26
        btn_h = 42
        if btn_y <= y <= btn_y + btn_h:
            for diff in (1, 2, 3, 4):
                btn_x = 730 + (diff - 1) * 50
                if btn_x <= x <= btn_x + 42:
                    self._switch_difficulty(diff)
                    return

            # Mode toggle button
            mode_x = 936
            if mode_x <= x <= mode_x + 74:
                self._toggle_mode()
                return

        # 2. Play Again button (bottom center on game over)
        if self.model.status != GameStatus.IN_PROGRESS:
            pa_rect = pygame.Rect((REFERENCE_WIDTH - 220) // 2, 535, 220, 50)
            if pa_rect.collidepoint((x, y)):
                self._restart_game()
                return

        # 3. Column drop click on board
        col = self.renderer.get_column_at_x(self.model, x)
        if col is not None:
            self.selected_col = col
            self._try_drop(col)

    def _switch_difficulty(self, diff: int) -> None:
        """Switch difficulty and reset board."""
        if diff != self.model.difficulty:
            self.model.set_difficulty(diff)
            self.active_drop = None
            self.cpu_thinking = False
            self.selected_col = min(self.selected_col, self.model.board.cols - 1)
            self.renderer.invalidate_cache()
            self.audio.play_click()
            self._emit_game_started()

    def _toggle_mode(self) -> None:
        """Toggle between Solo vs Leo and Two Players."""
        new_mode = (
            GameMode.TWO_PLAYERS
            if self.model.mode == GameMode.VS_CPU
            else GameMode.VS_CPU
        )
        self.model.set_mode(new_mode)
        self.active_drop = None
        self.cpu_thinking = False
        self.audio.play_click()
        self._emit_game_started()

    def _restart_game(self) -> None:
        """Restart a new game with current configuration."""
        self.model.reset()
        self.active_drop = None
        self.cpu_thinking = False
        self.audio.play_click()
        self._emit_game_started()

    def _try_drop(self, col: int) -> bool:
        """Initiate token drop if turn and column are legal."""
        # Disallow dropping while animation is playing or game is finished
        if self.active_drop is not None or self.model.status != GameStatus.IN_PROGRESS:
            return False

        # In vs CPU mode, child can only drop on Flash's turn
        if self.model.mode == GameMode.VS_CPU and self.model.current_player != Player.FLASH:
            return False

        return self._execute_drop(col)

    def _execute_drop(self, col: int) -> bool:
        """Execute drop logic and spawn falling animation."""
        if not self.model.can_drop(col):
            return False

        player = self.model.current_player
        success, row = self.model.drop_token(col)
        if not success:
            return False

        move_number = len(self.model.history)
        self._safe_emit(
            "quattro.token_dropped",
            f"game-{self.game_sequence}-move-{move_number}",
            {
                "difficulty": self.model.difficulty,
                "mode": self.model.mode.value,
                "column": col,
                "player": player.value,
            },
        )
        if self.model.status == GameStatus.WON:
            self._safe_emit(
                "quattro.game_won",
                f"game-{self.game_sequence}-won",
                {
                    "difficulty": self.model.difficulty,
                    "mode": self.model.mode.value,
                    "winner": self.model.winner.value,
                    "moves": move_number,
                },
            )
        elif self.model.status == GameStatus.DRAW:
            self._safe_emit(
                "quattro.game_draw",
                f"game-{self.game_sequence}-draw",
                {
                    "difficulty": self.model.difficulty,
                    "mode": self.model.mode.value,
                    "moves": move_number,
                },
            )

        board_rect, cell_size, _ = self.renderer._compute_board_layout(self.model)
        target_y = board_rect.top + row * cell_size + cell_size / 2.0
        start_y = board_rect.top - cell_size * 0.75

        self.active_drop = DropAnimation(
            col=col,
            target_row=row,
            player=player,
            current_y=start_y,
            target_y=target_y,
        )
        self.audio.play_drop_slide()
        return True

    def _emit_game_started(self) -> None:
        self.game_sequence += 1
        self._safe_emit(
            "quattro.game_started",
            f"game-{self.game_sequence}-started",
            {
                "difficulty": self.model.difficulty,
                "mode": self.model.mode.value,
            },
        )

    @staticmethod
    def _safe_emit(
        event_id: str,
        idempotency_key: str,
        payload: dict[str, object],
    ) -> None:
        try:
            emit_activity_event(
                event_id,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        except Exception:
            pass

    def _update(self, dt: float) -> None:
        """Update active animations and CPU opponent decision."""
        # 1. Update falling token animation
        if self.active_drop is not None:
            settled = self.active_drop.update(dt)

            # The clack plays once, on the frame the token reaches its row.
            if self.active_drop.consume_landing():
                self.audio.play_drop_clack()

            if settled:
                # Dropped token has come to rest
                self.active_drop = None
                # Check win reaction
                if self.model.status == GameStatus.WON:
                    board_rect, _, _ = self.renderer._compute_board_layout(self.model)
                    self.renderer.spawn_win_particles(board_rect)
                    self.audio.play_win(self.model.winner == Player.FLASH)

        # 2. CPU opponent thinking and move triggering
        if (
            self.model.mode == GameMode.VS_CPU
            and self.model.current_player == Player.LEO
            and self.model.status == GameStatus.IN_PROGRESS
            and self.active_drop is None
        ):
            if not self.cpu_thinking:
                self.cpu_thinking = True
                # Friendly natural thinking delay (0.5s) so the child sees Leo thinking
                self.cpu_think_timer = 0.5
            else:
                self.cpu_think_timer -= dt
                if self.cpu_think_timer <= 0.0:
                    self.cpu_thinking = False
                    cpu_col = self.model.cpu_choose_move()
                    if cpu_col >= 0:
                        self.selected_col = cpu_col
                        self._execute_drop(cpu_col)

    def _draw(self) -> None:
        """Render frame to the reference canvas."""
        self.renderer.render(
            model=self.model,
            selected_col=self.selected_col,
            active_drop=self.active_drop,
            cpu_thinking=self.cpu_thinking,
        )


def build_app(
    screen: pygame.Surface,
    locale: str = "it",
    package_root: Path | None = None,
) -> QuattroApp:
    """Construct application with injected canvas, renderer, audio, and model."""
    root = package_root or Path(__file__).resolve().parent
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()

    # UI and spoken character voices must use the SAME effective Activity
    # language. A staged-but-unsupported profile locale falls back once here.
    resources = activity_resources(root, requested_locale=locale)
    audio = QuattroAudio(locale=resources.context.selected.language)

    # Storybook renderer
    renderer = QuattroRenderer(
        surface=canvas.surface,
        typography=typography,
        resources=resources,
    )

    # Domain model (starts at Level 2, Solo vs Leo)
    model = QuattroModel(difficulty=2, mode=GameMode.VS_CPU)

    return QuattroApp(
        screen=screen,
        canvas=canvas,
        renderer=renderer,
        typography=typography,
        resources=resources,
        audio=audio,
        model=model,
    )
