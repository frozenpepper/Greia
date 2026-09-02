"""Pygame lifecycle and input controller for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .bosco_audio import BoscoAudio
    from .bosco_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .bosco_model import BoscoModel
    from .bosco_renderer import BoscoRenderer
else:
    from bosco_audio import BoscoAudio
    from bosco_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from bosco_model import BoscoModel
    from bosco_renderer import BoscoRenderer


@dataclass
class BoscoStorageState:
    total_completed: int
    highest_number: int


class BoscoApp:
    """Coordinates lifecycle, pointer inputs, rendering, and persistence."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        metrics: ChildUiMetrics,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: BoscoAudio,
        storage: Any = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.metrics = metrics
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.storage = storage

        self.model = BoscoModel()
        self.renderer = BoscoRenderer(canvas, typography, resources)
        self.ready_published = False
        self.anim_time = 0.0
        self.last_save_time = time.monotonic()
        self._load_saved_state()

    def _load_saved_state(self) -> None:
        if self.storage is None:
            return
        try:
            data = self.storage.kv_get(STORAGE_KEY)
            if isinstance(data, dict):
                self.model.total_completed = int(data.get("total_completed", 0))
                highest = int(data.get("highest_number", 1))
                if 1 <= highest <= 10:
                    self.model.setup_number(highest)
        except Exception:
            pass

    def _autosave(self) -> None:
        if self.storage is None:
            return
        try:
            self.storage.kv_set(
                STORAGE_KEY,
                {
                    "total_completed": self.model.total_completed,
                    "highest_number": self.model.current_number,
                },
            )
        except Exception:
            pass

    def run(self) -> int:
        clock = pygame.time.Clock()

        while not activity_stop_requested():
            dt = 0.033
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._autosave()
                    return 0
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._autosave()
                        return 0
                    elif event.key == pygame.K_RIGHT:
                        self.model.next_number()
                    elif event.key == pygame.K_LEFT:
                        self.model.prev_number()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    pos = getattr(event, "pos", None)
                    if pos is None and hasattr(event, "x") and hasattr(event, "y"):
                        sw, sh = self.screen.get_size()
                        pos = (int(event.x * sw), int(event.y * sh))
                    if pos is not None:
                        ref_pos = self._screen_to_reference(pos)
                        self._handle_click(ref_pos)

            # Advance model state
            was_pending = self.model.pending_celebration
            self.model.update(dt)

            # Check if celebration just triggered
            if was_pending and self.model.celebrating:
                # Repeat final number loud and clear, then celebrate!
                self.audio.play_celebration(self.model.current_number)
                emit_activity_event(
                    "bosco.number_completed",
                    {"number": self.model.current_number, "total": self.model.total_completed},
                )

            # Auto-advance to next number in count mode
            if self.model.auto_advanced:
                self.model.auto_advanced = False
                self.audio.play_tap()

            # Next challenge question in guess mode
            if self.model.advance_guess_round:
                self.model.advance_guess_round = False
                self.audio.play_ask_number(self.model.guess_target)

            # Render
            self.renderer.render(self.model, self.anim_time)
            self.canvas.present()
            pygame.display.flip()

            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
                self.audio.play_intro()

            # Periodic autosave
            now = time.monotonic()
            if self.storage is not None and now - self.last_save_time > 15.0:
                self.last_save_time = now
                self._autosave()

            clock.tick(30)

        self._autosave()
        self.typography.clear()
        return 0

    def _screen_to_reference(self, pos: tuple[int, int]) -> tuple[float, float]:
        sw, sh = self.screen.get_size()
        scale_x = REFERENCE_WIDTH / max(1, sw)
        scale_y = REFERENCE_HEIGHT / max(1, sh)
        return (pos[0] * scale_x, pos[1] * scale_y)

    def _handle_click(self, ref_pos: tuple[float, float]) -> None:
        rx, ry = ref_pos
        # 1. Protect Greia Home area (88x88 at top-left)
        if rx <= 88 and ry <= 88:
            return

        # 2. Mode toggle button at top-right (870..1005, 30..75)
        if 870 <= rx <= 1005 and 30 <= ry <= 75:
            if self.model.mode == "count":
                self.model.mode = "guess"
                self.model.setup_guess_round()
                self.audio.play_ask_number(self.model.guess_target)
            else:
                self.model.mode = "count"
                self.model.setup_number(self.model.current_number)
                self.audio.play_intro()
            return

        if self.model.mode == "count":
            # 3. Number carousel clicks
            # Left arrow: circle at (100, 52), r=24
            if (rx - 100) ** 2 + (ry - 52) ** 2 <= 28 ** 2:
                self.model.prev_number()
                self.audio.play_tap()
                return

            # Right arrow: circle at (825, 52), r=24
            if (rx - 825) ** 2 + (ry - 52) ** 2 <= 28 ** 2:
                self.model.next_number()
                self.audio.play_tap()
                return

            # Number pills 1 to 10
            start_x = 150
            spacing = 65
            for idx in range(10):
                num = idx + 1
                bx = start_x + idx * spacing
                if bx - 26 <= rx <= bx + 26 and 52 - 26 <= ry <= 52 + 26:
                    self.model.setup_number(num)
                    self.audio.play_tap()
                    return

            # 4. Item taps in clearing
            outcome, count_num = self.model.handle_tap(rx, ry)
            if outcome == "counted":
                self.audio.play_count_number(count_num)
            elif outcome == "already_counted":
                self.audio.play_tap()

        else:
            # Guess mode: ignore clicks while winner card is celebrating transition
            if self.model.guess_solved:
                return

            # Question banner tap repeats the spoken prompt
            if 260 <= rx <= 720 and 80 <= ry <= 140:
                self.audio.play_ask_number(self.model.guess_target)
                return

            # Guess mode card clicks
            card_xs = [280, 490, 700]
            for idx, num in enumerate(self.model.guess_options):
                cx = card_xs[idx]
                if cx - 75 <= rx <= cx + 75 and 280 - 90 <= ry <= 280 + 90:
                    correct = self.model.handle_guess_tap(num)
                    if correct:
                        self.audio.play_well_done()
                        emit_activity_event(
                            "bosco.challenge_completed",
                            {"target": num, "total": self.model.total_completed},
                        )
                    else:
                        self.audio.play_try_again()
                    return
