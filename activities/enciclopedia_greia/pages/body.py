"""My Body section: five visual callouts around one friendly body schematic."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class BodyTarget:
    target_id: str
    page_id: str
    center: tuple[int, int]
    connector: tuple[int, int]


BODY_TARGETS = (
    BodyTarget("senses", "body.senses", (250, 180), (505, 176)),
    BodyTarget("teeth", "body.teeth", (755, 180), (505, 210)),
    BodyTarget("lungs", "body.lungs", (250, 405), (486, 300)),
    BodyTarget("heart", "body.heart", (755, 405), (520, 334)),
    BodyTarget("bones", "body.bones", (505, 470), (555, 395)),
)


class BodyPage(EncyclopediaPage):
    page_id = "body"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._target_rects = tuple(
            pygame.Rect(target.center[0] - 43, target.center[1] - 43, 86, 86)
            for target in BODY_TARGETS
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.intro")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(self._target_rects) if rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._open_selected()
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._open_selected()
            return
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(BODY_TARGETS),
        )

    def _open_selected(self) -> None:
        self.context.host.open_page(BODY_TARGETS[self._selected].page_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((249, 232, 227))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("section.body"),
            center=(500, 90),
            size=40,
            color=self.context.palette.ink,
        )
        self._draw_body(surface)
        self._draw_targets(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "lilli",
            position=(900, 565),
            height=155,
            variant="happy",
            fallback_color=(229, 137, 183),
        )

    def _draw_body(self, surface: pygame.Surface) -> None:
        skin = (234, 184, 151)
        bone = (244, 235, 207)
        pygame.draw.circle(surface, skin, (510, 180), 52)
        pygame.draw.rect(surface, skin, (445, 225, 130, 220), border_radius=55)
        pygame.draw.line(surface, skin, (455, 255), (380, 405), 28)
        pygame.draw.line(surface, skin, (565, 255), (640, 405), 28)
        pygame.draw.line(surface, skin, (478, 430), (450, 545), 32)
        pygame.draw.line(surface, skin, (542, 430), (570, 545), 32)

        # Small animated anatomy hints make the section itself alive without
        # duplicating the deeper teaching state owned by each final entry.
        breath = 1.0 + 0.06 * math.sin(self._time * 1.6)
        lung_w = int(36 * breath)
        pygame.draw.ellipse(surface, (226, 154, 161), (486 - lung_w, 267, lung_w, 76))
        pygame.draw.ellipse(surface, (226, 154, 161), (510, 267, lung_w, 76))

        beat = 1.0 + 0.08 * max(0.0, math.sin(self._time * 6.0))
        heart_size = int(20 * beat)
        hx, hy = 516, 332
        pygame.draw.circle(surface, (203, 70, 82), (hx - heart_size // 3, hy), heart_size // 2)
        pygame.draw.circle(surface, (203, 70, 82), (hx + heart_size // 3, hy), heart_size // 2)
        pygame.draw.polygon(surface, (203, 70, 82), [(hx - heart_size, hy), (hx + heart_size, hy), (hx, hy + heart_size * 2)])

        pygame.draw.line(surface, bone, (510, 220), (510, 425), 5)
        pygame.draw.line(surface, bone, (483, 250), (450, 365), 5)
        pygame.draw.line(surface, bone, (537, 250), (570, 365), 5)

        pygame.draw.arc(surface, (119, 76, 81), (492, 192, 36, 18), 0.15, math.pi - 0.15, 3)
        pygame.draw.circle(surface, (83, 91, 111), (494, 170), 5)
        pygame.draw.circle(surface, (83, 91, 111), (526, 170), 5)

    def _draw_targets(self, surface: pygame.Surface) -> None:
        for index, (target, rect) in enumerate(zip(BODY_TARGETS, self._target_rects)):
            pygame.draw.line(surface, (184, 145, 145), target.center, target.connector, 3)
            pygame.draw.circle(surface, (255, 248, 235), target.center, 37)
            pygame.draw.circle(surface, (96, 66, 70), target.center, 37, 3)
            self._draw_target_icon(surface, target)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    @staticmethod
    def _draw_target_icon(surface: pygame.Surface, target: BodyTarget) -> None:
        cx, cy = target.center
        if target.target_id == "senses":
            pygame.draw.ellipse(surface, (252, 250, 239), (cx - 27, cy - 14, 54, 28))
            pygame.draw.circle(surface, (84, 99, 136), (cx, cy), 9)
            for radius in (20, 28):
                pygame.draw.arc(surface, (90, 145, 193), (cx - radius, cy - radius, radius * 2, radius * 2), math.pi * 0.68, math.pi * 1.32, 2)
        elif target.target_id == "teeth":
            # Teeth must remain readable against the warm-white target disk at
            # netbook scale. A darker enamel fill plus a compact gum-colored
            # outline preserves the pastel palette without making the icon
            # disappear for pre-readers.
            tooth_fill = (238, 220, 184)
            tooth_outline = (132, 91, 83)
            for x in (cx - 18, cx - 6, cx + 6, cx + 18):
                for y in (cy - 7, cy + 9):
                    pygame.draw.circle(surface, tooth_fill, (x, y), 7)
                    pygame.draw.circle(surface, tooth_outline, (x, y), 7, 2)
        elif target.target_id == "lungs":
            pygame.draw.ellipse(surface, (226, 154, 161), (cx - 27, cy - 27, 22, 53))
            pygame.draw.ellipse(surface, (226, 154, 161), (cx + 5, cy - 27, 22, 53))
            pygame.draw.line(surface, (126, 98, 113), (cx, cy - 29), (cx, cy + 12), 4)
        elif target.target_id == "heart":
            pygame.draw.circle(surface, (203, 70, 82), (cx - 10, cy - 4), 14)
            pygame.draw.circle(surface, (203, 70, 82), (cx + 10, cy - 4), 14)
            pygame.draw.polygon(surface, (203, 70, 82), [(cx - 24, cy), (cx + 24, cy), (cx, cy + 29)])
        else:
            pygame.draw.line(surface, (239, 226, 191), (cx - 22, cy - 20), (cx + 22, cy + 20), 9)
            pygame.draw.line(surface, (239, 226, 191), (cx + 22, cy - 20), (cx - 22, cy + 20), 9)
            pygame.draw.circle(surface, (113, 98, 88), (cx, cy), 7)
