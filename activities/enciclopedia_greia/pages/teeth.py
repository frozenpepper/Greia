"""Teeth entry: tooth jobs, primary/permanent sets, layers and care."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step


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

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.body.teeth.dental_room"


class TeethPage(EncyclopediaPage):
    page_id = "body.teeth"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
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
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((248, 236, 232))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("teeth.title"),
            self.context.palette.ink,
        )
        self._draw_mouth(surface, authored=authored)
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

    def _draw_mouth(self, surface: pygame.Surface, *, authored: bool) -> None:
        if not authored:
            mouth = pygame.Rect(390, 238, 230, 185)
            # Lips with highlight and shadow
            pygame.draw.ellipse(surface, (92, 50, 58), mouth.move(2, 3))
            pygame.draw.ellipse(surface, (172, 75, 91), mouth)
            pygame.draw.ellipse(surface, (200, 95, 115), (mouth.x + 8, mouth.y + 8, mouth.width - 16, mouth.height - 24))
            pygame.draw.ellipse(surface, (92, 50, 58), mouth, 4)
            pygame.draw.ellipse(surface, (230, 127, 142), (413, 310, 184, 82))
            pygame.draw.ellipse(surface, (245, 160, 175), (420, 316, 170, 68))
        # A complete primary set has 20 teeth; the permanent comparison has 32.
        # The rows are schematic and evenly spaced for readability, not a dental chart.
        per_row = 16 if self._show_permanent else 10
        radius = 5 if self._show_permanent else 10
        width = 184
        start_x = 413
        gap = width / max(1, per_row - 1)
        if authored and not self._show_permanent:
            # The authored dental model already shows the 20 primary teeth.
            per_row = 0
        elif authored:
            # Cover the baked primary rows with gum before the larger set.
            for row_y in (270, 352):
                pygame.draw.rect(surface, (235, 169, 191), (406, row_y - 14, 198, 28), border_radius=12)
        for row_y in (270, 352):
            for index in range(per_row):
                x = int(start_x + index * gap)
                # Tooth with shadow and highlight
                pygame.draw.circle(surface, (180, 160, 140), (x + 1, row_y + 1), radius)
                pygame.draw.circle(surface, (253, 250, 229), (x, row_y), radius)
                pygame.draw.circle(surface, (255, 255, 255, 90), (x - 3, row_y - 3), max(1, radius // 3))
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
        # Enamel-white icons get a warm outline so they read on the cream tag.
        enamel = (255, 252, 240)
        edge = (148, 130, 110)
        if item.discovery_id == "jobs":
            incisor = pygame.Rect(cx - 26, cy - 20, 18, 40)
            canine = [(cx - 2, cy - 20), (cx + 16, cy - 20), (cx + 7, cy + 20)]
            molar = pygame.Rect(cx + 19, cy - 20, 20, 40)
            pygame.draw.rect(surface, enamel, incisor, border_radius=6)
            pygame.draw.rect(surface, edge, incisor, 2, border_radius=6)
            pygame.draw.polygon(surface, enamel, canine)
            pygame.draw.polygon(surface, edge, canine, 2)
            pygame.draw.rect(surface, enamel, molar, border_radius=8)
            pygame.draw.rect(surface, edge, molar, 2, border_radius=8)
        elif item.discovery_id == "sets":
            for x in (cx - 18, cx - 6, cx + 6, cx + 18):
                for y in (cy - 8, cy + 10):
                    pygame.draw.circle(surface, enamel, (x, y), 7)
                    pygame.draw.circle(surface, edge, (x, y), 7, 2)
        elif item.discovery_id == "layers":
            outline = [(cx - 20, cy - 22), (cx + 20, cy - 22), (cx + 8, cy + 26), (cx, cy + 13), (cx - 8, cy + 26)]
            pygame.draw.polygon(surface, enamel, outline)
            pygame.draw.polygon(surface, edge, outline, 2)
            pygame.draw.circle(surface, (211, 113, 122), (cx, cy), 8)
        else:
            pygame.draw.line(surface, (78, 147, 194), (cx - 24, cy - 10), (cx + 25, cy + 15), 8)
            pygame.draw.rect(surface, (245, 244, 231), (cx - 28, cy - 17, 24, 12), border_radius=3)
            pygame.draw.rect(surface, edge, (cx - 28, cy - 17, 24, 12), 2, border_radius=3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._caption_key == item.caption_key,
                icon=lambda target, _center, item=item: self._draw_hotspot_icon(target, item),
                token_shape=TOKEN_SHAPE_FELT_TAG,
            )

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
