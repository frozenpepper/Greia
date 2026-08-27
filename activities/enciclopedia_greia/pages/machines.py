"""Science & Machines section: linked gears and other simple mechanisms."""

from __future__ import annotations

import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring


GEARS_RECT = pygame.Rect(238, 245, 390, 220)


class MachinesPage(EncyclopediaPage):
    page_id = "machines"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._gears_hovered = False

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            self._gears_hovered = GEARS_RECT.collidepoint(point)
            if event.kind is PageInputKind.POINTER_PRESS and self._gears_hovered:
                self.context.host.open_page("machines.gears")
            return
        if (
            event.kind is PageInputKind.COMMAND
            and event.command is PageCommand.ACTIVATE
        ):
            self.context.host.open_page("machines.gears")

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((239, 231, 205))
        pygame.draw.rect(surface, (178, 125, 77), (0, 455, 1024, 145))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.machines"),
            center=(500, 95),
            size=40,
            color=self.context.palette.ink,
        )
        self._gear(surface, (330, 335), 78, 12, self._time, (83, 145, 181))
        self._gear(surface, (470, 335), 56, 10, -self._time * 1.4, (231, 157, 71))
        self._gear(surface, (570, 385), 42, 9, self._time * 1.9, (119, 177, 102))
        focus_ring(surface, GEARS_RECT, self._gears_hovered)

        pygame.draw.arc(surface, (196, 71, 74), (160, 270, 90, 110), math.pi, 2 * math.pi, 18)
        pygame.draw.arc(surface, (91, 119, 183), (160, 270, 90, 110), 0, math.pi, 18)
        pygame.draw.line(surface, (91, 80, 66), (670, 410), (800, 410), 12)
        pygame.draw.line(surface, (91, 80, 66), (690, 410), (730, 325), 8)
        pygame.draw.line(surface, (91, 80, 66), (780, 410), (740, 325), 8)
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(910, 565),
            height=150,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    @staticmethod
    def _gear(
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        teeth: int,
        angle: float,
        color: tuple[int, int, int],
    ) -> None:
        cx, cy = center
        points: list[tuple[int, int]] = []
        for index in range(teeth * 2):
            theta = angle + index * math.pi / teeth
            r = radius if index % 2 == 0 else radius - 13
            points.append((cx + int(math.cos(theta) * r), cy + int(math.sin(theta) * r)))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, (239, 231, 205), center, max(10, radius // 3))
        pygame.draw.circle(surface, (91, 80, 66), center, max(10, radius // 3), 4)
