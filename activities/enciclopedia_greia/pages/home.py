"""Home page: six living visual worlds, not a text-heavy menu."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class Portal:
    page_id: str
    label_key: str
    color: tuple[int, int, int]
    symbol: str


PORTALS = (
    Portal("animals", "section.animals", (116, 187, 104), "paw"),
    Portal("space", "section.space", (83, 102, 176), "space"),
    Portal("earth", "section.earth", (83, 177, 183), "earth"),
    Portal("body", "section.body", (235, 139, 155), "heart"),
    Portal("machines", "section.machines", (232, 174, 83), "gear"),
    Portal("history", "section.history", (175, 132, 92), "history"),
)


class HomePage(EncyclopediaPage):
    page_id = "home"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._selected = 0
        self._hovered: int | None = None
        self._time = 0.0
        self._rects = self._portal_rects()

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.home.welcome")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS} and event.position:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._rects) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self.context.host.open_page(PORTALS[hit].page_id)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self.context.host.open_page(PORTALS[self._selected].page_id)
            return
        self._selected = grid_step(self._selected, event.command, columns=3, count=len(PORTALS))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((242, 248, 239))
        pygame.draw.circle(surface, (255, 238, 155), (900, 100), 58)
        pygame.draw.ellipse(surface, (192, 224, 173), (-80, 425, 1180, 260))
        pygame.draw.ellipse(surface, (142, 199, 151), (-100, 500, 1220, 190))

        title = self.context.resources.text("home.title")
        draw_centered_text(
            surface,
            self.context.typography,
            title,
            center=(510, 92),
            size=42,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )

        for index, (portal, rect) in enumerate(zip(PORTALS, self._rects)):
            pulse = 4 if index in {self._selected, self._hovered} else 0
            body = rect.inflate(pulse, pulse)
            pygame.draw.rect(surface, (255, 252, 242), body, border_radius=26)
            pygame.draw.rect(surface, portal.color, body, 5, border_radius=26)
            self._draw_symbol(surface, portal.symbol, body, portal.color, index)
            draw_centered_text(
                surface,
                self.context.typography,
                self.context.resources.text(portal.label_key),
                center=(body.centerx, body.bottom - 25),
                size=22,
                color=self.context.palette.ink,
                role=FontRole.CONTROL,
            )
            focus_ring(surface, body, index == self._selected)

        bob = int(round(math.sin(self._time * 2.0) * 4))
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(935, 560 + bob),
            height=155,
            variant="happy",
        )

    @staticmethod
    def _portal_rects() -> tuple[pygame.Rect, ...]:
        rects: list[pygame.Rect] = []
        for row in range(2):
            for col in range(3):
                rects.append(pygame.Rect(90 + col * 245, 145 + row * 190, 205, 160))
        return tuple(rects)

    def _draw_symbol(
        self,
        surface: pygame.Surface,
        symbol: str,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        index: int,
    ) -> None:
        cx, cy = rect.centerx, rect.centery - 18
        t = self._time + index * 0.7
        if symbol == "paw":
            pygame.draw.circle(surface, color, (cx, cy + 8), 24)
            for dx, dy in ((-28, -22), (-10, -32), (12, -32), (30, -18)):
                pygame.draw.circle(surface, color, (cx + dx, cy + dy), 10)
        elif symbol == "space":
            pygame.draw.circle(surface, (247, 208, 75), (cx, cy), 18)
            angle = t * 0.7
            px = cx + int(math.cos(angle) * 48)
            py = cy + int(math.sin(angle) * 20)
            pygame.draw.ellipse(surface, color, (cx - 52, cy - 24, 104, 48), 2)
            pygame.draw.circle(surface, (104, 155, 219), (px, py), 9)
        elif symbol == "earth":
            pygame.draw.circle(surface, (81, 161, 207), (cx, cy), 36)
            pygame.draw.ellipse(surface, (94, 179, 104), (cx - 28, cy - 16, 28, 22))
            pygame.draw.ellipse(surface, (94, 179, 104), (cx + 2, cy + 3, 25, 20))
        elif symbol == "heart":
            points = [(cx, cy + 34), (cx - 38, cy - 5), (cx - 28, cy - 31), (cx, cy - 13), (cx + 28, cy - 31), (cx + 38, cy - 5)]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.circle(surface, color, (cx - 18, cy - 12), 22)
            pygame.draw.circle(surface, color, (cx + 18, cy - 12), 22)
        elif symbol == "gear":
            pygame.draw.circle(surface, color, (cx, cy), 38, 9)
            pygame.draw.circle(surface, (255, 252, 242), (cx, cy), 12)
            for n in range(8):
                a = t * 0.2 + n * math.pi / 4
                x = cx + int(math.cos(a) * 43)
                y = cy + int(math.sin(a) * 43)
                pygame.draw.rect(surface, color, (x - 6, y - 6, 12, 12), border_radius=3)
        else:
            pygame.draw.line(surface, color, (cx - 45, cy + 28), (cx + 45, cy + 28), 6)
            for dx, height in ((-34, 22), (-12, 36), (12, 52), (36, 68)):
                pygame.draw.line(surface, color, (cx + dx, cy + 28), (cx + dx, cy + 28 - height), 6)
