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
    planet_id: str
    label_key: str
    radius_x: int
    radius_y: int
    size: int
    speed: float
    color: tuple[int, int, int]
    phase: float


PLANETS = (
    Planet("mercury", "planet.mercury", 70, 28, 5, 1.25, (175, 164, 146), 0.2),
    Planet("venus", "planet.venus", 100, 40, 7, 0.95, (225, 180, 104), 1.1),
    Planet("earth", "planet.earth", 135, 54, 8, 0.75, (70, 143, 214), 2.0),
    Planet("mars", "planet.mars", 170, 68, 7, 0.61, (194, 101, 70), 2.8),
    Planet("jupiter", "planet.jupiter", 215, 86, 15, 0.38, (207, 163, 118), 3.5),
    Planet("saturn", "planet.saturn", 260, 103, 13, 0.30, (220, 194, 129), 4.1),
    Planet("uranus", "planet.uranus", 300, 119, 10, 0.24, (153, 214, 220), 4.8),
    Planet("neptune", "planet.neptune", 340, 134, 10, 0.20, (82, 116, 201), 5.4),
)

# The section may display the complete Solar System before every detail page is
# authored. The gold open marker appears only on real runtime entries, and this
# explicit mapping grows without subject-specific branches in the engine.
IMPLEMENTED_ENTRY_IDS = {
    "sun": "space.sun",
    "mercury": "space.mercury",
    "venus": "space.venus",
    "saturn": "space.saturn",
}

_TARGET_IDS = ("sun", *(planet.planet_id for planet in PLANETS))
_TARGET_LABEL_KEYS = ("sun.title", *(planet.label_key for planet in PLANETS))


class SpacePage(EncyclopediaPage):
    page_id = "space"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 3  # Earth in the Sun + planet sequence.
        self._target_positions: list[tuple[str, int, int, int]] = []

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.LEFT:
                self._selected = max(0, self._selected - 1)
            elif event.command is PageCommand.RIGHT:
                self._selected = min(len(_TARGET_IDS) - 1, self._selected + 1)
            elif event.command is PageCommand.ACTIVATE:
                self._open_selected()
            return
        if event.kind is PageInputKind.POINTER_PRESS and event.position:
            px, py = event.position
            candidates: list[tuple[float, int]] = []
            for index, (_, x, y, hit_radius) in enumerate(self._target_positions):
                distance = (px - x) ** 2 + (py - y) ** 2
                if distance <= hit_radius**2:
                    candidates.append((distance, index))
            if candidates:
                _, index = min(candidates)
                self._selected = index
                self._open_selected()

    def _open_selected(self) -> None:
        page_id = IMPLEMENTED_ENTRY_IDS.get(_TARGET_IDS[self._selected])
        if page_id is not None:
            self.context.host.open_page(page_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 28, 67))
        for index in range(38):
            x = (index * 83 + 17) % 1010
            y = 80 + ((index * 47) % 480)
            pygame.draw.circle(surface, (225, 231, 248), (x, y), 1 + (index % 2))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.space"),
            center=(500, 100),
            size=40,
            color=(247, 242, 214),
        )

        center = (500, 340)
        self._target_positions = [("sun", center[0], center[1], 34)]
        sun_selected = self._selected == 0
        pygame.draw.circle(surface, (251, 205, 66), center, 27)
        if "sun" in IMPLEMENTED_ENTRY_IDS:
            pygame.draw.circle(surface, (255, 222, 91), (524, 318), 6)
        if sun_selected:
            pygame.draw.circle(surface, (255, 222, 91), center, 36, 3)

        for planet_index, planet in enumerate(PLANETS):
            orbit = pygame.Rect(
                center[0] - planet.radius_x,
                center[1] - planet.radius_y,
                planet.radius_x * 2,
                planet.radius_y * 2,
            )
            pygame.draw.ellipse(surface, (68, 78, 120), orbit, 1)
            angle = self._time * planet.speed + planet.phase
            x = center[0] + int(math.cos(angle) * planet.radius_x)
            y = center[1] + int(math.sin(angle) * planet.radius_y)
            target_index = planet_index + 1
            hit_radius = max(22, planet.size + 10)
            self._target_positions.append((planet.planet_id, x, y, hit_radius))
            pygame.draw.circle(surface, planet.color, (x, y), planet.size)
            if planet.planet_id == "saturn":
                pygame.draw.ellipse(
                    surface,
                    (236, 218, 164),
                    (x - planet.size - 8, y - 5, (planet.size + 8) * 2, 10),
                    2,
                )
            if planet.planet_id in IMPLEMENTED_ENTRY_IDS:
                pygame.draw.circle(
                    surface,
                    (255, 222, 91),
                    (x + planet.size + 6, y - planet.size - 5),
                    4,
                )
            if target_index == self._selected:
                ring_radius = planet.size + 8
                ring = pygame.Rect(
                    x - ring_radius,
                    y - ring_radius,
                    ring_radius * 2,
                    ring_radius * 2,
                )
                pygame.draw.ellipse(surface, (255, 222, 91), ring, 3)

        label_rect = pygame.Rect(350, 500, 300, 55)
        pygame.draw.rect(surface, (248, 244, 222), label_rect, border_radius=20)
        focus_ring(surface, label_rect, True)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text(_TARGET_LABEL_KEYS[self._selected]),
            center=label_rect.center,
            size=22,
            color=(48, 43, 61),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=145,
            variant="surprised",
        )
