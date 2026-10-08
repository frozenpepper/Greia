"""My Time Greia Activity: no trusted system-control or clock-setting authority."""
from __future__ import annotations

import time
from typing import Mapping

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface

if __package__:
    from .time_model import PRESET_MINUTES, TimeExperience, TimeMode
    from .time_renderer import ACTION_BUTTONS, MODE_BUTTONS, PRESET_BUTTONS, TimeRenderer
else:
    from time_model import PRESET_MINUTES, TimeExperience, TimeMode
    from time_renderer import ACTION_BUTTONS, MODE_BUTTONS, PRESET_BUTTONS, TimeRenderer


class TimeActivity:
    """Three small, related tools. All timers end with the Activity session."""

    def __init__(self, screen: pygame.Surface, locale: str,
                 words: Mapping[str, str], model: TimeExperience | None = None) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.model = model if model is not None else TimeExperience()
        self.renderer = TimeRenderer(locale, words)
        self.running = True
        self.ready_published = False
        self.celebrate_until = 0.0
        self.dirty = True

    def _logical_point(self, position: tuple[int, int]) -> tuple[int, int] | None:
        viewport = activity_viewport_for_surface(self.screen)
        x, y = position
        if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
            return None
        if any(r.x <= x < r.right and r.y <= y < r.bottom for r in viewport.protected_regions):
            return None
        point = self.canvas.pointer(position)
        return (int(point[0]), int(point[1])) if point is not None else None

    def press(self, point: tuple[int, int]) -> None:
        for mode, rect in MODE_BUTTONS.items():
            if rect.collidepoint(point):
                self.model.mode = mode
                self.dirty = True
                return
        if self.model.mode is TimeMode.CLOCK:
            if ACTION_BUTTONS["practice"].collidepoint(point):
                self.model.set_practice(not self.model.practice)
            elif self.model.practice and ACTION_BUTTONS["minus"].collidepoint(point):
                self.model.nudge_practice(-15)
            elif self.model.practice and ACTION_BUTTONS["plus"].collidepoint(point):
                self.model.nudge_practice(15)
        else:
            if ACTION_BUTTONS["primary"].collidepoint(point):
                clock = self.model.stopwatch if self.model.mode is TimeMode.STOPWATCH else self.model.timer
                if clock.running:
                    clock.pause()
                else:
                    if self.model.mode is TimeMode.TIMER and self.model.timer.remaining() == 0:
                        self.model.timer.reset()
                    clock.start()
            elif ACTION_BUTTONS["reset"].collidepoint(point):
                clock = self.model.stopwatch if self.model.mode is TimeMode.STOPWATCH else self.model.timer
                clock.reset()
                self.celebrate_until = 0
            elif self.model.mode is TimeMode.TIMER:
                for minutes, rect in zip(PRESET_MINUTES, PRESET_BUTTONS):
                    if rect.collidepoint(point):
                        self.model.timer.set_duration(minutes * 60)
                        self.celebrate_until = 0
                        break
        self.dirty = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self.dirty = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.model.mode = (TimeMode.CLOCK, TimeMode.STOPWATCH, TimeMode.TIMER)[event.key - pygame.K_1]
                self.dirty = True
            elif event.key == pygame.K_SPACE and self.model.mode is not TimeMode.CLOCK:
                self.press(ACTION_BUTTONS["primary"].center)
            elif event.key == pygame.K_r and self.model.mode is not TimeMode.CLOCK:
                self.press(ACTION_BUTTONS["reset"].center)
            elif event.key == pygame.K_UP and self.model.mode is TimeMode.CLOCK:
                self.model.set_practice(True)
                self.model.nudge_practice(15)
                self.dirty = True
            elif event.key == pygame.K_DOWN and self.model.mode is TimeMode.CLOCK:
                self.model.set_practice(True)
                self.model.nudge_practice(-15)
                self.dirty = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            point = self._logical_point(event.pos)
            if point is not None:
                self.press(point)

    def run(self) -> int:
        ticker = pygame.time.Clock()
        next_draw = 0.0
        while self.running and not activity_stop_requested():
            for event in pygame.event.get():
                self.handle_event(event)
            moment = time.monotonic()
            if self.model.timer.consume_completion():
                self.celebrate_until = moment + 3.0
                self.dirty = True
            # Idle clock redraws only once/second; an active elapsed counter
            # uses 10 Hz for a legible visual ring. No per-frame busy repaint
            # when a child is simply looking at a stationary clock.
            active_counter = (
                self.model.mode is TimeMode.STOPWATCH and self.model.stopwatch.running
            ) or (
                self.model.mode is TimeMode.TIMER and self.model.timer.running
            )
            if self.dirty or moment >= next_draw:
                self.renderer.draw(self.canvas.surface, self.model,
                    celebrate=moment < self.celebrate_until)
                self.canvas.present(clear=(247, 241, 226))
                pygame.display.flip()
                if not self.ready_published:
                    mark_activity_ready()
                    self.ready_published = True
                self.dirty = False
                next_draw = moment + (0.1 if active_counter else 1.0)
            ticker.tick(30)
        return 0


__all__ = ["TimeActivity"]
