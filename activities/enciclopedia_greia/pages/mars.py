"""Mars entry: rusty color, near-Earth day, ancient water, and Olympus Mons."""

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
class MarsDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MarsDiscovery("red", "mars.red", "encyclopedia.space.mars.red", (250, 190)),
    MarsDiscovery("day", "mars.day", "encyclopedia.space.mars.day", (755, 190)),
    MarsDiscovery("water", "mars.water", "encyclopedia.space.mars.water", (250, 420)),
    MarsDiscovery("olympus", "mars.olympus", "encyclopedia.space.mars.olympus", (755, 420)),
)

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.space.mars.observatory"


class MarsPage(EncyclopediaPage):
    page_id = "space.mars"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "mars.intro"
        self._rust_age = 0.0
        self._day_age = 0.0
        self._water_age = 0.0
        self._olympus_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.mars.intro")
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
        self._rust_age = max(0.0, self._rust_age - dt)
        self._day_age = max(0.0, self._day_age - dt)
        self._water_age = max(0.0, self._water_age - dt)
        self._olympus_age = max(0.0, self._olympus_age - dt)

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
        if discovery.discovery_id == "red":
            self._rust_age = 4.0
        elif discovery.discovery_id == "day":
            self._day_age = 4.5
        elif discovery.discovery_id == "water":
            self._water_age = 4.5
        else:
            self._olympus_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((30, 28, 49))
            for index in range(30):
                x = (index * 97 + 21) % 1000
                y = 76 + (index * 61) % 470
                pygame.draw.circle(surface, (226, 229, 238), (x, y), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("mars.title"),
            (246, 238, 220),
        )
        self._draw_mars(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="mars", time=getattr(self, '_time', 0.0), active=True
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

    def _draw_mars(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = (505, 326)
        radius = 94
        if not authored:
            # Soft drop shadow + rim light for depth
            shadow = pygame.Surface((radius * 2 + 18, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (40, 28, 20, 34), shadow.get_rect())
            surface.blit(shadow, (center[0] - radius - 9, center[1] + radius + 7))
            base = (184, 92, 63) if self._rust_age <= 0 else (210, 103, 64)
            pygame.draw.circle(surface, (58, 42, 38), center, radius + 2)
            pygame.draw.circle(surface, base, center, radius)
            # Subtle terminator highlight (not during rust pulse)
            if self._rust_age == 0:
                hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(hl, (255, 225, 190, 22), (radius // 2, 8, radius, radius // 2))
                surface.blit(hl, (center[0] - radius, center[1] - radius))
            pygame.draw.circle(surface, (255, 245, 220, 14), center, radius - 8, 2)
            # Craters — more, with inner highlight
            for dx, dy, rr, depth in ((-38, -28, 16, 0.52), (27, -42, 11, 0.48), (43, 18, 18, 0.55), (-18, 44, 13, 0.50), (12, 22, 9, 0.44), (-42, 12, 12, 0.46)):
                cx, cy = center[0] + dx, center[1] + dy
                pygame.draw.circle(surface, (133, 72, 57), (cx, cy), rr)
                pygame.draw.circle(surface, (175, 105, 80), (cx - 2, cy - 2), max(4, int(rr * 0.62)))
                pygame.draw.circle(surface, (215, 137, 92), (cx - 3, cy - 3), max(3, rr - 6), 2)
                pygame.draw.circle(surface, (90, 52, 40), (cx, cy), rr, 1)
            pygame.draw.arc(surface, (231, 211, 184), (450, 238, 110, 42), 0.1, 3.0, 5)
            pygame.draw.arc(surface, (231, 211, 184), (459, 371, 91, 33), 3.2, 6.0, 4)
        if self._rust_age > 0:
            for i in range(12):
                angle = i * math.tau / 12 + self._time * 0.3
                x = center[0] + int(math.cos(angle) * 72)
                y = center[1] + int(math.sin(angle) * 58)
                pygame.draw.circle(surface, (238, 139, 74), (x, y), 4)

        if self._day_age > 0:
            orbit = pygame.Rect(426, 247, 158, 158)
            pygame.draw.arc(surface, (246, 213, 92), orbit, 0.2, 5.4, 5)
            angle = self._time * 1.4
            marker = (
                center[0] + int(math.cos(angle) * 82),
                center[1] + int(math.sin(angle) * 82),
            )
            pygame.draw.circle(surface, (246, 213, 92), marker, 7)
            draw_centered_text(
                surface,
                self.context.typography,
                "24.6h",
                center=(505, 436),
                size=18,
                color=(244, 230, 194),
                role=FontRole.CONTROL,
            )

        if self._water_age > 0:
            pygame.draw.lines(surface, (84, 161, 203), False, [(450, 292), (476, 311), (465, 338), (493, 362), (523, 387)], 6)
            pygame.draw.ellipse(surface, (75, 142, 188), (520, 370, 72, 29), 4)
            pygame.draw.line(surface, (244, 226, 155), (445, 410), (589, 410), 2)

        if self._olympus_age > 0:
            ground = 444
            pygame.draw.line(surface, (227, 213, 185), (382, ground), (640, ground), 3)
            pygame.draw.polygon(surface, (143, 75, 59), [(410, ground), (490, 278), (570, ground)])
            pygame.draw.polygon(surface, (205, 123, 78), [(465, 331), (490, 278), (515, 331)])
            pygame.draw.circle(surface, (228, 215, 185), (603, ground - 36), 4)
            pygame.draw.line(surface, (228, 215, 185), (603, ground - 32), (603, ground - 10), 3)
            pygame.draw.line(surface, (228, 215, 185), (596, ground - 23), (610, ground - 23), 2)

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
        if discovery_id == "red":
            pygame.draw.circle(surface, (194, 95, 63), (cx, cy), 20)
            pygame.draw.circle(surface, (235, 139, 74), (cx + 8, cy - 7), 7)
        elif discovery_id == "day":
            pygame.draw.circle(surface, (194, 95, 63), (cx, cy), 17)
            pygame.draw.arc(surface, (235, 194, 75), (cx - 25, cy - 25, 50, 50), 0.2, 5.0, 4)
        elif discovery_id == "water":
            pygame.draw.lines(surface, (74, 150, 198), False, [(cx - 21, cy - 14), (cx - 8, cy), (cx - 16, cy + 18), (cx + 19, cy + 12)], 5)
        else:
            pygame.draw.polygon(surface, (181, 93, 64), [(cx - 25, cy + 20), (cx, cy - 23), (cx + 25, cy + 20)])
            pygame.draw.circle(surface, (235, 221, 185), (cx + 24, cy + 12), 4)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
