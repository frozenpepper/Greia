"""Earth-as-a-planet entry: rotation, water, seasons and atmosphere/life."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class EarthDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    EarthDiscovery("rotation", "planet_earth.rotation", "encyclopedia.space.earth.rotation", (250, 190)),
    EarthDiscovery("water", "planet_earth.water", "encyclopedia.space.earth.water", (755, 190)),
    EarthDiscovery("seasons", "planet_earth.seasons", "encyclopedia.space.earth.seasons", (250, 420)),
    EarthDiscovery("life", "planet_earth.life", "encyclopedia.space.earth.life", (755, 420)),
)


class EarthPlanetPage(EncyclopediaPage):
    page_id = "space.earth"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "planet_earth.intro"
        self._rotation_age = 0.0
        self._water_age = 0.0
        self._season_state = 0
        self._season_age = 0.0
        self._life_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.earth.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        # Use helper that avoids ledger fragment
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        if not announce_focus_name(self.context.audio, cue):
            announce_focus_name(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._activate(0)
        disc = DISCOVERIES[0]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        announce_focus_name(self.context.audio, cue)

    def update(self, dt: float) -> None:
        self._time += dt
        self._rotation_age = max(0.0, self._rotation_age - dt)
        self._water_age = max(0.0, self._water_age - dt)
        self._season_age = max(0.0, self._season_age - dt)
        self._life_age = max(0.0, self._life_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._action_hit.collidepoint(point):
                    self._trigger_main()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue(disc.discovery_id, "name")
                announce_focus_name(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == DISCOVERIES[0].discovery_id:
                self._trigger_main()
                return
            self._activate(self._selected)
            return
        prev = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )
        if self._selected != prev:
            self._announce_selected()
    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "rotation":
            self._rotation_age = 4.0
        elif discovery.discovery_id == "water":
            self._water_age = 4.0
        elif discovery.discovery_id == "seasons":
            self._season_state = 1 - self._season_state
            self._season_age = 4.5
        else:
            self._life_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((17, 28, 60))
        for index in range(34):
            x = (index * 79 + 37) % 1000
            y = 78 + (index * 67) % 470
            pygame.draw.circle(surface, (224, 231, 244), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("planet_earth.title"),
            center=(500, 92),
            size=40,
            color=(245, 241, 219),
            role=FontRole.DISPLAY,
        )
        self._draw_earth(surface)
        self._draw_hotspots(surface)
        for idx, rect in enumerate(self._hotspots):
            if idx == self._selected or idx == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=getattr(self, '_time', 0.0))
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="earth", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(227, 174, 87),
        )

    def _draw_earth(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 96
        angle = self._time * (1.15 if self._rotation_age > 0 else 0.20)

        # Thin atmosphere first, then ocean disk and stylized land. This is a
        # teaching globe, deliberately not a geographic map.
        pygame.draw.circle(surface, (128, 203, 242), center, radius + 7, 5)
        pygame.draw.circle(surface, (63, 137, 210), center, radius)

        land_color = (100, 174, 99)
        for base_angle, spread in ((0.25, 0.42), (2.0, 0.50), (4.2, 0.38)):
            theta = base_angle + angle
            x = center[0] + int(math.cos(theta) * 48)
            y = center[1] + int(math.sin(theta) * 34)
            pygame.draw.ellipse(
                surface,
                land_color,
                (x - int(38 * spread), y - int(28 * spread), int(76 * spread), int(56 * spread)),
            )

        if self._rotation_age > 0:
            # Fixed Sun at left; clipped shade on the opposite half makes the
            # day/night relation visible without a lighting engine.
            pygame.draw.circle(surface, (250, 204, 65), (365, 326), 25)
            previous_clip = surface.get_clip()
            surface.set_clip(pygame.Rect(center[0], center[1] - radius - 8, radius + 12, radius * 2 + 16))
            pygame.draw.circle(surface, (26, 43, 78), center, radius)
            surface.set_clip(previous_clip)
            pygame.draw.line(surface, (231, 224, 183), (505, 232), (505, 420), 2)

        if self._water_age > 0:
            for index in range(8):
                y = 273 + index * 14
                pygame.draw.arc(
                    surface,
                    (157, 221, 246),
                    (438, y, 134, 25),
                    0.15,
                    2.9,
                    3,
                )

        if self._season_age > 0:
            tilt = -0.38 if self._season_state == 0 else 0.38
            length = 126
            dx = int(math.sin(tilt) * length / 2)
            dy = int(math.cos(tilt) * length / 2)
            pygame.draw.line(
                surface,
                (250, 224, 115),
                (center[0] - dx, center[1] + dy),
                (center[0] + dx, center[1] - dy),
                5,
            )
            north = (center[0] + dx, center[1] - dy)
            south = (center[0] - dx, center[1] + dy)
            pygame.draw.circle(surface, (255, 232, 127), north if self._season_state == 0 else south, 13, 3)
            pygame.draw.circle(surface, (181, 205, 230), south if self._season_state == 0 else north, 13, 3)

        if self._life_age > 0:
            # A few abstract leaf/wave marks signal known life without implying
            # exact geography or a complete biosphere inventory.
            for x, y, flip in ((470, 300, 1), (535, 285, -1), (520, 355, 1), (458, 360, -1)):
                pygame.draw.ellipse(surface, (196, 231, 114), (x - 9, y - 5, 18, 10))
                pygame.draw.line(surface, (77, 124, 70), (x, y), (x + 8 * flip, y - 12), 2)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (249, 245, 226), item.center, 37)
            pygame.draw.circle(surface, (70, 60, 57), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "rotation":
                pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 18)
                pygame.draw.arc(surface, (240, 194, 63), (cx - 25, cy - 25, 50, 50), 0.2, 4.9, 5)
            elif item.discovery_id == "water":
                pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 20)
                pygame.draw.arc(surface, (162, 222, 245), (cx - 18, cy - 4, 36, 20), 0.2, 2.9, 4)
            elif item.discovery_id == "seasons":
                pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 18)
                pygame.draw.line(surface, (239, 196, 72), (cx - 10, cy + 24), (cx + 10, cy - 24), 5)
            else:
                pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 20)
                pygame.draw.ellipse(surface, (111, 181, 100), (cx - 12, cy - 8, 24, 16))
                pygame.draw.arc(surface, (159, 218, 244), (cx - 25, cy - 25, 50, 50), 0, math.tau, 4)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (249, 245, 226), panel, border_radius=22)
        pygame.draw.rect(surface, (70, 60, 57), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 49, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 49, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
