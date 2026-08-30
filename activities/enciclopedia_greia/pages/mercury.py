"""Mercury entry: place/size, fast year, thermal contrast and craters."""

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
class MercuryDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MercuryDiscovery("place", "mercury.place", "encyclopedia.space.mercury.place", (250, 190)),
    MercuryDiscovery("orbit", "mercury.orbit", "encyclopedia.space.mercury.orbit", (755, 190)),
    MercuryDiscovery("temperature", "mercury.temperature", "encyclopedia.space.mercury.temperature", (250, 420)),
    MercuryDiscovery("craters", "mercury.craters", "encyclopedia.space.mercury.craters", (755, 420)),
)

_CRATERS = (
    (-48, -31, 17),
    (36, -42, 12),
    (52, 15, 19),
    (-23, 42, 13),
    (9, 10, 9),
    (-63, 17, 8),
)


class MercuryPage(EncyclopediaPage):
    page_id = "space.mercury"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "mercury.intro"
        self._place_age = 0.0
        self._orbit_age = 0.0
        self._temperature_mode = 0
        self._temperature_age = 0.0
        self._crater_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.mercury.intro")
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
        self._place_age = max(0.0, self._place_age - dt)
        self._orbit_age = max(0.0, self._orbit_age - dt)
        self._temperature_age = max(0.0, self._temperature_age - dt)
        self._crater_age = max(0.0, self._crater_age - dt)

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
        if discovery.discovery_id == "place":
            self._place_age = 4.0
        elif discovery.discovery_id == "orbit":
            self._orbit_age = 4.0
        elif discovery.discovery_id == "temperature":
            self._temperature_mode = 1 - self._temperature_mode
            self._temperature_age = 4.0
        else:
            self._crater_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((26, 31, 53))
        for index in range(30):
            x = (index * 91 + 31) % 1000
            y = 78 + (index * 61) % 465
            pygame.draw.circle(surface, (222, 229, 239), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("mercury.title"),
            center=(500, 92),
            size=40,
            color=(244, 239, 220),
            role=FontRole.DISPLAY,
        )
        self._draw_mercury(surface)
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
            surface, (512, 485), entry="mercury", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="default",
            fallback_color=(227, 174, 87),
        )

    def _draw_mercury(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 92

        if self._orbit_age > 0:
            sun = (385, 326)
            orbit_rect = pygame.Rect(392, 245, 226, 162)
            pygame.draw.circle(surface, (249, 199, 58), sun, 25)
            pygame.draw.ellipse(surface, (78, 87, 119), orbit_rect, 2)
            phase = self._time * 2.8
            moving = (
                orbit_rect.centerx + int(math.cos(phase) * orbit_rect.width / 2),
                orbit_rect.centery + int(math.sin(phase) * orbit_rect.height / 2),
            )
            pygame.draw.circle(surface, (172, 166, 154), moving, 10)
            return

        pygame.draw.circle(surface, (177, 170, 157), center, radius)

        # One circle, two clipped hemispheres: the comparison stays visually a
        # single world and does not allocate a temporary surface in the hot loop.
        if self._temperature_age > 0:
            previous_clip = surface.get_clip()
            surface.set_clip(pygame.Rect(center[0] - radius, center[1] - radius, radius, radius * 2))
            pygame.draw.circle(surface, (210, 147, 86), center, radius)
            surface.set_clip(pygame.Rect(center[0], center[1] - radius, radius, radius * 2))
            pygame.draw.circle(surface, (91, 105, 133), center, radius)
            surface.set_clip(previous_clip)
            pygame.draw.line(surface, (237, 215, 165), (505, 235), (505, 417), 3)
            pygame.draw.circle(surface, (250, 202, 73), (420, 253), 14)
            pygame.draw.circle(surface, (191, 222, 244), (585, 395), 12)

        for dx, dy, crater_radius in _CRATERS:
            x, y = center[0] + dx, center[1] + dy
            pygame.draw.circle(surface, (127, 121, 113), (x, y), crater_radius)
            pygame.draw.circle(surface, (201, 194, 179), (x - 3, y - 3), max(3, crater_radius - 5), 2)

        if self._crater_age > 0:
            for dx, dy, crater_radius in _CRATERS[:3]:
                x, y = center[0] + dx, center[1] + dy
                pygame.draw.line(surface, (217, 210, 193), (x, y), (x + crater_radius * 2, y - crater_radius), 2)
                pygame.draw.line(surface, (217, 210, 193), (x, y), (x - crater_radius * 2, y + crater_radius), 2)
            polar = (505, 245)
            pygame.draw.circle(surface, (70, 76, 91), polar, 18)
            pygame.draw.arc(surface, (184, 226, 243), (493, 235, 24, 18), 0.2, 3.0, 4)

        if self._place_age > 0:
            earth_center = (627, 363)
            pygame.draw.circle(surface, (73, 145, 213), earth_center, 28)
            pygame.draw.arc(surface, (87, 176, 101), (612, 348, 28, 24), 0.2, 2.8, 5)
            pygame.draw.line(surface, (245, 226, 151), (586, 400), (649, 400), 4)
            pygame.draw.line(surface, (245, 226, 151), (586, 393), (586, 407), 4)
            pygame.draw.line(surface, (245, 226, 151), (649, 393), (649, 407), 4)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 244, 226), item.center, 37)
            pygame.draw.circle(surface, (72, 62, 57), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "place":
                pygame.draw.circle(surface, (174, 167, 154), (cx - 12, cy), 13)
                pygame.draw.circle(surface, (73, 145, 213), (cx + 17, cy + 5), 20)
            elif item.discovery_id == "orbit":
                pygame.draw.circle(surface, (247, 196, 59), (cx - 6, cy), 10)
                pygame.draw.ellipse(surface, (143, 135, 125), (cx - 25, cy - 18, 50, 36), 3)
                pygame.draw.circle(surface, (174, 167, 154), (cx + 22, cy), 6)
            elif item.discovery_id == "temperature":
                pygame.draw.circle(surface, (224, 141, 71), (cx - 12, cy), 15)
                pygame.draw.circle(surface, (124, 163, 201), (cx + 14, cy), 15)
            else:
                pygame.draw.circle(surface, (151, 145, 134), (cx, cy), 21)
                pygame.draw.circle(surface, (101, 96, 90), (cx - 7, cy - 4), 7)
                pygame.draw.circle(surface, (190, 222, 241), (cx + 11, cy - 12), 5)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 244, 226), panel, border_radius=22)
        pygame.draw.rect(surface, (72, 62, 57), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 50, 57))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 50, 57))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
