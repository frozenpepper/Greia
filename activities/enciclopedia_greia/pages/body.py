"""My Body section: friendly schematic with visible heart and breathing loop."""

from __future__ import annotations

import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter
else:
    from enciclopedia_engine import EncyclopediaPage, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter


class BodyPage(EncyclopediaPage):
    page_id = "body"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._pulse_boost = 0.0

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._pulse_boost = max(0.0, self._pulse_boost - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.kind is not PageInputKind.POINTER_PRESS or event.position is None:
            return
        x, y = event.position
        if 440 <= x <= 580 and 245 <= y <= 390:
            self._pulse_boost = 1.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((249, 232, 227))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("section.body"), center=(500, 95), size=40, color=self.context.palette.ink)
        skin = (234, 184, 151)
        pygame.draw.circle(surface, skin, (510, 180), 52)
        pygame.draw.rect(surface, skin, (445, 225, 130, 220), border_radius=55)
        pygame.draw.line(surface, skin, (455, 255), (380, 405), 28)
        pygame.draw.line(surface, skin, (565, 255), (640, 405), 28)
        pygame.draw.line(surface, skin, (478, 430), (450, 545), 32)
        pygame.draw.line(surface, skin, (542, 430), (570, 545), 32)
        breath = 1.0 + 0.08 * math.sin(self._time * 1.6)
        lung_w = int(42 * breath)
        pygame.draw.ellipse(surface, (226, 154, 161), (480 - lung_w, 260, lung_w, 90))
        pygame.draw.ellipse(surface, (226, 154, 161), (510, 260, lung_w, 90))
        beat = 1.0 + (0.10 + 0.12 * self._pulse_boost) * max(0.0, math.sin(self._time * 6.0))
        heart_size = int(27 * beat)
        hx, hy = 510, 330
        pygame.draw.circle(surface, (203, 70, 82), (hx - heart_size // 3, hy), heart_size // 2)
        pygame.draw.circle(surface, (203, 70, 82), (hx + heart_size // 3, hy), heart_size // 2)
        pygame.draw.polygon(surface, (203, 70, 82), [(hx - heart_size, hy), (hx + heart_size, hy), (hx, hy + heart_size * 2)])
        draw_presenter(surface, self.context.visuals, "lilli", position=(900, 565), height=155, variant="happy", fallback_color=(229, 137, 183))
