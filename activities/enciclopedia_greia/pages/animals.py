"""Animals section page: one lively habitat collage with six planned subjects."""

from __future__ import annotations

import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


ANIMALS = (
    ("lion", "animal.lion"),
    ("elephant", "animal.elephant"),
    ("octopus", "animal.octopus"),
    ("bee", "animal.bee"),
    ("penguin", "animal.penguin"),
    ("frog", "animal.frog"),
)


class AnimalsPage(EncyclopediaPage):
    page_id = "animals"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._rects = tuple(
            pygame.Rect(95 + (i % 3) * 240, 200 + (i // 3) * 150, 190, 120)
            for i in range(len(ANIMALS))
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._rects) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
            return
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.ACTIVATE:
                return
            self._selected = grid_step(self._selected, event.command, columns=3, count=len(ANIMALS))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((205, 236, 242))
        pygame.draw.circle(surface, (255, 230, 113), (875, 125), 42)
        pygame.draw.ellipse(surface, (124, 188, 113), (-50, 385, 1120, 250))
        pygame.draw.rect(surface, (81, 161, 184), (0, 455, 1024, 145))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.animals"),
            center=(505, 110),
            size=40,
            color=self.context.palette.ink,
        )

        for i, ((animal_id, label_key), rect) in enumerate(zip(ANIMALS, self._rects)):
            active = i == self._selected or i == self._hovered
            pygame.draw.rect(surface, (255, 252, 242), rect, border_radius=24)
            pygame.draw.rect(surface, (81, 136, 89), rect, 4, border_radius=24)
            self._draw_animal(surface, animal_id, rect, i)
            draw_centered_text(
                surface,
                self.context.typography,
                self.context.resources.text(label_key),
                center=(rect.centerx, rect.bottom - 18),
                size=19,
                color=self.context.palette.ink,
            )
            focus_ring(surface, rect, active and i == self._selected)

        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(930, 565),
            height=150,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_animal(self, surface: pygame.Surface, animal_id: str, rect: pygame.Rect, index: int) -> None:
        cx, cy = rect.centerx, rect.centery - 10
        bob = int(math.sin(self._time * 2.0 + index) * 3)
        cy += bob
        ink = (74, 55, 42)
        if animal_id == "lion":
            pygame.draw.circle(surface, (194, 122, 58), (cx, cy), 34)
            pygame.draw.circle(surface, (239, 177, 77), (cx, cy), 24)
        elif animal_id == "elephant":
            pygame.draw.circle(surface, (151, 163, 174), (cx, cy), 30)
            pygame.draw.circle(surface, (151, 163, 174), (cx - 25, cy), 18)
            pygame.draw.circle(surface, (151, 163, 174), (cx + 25, cy), 18)
            pygame.draw.line(surface, (151, 163, 174), (cx + 8, cy + 10), (cx + 26, cy + 35), 12)
        elif animal_id == "octopus":
            pygame.draw.circle(surface, (183, 103, 173), (cx, cy - 5), 28)
            for dx in (-24, -12, 0, 12, 24):
                pygame.draw.arc(surface, (183, 103, 173), (cx + dx - 14, cy + 8, 28, 35), 0, math.pi, 5)
        elif animal_id == "bee":
            pygame.draw.ellipse(surface, (247, 204, 63), (cx - 30, cy - 18, 60, 36))
            for x in (cx - 14, cx + 5):
                pygame.draw.line(surface, ink, (x, cy - 15), (x, cy + 15), 5)
            pygame.draw.ellipse(surface, (213, 238, 246), (cx - 28, cy - 40, 24, 25))
            pygame.draw.ellipse(surface, (213, 238, 246), (cx + 3, cy - 40, 24, 25))
        elif animal_id == "penguin":
            pygame.draw.ellipse(surface, (48, 57, 69), (cx - 25, cy - 36, 50, 72))
            pygame.draw.ellipse(surface, (245, 245, 236), (cx - 16, cy - 10, 32, 40))
            pygame.draw.polygon(surface, (241, 170, 60), [(cx, cy - 5), (cx + 14, cy), (cx, cy + 5)])
        else:
            pygame.draw.ellipse(surface, (100, 177, 91), (cx - 30, cy - 20, 60, 40))
            pygame.draw.circle(surface, (100, 177, 91), (cx - 20, cy - 23), 12)
            pygame.draw.circle(surface, (100, 177, 91), (cx + 20, cy - 23), 12)
        pygame.draw.circle(surface, ink, (cx - 8, cy - 6), 3)
        pygame.draw.circle(surface, ink, (cx + 8, cy - 6), 3)
