"""Pygame lifecycle and input controller for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

import time
from typing import Any

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    mark_activity_ready,
)
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .bosco_audio import BoscoAudio
    from .bosco_content import (
        CAROUSEL_ARROW_RADIUS,
        CAROUSEL_BUTTON_SIZE,
        CAROUSEL_NEXT_X,
        CAROUSEL_PREV_X,
        CAROUSEL_SPACING,
        CAROUSEL_START_X,
        CAROUSEL_Y,
        STORAGE_KEY,
    )
    from .bosco_model import BoscoModel
    from .bosco_renderer import BoscoRenderer
else:
    from bosco_audio import BoscoAudio
    from bosco_content import (
        CAROUSEL_ARROW_RADIUS,
        CAROUSEL_BUTTON_SIZE,
        CAROUSEL_NEXT_X,
        CAROUSEL_PREV_X,
        CAROUSEL_SPACING,
        CAROUSEL_START_X,
        CAROUSEL_Y,
        STORAGE_KEY,
    )
    from bosco_model import BoscoModel
    from bosco_renderer import BoscoRenderer


class BoscoApp:
    """Coordinates lifecycle, pointer inputs, rendering, and persistence."""

    def __init__(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources,
        audio: BoscoAudio,
        storage: Any = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
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
                current = int(
                    data.get("current_number", data.get("highest_number", 1))
                )
                if 1 <= current <= 10:
                    self.model.setup_number(current)
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
                    "current_number": self.model.current_number,
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
                        ref_pos = self.canvas.pointer(pos)
                        if ref_pos is not None:
                            self._handle_click(ref_pos)

            was_pending = self.model.pending_celebration
            self.model.update(dt)

            if was_pending and self.model.celebrating:
                self.audio.play_celebration(self.model.current_number)
                emit_activity_event(
                    "bosco.number_completed",
                    {
                        "number": self.model.current_number,
                        "total": self.model.total_completed,
                    },
                )

            if self.model.auto_advanced:
                self.model.auto_advanced = False
                self.audio.play_tap()

            if self.model.advance_guess_round:
                self.model.advance_guess_round = False
                self.audio.play_ask_number(self.model.guess_target)

            self.renderer.render(self.model, self.anim_time)
            self.canvas.present()
            pygame.display.flip()

            if not self.ready_published:
                mark_activity_ready()
                self.ready_published = True
                self.audio.play_intro()

            now = time.monotonic()
            if self.storage is not None and now - self.last_save_time > 15.0:
                self.last_save_time = now
                self._autosave()

            clock.tick(30)

        self._autosave()
        self.typography.clear()
        return 0

    def _handle_click(self, ref_pos: tuple[float, float]) -> None:
        rx, ry = ref_pos

        # System Home/Back is consumed by Greia before Activity input. Activity
        # code must not recreate or police the protected chrome hitbox here.

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
            hit_radius = CAROUSEL_ARROW_RADIUS + 4
            if (rx - CAROUSEL_PREV_X) ** 2 + (ry - CAROUSEL_Y) ** 2 <= hit_radius**2:
                self.model.prev_number()
                self.audio.play_tap()
                return

            if (rx - CAROUSEL_NEXT_X) ** 2 + (ry - CAROUSEL_Y) ** 2 <= hit_radius**2:
                self.model.next_number()
                self.audio.play_tap()
                return

            half = CAROUSEL_BUTTON_SIZE // 2
            for idx in range(10):
                num = idx + 1
                bx = CAROUSEL_START_X + idx * CAROUSEL_SPACING
                if bx - half <= rx <= bx + half and CAROUSEL_Y - half <= ry <= CAROUSEL_Y + half:
                    self.model.setup_number(num)
                    self.audio.play_tap()
                    return

            outcome, count_num = self.model.handle_tap(rx, ry)
            if outcome == "counted":
                self.audio.play_count_number(count_num)
            elif outcome == "already_counted":
                self.audio.play_tap()

        else:
            if self.model.guess_solved:
                return

            if 260 <= rx <= 720 and 80 <= ry <= 140:
                self.audio.play_ask_number(self.model.guess_target)
                return

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
