"""Teeth entry: tooth jobs, primary/permanent sets, layers and care."""

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
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class TeethDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    TeethDiscovery("jobs", "teeth.jobs", "encyclopedia.body.teeth.jobs", (250, 190)),
    TeethDiscovery("sets", "teeth.sets", "encyclopedia.body.teeth.sets", (755, 190)),
    TeethDiscovery("layers", "teeth.layers", "encyclopedia.body.teeth.layers", (250, 420)),
    TeethDiscovery("care", "teeth.care", "encyclopedia.body.teeth.care", (755, 420)),
)


class TeethPage(EncyclopediaPage):
    page_id = "body.teeth"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "teeth.intro"
        self._job_index = 0
        self._show_permanent = False
        self._layers_age = 0.0
        self._care_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.teeth.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("body", "teeth", disc.discovery_id, "name")
        if not announce_focus_name(self.context.audio, cue):
            announce_focus_name(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt
        self._layers_age = max(0.0, self._layers_age - dt)
        self._care_age = max(0.0, self._care_age - dt)

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
                cue = encyclopedia_focus_cue("body", "teeth", disc.discovery_id, "name")
                announce_focus_name(self.context.audio, cue)
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
        if discovery.discovery_id == "jobs":
            self._job_index = (self._job_index + 1) % 3
        elif discovery.discovery_id == "sets":
            self._show_permanent = not self._show_permanent
        elif discovery.discovery_id == "layers":
            self._layers_age = 4.5
        else:
            self._care_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((248, 236, 232))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("teeth.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_mouth(surface)
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

    def _draw_mouth(self, surface: pygame.Surface) -> None:
        mouth = pygame.Rect(390, 238, 230, 185)
        pygame.draw.ellipse(surface, (172, 75, 91), mouth)
        pygame.draw.ellipse(surface, (92, 50, 58), mouth, 4)
        pygame.draw.ellipse(surface, (230, 127, 142), (413, 310, 184, 82))

        # A complete primary set has 20 teeth; the permanent comparison has 32.
        # The rows are schematic and evenly spaced for readability, not a dental chart.
        per_row = 16 if self._show_permanent else 10
        radius = 5 if self._show_permanent else 10
        width = 184
        start_x = 413
        gap = width / max(1, per_row - 1)
        for row_y in (270, 352):
            for index in range(per_row):
                x = int(start_x + index * gap)
                color = (253, 250, 229)
                pygame.draw.circle(surface, color, (x, row_y), radius)
                pygame.draw.circle(surface, (181, 166, 144), (x, row_y), radius, 1)

        self._draw_job_demo(surface)
        if self._layers_age > 0.0:
            self._draw_tooth_cutaway(surface)
        if self._care_age > 0.0:
            self._draw_brush(surface)

    def _draw_job_demo(self, surface: pygame.Surface) -> None:
        center = (505, 335)
        if self._job_index == 0:
            pygame.draw.rect(surface, (252, 248, 226), (480, 296, 50, 56), border_radius=11)
            pygame.draw.line(surface, (130, 117, 103), (481, 349), (529, 349), 3)
            pygame.draw.circle(surface, (116, 181, 91), (470, 375), 15)
            pygame.draw.circle(surface, (116, 181, 91), (540, 375), 15)
            pygame.draw.line(surface, (236, 188, 68), (505, 359), (505, 391), 5)
        elif self._job_index == 1:
            pygame.draw.polygon(surface, (252, 248, 226), [(480, 305), (530, 305), (505, 357)])
            pygame.draw.line(surface, (130, 117, 103), (480, 305), (505, 357), 3)
            pygame.draw.line(surface, (130, 117, 103), (530, 305), (505, 357), 3)
            pygame.draw.ellipse(surface, (231, 159, 76), (474, 366, 62, 24))
            pygame.draw.line(surface, (236, 188, 68), (491, 370), (519, 386), 4)
        else:
            pygame.draw.rect(surface, (252, 248, 226), (472, 304, 66, 53), border_radius=17)
            for dx in (486, 505, 524):
                pygame.draw.circle(surface, (206, 196, 173), (dx, 316), 5)
            pygame.draw.ellipse(surface, (207, 159, 93), (476, 371, 58, 20))
            for x in (487, 505, 523):
                pygame.draw.line(surface, (236, 188, 68), (x, 360), (x, 378), 4)

    @staticmethod
    def _draw_tooth_cutaway(surface: pygame.Surface) -> None:
        panel = pygame.Rect(625, 258, 150, 140)
        pygame.draw.rect(surface, (254, 250, 238), panel, border_radius=20)
        pygame.draw.rect(surface, (99, 82, 79), panel, 3, border_radius=20)
        pygame.draw.polygon(surface, (252, 248, 226), [(655, 280), (742, 280), (723, 355), (704, 382), (682, 355)])
        pygame.draw.polygon(surface, (233, 213, 169), [(670, 294), (727, 294), (713, 347), (699, 369), (685, 347)])
        pygame.draw.polygon(surface, (211, 113, 122), [(687, 312), (711, 312), (707, 342), (699, 354), (691, 342)])

    def _draw_brush(self, surface: pygame.Surface) -> None:
        phase = (self._time * 0.7) % 1.0
        x = 410 + int(160 * phase)
        y = 286 + int(8 * math.sin(phase * math.tau))
        pygame.draw.line(surface, (78, 147, 194), (x, y), (x + 58, y + 22), 11)
        pygame.draw.rect(surface, (245, 244, 231), (x - 2, y - 8, 28, 14), border_radius=4)
        for off in range(0, 25, 6):
            pygame.draw.line(surface, (108, 181, 208), (x + off, y - 8), (x + off - 2, y - 17), 2)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: TeethDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "jobs":
            pygame.draw.rect(surface, (250, 246, 224), (cx - 26, cy - 20, 18, 40), border_radius=6)
            pygame.draw.polygon(surface, (250, 246, 224), [(cx - 2, cy - 20), (cx + 16, cy - 20), (cx + 7, cy + 20)])
            pygame.draw.rect(surface, (250, 246, 224), (cx + 19, cy - 20, 20, 40), border_radius=8)
        elif item.discovery_id == "sets":
            for x in (cx - 18, cx - 6, cx + 6, cx + 18):
                pygame.draw.circle(surface, (250, 246, 224), (x, cy - 8), 7)
                pygame.draw.circle(surface, (250, 246, 224), (x, cy + 10), 7)
        elif item.discovery_id == "layers":
            pygame.draw.polygon(surface, (250, 246, 224), [(cx - 20, cy - 22), (cx + 20, cy - 22), (cx + 8, cy + 26), (cx, cy + 13), (cx - 8, cy + 26)])
            pygame.draw.circle(surface, (211, 113, 122), (cx, cy), 8)
        else:
            pygame.draw.line(surface, (78, 147, 194), (cx - 24, cy - 10), (cx + 25, cy + 15), 8)
            pygame.draw.rect(surface, (245, 244, 231), (cx - 28, cy - 17, 24, 12), border_radius=3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (254, 249, 237), item.center, 37)
            pygame.draw.circle(surface, (94, 70, 72), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (254, 249, 237), panel, border_radius=22)
        pygame.draw.rect(surface, (94, 70, 72), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (60, 50, 51))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (60, 50, 51))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
