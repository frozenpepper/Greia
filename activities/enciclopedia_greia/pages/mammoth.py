"""Woolly mammoth entry: cold adaptations, elephant kinship and timeline context."""

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
        draw_history_action_button,
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
        draw_history_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class MammothDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MammothDiscovery("coat", "mammoth.coat", "encyclopedia.history.mammoth.coat", (250, 190)),
    MammothDiscovery("ears", "mammoth.ears", "encyclopedia.history.mammoth.ears", (755, 190)),
    MammothDiscovery("elephants", "mammoth.elephants", "encyclopedia.history.mammoth.elephants", (250, 420)),
    MammothDiscovery("time", "mammoth.time", "encyclopedia.history.mammoth.time", (755, 420)),
)


class MammothPage(EncyclopediaPage):
    page_id = "history.mammoth"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "mammoth.intro"
        self._coat_age = 0.0
        self._ears_age = 0.0
        self._compare_age = 0.0
        self._timeline_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.mammoth.intro")
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

    def _trigger_main(self) -> None:
        # Action button now correctly activates the currently selected discovery
        self._activate(self._selected)

    def update(self, dt: float) -> None:
        self._time += dt
        self._coat_age = max(0.0, self._coat_age - dt)
        self._ears_age = max(0.0, self._ears_age - dt)
        self._compare_age = max(0.0, self._compare_age - dt)
        self._timeline_age = max(0.0, self._timeline_age - dt)

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
                cue = encyclopedia_focus_cue("history", disc.discovery_id, "name")
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
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "coat":
            self._coat_age = 5.0
        elif item.discovery_id == "ears":
            self._ears_age = 5.0
        elif item.discovery_id == "elephants":
            self._compare_age = 5.0
        else:
            self._timeline_age = 5.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((219, 232, 234))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("mammoth.title"), center=(500, 92), size=40, color=self.context.palette.ink, role=FontRole.DISPLAY)
        self._draw_scene(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_history_action_button(
            surface, (512, 460), history="mammoth", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default")

    def _draw_scene(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (236, 242, 241), (325, 370, 365, 90), border_radius=30)
        # Mammoth body.
        body = (131, 91, 64)
        fur = (105, 72, 52)
        pygame.draw.ellipse(surface, body, (425, 275, 170, 100))
        pygame.draw.circle(surface, body, (590, 300), 53)
        pygame.draw.line(surface, body, (610, 320), (635, 385), 24)
        for x in (455, 505, 555):
            pygame.draw.line(surface, body, (x, 345), (x - 3, 410), 20)
        pygame.draw.arc(surface, (233, 220, 188), (584, 305, 76, 90), 0.25, math.pi * 1.35, 7)
        if self._coat_age > 0.0:
            # Fur with layered depth and highlight
            for row in range(5):
                y = 282 + row * 18
                for col in range(8):
                    x = 442 + col * 20 + (row % 2) * 10
                    pygame.draw.line(surface, (85, 58, 42), (x + 1, y + 1), (x - 3, y + 22), 6)
                    pygame.draw.line(surface, fur, (x, y), (x - 4, y + 22), 5)
                    pygame.draw.line(surface, (130, 95, 70), (x, y), (x - 2, y + 12), 2)
            pygame.draw.arc(surface, (231, 197, 135), (442, 288, 132, 70), math.pi, math.tau, 7)
            pygame.draw.arc(surface, (255, 225, 175, 60), (444, 290, 128, 66), math.pi, math.tau, 3)
        if self._ears_age > 0.0:
            pygame.draw.ellipse(surface, (116, 82, 64), (563, 286, 30, 38))
            pygame.draw.ellipse(surface, (177, 135, 101), (710, 280, 72, 92))
            pygame.draw.circle(surface, (177, 135, 101), (725, 315), 42)
            pygame.draw.line(surface, (177, 135, 101), (744, 330), (763, 388), 19)
        if self._compare_age > 0.0:
            # Modern elephant comparison, separated from mammoth silhouette.
            color = (154, 151, 143)
            pygame.draw.ellipse(surface, color, (690, 310, 105, 62))
            pygame.draw.circle(surface, color, (790, 320), 35)
            pygame.draw.ellipse(surface, (174, 169, 159), (760, 290, 48, 55))
            pygame.draw.line(surface, color, (803, 335), (817, 390), 16)
            for x in (713, 748, 780):
                pygame.draw.line(surface, color, (x, 358), (x, 406), 14)
        if self._timeline_age > 0.0:
            pygame.draw.line(surface, (83, 80, 74), (355, 235), (665, 235), 5)
            pygame.draw.circle(surface, (117, 144, 85), (380, 235), 10)
            pygame.draw.circle(surface, (139, 94, 67), (540, 235), 10)
            pygame.draw.circle(surface, (218, 168, 118), (635, 235), 10)
            draw_centered_text(surface, self.context.typography, "66 000 000", center=(380, 210), size=14, color=(72, 68, 62))
            draw_centered_text(surface, self.context.typography, "4 000", center=(635, 210), size=14, color=(72, 68, 62))

    @staticmethod
    def _draw_icon(surface: pygame.Surface, item: MammothDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "coat":
            for dx in (-18, -6, 6, 18):
                pygame.draw.line(surface, (112, 78, 55), (cx + dx, cy - 18), (cx + dx - 4, cy + 18), 5)
        elif item.discovery_id == "ears":
            pygame.draw.ellipse(surface, (145, 103, 76), (cx - 22, cy - 18, 22, 36))
            pygame.draw.ellipse(surface, (181, 144, 111), (cx + 2, cy - 26, 34, 52))
        elif item.discovery_id == "elephants":
            pygame.draw.circle(surface, (129, 91, 67), (cx - 14, cy), 17)
            pygame.draw.circle(surface, (158, 154, 146), (cx + 15, cy), 17)
        else:
            pygame.draw.line(surface, (86, 80, 70), (cx - 25, cy), (cx + 25, cy), 5)
            pygame.draw.circle(surface, (117, 144, 85), (cx - 16, cy), 6)
            pygame.draw.circle(surface, (219, 170, 118), (cx + 18, cy), 6)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (253, 249, 233), item.center, 37)
            pygame.draw.circle(surface, (81, 74, 65), item.center, 37, 3)
            self._draw_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (253, 249, 233), panel, border_radius=22)
        pygame.draw.rect(surface, (81, 74, 65), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 51, 47))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 51, 47))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
