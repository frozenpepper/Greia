"""Space section: a live Solar System inside an authored observatory."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import draw_authored_scene
    from .common import draw_centered_text, draw_presenter, focus_ring
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import draw_authored_scene
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

IMPLEMENTED_ENTRY_IDS = {
    "sun": "space.sun",
    "mercury": "space.mercury",
    "venus": "space.venus",
    "earth": "space.earth",
    "moon": "space.moon",
    "mars": "space.mars",
    "jupiter": "space.jupiter",
    "saturn": "space.saturn",
    "uranus": "space.uranus",
    "neptune": "space.neptune",
}

_TARGET_IDS = (
    "sun",
    "mercury",
    "venus",
    "earth",
    "moon",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
)
_TARGET_LABEL_KEYS = (
    "sun.title",
    "planet.mercury",
    "planet.venus",
    "planet.earth",
    "moon.title",
    "planet.mars",
    "planet.jupiter",
    "planet.saturn",
    "planet.uranus",
    "planet.neptune",
)
_TARGET_HIT_RADIUS = 32
SOLAR_SYSTEM_CENTER = (500, 340)
# x, y, width, height. Mirrors the non-rendering data-stage metadata in the
# authored observatory SVG; the static source test keeps live and authored
# geometry from drifting apart.
SOLAR_SYSTEM_STAGE_BOUNDS = (128, 108, 744, 377)


class SpacePage(EncyclopediaPage):
    page_id = "space"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 3  # Earth.
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
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.space.gallery.observatory",
        )
        if not authored:
            self._draw_fallback_background(surface)

        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.space"),
            center=(500, 95),
            size=40,
            color=(247, 242, 214),
        )
        self._draw_live_solar_system(surface, authored=authored)

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

    def _draw_fallback_background(self, surface: pygame.Surface) -> None:
        surface.fill((20, 28, 67))
        for index in range(38):
            x = (index * 83 + 17) % 1010
            y = 80 + ((index * 47) % 480)
            pygame.draw.circle(surface, (225, 231, 248), (x, y), 1 + (index % 2))

    def _draw_live_solar_system(self, surface: pygame.Surface, *, authored: bool) -> None:
        """Preserve the continuously orbiting teaching model over either backdrop."""

        center = SOLAR_SYSTEM_CENTER
        selected_id = _TARGET_IDS[self._selected]
        positions: dict[str, tuple[int, int, int]] = {
            "sun": (center[0], center[1], _TARGET_HIT_RADIUS)
        }
        orbit_color = (83, 107, 159) if authored else (68, 78, 120)

        pygame.draw.circle(surface, (251, 205, 66), center, 27)
        self._draw_open_marker(surface, "sun", (524, 318), 6)
        if selected_id == "sun":
            pygame.draw.circle(surface, (255, 222, 91), center, 36, 3)

        earth_position: tuple[int, int] | None = None
        for planet in PLANETS:
            orbit = pygame.Rect(
                center[0] - planet.radius_x,
                center[1] - planet.radius_y,
                planet.radius_x * 2,
                planet.radius_y * 2,
            )
            pygame.draw.ellipse(surface, orbit_color, orbit, 1)
            angle = self._time * planet.speed + planet.phase
            x = center[0] + int(math.cos(angle) * planet.radius_x)
            y = center[1] + int(math.sin(angle) * planet.radius_y)
            positions[planet.planet_id] = (x, y, _TARGET_HIT_RADIUS)
            if planet.planet_id == "earth":
                earth_position = (x, y)

            pygame.draw.circle(surface, planet.color, (x, y), planet.size)
            if planet.planet_id == "saturn":
                pygame.draw.ellipse(
                    surface,
                    (236, 218, 164),
                    (x - planet.size - 8, y - 5, (planet.size + 8) * 2, 10),
                    2,
                )
            self._draw_open_marker(
                surface,
                planet.planet_id,
                (x + planet.size + 6, y - planet.size - 5),
                4,
            )
            if selected_id == planet.planet_id:
                ring_radius = max(planet.size + 8, 15)
                pygame.draw.circle(surface, (255, 222, 91), (x, y), ring_radius, 3)

        if earth_position is not None:
            ex, ey = earth_position
            moon_angle = self._time * 1.8 + 0.4
            moon_x = ex + int(math.cos(moon_angle) * 28)
            moon_y = ey + int(math.sin(moon_angle) * 14)
            positions["moon"] = (moon_x, moon_y, _TARGET_HIT_RADIUS)
            pygame.draw.ellipse(surface, orbit_color, (ex - 30, ey - 16, 60, 32), 1)
            pygame.draw.circle(surface, (194, 193, 188), (moon_x, moon_y), 4)
            self._draw_open_marker(surface, "moon", (moon_x + 9, moon_y - 8), 3)
            if selected_id == "moon":
                pygame.draw.circle(surface, (255, 222, 91), (moon_x, moon_y), 15, 3)

        self._target_positions = [
            (target_id, *positions[target_id])
            for target_id in _TARGET_IDS
            if target_id in positions
        ]

    @staticmethod
    def _draw_open_marker(
        surface: pygame.Surface,
        target_id: str,
        position: tuple[int, int],
        radius: int,
    ) -> None:
        if target_id in IMPLEMENTED_ENTRY_IDS:
            pygame.draw.circle(surface, (255, 222, 91), position, radius)
