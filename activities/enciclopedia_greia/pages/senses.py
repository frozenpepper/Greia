"""Senses entry: sight, hearing, flavor and everyday touch signals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
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
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class SensesDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    SensesDiscovery("sight", "senses.sight", "encyclopedia.body.senses.sight", (250, 190)),
    SensesDiscovery("hearing", "senses.hearing", "encyclopedia.body.senses.hearing", (755, 190)),
    SensesDiscovery("flavor", "senses.flavor", "encyclopedia.body.senses.flavor", (250, 420)),
    SensesDiscovery("touch", "senses.touch", "encyclopedia.body.senses.touch", (755, 420)),
)


class SensesPage(EncyclopediaPage):
    page_id = "body.senses"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "senses.intro"
        self._sight_age = 0.0
        self._hearing_age = 0.0
        self._flavor_step = 0
        self._touch_step = 0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.senses.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        # Use deduped announce for focus changes
        if not self._focus_audio.announce_once(self.context.audio, cue):
            # Fallback to disc.cue_id if focus cue not yet integrated (will fail silently until audio exists)
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt
        self._sight_age = max(0.0, self._sight_age - dt)
        self._hearing_age = max(0.0, self._hearing_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
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
                cue = encyclopedia_focus_cue("body", "senses", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
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
        if discovery.discovery_id == "sight":
            self._sight_age = 4.5
        elif discovery.discovery_id == "hearing":
            self._hearing_age = 4.5
        elif discovery.discovery_id == "flavor":
            self._flavor_step = (self._flavor_step + 1) % 3
        else:
            self._touch_step = (self._touch_step + 1) % 3
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((239, 237, 248))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("senses.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_sense_scene(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "lilli",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(229, 137, 183),
        )

    def _draw_sense_scene(self, surface: pygame.Surface) -> None:
        face = (505, 323)
        skin = (234, 190, 162)
        pygame.draw.circle(surface, skin, face, 92)
        pygame.draw.circle(surface, (255, 255, 250), (474, 300), 15)
        pygame.draw.circle(surface, (255, 255, 250), (536, 300), 15)
        pygame.draw.circle(surface, (83, 94, 118), (474, 300), 7)
        pygame.draw.circle(surface, (83, 94, 118), (536, 300), 7)
        pygame.draw.arc(surface, (116, 74, 77), (475, 338, 60, 37), 0.15, math.pi - 0.15, 4)
        pygame.draw.arc(surface, (139, 94, 86), (402, 286, 30, 66), math.pi / 2, math.pi * 1.5, 5)
        pygame.draw.arc(surface, (139, 94, 86), (578, 286, 30, 66), -math.pi / 2, math.pi / 2, 5)
        pygame.draw.circle(surface, (209, 126, 124), (505, 332), 7)

        brain_center = (505, 245)
        for dx, dy in ((-16, 0), (0, -9), (16, 0), (-7, 13), (10, 14)):
            pygame.draw.circle(surface, (202, 141, 178), (brain_center[0] + dx, brain_center[1] + dy), 17)

        if self._sight_age > 0.0:
            object_center = (650, 284)
            pygame.draw.rect(surface, (95, 165, 95), (630, 264, 40, 40), border_radius=8)
            for eye in ((474, 300), (536, 300)):
                pygame.draw.line(surface, (238, 199, 85), object_center, eye, 3)
                pygame.draw.line(surface, (116, 104, 160), eye, brain_center, 3)

        if self._hearing_age > 0.0:
            source = (650, 360)
            pygame.draw.circle(surface, (94, 148, 197), source, 8)
            for radius in (18, 33, 48):
                pygame.draw.arc(
                    surface,
                    (94, 148, 197),
                    (source[0] - radius, source[1] - radius, radius * 2, radius * 2),
                    math.pi * 0.72,
                    math.pi * 1.28,
                    3,
                )
            pygame.draw.line(surface, (116, 104, 160), (594, 320), brain_center, 3)

        self._draw_flavor_demo(surface)
        self._draw_touch_demo(surface)

    def _draw_flavor_demo(self, surface: pygame.Surface) -> None:
        if self._flavor_step == 0:
            return
        panel = pygame.Rect(620, 395, 150, 82)
        pygame.draw.rect(surface, (252, 248, 237), panel, border_radius=18)
        pygame.draw.rect(surface, (101, 85, 100), panel, 2, border_radius=18)
        pygame.draw.circle(surface, (216, 91, 86), (655, 435), 20)
        pygame.draw.line(surface, (90, 150, 88), (655, 414), (663, 401), 4)
        if self._flavor_step == 1:
            pygame.draw.ellipse(surface, (216, 126, 137), (684, 421, 55, 30))
            for x, y in ((696, 431), (710, 438), (724, 429), (731, 440)):
                pygame.draw.circle(surface, (147, 79, 98), (x, y), 3)
        else:
            pygame.draw.ellipse(surface, (216, 126, 137), (682, 434, 35, 21))
            pygame.draw.arc(surface, (92, 151, 190), (704, 398, 33, 37), 0.2, math.pi * 1.6, 4)
            for index in range(4):
                x = 715 + index * 8
                y = 411 - (index % 2) * 5
                pygame.draw.circle(surface, (112, 180, 110), (x, y), 3)

    def _draw_touch_demo(self, surface: pygame.Surface) -> None:
        if self._touch_step == 0:
            return
        panel = pygame.Rect(240, 394, 150, 82)
        pygame.draw.rect(surface, (252, 248, 237), panel, border_radius=18)
        pygame.draw.rect(surface, (101, 85, 100), panel, 2, border_radius=18)
        hand = [
            (275, 453),
            (267, 426),
            (275, 415),
            (283, 428),
            (288, 405),
            (297, 405),
            (300, 429),
            (308, 409),
            (317, 412),
            (316, 438),
            (330, 427),
            (338, 434),
            (324, 461),
        ]
        pygame.draw.polygon(surface, (234, 190, 162), hand)
        if self._touch_step == 1:
            for index in range(6):
                pygame.draw.line(surface, (100, 157, 198), (345 + index * 5, 412), (340 + index * 5, 444), 3)
        else:
            for x in (348, 363, 378):
                pygame.draw.circle(surface, (226, 132, 77), (x, 429), 9)
                pygame.draw.circle(surface, (250, 202, 102), (x, 429), 4)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: SensesDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "sight":
            pygame.draw.ellipse(surface, (252, 250, 239), (cx - 27, cy - 16, 54, 32))
            pygame.draw.circle(surface, (84, 99, 136), (cx, cy), 10)
            pygame.draw.circle(surface, (54, 53, 60), (cx, cy), 4)
        elif item.discovery_id == "hearing":
            pygame.draw.arc(surface, (183, 129, 119), (cx - 16, cy - 27, 32, 54), -math.pi / 2, math.pi / 2, 6)
            for radius in (20, 29):
                pygame.draw.arc(
                    surface,
                    (86, 145, 195),
                    (cx - radius, cy - radius, radius * 2, radius * 2),
                    math.pi * 0.65,
                    math.pi * 1.35,
                    3,
                )
        elif item.discovery_id == "flavor":
            pygame.draw.circle(surface, (215, 90, 85), (cx - 14, cy - 5), 14)
            pygame.draw.ellipse(surface, (216, 126, 137), (cx + 1, cy - 3, 31, 20))
            for x in (cx + 10, cx + 20, cx + 27):
                pygame.draw.circle(surface, (111, 176, 107), (x, cy - 16), 3)
        else:
            pygame.draw.rect(surface, (121, 166, 205), (cx - 26, cy - 22, 21, 44), border_radius=7)
            pygame.draw.rect(surface, (231, 158, 91), (cx + 5, cy - 22, 21, 44), border_radius=7)
            pygame.draw.line(surface, (92, 77, 83), (cx, cy - 24), (cx, cy + 24), 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (253, 249, 239), item.center, 37)
            pygame.draw.circle(surface, (91, 76, 93), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (253, 249, 239), panel, border_radius=22)
        pygame.draw.rect(surface, (91, 76, 93), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (57, 52, 62))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (57, 52, 62))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
