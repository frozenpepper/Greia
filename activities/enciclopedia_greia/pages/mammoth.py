"""Woolly mammoth entry: cold adaptations, elephant kinship and timeline context."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
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

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.mammoth.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._coat_age = max(0.0, self._coat_age - dt)
        self._ears_age = max(0.0, self._ears_age - dt)
        self._compare_age = max(0.0, self._compare_age - dt)
        self._timeline_age = max(0.0, self._timeline_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
        else:
            self._selected = grid_step(self._selected, event.command, columns=2, count=len(DISCOVERIES))

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
            for row in range(4):
                y = 285 + row * 20
                for col in range(7):
                    x = 445 + col * 22 + (row % 2) * 9
                    pygame.draw.line(surface, fur, (x, y), (x - 4, y + 22), 5)
            pygame.draw.arc(surface, (231, 197, 135), (442, 288, 132, 70), math.pi, math.tau, 7)
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
