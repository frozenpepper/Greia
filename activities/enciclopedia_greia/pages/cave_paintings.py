"""Cave-art entry: reveal ancient imagery, pigments, hand stencils and uncertainty."""

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
class CaveDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    CaveDiscovery("images", "cave_paintings.images", "encyclopedia.history.cave_paintings.images", (250, 190)),
    CaveDiscovery("pigments", "cave_paintings.pigments", "encyclopedia.history.cave_paintings.pigments", (755, 190)),
    CaveDiscovery("hands", "cave_paintings.hands", "encyclopedia.history.cave_paintings.hands", (250, 420)),
    CaveDiscovery("uncertainty", "cave_paintings.uncertainty", "encyclopedia.history.cave_paintings.uncertainty", (755, 420)),
)


class CavePaintingsPage(EncyclopediaPage):
    page_id = "history.cave_paintings"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "cave_paintings.intro"
        self._lamp_step = 0
        self._pigment_age = 0.0
        self._hands_age = 0.0
        self._uncertainty_age = 0.0
        self._child_mark_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.cave_paintings.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._pigment_age = max(0.0, self._pigment_age - dt)
        self._hands_age = max(0.0, self._hands_age - dt)
        self._uncertainty_age = max(0.0, self._uncertainty_age - dt)
        self._child_mark_age = max(0.0, self._child_mark_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._activate(hit)
            elif event.kind is PageInputKind.POINTER_PRESS and pygame.Rect(385, 255, 250, 165).collidepoint(point):
                # Temporary child-authored overlay only; never modifies source art.
                self._child_mark_age = 4.0
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
        if item.discovery_id == "images":
            self._lamp_step = (self._lamp_step + 1) % 3
        elif item.discovery_id == "pigments":
            self._pigment_age = 5.0
        elif item.discovery_id == "hands":
            self._hands_age = 5.0
        else:
            self._uncertainty_age = 5.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((79, 68, 59))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("cave_paintings.title"), center=(500, 92), size=40, color=(246, 228, 189), role=FontRole.DISPLAY)
        self._draw_cave(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default")

    def _draw_cave(self, surface: pygame.Surface) -> None:
        wall = pygame.Rect(350, 225, 320, 235)
        pygame.draw.rect(surface, (132, 101, 76), wall, border_radius=35)
        for index in range(14):
            x = wall.x + 24 + (index * 47) % (wall.width - 40)
            y = wall.y + 20 + (index * 37) % (wall.height - 35)
            pygame.draw.circle(surface, (116, 88, 68), (x, y), 4 + index % 5)

        lamp_positions = ((395, 410), (505, 390), (615, 410))
        lamp = lamp_positions[self._lamp_step]
        pygame.draw.circle(surface, (246, 190, 79), lamp, 18)
        pygame.draw.circle(surface, (246, 190, 79), lamp, 30, 3)
        reveal_center = (505 + (self._lamp_step - 1) * 78, 315)
        pygame.draw.circle(surface, (226, 177, 89), reveal_center, 92, 2)

        # Observed ancient-style forms: animal, hand/stencil, simple geometry.
        color = (121, 48, 39)
        ax, ay = reveal_center
        pygame.draw.ellipse(surface, color, (ax - 60, ay - 12, 82, 35), 6)
        pygame.draw.line(surface, color, (ax - 40, ay + 12), (ax - 48, ay + 42), 5)
        pygame.draw.line(surface, color, (ax + 5, ay + 12), (ax + 15, ay + 42), 5)
        pygame.draw.line(surface, color, (ax + 15, ay - 4), (ax + 42, ay - 26), 5)
        pygame.draw.circle(surface, color, (ax + 42, ay - 28), 8, 3)
        pygame.draw.polygon(surface, (183, 83, 51), [(ax - 80, ay + 56), (ax - 57, ay + 24), (ax - 34, ay + 56)], 4)

        if self._pigment_age > 0.0:
            for i, pigment in enumerate(((156, 62, 42), (201, 143, 67), (71, 58, 51), (186, 177, 144))):
                pygame.draw.circle(surface, pigment, (395 + i * 48, 445), 15)
                pygame.draw.circle(surface, (231, 213, 175), (395 + i * 48, 445), 15, 2)

        if self._hands_age > 0.0:
            hx, hy = 580, 315
            pygame.draw.circle(surface, (213, 164, 112), (hx, hy + 14), 18, 5)
            for dx in (-18, -9, 0, 9, 18):
                pygame.draw.line(surface, (213, 164, 112), (hx + dx // 2, hy + 6), (hx + dx, hy - 27 + abs(dx) // 2), 5)

        if self._uncertainty_age > 0.0:
            pygame.draw.circle(surface, (241, 224, 178), (620, 264), 25)
            draw_centered_text(surface, self.context.typography, "?", center=(620, 264), size=28, color=(88, 72, 59), role=FontRole.DISPLAY)

        if self._child_mark_age > 0.0:
            # Clearly separate temporary overlay in Greia gold.
            pulse = 2 + int((math.sin(self._time * 6.0) + 1.0) * 2)
            pygame.draw.line(surface, (244, 198, 70), (470, 365), (495, 342), 4 + pulse)
            pygame.draw.line(surface, (244, 198, 70), (495, 342), (520, 367), 4 + pulse)

    @staticmethod
    def _draw_icon(surface: pygame.Surface, item: CaveDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "images":
            pygame.draw.circle(surface, (242, 189, 78), (cx - 14, cy), 10)
            pygame.draw.ellipse(surface, (132, 56, 42), (cx + 1, cy - 10, 30, 20), 4)
        elif item.discovery_id == "pigments":
            for dx, color in ((-18, (151, 60, 42)), (0, (199, 140, 65)), (18, (75, 60, 52))):
                pygame.draw.circle(surface, color, (cx + dx, cy), 9)
        elif item.discovery_id == "hands":
            pygame.draw.circle(surface, (203, 151, 103), (cx, cy + 8), 12, 4)
            for dx in (-14, -7, 0, 7, 14):
                pygame.draw.line(surface, (203, 151, 103), (cx + dx // 2, cy + 2), (cx + dx, cy - 19), 4)
        else:
            draw_centered_text(surface, pygame.font.Font(None, 1), "", center=(cx, cy), size=1, color=(0, 0, 0)) if False else None
            pygame.draw.circle(surface, (232, 217, 177), (cx, cy), 22)
            pygame.draw.line(surface, (89, 72, 58), (cx, cy - 11), (cx, cy + 3), 4)
            pygame.draw.circle(surface, (89, 72, 58), (cx, cy + 13), 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (247, 232, 196), item.center, 37)
            pygame.draw.circle(surface, (72, 61, 53), item.center, 37, 3)
            self._draw_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (247, 232, 196), panel, border_radius=22)
        pygame.draw.rect(surface, (72, 61, 53), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 47, 42))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 47, 42))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
