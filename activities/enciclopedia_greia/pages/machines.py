"""Science & Machines section: linked gears and other simple mechanisms."""

from __future__ import annotations

import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter
else:
    from enciclopedia_engine import EncyclopediaPage, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter


class MachinesPage(EncyclopediaPage):
    page_id = "machines"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._speed = 1.0

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.intro")

    def update(self, dt: float) -> None:
        self._time += dt * self._speed
        self._speed += (1.0 - self._speed) * min(1.0, dt * 2.0)

    def handle_input(self, event: PageInput) -> None:
        if event.kind is not PageInputKind.POINTER_PRESS or event.position is None:
            return
        x, y = event.position
        if 180 <= x <= 720 and 190 <= y <= 500:
            self._speed = 2.6

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((239, 231, 205))
        pygame.draw.rect(surface, (178, 125, 77), (0, 455, 1024, 145))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("section.machines"), center=(500, 95), size=40, color=self.context.palette.ink)
        self._gear(surface, (330, 335), 78, 12, self._time, (83, 145, 181))
        self._gear(surface, (470, 335), 56, 10, -self._time * 1.4, (231, 157, 71))
        self._gear(surface, (570, 385), 42, 9, self._time * 1.9, (119, 177, 102))
        pygame.draw.arc(surface, (196, 71, 74), (160, 270, 90, 110), math.pi, 2 * math.pi, 18)
        pygame.draw.arc(surface, (91, 119, 183), (160, 270, 90, 110), 0, math.pi, 18)
        pygame.draw.line(surface, (91, 80, 66), (670, 410), (800, 410), 12)
        pygame.draw.line(surface, (91, 80, 66), (690, 410), (730, 325), 8)
        pygame.draw.line(surface, (91, 80, 66), (780, 410), (740, 325), 8)
        draw_presenter(surface, self.context.visuals, "dani", position=(910, 565), height=150, variant="happy", fallback_color=(101, 171, 211))

    @staticmethod
    def _gear(surface: pygame.Surface, center: tuple[int, int], radius: int, teeth: int, angle: float, color: tuple[int, int, int]) -> None:
        cx, cy = center
        points = []
        for i in range(teeth * 2):
            a = angle + i * math.pi / teeth
            r = radius if i % 2 == 0 else radius - 13
            points.append((cx + int(math.cos(a) * r), cy + int(math.sin(a) * r)))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, (239, 231, 205), center, max(10, radius // 3))
        pygame.draw.circle(surface, (91, 80, 66), center, max(10, radius // 3), 4)
