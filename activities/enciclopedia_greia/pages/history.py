"""Long Ago section: a visual journey backward through five semantic anchors."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring


@dataclass(frozen=True, slots=True)
class HistoryMoment:
    label_key: str
    page_id: str
    color: tuple[int, int, int]


MOMENTS = (
    HistoryMoment("history.dinosaurs", "history.dinosaurs", (115, 178, 94)),
    HistoryMoment("history.fossils", "history.fossils", (184, 145, 94)),
    HistoryMoment("history.mammoth", "history.mammoth", (151, 124, 108)),
    HistoryMoment("history.cave_paintings", "history.cave_paintings", (191, 114, 76)),
    HistoryMoment("history.pyramids", "history.pyramids", (219, 181, 94)),
)


class HistoryPage(EncyclopediaPage):
    page_id = "history"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._rects = tuple(
            pygame.Rect(75 + i * 170, 260, 140, 170)
            for i in range(len(MOMENTS))
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.LEFT:
                self._selected = max(0, self._selected - 1)
            elif event.command is PageCommand.RIGHT:
                self._selected = min(len(MOMENTS) - 1, self._selected + 1)
            elif event.command is PageCommand.ACTIVATE:
                self._open_selected()
            return

        if event.kind is PageInputKind.POINTER_MOVE and event.position:
            point = (int(event.position[0]), int(event.position[1]))
            self._hovered = next(
                (index for index, rect in enumerate(self._rects) if rect.collidepoint(point)),
                None,
            )
            return

        if event.kind is PageInputKind.POINTER_PRESS and event.position:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(self._rects) if rect.collidepoint(point)),
                None,
            )
            if hit is not None:
                self._selected = hit
                self._open_selected()

    def _open_selected(self) -> None:
        self.context.host.open_page(MOMENTS[self._selected].page_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((244, 229, 194))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.history"),
            center=(500, 95),
            size=40,
            color=self.context.palette.ink,
        )
        pygame.draw.line(surface, (130, 94, 61), (95, 470), (880, 470), 8)
        for index, (moment, rect) in enumerate(zip(MOMENTS, self._rects)):
            bob = int(math.sin(self._time * 1.5 + index) * 3)
            body = rect.move(0, bob)
            pygame.draw.rect(surface, (255, 248, 227), body, border_radius=24)
            pygame.draw.rect(surface, moment.color, body, 4, border_radius=24)
            self._draw_moment(surface, index, body, moment.color)
            draw_centered_text(
                surface,
                self.context.typography,
                self.context.resources.text(moment.label_key),
                center=(body.centerx, body.bottom - 22),
                size=17,
                color=self.context.palette.ink,
            )
            focus_ring(surface, body, index == self._selected or index == self._hovered)
            pygame.draw.circle(surface, (130, 94, 61), (body.centerx, 470), 7)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(945, 565),
            height=145,
            variant="default",
        )

    @staticmethod
    def _draw_moment(
        surface: pygame.Surface,
        index: int,
        rect: pygame.Rect,
        color: tuple[int, int, int],
    ) -> None:
        cx, cy = rect.centerx, rect.centery - 20
        if index == 0:
            pygame.draw.ellipse(surface, color, (cx - 40, cy - 15, 80, 36))
            pygame.draw.line(surface, color, (cx + 25, cy - 5), (cx + 55, cy - 35), 12)
            pygame.draw.polygon(surface, color, [(cx - 42, cy - 5), (cx - 70, cy - 35), (cx - 38, cy + 5)])
        elif index == 1:
            pygame.draw.ellipse(surface, color, (cx - 45, cy - 25, 90, 50), 9)
            pygame.draw.arc(surface, (255, 248, 227), (cx - 24, cy - 15, 48, 30), 0, math.tau, 7)
        elif index == 2:
            pygame.draw.ellipse(surface, color, (cx - 42, cy - 20, 84, 50))
            pygame.draw.circle(surface, color, (cx + 35, cy - 22), 26)
            pygame.draw.arc(surface, (238, 224, 190), (cx + 20, cy - 10, 34, 50), 0, math.pi, 4)
        elif index == 3:
            pygame.draw.polygon(surface, color, [(cx - 55, cy + 30), (cx, cy - 45), (cx + 55, cy + 30)])
            pygame.draw.circle(surface, (255, 218, 126), (cx - 10, cy), 10)
            pygame.draw.line(surface, (255, 218, 126), (cx - 20, cy + 20), (cx + 25, cy - 18), 5)
        else:
            pygame.draw.polygon(surface, color, [(cx - 55, cy + 35), (cx, cy - 55), (cx + 55, cy + 35)])
            pygame.draw.line(surface, (255, 248, 227), (cx, cy - 20), (cx, cy + 25), 4)
