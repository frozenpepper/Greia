"""Jupiter entry: scale, fast day, giant storm, and gas-giant structure."""

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
    from ..enciclopedia_focus_audio import FocusAudioTracker
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
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class JupiterDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    JupiterDiscovery("scale", "jupiter.scale", "encyclopedia.space.jupiter.scale", (250, 190)),
    JupiterDiscovery("day", "jupiter.day", "encyclopedia.space.jupiter.day", (755, 190)),
    JupiterDiscovery("storm", "jupiter.storm", "encyclopedia.space.jupiter.storm", (250, 420)),
    JupiterDiscovery("gas", "jupiter.gas", "encyclopedia.space.jupiter.gas", (755, 420)),
)


class JupiterPage(EncyclopediaPage):
    page_id = "space.jupiter"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "jupiter.intro"
        self._scale_age = 0.0
        self._day_age = 0.0
        self._storm_age = 0.0
        self._gas_age = 0.0
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.jupiter.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        # Use helper that avoids ledger fragment
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._activate(self._selected)
        # Announce is handled by _activate's audio; no extra cue needed
        disc = DISCOVERIES[0]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        announce_focus_name(self.context.audio, cue)

    def update(self, dt: float) -> None:
        self._time += dt
        self._scale_age = max(0.0, self._scale_age - dt)
        self._day_age = max(0.0, self._day_age - dt)
        self._storm_age = max(0.0, self._storm_age - dt)
        self._gas_age = max(0.0, self._gas_age - dt)

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
                self._focus_audio.announce_once(self.context.audio, cue)
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
        # Announce is handled by _activate's audio; no extra cue needed
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
        if discovery.discovery_id == "scale":
            self._scale_age = 4.0
        elif discovery.discovery_id == "day":
            self._day_age = 4.0
        elif discovery.discovery_id == "storm":
            self._storm_age = 4.5
        else:
            self._gas_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((24, 27, 50))
        for i in range(31):
            pygame.draw.circle(surface, (226, 230, 239), ((i * 91 + 17) % 1000, 78 + (i * 53) % 468), 1)
        draw_centered_text(surface, self.context.typography, self.context.resources.text("jupiter.title"), center=(500, 92), size=40, color=(246, 239, 220), role=FontRole.DISPLAY)
        self._draw_jupiter(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="jupiter", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="surprised", fallback_color=(227, 174, 87))

    def _draw_jupiter(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 100
        # Soft contact shadow beneath the giant — shallow tactile depth
        shadow = pygame.Surface((radius * 2 + 20, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (40, 28, 20, 38), shadow.get_rect())
        surface.blit(shadow, (center[0] - radius - 10, center[1] + radius + 8))
        pygame.draw.circle(surface, (205, 169, 127), center, radius)
        # Subtle limb shading for depth, not 3D gloss
        highlight = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(highlight, (255, 245, 220, 18), (radius, radius), radius)
        surface.blit(highlight, (center[0] - radius, center[1] - radius))
        # Bands via circular-masked temp for clean limb (avoids square clip)
        bands = (
            (-70, 22, (245, 230, 205)),
            (-48, 18, (205, 150, 110)),
            (-30, 20, (250, 238, 215)),
            (-10, 16, (225, 175, 135)),
            (6, 18, (248, 235, 210)),
            (24, 16, (190, 135, 95)),
            (40, 20, (242, 225, 190)),
            (60, 18, (200, 145, 105)),
        )
        drift = math.sin(self._time * (1.9 if self._day_age > 0 else 0.42)) * (10 if self._day_age > 0 else 4)
        offset = int(drift)
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), radius)
        temp = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for yoff, height, color in bands:
            rect = pygame.Rect(radius - 118 + offset, radius + yoff, 236, height)
            pygame.draw.rect(temp, color, rect, border_radius=3)
            hl = pygame.Rect(rect.x + 4, rect.y + 2, rect.width - 8, height // 2)
            pygame.draw.rect(temp, (255, 255, 255, 18), hl, border_radius=2)
            pygame.draw.line(temp, (120, 85, 65, 42), (rect.x, rect.y + height), (rect.right, rect.y + height), 1)
            for tx in range(0, 220, 38):
                sx = rect.x + tx + int(4 * math.sin(self._time * 0.6 + yoff * 0.1 + tx * 0.02))
                pygame.draw.line(temp, (255, 255, 255, 12), (sx, rect.y + 4), (sx + 12, rect.y + height - 4), 1)
        temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(temp, (center[0] - radius, center[1] - radius))
        pygame.draw.circle(surface, (90, 66, 55), center, radius, 3)
        pygame.draw.circle(surface, (255, 245, 220, 22), center, radius - 6, 2)

        storm_center = (544, 358)
        storm_w = 62 + (10 if self._storm_age > 0 else 0)
        storm_h = 34 + (6 if self._storm_age > 0 else 0)
        # Storm with layered swirl when emphasized
        pygame.draw.ellipse(
            surface, (185, 95, 72), (storm_center[0] - storm_w // 2, storm_center[1] - storm_h // 2, storm_w, storm_h)
        )
        pygame.draw.ellipse(
            surface, (205, 105, 82), (storm_center[0] - storm_w // 2 + 4, storm_center[1] - storm_h // 2 + 3, storm_w - 8, storm_h - 6)
        )
        # Central swirl
        pygame.draw.ellipse(
            surface, (225, 145, 110), (storm_center[0] - 18, storm_center[1] - 7, 36, 14)
        )
        if self._storm_age > 0:
            for ring in range(3):
                pygame.draw.ellipse(
                    surface,
                    (240, 160, 115, 90 - ring * 20),
                    (storm_center[0] - 44 - ring * 7, storm_center[1] - 23 - ring * 4, 88 + ring * 14, 46 + ring * 8),
                    3,
                )

        if self._scale_age > 0:
            for row in range(2):
                for col in range(6):
                    pygame.draw.circle(surface, (73, 145, 214), (404 + col * 27, 442 + row * 22), 8)
            draw_centered_text(surface, self.context.typography, "≈11×", center=(505, 475), size=18, color=(245, 229, 177), role=FontRole.CONTROL)

        if self._gas_age > 0:
            for ring, color in ((82, (235, 210, 175)), (62, (210, 165, 130)), (42, (175, 125, 105))):
                pygame.draw.circle(surface, color, center, ring, 5)
                pygame.draw.circle(surface, (255, 245, 220, 18), center, ring - 4, 2)
            pygame.draw.line(surface, (246, 220, 143), (605, 280), (650, 248), 4)
            pygame.draw.line(surface, (246, 220, 143), (605, 372), (650, 404), 4)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (249, 244, 226), item.center, 37)
            pygame.draw.circle(surface, (73, 60, 55), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "scale":
                pygame.draw.circle(surface, (205, 169, 127), (cx - 10, cy), 21)
                pygame.draw.circle(surface, (73, 145, 214), (cx + 20, cy + 8), 7)
            elif item.discovery_id == "day":
                pygame.draw.arc(surface, (214, 176, 93), (cx - 24, cy - 24, 48, 48), 0.1, 5.2, 5)
                pygame.draw.polygon(surface, (214, 176, 93), [(cx + 21, cy - 9), (cx + 29, cy + 3), (cx + 13, cy + 4)])
            elif item.discovery_id == "storm":
                pygame.draw.ellipse(surface, (178, 83, 64), (cx - 25, cy - 13, 50, 26))
                pygame.draw.ellipse(surface, (228, 144, 101), (cx - 18, cy - 9, 36, 18), 3)
            else:
                for r in (21, 14, 7):
                    pygame.draw.circle(surface, (205, 169 - r, 115), (cx, cy), r, 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (249, 244, 226), panel, border_radius=22)
        pygame.draw.rect(surface, (73, 60, 55), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 49, 56))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 49, 56))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
