"""Pyramids golden master: authored archaeological diorama with factual overlays."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_EXCAVATION,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_EXCAVATION,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class PyramidDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    PyramidDiscovery(
        "blocks",
        "pyramids.blocks",
        "encyclopedia.history.pyramids.blocks",
        (235, 195),
    ),
    PyramidDiscovery(
        "workers",
        "pyramids.workers",
        "encyclopedia.history.pyramids.workers",
        (775, 195),
    ),
    PyramidDiscovery(
        "inside",
        "pyramids.inside",
        "encyclopedia.history.pyramids.inside",
        (235, 405),
    ),
    PyramidDiscovery(
        "engineering",
        "pyramids.engineering",
        "encyclopedia.history.pyramids.engineering",
        (775, 405),
    ),
)


class PyramidBuildModel:
    """Own finite construction/reveal state; rendering consumes it."""

    MAX_COURSES = 6
    REVEAL_SECONDS = 5.0

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

    def reveal_workers(self) -> None:
        self.workers_age = self.REVEAL_SECONDS

    def reveal_inside(self) -> None:
        self.inside_age = self.REVEAL_SECONDS

    def reveal_engineering(self) -> None:
        self.engineering_age = self.REVEAL_SECONDS


class PyramidsPage(EncyclopediaPage):
    page_id = "history.pyramids"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = PyramidBuildModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "pyramids.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.pyramids.intro")

    def update(self, dt: float) -> None:
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
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
            self._selected = grid_step(
                self._selected,
                event.command,
                columns=2,
                count=len(DISCOVERIES),
            )

    def _activate(self, index: int) -> None:
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "blocks":
            self._model.add_course()
        elif item.discovery_id == "workers":
            self._model.reveal_workers()
        elif item.discovery_id == "inside":
            self._model.reveal_inside()
        else:
            self._model.reveal_engineering()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.history.pyramids.diorama",
        ):
            surface.fill((240, 215, 151))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("pyramids.title"),
            self.context.palette.ink,
        )
        self._draw_reveals(surface)
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_EXCAVATION,
            )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(360, 575),
            height=190,
            variant="default",
        )

    def _recent(self, discovery_id: str) -> bool:
        ages = {
            "workers": self._model.workers_age,
            "inside": self._model.inside_age,
            "engineering": self._model.engineering_age,
        }
        return ages.get(discovery_id, 0.0) > 0

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._model.courses > 1:
            for course in range(self._model.courses - 1):
                width = 170 - course * 20
                y = 446 - course * 17
                pygame.draw.rect(
                    surface,
                    (245, 210, 139),
                    (505 - width // 2, y, width, 14),
                    border_radius=3,
                )

        if self._model.workers_age > 0:
            for x in (350, 390, 655, 695):
                pygame.draw.circle(surface, (255, 221, 104), (x, 455), 12, 4)

        if self._model.inside_age > 0:
            # Outlined inner chambers so the cross-section reads clearly.
            pygame.draw.polygon(
                surface,
                (255, 246, 208),
                [(505, 215), (405, 430), (605, 430)],
            )
            pygame.draw.line(surface, (93, 66, 46), (505, 265), (505, 395), 5)
            pygame.draw.rect(surface, (93, 66, 46), (488, 344, 34, 24), 3)
            # Burial chamber highlight.
            pygame.draw.rect(surface, (255, 220, 100), (488, 344, 34, 24), 4)

        if self._model.engineering_age > 0:
            # Sledge direction of travel.
            pygame.draw.line(
                surface,
                (255, 224, 96),
                (650, 438),
                (865, 405),
                6,
            )
            pygame.draw.polygon(
                surface,
                (255, 224, 96),
                [(865, 405), (846, 397), (850, 417)],
            )

        if self._model.engineering_age > 0 and self._model.courses > 1:
            # A clearly outlined base block (the "first course" being placed).
            base_width = 110
            pygame.draw.rect(
                surface,
                (255, 240, 170),
                (505 - base_width // 2, 432, base_width, 16),
                border_radius=3,
            )
            pygame.draw.rect(
                surface,
                (93, 66, 46),
                (505 - base_width // 2, 432, base_width, 16),
                width=3,
                border_radius=3,
            )
            # Two label arrows pointing at the base block.
            for arrow_x in (505 - base_width // 2 - 10, 505 + base_width // 2 + 10):
                direction = 1 if arrow_x < 505 else -1
                pygame.draw.line(surface, (93, 66, 46), (arrow_x, 440), (arrow_x + direction * 18, 440), 3)
                pygame.draw.polygon(
                    surface,
                    (93, 66, 46),
                    [
                        (arrow_x + direction * 18, 440),
                        (arrow_x + direction * 12, 435),
                        (arrow_x + direction * 12, 445),
                    ],
                )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "blocks":
            for row in range(3):
                for col in range(3 - row):
                    pygame.draw.rect(
                        surface,
                        (198, 156, 92),
                        (cx - 25 + col * 18 + row * 9, cy + 12 - row * 15, 16, 12),
                    )
        elif discovery_id == "workers":
            for dx in (-14, 14):
                pygame.draw.circle(surface, (137, 84, 56), (cx + dx, cy - 8), 7)
                pygame.draw.line(
                    surface,
                    (137, 84, 56),
                    (cx + dx, cy),
                    (cx + dx, cy + 18),
                    5,
                )
        elif discovery_id == "inside":
            pygame.draw.polygon(
                surface,
                (200, 158, 94),
                [(cx - 27, cy + 20), (cx, cy - 25), (cx + 27, cy + 20)],
            )
            pygame.draw.line(surface, (84, 68, 57), (cx, cy - 10), (cx, cy + 15), 4)
        else:
            pygame.draw.line(
                surface,
                (112, 85, 65),
                (cx - 25, cy + 16),
                (cx + 22, cy - 12),
                6,
            )
            pygame.draw.rect(surface, (188, 142, 83), (cx - 7, cy - 8, 26, 20))
