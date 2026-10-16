"""Uranus entry: sideways axis, long seasons, methane color, and faint rings."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, grid_step


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

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.space.uranus.observatory"


class UranusPage(EncyclopediaPage):
    page_id = "space.uranus"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
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
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((21, 27, 53))
            for i in range(31):
                pygame.draw.circle(surface, (226, 232, 242), ((i * 103 + 15) % 1000, 78 + (i * 49) % 468), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("uranus.title"),
            (243, 240, 220),
        )
        self._draw_uranus(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="uranus", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="surprised", fallback_color=(227, 174, 87))

    def _draw_uranus(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = (505, 326)
        radius = 88
        planet_color = (144, 207, 211) if self._color_age <= 0 else (119, 199, 207)

        ring_rect = pygame.Rect(center[0] - 132, center[1] - 44, 264, 88)
        if self._rings_visible and not authored:
            for inset, alpha in ((0, 90), (8, 70), (16, 50), (24, 30)):
                pygame.draw.ellipse(surface, (151, 160, 160, alpha), ring_rect.inflate(-inset * 2, -inset), 2)
                pygame.draw.ellipse(surface, (255, 255, 255, 18), ring_rect.inflate(-inset * 2 - 4, -inset - 2), 1)
        if not authored:
            # Soft shadow + highlight for depth
            shadow = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(shadow, (0, 0, 0, 24), (radius + 6, radius + 6), radius)
            surface.blit(shadow, (center[0] - radius - 6, center[1] - radius - 6))
            pygame.draw.circle(surface, planet_color, center, radius)
            hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 255, 255, 22), (radius // 2, 6, radius, radius // 3))
            surface.blit(hl, (center[0] - radius, center[1] - radius))
            pygame.draw.circle(surface, (82, 116, 123), center, radius, 3)
        elif self._rings_visible:
            # The planet is baked into the scene, so the far half of each ring
            # is only drawn where it clears the disc; the near half crosses it.
            for inset in (0, 8, 16, 24):
                rect = ring_rect.inflate(-inset * 2, -inset)
                pygame.draw.arc(surface, (176, 196, 198), rect, math.pi, math.tau, 2)
                pygame.draw.arc(surface, (176, 196, 198), rect, 0.0, 0.85, 2)
                pygame.draw.arc(surface, (176, 196, 198), rect, math.pi - 0.85, math.pi, 2)

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
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._caption_key == item.caption_key,
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_TELESCOPE_CARD,
            )

    def _draw_icon(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "tilt":
            pygame.draw.circle(surface, (144, 207, 211), (cx, cy), 18)
            pygame.draw.line(surface, (230, 194, 70), (cx - 22, cy + 18), (cx + 22, cy - 18), 5)
        elif discovery_id == "seasons":
            pygame.draw.circle(surface, (250, 203, 69), (cx - 14, cy), 9)
            pygame.draw.ellipse(surface, (127, 135, 158), (cx - 26, cy - 19, 52, 38), 3)
            pygame.draw.circle(surface, (144, 207, 211), (cx + 22, cy), 7)
        elif discovery_id == "color":
            pygame.draw.circle(surface, (119, 199, 207), (cx, cy), 21)
            pygame.draw.arc(surface, (204, 239, 234), (cx - 22, cy - 9, 44, 18), 0.2, 3.0, 4)
        else:
            pygame.draw.ellipse(surface, (144, 207, 211), (cx - 16, cy - 16, 32, 32))
            pygame.draw.ellipse(surface, (123, 130, 133), (cx - 29, cy - 11, 58, 22), 3)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
