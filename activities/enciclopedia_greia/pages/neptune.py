"""Neptune entry: distance, long year, supersonic winds, blue ice-giant structure."""

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
class NeptuneDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    NeptuneDiscovery("distance", "neptune.distance", "encyclopedia.space.neptune.distance", (250, 190)),
    NeptuneDiscovery("year", "neptune.year", "encyclopedia.space.neptune.year", (755, 190)),
    NeptuneDiscovery("winds", "neptune.winds", "encyclopedia.space.neptune.winds", (250, 420)),
    NeptuneDiscovery("blue", "neptune.blue", "encyclopedia.space.neptune.blue", (755, 420)),
)

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.space.neptune.observatory"


class NeptunePage(EncyclopediaPage):
    page_id = "space.neptune"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "neptune.intro"
        self._distance_age = 0.0
        self._year_age = 0.0
        self._wind_age = 0.0
        self._rings_visible = False
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.neptune.intro")
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
        self._distance_age = max(0.0, self._distance_age - dt)
        self._year_age = max(0.0, self._year_age - dt)
        self._wind_age = max(0.0, self._wind_age - dt)

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
        if discovery.discovery_id == "distance":
            self._distance_age = 5.0
        elif discovery.discovery_id == "year":
            self._year_age = 5.0
        elif discovery.discovery_id == "winds":
            self._wind_age = 4.5
        else:
            self._rings_visible = not self._rings_visible
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((17, 24, 53))
            for i in range(33):
                pygame.draw.circle(surface, (226, 232, 243), ((i * 107 + 11) % 1000, 77 + (i * 51) % 470), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("neptune.title"),
            (244, 241, 222),
        )
        self._draw_neptune(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="neptune", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default", fallback_color=(227, 174, 87))

    def _draw_neptune(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = (505, 326)
        radius = 90
        if self._rings_visible and not authored:
            for inset, alpha in ((0, 90), (7, 70), (14, 45)):
                pygame.draw.ellipse(surface, (113, 125, 149, alpha), (center[0] - 132 + inset, center[1] - 33 + inset // 2, 264 - inset * 2, 66 - inset), 2)
                pygame.draw.ellipse(surface, (255, 255, 255, 18), (center[0] - 130 + inset, center[1] - 31 + inset // 2, 260 - inset * 2, 62 - inset), 1)
        if not authored:
            # Soft shadow + highlight for depth
            shadow = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(shadow, (0, 0, 0, 24), (radius + 6, radius + 6), radius)
            surface.blit(shadow, (center[0] - radius - 6, center[1] - radius - 6))
            pygame.draw.circle(surface, (75, 112, 194), center, radius)
            hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 255, 255, 20), (radius // 2, 8, radius, radius // 3))
            surface.blit(hl, (center[0] - radius, center[1] - radius))
            pygame.draw.circle(surface, (45, 67, 122), center, radius, 3)
            for yoff in (-47, -19, 14, 46):
                wave = int(math.sin(self._time * 0.45 + yoff) * 7)
                wobble = int(math.cos(self._time * 0.33 + yoff * 0.08) * 2)
                pygame.draw.arc(surface, (110, 148, 218), (center[0] - 80 + wave, center[1] + yoff - 9 + wobble, 160, 22), 0.15, 3.0, 4)
                pygame.draw.arc(surface, (255, 255, 255, 14), (center[0] - 78 + wave, center[1] + yoff - 7 + wobble, 156, 18), 0.15, 3.0, 2)
        elif self._rings_visible:
            # The planet is baked into the scene, so the far half of each ring
            # is only drawn where it clears the disc; the near half crosses it.
            for inset in (0, 7, 14):
                rect = pygame.Rect(center[0] - 132 + inset, center[1] - 33 + inset // 2, 264 - inset * 2, 66 - inset)
                pygame.draw.arc(surface, (150, 166, 196), rect, math.pi, math.tau, 2)
                pygame.draw.arc(surface, (150, 166, 196), rect, 0.0, 0.85, 2)
                pygame.draw.arc(surface, (150, 166, 196), rect, math.pi - 0.85, math.pi, 2)

        if self._wind_age > 0:
            speed = 155
            for i in range(10):
                y = 255 + i * 17
                x = 395 + int((self._time * speed + i * 47) % 220)
                pygame.draw.line(surface, (188, 220, 246), (x - 26, y), (x + 16, y - 4), 4)
            pygame.draw.ellipse(surface, (58, 77, 139), (530, 340, 70, 34))
            pygame.draw.ellipse(surface, (133, 169, 221), (539, 347, 51, 20), 3)

        if self._distance_age > 0:
            sun = (362, 326)
            pygame.draw.circle(surface, (250, 204, 68), sun, 19)
            for step in range(1, 7):
                x = sun[0] + step * 35
                alpha_color = (245 - step * 15, 213 - step * 12, 103)
                pygame.draw.circle(surface, alpha_color, (x, 326), max(2, 8 - step))
            draw_centered_text(surface, self.context.typography, "≈4h", center=(505, 446), size=18, color=(237, 228, 194), role=FontRole.CONTROL)

        if self._year_age > 0:
            if authored:
                # Zoomed-out viewing lens over the baked planet for the orbit.
                pygame.draw.circle(surface, (36, 50, 84), center, 132)
                pygame.draw.circle(surface, (154, 112, 62), center, 132, 6)
                pygame.draw.circle(surface, (236, 199, 120), center, 125, 2)
            orbit = pygame.Rect(392, 245, 226, 164)
            pygame.draw.circle(surface, (250, 204, 68), (505, 327), 19)
            pygame.draw.ellipse(surface, (75, 84, 117), orbit, 2)
            phase = self._time * 0.34
            pos = (orbit.centerx + int(math.cos(phase) * orbit.width / 2), orbit.centery + int(math.sin(phase) * orbit.height / 2))
            pygame.draw.circle(surface, (75, 112, 194), pos, 12)
            draw_centered_text(surface, self.context.typography, "165y / 16h", center=(505, 450), size=18, color=(237, 228, 194), role=FontRole.CONTROL)

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
        if discovery_id == "distance":
            pygame.draw.circle(surface, (249, 202, 67), (cx - 19, cy), 8)
            pygame.draw.circle(surface, (75, 112, 194), (cx + 22, cy), 9)
            pygame.draw.line(surface, (178, 184, 194), (cx - 8, cy), (cx + 10, cy), 3)
        elif discovery_id == "year":
            pygame.draw.ellipse(surface, (115, 124, 153), (cx - 27, cy - 18, 54, 36), 3)
            pygame.draw.circle(surface, (75, 112, 194), (cx + 24, cy), 7)
        elif discovery_id == "winds":
            for off in (-11, 0, 11):
                pygame.draw.line(surface, (96, 145, 211), (cx - 24, cy + off), (cx + 22, cy + off - 5), 4)
        else:
            pygame.draw.circle(surface, (75, 112, 194), (cx, cy), 20)
            pygame.draw.ellipse(surface, (119, 130, 151), (cx - 28, cy - 9, 56, 18), 3)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
