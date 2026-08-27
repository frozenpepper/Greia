"""Earth & Nature section: sky, rain, ocean, tree, rainbow and volcano in one scene."""

from __future__ import annotations

import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring


VOLCANO_RECT = pygame.Rect(645, 278, 190, 185)


class EarthPage(EncyclopediaPage):
    page_id = "earth"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._volcano_hovered = False

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
            self._volcano_hovered = VOLCANO_RECT.collidepoint(point)
            if event.kind is PageInputKind.POINTER_PRESS and self._volcano_hovered:
                self.context.host.open_page("earth.volcano")
            return
        if (
            event.kind is PageInputKind.COMMAND
            and event.command is PageCommand.ACTIVATE
        ):
            self.context.host.open_page("earth.volcano")

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
        pygame.draw.ellipse(surface, (255, 255, 255), (120, 145, 150, 55))
        pygame.draw.ellipse(surface, (255, 255, 255), (230, 150, 110, 45))
        for i in range(8):
            x = 155 + i * 23
            y = 215 + (i % 2) * 7
            pygame.draw.line(surface, (89, 155, 210), (x, y), (x - 5, y + 25), 3)
        pygame.draw.rect(surface, (72, 164, 190), (0, 445, 1024, 155))
        pygame.draw.ellipse(surface, (120, 184, 102), (-90, 380, 870, 170))
        pygame.draw.rect(surface, (120, 83, 51), (185, 310, 28, 145), border_radius=8)
        for cx, cy, radius in ((170, 305, 45), (220, 300, 50), (195, 265, 48)):
            pygame.draw.circle(surface, (89, 166, 83), (cx, cy), radius)
        for n, color in enumerate(
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
                (340 + n * 4, 220 + n * 4, 260 - n * 8, 180 - n * 8),
                0,
                math.pi,
                6,
            )

        volcano = [(655, 445), (735, 300), (815, 445)]
        pygame.draw.polygon(surface, (121, 99, 80), volcano)
        pygame.draw.polygon(surface, (160, 122, 89), [(710, 345), (735, 300), (760, 345)])
        # A tiny glow communicates that the volcano is the active door into the
        # final entry; the actual eruption belongs to earth.volcano.
        glow = 5 + int((math.sin(self._time * 2.4) + 1.0) * 2.0)
        pygame.draw.ellipse(surface, (228, 91, 43), (720, 294, 30, 13))
        pygame.draw.ellipse(surface, (250, 183, 71), (727, 298, 16, glow))
        focus_ring(surface, VOLCANO_RECT, self._volcano_hovered)

        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(930, 565),
            height=150,
            variant="surprised",
            fallback_color=(247, 151, 77),
        )
