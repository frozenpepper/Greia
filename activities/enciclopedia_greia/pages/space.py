"""Space section page: a lightweight continuously orbiting Solar System."""

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
class Planet:
    label_key: str
    radius_x: int
    radius_y: int
    size: int
    speed: float
    color: tuple[int, int, int]
    phase: float


PLANETS = (
    Planet("planet.mercury", 70, 28, 5, 1.25, (175, 164, 146), 0.2),
    Planet("planet.venus", 100, 40, 7, 0.95, (225, 180, 104), 1.1),
    Planet("planet.earth", 135, 54, 8, 0.75, (70, 143, 214), 2.0),
    Planet("planet.mars", 170, 68, 7, 0.61, (194, 101, 70), 2.8),
    Planet("planet.jupiter", 215, 86, 15, 0.38, (207, 163, 118), 3.5),
    Planet("planet.saturn", 260, 103, 13, 0.30, (220, 194, 129), 4.1),
    Planet("planet.uranus", 300, 119, 10, 0.24, (153, 214, 220), 4.8),
    Planet("planet.neptune", 340, 134, 10, 0.20, (82, 116, 201), 5.4),
)


class SpacePage(EncyclopediaPage):
    page_id = "space"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 2
        self._planet_positions: list[tuple[int, int]] = []

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.LEFT:
                self._selected = max(0, self._selected - 1)
            elif event.command is PageCommand.RIGHT:
                self._selected = min(len(PLANETS) - 1, self._selected + 1)
            return
        if event.kind is PageInputKind.POINTER_PRESS and event.position:
            px, py = event.position
            if self._planet_positions:
                distances = [((px - x) ** 2 + (py - y) ** 2, i) for i, (x, y) in enumerate(self._planet_positions)]
                distance, index = min(distances)
                if distance <= 28 ** 2:
                    self._selected = index

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 28, 67))
        for i in range(38):
            x = (i * 83 + 17) % 1010
            y = 80 + ((i * 47) % 480)
            pygame.draw.circle(surface, (225, 231, 248), (x, y), 1 + (i % 2))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.space"),
            center=(500, 100),
            size=40,
            color=(247, 242, 214),
        )
        center = (500, 340)
        pygame.draw.circle(surface, (251, 205, 66), center, 27)
        self._planet_positions = []
        for i, planet in enumerate(PLANETS):
            orbit = pygame.Rect(center[0] - planet.radius_x, center[1] - planet.radius_y, planet.radius_x * 2, planet.radius_y * 2)
            pygame.draw.ellipse(surface, (68, 78, 120), orbit, 1)
            angle = self._time * planet.speed + planet.phase
            x = center[0] + int(math.cos(angle) * planet.radius_x)
            y = center[1] + int(math.sin(angle) * planet.radius_y)
            self._planet_positions.append((x, y))
            pygame.draw.circle(surface, planet.color, (x, y), planet.size)
            if i == self._selected:
                ring = pygame.Rect(x - planet.size - 8, y - planet.size - 8, 2 * (planet.size + 8), 2 * (planet.size + 8))
                pygame.draw.ellipse(surface, (255, 222, 91), ring, 3)
        selected = PLANETS[self._selected]
        label_rect = pygame.Rect(350, 500, 300, 55)
        pygame.draw.rect(surface, (248, 244, 222), label_rect, border_radius=20)
        focus_ring(surface, label_rect, True)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text(selected.label_key),
            center=label_rect.center,
            size=22,
            color=(48, 43, 61),
        )
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=145, variant="surprised")
