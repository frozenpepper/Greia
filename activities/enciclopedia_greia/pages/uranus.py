"""Uranus entry: sideways axis, long seasons, methane color, and faint rings."""

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
class UranusDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    UranusDiscovery("tilt", "uranus.tilt", "encyclopedia.space.uranus.tilt", (250, 190)),
    UranusDiscovery("seasons", "uranus.seasons", "encyclopedia.space.uranus.seasons", (755, 190)),
    UranusDiscovery("color", "uranus.color", "encyclopedia.space.uranus.color", (250, 420)),
    UranusDiscovery("rings", "uranus.rings", "encyclopedia.space.uranus.rings", (755, 420)),
)


class UranusPage(EncyclopediaPage):
    page_id = "space.uranus"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "uranus.intro"
        self._tilt_age = 0.0
        self._season_age = 0.0
        self._color_age = 0.0
        self._rings_visible = False
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.uranus.intro")
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
        self._tilt_age = max(0.0, self._tilt_age - dt)
        self._season_age = max(0.0, self._season_age - dt)
        self._color_age = max(0.0, self._color_age - dt)

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
        if discovery.discovery_id == "tilt":
            self._tilt_age = 4.5
        elif discovery.discovery_id == "seasons":
            self._season_age = 5.0
        elif discovery.discovery_id == "color":
            self._color_age = 4.0
        else:
            self._rings_visible = not self._rings_visible
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((21, 27, 53))
        for i in range(31):
            pygame.draw.circle(surface, (226, 232, 242), ((i * 103 + 15) % 1000, 78 + (i * 49) % 468), 1)
        draw_centered_text(surface, self.context.typography, self.context.resources.text("uranus.title"), center=(500, 92), size=40, color=(243, 240, 220), role=FontRole.DISPLAY)
        self._draw_uranus(surface)
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
            surface, (512, 485), entry="uranus", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="surprised", fallback_color=(227, 174, 87))

    def _draw_uranus(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 88
        planet_color = (144, 207, 211) if self._color_age <= 0 else (119, 199, 207)

        ring_rect = pygame.Rect(center[0] - 132, center[1] - 44, 264, 88)
        if self._rings_visible:
            for inset in (0, 8, 16):
                pygame.draw.ellipse(surface, (151, 160, 160), ring_rect.inflate(-inset * 2, -inset), 2)

        pygame.draw.circle(surface, planet_color, center, radius)
        pygame.draw.circle(surface, (82, 116, 123), center, radius, 3)

        axis_angle = math.radians(82)
        if self._tilt_age > 0:
            wobble = math.sin(self._time * 1.8) * 0.08
            axis_angle += wobble
        dx = int(math.cos(axis_angle) * 126)
        dy = int(math.sin(axis_angle) * 126)
        pygame.draw.line(surface, (247, 219, 97), (center[0] - dx, center[1] - dy), (center[0] + dx, center[1] + dy), 5)
        pygame.draw.circle(surface, (247, 219, 97), (center[0] + dx, center[1] + dy), 6)
        if self._tilt_age > 0:
            pygame.draw.arc(surface, (247, 219, 97), pygame.Rect(center[0] - 115, center[1] - 115, 230, 230), 0.5, 5.1, 4)

        if self._season_age > 0:
            sun = (360, 326)
            orbit = pygame.Rect(390, 238, 250, 176)
            pygame.draw.circle(surface, (250, 203, 69), sun, 22)
            pygame.draw.ellipse(surface, (71, 80, 112), orbit, 2)
            angle = self._time * 0.55
            pos = (orbit.centerx + int(math.cos(angle) * orbit.width / 2), orbit.centery + int(math.sin(angle) * orbit.height / 2))
            pygame.draw.circle(surface, planet_color, pos, 17)
            pole = (pos[0] + int(math.cos(angle) * 19), pos[1] + int(math.sin(angle) * 19))
            pygame.draw.circle(surface, (251, 224, 112), pole, 5)
            draw_centered_text(surface, self.context.typography, "84y", center=(505, 453), size=18, color=(240, 229, 190), role=FontRole.CONTROL)

        if self._color_age > 0:
            for offset in (-36, -12, 12, 36):
                pygame.draw.arc(surface, (180, 232, 228), (center[0] - 82, center[1] + offset - 9, 164, 18), 0.1, 3.0, 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 245, 228), item.center, 37)
            pygame.draw.circle(surface, (68, 61, 58), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "tilt":
                pygame.draw.circle(surface, (144, 207, 211), (cx, cy), 18)
                pygame.draw.line(surface, (230, 194, 70), (cx - 22, cy + 18), (cx + 22, cy - 18), 5)
            elif item.discovery_id == "seasons":
                pygame.draw.circle(surface, (250, 203, 69), (cx - 14, cy), 9)
                pygame.draw.ellipse(surface, (127, 135, 158), (cx - 26, cy - 19, 52, 38), 3)
                pygame.draw.circle(surface, (144, 207, 211), (cx + 22, cy), 7)
            elif item.discovery_id == "color":
                pygame.draw.circle(surface, (119, 199, 207), (cx, cy), 21)
                pygame.draw.arc(surface, (204, 239, 234), (cx - 22, cy - 9, 44, 18), 0.2, 3.0, 4)
            else:
                pygame.draw.ellipse(surface, (144, 207, 211), (cx - 16, cy - 16, 32, 32))
                pygame.draw.ellipse(surface, (123, 130, 133), (cx - 29, cy - 11, 58, 22), 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 245, 228), panel, border_radius=22)
        pygame.draw.rect(surface, (68, 61, 58), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 49, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 49, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
