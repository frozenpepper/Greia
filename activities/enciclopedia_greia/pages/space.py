"""Space section: a live Solar System inside an authored observatory."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        ORBIT_SPEED_FACTORS,
        announce_focus_name,
        decorate_planet,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_labels_toggle,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        ORBIT_SPEED_FACTORS,
        announce_focus_name,
        decorate_planet,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_labels_toggle,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter


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
    # Speeds reduced vs E3: slower orbit animation to remove click-frustration
    # while keeping continuous gentle motion. See Quality Plan Track B.
    Planet("mercury", "planet.mercury", 70, 28, 5, 0.62, (175, 164, 146), 0.2),
    Planet("venus", "planet.venus", 100, 40, 7, 0.48, (225, 180, 104), 1.1),
    Planet("earth", "planet.earth", 135, 54, 8, 0.38, (70, 143, 214), 2.0),
    Planet("mars", "planet.mars", 170, 68, 7, 0.31, (194, 101, 70), 2.8),
    Planet("jupiter", "planet.jupiter", 215, 86, 15, 0.19, (207, 163, 118), 3.5),
    Planet("saturn", "planet.saturn", 260, 103, 13, 0.16, (220, 194, 129), 4.1),
    Planet("uranus", "planet.uranus", 300, 119, 10, 0.13, (153, 214, 220), 4.8),
    Planet("neptune", "planet.neptune", 340, 134, 10, 0.11, (82, 116, 201), 5.4),
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
_TARGET_HIT_RADIUS = 40
SOLAR_SYSTEM_CENTER = (500, 340)
# x, y, width, height. Mirrors the non-rendering data-stage metadata in the
# authored observatory SVG; the static source test keeps live and authored
# geometry from drifting apart.
SOLAR_SYSTEM_STAGE_BOUNDS = (128, 108, 744, 377)


class SpacePage(EncyclopediaPage):
    page_id = "space"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 3  # Earth.
        self._target_positions: list[tuple[str, int, int, int]] = []
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._discover_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._speed_level = 1  # medium
        self._paused = False
        self._labels_enabled = True
        self._slider_hits: tuple[pygame.Rect, pygame.Rect, pygame.Rect] = (
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
        )
        self._pause_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._labels_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        target = _TARGET_IDS[self._selected]
        # Prefer dedicated name cue; falls back silently if not yet produced.
        cue = encyclopedia_focus_cue("space", target, "name")
        self._focus_audio.announce_once(self.context.audio, cue)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(_TARGET_IDS) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        if not self._paused:
            self._time += dt * ORBIT_SPEED_FACTORS[self._speed_level]
        else:
            # Still advance a tiny amount for halo pulse, but not orbit.
            self._time += dt * 0.15

    def handle_input(self, event: PageInput) -> None:
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.LEFT:
                self._set_selected(self._selected - 1)
            elif event.command is PageCommand.RIGHT:
                self._set_selected(self._selected + 1)
            elif event.command is PageCommand.ACTIVATE:
                self._open_selected()
            return
        if event.kind is PageInputKind.POINTER_MOVE and event.position:
            px, py = event.position
            # Hover announces name without changing persistent selection
            for idx, (_, x, y, hit_radius) in enumerate(self._target_positions):
                if (px - x) ** 2 + (py - y) ** 2 <= hit_radius**2:
                    self._focus_audio.announce_once(
                        self.context.audio, encyclopedia_focus_cue("space", _TARGET_IDS[idx], "name")
                    )
                    break
            return
        if event.kind is PageInputKind.POINTER_PRESS and event.position:
            px, py = event.position
            ipx, ipy = int(px), int(py)
            # Orbit controls first — large hit areas, reliable even while planets move.
            for lvl, hit in enumerate(self._slider_hits):
                if hit.collidepoint((ipx, ipy)):
                    self._speed_level = lvl
                    self._paused = False
                    return
            if self._pause_hit.collidepoint((ipx, ipy)):
                self._paused = not self._paused
                return
            if self._labels_hit.collidepoint((ipx, ipy)):
                self._labels_enabled = not self._labels_enabled
                return
            if self._discover_hit.collidepoint((ipx, ipy)):
                self._open_selected()
                return
            if self._arrow_left_hit.collidepoint((ipx, ipy)):
                self._set_selected(self._selected - 1)
                return
            if self._arrow_right_hit.collidepoint((ipx, ipy)):
                self._set_selected(self._selected + 1)
                return
            candidates: list[tuple[float, int]] = []
            for index, (_, x, y, hit_radius) in enumerate(self._target_positions):
                distance = (px - x) ** 2 + (py - y) ** 2
                if distance <= hit_radius**2:
                    candidates.append((distance, index))
            if candidates:
                _, index = min(candidates)
                self._set_selected(index)
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

        # Standard navigation chrome — consistent across section pages.
        can_left = self._selected > 0
        can_right = self._selected < len(_TARGET_IDS) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Orbit toy controls — low-cost, large hit areas, consistent grammar.
        _, self._slider_hits = draw_speed_slider(
            surface, (180, 540), time=self._time, level=self._speed_level, paused=self._paused
        )
        self._pause_hit = draw_pause_button(
            surface, (315, 540), time=self._time, paused=self._paused
        )
        self._labels_hit = draw_labels_toggle(
            surface, (380, 540), time=self._time, enabled=self._labels_enabled
        )
        self._discover_hit = draw_discover_button(
            surface, (760, 540), active=True, time=self._time, enabled=True
        )

        # The selected planet/Moon itself owns the bright focus indication.
        # This plaque is only reading support, so keep it visually quiet rather
        # than drawing a second permanent yellow selection ring around text.
        if self._labels_enabled:
            label_rect = pygame.Rect(415, 500, 300, 42)
            pygame.draw.rect(surface, (248, 244, 222), label_rect, border_radius=20)
            pygame.draw.rect(surface, (92, 82, 72), label_rect, 2, border_radius=20)
            draw_centered_text(
                surface,
                self.context.typography,
                self.context.resources.text(_TARGET_LABEL_KEYS[self._selected]),
                center=label_rect.center,
                size=20,
                color=(48, 43, 61),
            )
        # Ambient twinkle is deliberately sparse — static completeness must remain.
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

        # Sun with unified focus halo (non-occluding, pulse)
        pygame.draw.circle(surface, (251, 205, 66), center, 27)
        if selected_id == "sun":
            sun_rect = pygame.Rect(center[0] - 38, center[1] - 38, 76, 76)
            draw_focus_patch(surface, sun_rect, active=True, radius=18, time=self._time, shape="circle")
        if self._labels_enabled:
            self._draw_open_marker(surface, "sun", (524, 318), 6)

        earth_position: tuple[int, int] | None = None
        for planet in PLANETS:
            orbit = pygame.Rect(
                center[0] - planet.radius_x,
                center[1] - planet.radius_y,
                planet.radius_x * 2,
                planet.radius_y * 2,
            )
            pygame.draw.ellipse(surface, orbit_color, orbit, 1)
            # Slight highlight of current planet's orbit
            if selected_id == planet.planet_id:
                pygame.draw.ellipse(surface, (120, 145, 193), orbit, 2)
            angle = self._time * planet.speed + planet.phase
            x = center[0] + int(math.cos(angle) * planet.radius_x)
            y = center[1] + int(math.sin(angle) * planet.radius_y)
            positions[planet.planet_id] = (x, y, _TARGET_HIT_RADIUS)
            if planet.planet_id == "earth":
                earth_position = (x, y)

            # Earth uses authored sprite when available — instant recognition
            if planet.planet_id == "earth":
                is_sel = selected_id == "earth"
                diam = planet.size * 2 + (2 if is_sel else 0)
                if is_sel:
                    diam = int(diam * 1.25)
                sprite = self.context.visuals.planet("earth", diam)
                if sprite is not None:
                    surface.blit(sprite, sprite.get_rect(center=(x, y)))
                else:
                    pygame.draw.circle(surface, planet.color, (x, y), planet.size)
                    decorate_planet(surface, planet.planet_id, (x, y), planet.size, planet.color, self._time)
            else:
                pygame.draw.circle(surface, planet.color, (x, y), planet.size)
                decorate_planet(surface, planet.planet_id, (x, y), planet.size, planet.color, self._time)
            if planet.planet_id == "saturn":
                pygame.draw.ellipse(
                    surface,
                    (236, 218, 164),
                    (x - planet.size - 8, y - 5, (planet.size + 8) * 2, 10),
                    2,
                )
            if self._labels_enabled:
                self._draw_open_marker(
                    surface,
                    planet.planet_id,
                    (x + planet.size + 6, y - planet.size - 5),
                    4,
                )
            if selected_id == planet.planet_id:
                # Fitted halo — circle for planets
                pad = max(14, planet.size + 10)
                halo_rect = pygame.Rect(x - pad, y - pad, pad * 2, pad * 2)
                draw_focus_patch(surface, halo_rect, active=True, radius=16, time=self._time, shape="circle")

        if earth_position is not None:
            ex, ey = earth_position
            moon_angle = self._time * 0.95 + 0.4
            moon_x = ex + int(math.cos(moon_angle) * 28)
            moon_y = ey + int(math.sin(moon_angle) * 14)
            positions["moon"] = (moon_x, moon_y, _TARGET_HIT_RADIUS)
            pygame.draw.ellipse(surface, orbit_color, (ex - 30, ey - 16, 60, 32), 1)
            pygame.draw.circle(surface, (194, 193, 188), (moon_x, moon_y), 4)
            if self._labels_enabled:
                self._draw_open_marker(surface, "moon", (moon_x + 9, moon_y - 8), 3)
            if selected_id == "moon":
                moon_rect = pygame.Rect(moon_x - 18, moon_y - 18, 36, 36)
                draw_focus_patch(surface, moon_rect, active=True, radius=14, time=self._time, shape="circle")

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
