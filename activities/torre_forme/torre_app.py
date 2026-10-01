from __future__ import annotations

"""Lifecycle coordinator and event loop for La Torre delle Forme.

Coordinates Greia platform lifecycle, input routing, reference canvas presentation,
renderer updates, audio playback, and READY announcement after the first presented frame.
"""

from pathlib import Path
import random
import time
import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_storage,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .torre_audio import TorreAudio
    from .torre_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        TowerMode,
    )
    from .torre_model import StepOutcome, TorreModel
    from .torre_renderer import TorreRenderer
else:
    from torre_audio import TorreAudio
    from torre_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        TowerMode,
    )
    from torre_model import StepOutcome, TorreModel
    from torre_renderer import TorreRenderer


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Verify pointer is inside surface and outside protected top-left system chrome."""
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class TorreApp:
    """Greia lifecycle and interaction coordinator for Torre delle Forme."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas | None = None,
        metrics: ChildUiMetrics | None = None,
        typography: GreiaTypography | None = None,
        resources: LocalizedResources | None = None,
        model: TorreModel | None = None,
        renderer: TorreRenderer | None = None,
        audio: TorreAudio | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._screen = screen
        self._canvas = canvas or PygameReferenceCanvas(screen)
        self._metrics = metrics or ChildUiMetrics.for_size(*screen.get_size())
        self._typography = typography or GreiaTypography()
        self._resources = resources
        self._rng = rng or random.Random()

        # Storage & persistence
        self._storage = get_storage()
        saved: dict | None = None
        try:
            raw = self._storage.kv_get(STORAGE_KEY) if self._storage else {}
            saved = raw if isinstance(raw, dict) else {}
        except Exception:
            saved = {}

        total_stars = 0
        if isinstance(saved, dict):
            val = saved.get("stars", 0)
            if isinstance(val, int) and val >= 0:
                total_stars = val

        self._model = model or TorreModel(
            mode=TowerMode.FREE_BUILD,
            total_stars=total_stars,
            rng=self._rng,
        )
        self._renderer = renderer or TorreRenderer(self._typography, self._resources)
        self._audio = audio or TorreAudio()

        self._running = True
        self._ready_published = False
        self._clock = pygame.time.Clock()
        self._start_time = time.time()

    def run(self) -> int:
        while self._running and not activity_stop_requested():
            dt = self._clock.tick(60) / 1000.0
            elapsed = time.time() - self._start_time
            now = time.time()

            # 1. Process Events
            for event in pygame.event.get():
                self._handle_event(event)

            # 2. Step Model
            time_outcome = self._model.step_time(dt)
            self._process_outcome(time_outcome)

            # 3. Update Particles
            self._renderer.update_particles(dt)

            # 4. Render Scene onto Reference Canvas
            self._renderer.draw(self._canvas.surface, self._model, elapsed, now)

            # 5. Present Frame to Physical Display
            self._canvas.present()
            pygame.display.flip()

            # 6. Publish Activity Ready after first presented frame
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
            elif event.key == pygame.K_LEFT:
                if self._model.move_left():
                    self._audio.play("rotate")
            elif event.key == pygame.K_RIGHT:
                if self._model.move_right():
                    self._audio.play("rotate")
            elif event.key == pygame.K_UP:
                if self._model.rotate_active():
                    self._audio.play("rotate")
            elif event.key == pygame.K_DOWN:
                outcome = self._model.drop_down()
                self._process_outcome(outcome)
            elif event.key == pygame.K_SPACE:
                outcome = self._model.hard_drop()
                self._process_outcome(outcome)
            elif event.key == pygame.K_1:
                self._model.set_mode(TowerMode.FREE_BUILD)
                self._audio.play("clack")
            elif event.key == pygame.K_2:
                self._model.set_mode(TowerMode.SLOW_FALL)
                self._audio.play("clack")
            elif event.key == pygame.K_3:
                self._model.set_mode(TowerMode.TOWER_CHALLENGE)
                self._audio.play("clack")
        elif event.type == pygame.VIDEORESIZE:
            self._screen = pygame.display.get_surface() or self._screen
            self._metrics = ChildUiMetrics.for_size(*self._screen.get_size())
            self._canvas = PygameReferenceCanvas(self._screen)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_pointer(event.pos)
        # Controller handling
        elif event.type == pygame.JOYBUTTONDOWN:
            self._handle_joy_button(event.button)
        elif event.type == pygame.JOYHATMOTION:
            self._handle_joy_hat(event.value)

    def _handle_joy_button(self, button: int) -> None:
        # South button: Drop/Hard drop, North/West: Rotate
        if button in (0, 1):  # A / B button
            if self._model.is_celebrating:
                self._model.restart_after_celebration()
                self._audio.play("clack")
            else:
                outcome = self._model.drop_down()
                self._process_outcome(outcome)
        elif button in (2, 3):  # X / Y button
            if self._model.rotate_active():
                self._audio.play("rotate")

    def _handle_joy_hat(self, value: tuple[int, int]) -> None:
        hat_x, hat_y = value
        if hat_x < 0:
            if self._model.move_left():
                self._audio.play("rotate")
        elif hat_x > 0:
            if self._model.move_right():
                self._audio.play("rotate")
        if hat_y > 0:
            if self._model.rotate_active():
                self._audio.play("rotate")
        elif hat_y < 0:
            outcome = self._model.drop_down()
            self._process_outcome(outcome)

    def _handle_pointer(self, screen_pos: tuple[int, int]) -> None:
        if not _is_safe_point(self._screen, screen_pos):
            return
        pointer = self._canvas.pointer(screen_pos)
        if pointer is None:
            return
        px, py = int(pointer[0]), int(pointer[1])
        point = (px, py)

        # 1. If Celebrating: check Replay button
        if self._model.is_celebrating:
            if self._renderer.replay_button_rect.collidepoint(point):
                self._model.restart_after_celebration()
                self._audio.play("clack")
            return

        # 2. Mode Tabs
        if self._renderer.mode_free_rect.collidepoint(point):
            self._model.set_mode(TowerMode.FREE_BUILD)
            self._audio.play("clack")
            return
        elif self._renderer.mode_slow_rect.collidepoint(point):
            self._model.set_mode(TowerMode.SLOW_FALL)
            self._audio.play("clack")
            return
        elif self._renderer.mode_chal_rect.collidepoint(point):
            self._model.set_mode(TowerMode.TOWER_CHALLENGE)
            self._audio.play("clack")
            return

        # 3. Mode 1 (Free Build) Controls
        if self._model.mode == TowerMode.FREE_BUILD:
            # Shelf slots
            for idx, rect in enumerate(self._renderer.shelf_rects):
                if rect.collidepoint(point):
                    self._model.select_shelf_shape(idx)
                    self._audio.play("clack")
                    return
            # New Shapes button
            if self._renderer.new_shapes_rect.collidepoint(point):
                self._model._refresh_shelf()
                self._audio.play("clack")
                return
            # Tower Grid click -> place selected shape
            grid_coord = self._renderer.hit_test_grid(point)
            if grid_coord is not None:
                col, row = grid_coord
                outcome = self._model.place_free_shape(col, row)
                self._process_outcome(outcome)
                return

        # 4. Modes 2 & 3 (Falling Modes) Steering Buttons
        else:
            if self._model.mode == TowerMode.TOWER_CHALLENGE:
                if self._renderer.rotate_button_rect.collidepoint(point):
                    if self._model.rotate_active():
                        self._audio.play("rotate")
                    return
            if self._renderer.left_button_rect.collidepoint(point):
                if self._model.move_left():
                    self._audio.play("rotate")
                return
            elif self._renderer.right_button_rect.collidepoint(point):
                if self._model.move_right():
                    self._audio.play("rotate")
                return
            elif self._renderer.down_button_rect.collidepoint(point):
                outcome = self._model.drop_down()
                self._process_outcome(outcome)
                return

    def _process_outcome(self, outcome: StepOutcome) -> None:
        # Audio playback
        for cue in outcome.audio_cues:
            self._audio.play(cue)

        # Particle effects
        if outcome.snap_coords:
            for cx, cy in outcome.snap_coords:
                from .torre_content import CELL_SIZE, TOWER_X, TOWER_Y
                px = TOWER_X + cx * CELL_SIZE + CELL_SIZE // 2
                py = TOWER_Y + cy * CELL_SIZE + CELL_SIZE // 2
                self._renderer.spawn_particles(px, py, (254, 240, 138), count=5)

        if outcome.cleared_coords:
            for cx, cy in outcome.cleared_coords:
                from .torre_content import CELL_SIZE, TOWER_X, TOWER_Y
                px = TOWER_X + cx * CELL_SIZE + CELL_SIZE // 2
                py = TOWER_Y + cy * CELL_SIZE + CELL_SIZE // 2
                self._renderer.spawn_particles(
                    px, py, (250, 204, 21), count=6, size_range=(4.0, 9.0), life=1.1
                )

        if outcome.lines_count > 0:
            if self._storage is not None:
                try:
                    self._storage.kv_set(STORAGE_KEY, {"stars": self._model.total_stars})
                except Exception:
                    pass
            try:
                emit_activity_event(
                    "tower.line_cleared",
                    {"lines": outcome.lines_count, "stars": self._model.total_stars},
                )
            except Exception:
                pass

        if outcome.celebration_triggered:
            # Burst fireworks / confetti
            for _ in range(4):
                bx = random.uniform(260, 560)
                by = random.uniform(120, 300)
                color = random.choice([
                    (250, 204, 21),
                    (239, 68, 68),
                    (59, 130, 246),
                    (34, 197, 94),
                    (168, 85, 247),
                ])
                self._renderer.spawn_particles(
                    bx, by, color, count=16, vx_range=(-5, 5), vy_range=(-6, 1), size_range=(5, 10), life=1.5
                )
            if self._storage is not None:
                try:
                    self._storage.kv_set(STORAGE_KEY, {"stars": self._model.total_stars})
                except Exception:
                    pass
            try:
                emit_activity_event(
                    "tower.celebration_reached",
                    {"height": self._model.current_height, "stars": self._model.total_stars},
                )
            except Exception:
                pass
