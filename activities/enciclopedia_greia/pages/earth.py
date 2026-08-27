"""Earth & Nature section: one landscape with five semantic destinations."""

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
class EarthDestination:
    destination_id: str
    page_id: str
    rect: pygame.Rect


DESTINATIONS = (
    EarthDestination("rain", "earth.rain", pygame.Rect(105, 138, 225, 130)),
    EarthDestination("tree", "earth.tree", pygame.Rect(120, 250, 180, 205)),
    EarthDestination("rainbow", "earth.rainbow", pygame.Rect(340, 210, 270, 205)),
    EarthDestination("volcano", "earth.volcano", pygame.Rect(645, 278, 190, 185)),
    EarthDestination("ocean", "earth.ocean", pygame.Rect(305, 448, 325, 112)),
)


class EarthPage(EncyclopediaPage):
    page_id = "earth"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            self._hovered = next(
                (index for index, item in enumerate(DESTINATIONS) if item.rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_PRESS and self._hovered is not None:
                self._selected = self._hovered
                self._open_selected()
            return

        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command in {PageCommand.LEFT, PageCommand.UP}:
            self._selected = max(0, self._selected - 1)
        elif event.command in {PageCommand.RIGHT, PageCommand.DOWN}:
            self._selected = min(len(DESTINATIONS) - 1, self._selected + 1)
        elif event.command is PageCommand.ACTIVATE:
            self._open_selected()

    def _open_selected(self) -> None:
        self.context.host.open_page(DESTINATIONS[self._selected].page_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((184, 225, 242))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.earth"),
            center=(500, 95),
            size=40,
            color=self.context.palette.ink,
        )
        pygame.draw.circle(surface, (252, 218, 89), (855, 130), 42)

        # Rain cloud and droplets.
        pygame.draw.ellipse(surface, (255, 255, 255), (120, 145, 150, 55))
        pygame.draw.ellipse(surface, (255, 255, 255), (230, 150, 110, 45))
        for index in range(8):
            x = 155 + index * 23
            y = 215 + (index % 2) * 7
            pygame.draw.line(surface, (89, 155, 210), (x, y), (x - 5, y + 25), 3)

        # Ocean and rolling land.
        pygame.draw.rect(surface, (72, 164, 190), (0, 445, 1024, 155))
        for wave_x in range(315, 625, 55):
            pygame.draw.arc(surface, (164, 218, 227), (wave_x, 460, 58, 18), 0.1, math.pi - 0.1, 3)
        pygame.draw.ellipse(surface, (120, 184, 102), (-90, 380, 870, 170))

        # Tree.
        pygame.draw.rect(surface, (120, 83, 51), (185, 310, 28, 145), border_radius=8)
        for cx, cy, radius in ((170, 305, 45), (220, 300, 50), (195, 265, 48)):
            pygame.draw.circle(surface, (89, 166, 83), (cx, cy), radius)

        # Rainbow.
        for index, color in enumerate(
            (
                (221, 84, 91),
                (238, 146, 65),
                (242, 205, 74),
                (92, 177, 98),
                (79, 143, 205),
                (137, 105, 188),
            )
        ):
            pygame.draw.arc(
                surface,
                color,
                (340 + index * 4, 220 + index * 4, 260 - index * 8, 180 - index * 8),
                0,
                math.pi,
                6,
            )

        # Volcano: ambient glow only; eruption behavior belongs to earth.volcano.
        pygame.draw.polygon(surface, (121, 99, 80), [(655, 445), (735, 300), (815, 445)])
        pygame.draw.polygon(surface, (160, 122, 89), [(710, 345), (735, 300), (760, 345)])
        glow = 5 + int((math.sin(self._time * 2.4) + 1.0) * 2.0)
        pygame.draw.ellipse(surface, (228, 91, 43), (720, 294, 30, 13))
        pygame.draw.ellipse(surface, (250, 183, 71), (727, 298, 16, glow))

        # Focus follows the same semantic order used by keyboard/controller.
        for index, item in enumerate(DESTINATIONS):
            active = index == self._selected or index == self._hovered
            focus_ring(surface, item.rect, active)
            if active:
                pygame.draw.circle(surface, (255, 220, 78), (item.rect.right - 14, item.rect.top + 14), 7)

        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(930, 565),
            height=150,
            variant="surprised",
            fallback_color=(247, 151, 77),
        )
