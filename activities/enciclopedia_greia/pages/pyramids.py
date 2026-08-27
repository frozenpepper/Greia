"""Ancient Egyptian pyramids entry: human engineering, workforce and structure."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class PyramidDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    PyramidDiscovery("blocks", "pyramids.blocks", "encyclopedia.history.pyramids.blocks", (250, 190)),
    PyramidDiscovery("workers", "pyramids.workers", "encyclopedia.history.pyramids.workers", (755, 190)),
    PyramidDiscovery("inside", "pyramids.inside", "encyclopedia.history.pyramids.inside", (250, 420)),
    PyramidDiscovery("engineering", "pyramids.engineering", "encyclopedia.history.pyramids.engineering", (755, 420)),
)


class PyramidBuildModel:
    """Own the finite schematic course-building state and timed evidence reveals."""

    MAX_COURSES = 6

    def __init__(self) -> None:
        self.courses = 1
        self.workers_age = 0.0
        self.inside_age = 0.0
        self.engineering_age = 0.0

    def update(self, dt: float) -> None:
        self.workers_age = max(0.0, self.workers_age - dt)
        self.inside_age = max(0.0, self.inside_age - dt)
        self.engineering_age = max(0.0, self.engineering_age - dt)

    def add_course(self) -> None:
        self.courses = 1 if self.courses >= self.MAX_COURSES else self.courses + 1


class PyramidsPage(EncyclopediaPage):
    page_id = "history.pyramids"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = PyramidBuildModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "pyramids.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.pyramids.intro")

    def update(self, dt: float) -> None:
        self._model.update(dt)

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
        if item.discovery_id == "blocks":
            self._model.add_course()
        elif item.discovery_id == "workers":
            self._model.workers_age = 5.0
        elif item.discovery_id == "inside":
            self._model.inside_age = 5.0
        else:
            self._model.engineering_age = 5.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((240, 215, 151))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("pyramids.title"), center=(500, 92), size=40, color=self.context.palette.ink, role=FontRole.DISPLAY)
        self._draw_scene(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default")

    def _draw_scene(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, (250, 202, 75), (810, 155), 36)
        pygame.draw.rect(surface, (221, 181, 104), (310, 392, 395, 75), border_radius=25)
        # Schematic courses: deliberately diagrammatic, not a literal construction sequence.
        base_y = 405
        for course in range(self._model.courses):
            width = 260 - course * 34
            height = 24
            x = 505 - width // 2
            y = base_y - course * height
            blocks = max(2, 7 - course)
            block_w = width // blocks
            for block in range(blocks):
                rect = pygame.Rect(x + block * block_w, y, block_w - 2, height - 2)
                pygame.draw.rect(surface, (207, 168, 102), rect)
                pygame.draw.rect(surface, (139, 107, 72), rect, 2)

        if self._model.workers_age > 0.0:
            for i, x in enumerate((360, 400, 650, 690)):
                pygame.draw.circle(surface, (133, 82, 56), (x, 340 + (i % 2) * 12), 8)
                pygame.draw.line(surface, (133, 82, 56), (x, 348), (x, 375), 5)
                pygame.draw.line(surface, (133, 82, 56), (x, 357), (x - 10, 370), 4)
                pygame.draw.line(surface, (133, 82, 56), (x, 357), (x + 10, 370), 4)

        if self._model.inside_age > 0.0:
            pygame.draw.polygon(surface, (244, 221, 166), [(505, 235), (390, 405), (620, 405)])
            pygame.draw.line(surface, (112, 83, 62), (505, 268), (505, 375), 5)
            pygame.draw.rect(surface, (112, 83, 62), (493, 330, 36, 25), 3)
            pygame.draw.line(surface, (112, 83, 62), (505, 300), (540, 325), 4)

        if self._model.engineering_age > 0.0:
            # Quarry/sledge/ramp schematic beside the pyramid.
            pygame.draw.polygon(surface, (186, 137, 82), [(690, 390), (820, 390), (820, 355), (690, 385)])
            pygame.draw.rect(surface, (162, 124, 84), (720, 338, 54, 34))
            pygame.draw.line(surface, (101, 80, 64), (710, 378), (785, 378), 5)
            for x in (725, 755, 780):
                pygame.draw.circle(surface, (101, 80, 64), (x, 384), 5)

    @staticmethod
    def _draw_icon(surface: pygame.Surface, item: PyramidDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "blocks":
            for row in range(3):
                for col in range(3 - row):
                    pygame.draw.rect(surface, (198, 156, 92), (cx - 25 + col * 18 + row * 9, cy + 12 - row * 15, 16, 12))
        elif item.discovery_id == "workers":
            for dx in (-14, 14):
                pygame.draw.circle(surface, (137, 84, 56), (cx + dx, cy - 8), 7)
                pygame.draw.line(surface, (137, 84, 56), (cx + dx, cy), (cx + dx, cy + 18), 5)
        elif item.discovery_id == "inside":
            pygame.draw.polygon(surface, (200, 158, 94), [(cx - 27, cy + 20), (cx, cy - 25), (cx + 27, cy + 20)])
            pygame.draw.line(surface, (84, 68, 57), (cx, cy - 10), (cx, cy + 15), 4)
        else:
            pygame.draw.line(surface, (112, 85, 65), (cx - 25, cy + 16), (cx + 22, cy - 12), 6)
            pygame.draw.rect(surface, (188, 142, 83), (cx - 7, cy - 8, 26, 20))

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 245, 214), item.center, 37)
            pygame.draw.circle(surface, (91, 70, 55), item.center, 37, 3)
            self._draw_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 245, 214), panel, border_radius=22)
        pygame.draw.rect(surface, (91, 70, 55), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (56, 49, 43))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (56, 49, 43))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
