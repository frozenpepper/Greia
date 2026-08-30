"""Bones entry: support, joints, protection, living tissue and marrow."""

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
class BonesDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    BonesDiscovery("joints", "bones.joints", "encyclopedia.body.bones.joints", (250, 190)),
    BonesDiscovery("protect", "bones.protect", "encyclopedia.body.bones.protect", (755, 190)),
    BonesDiscovery("living", "bones.living", "encyclopedia.body.bones.living", (250, 420)),
    BonesDiscovery("marrow", "bones.marrow", "encyclopedia.body.bones.marrow", (755, 420)),
)


class BonesPage(EncyclopediaPage):
    page_id = "body.bones"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "bones.intro"
        self._arm_bent = False
        self._protect_age = 0.0
        self._living_age = 0.0
        self._marrow_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.bones.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("body", "bones", disc.discovery_id, "name")
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
        self._protect_age = max(0.0, self._protect_age - dt)
        self._living_age = max(0.0, self._living_age - dt)
        self._marrow_age = max(0.0, self._marrow_age - dt)

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
                cue = encyclopedia_focus_cue("body", "bones", disc.discovery_id, "name")
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
        if discovery.discovery_id == "joints":
            self._arm_bent = not self._arm_bent
        elif discovery.discovery_id == "protect":
            self._protect_age = 4.5
        elif discovery.discovery_id == "living":
            self._living_age = 4.5
        else:
            self._marrow_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((244, 238, 228))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("bones.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_body_and_skeleton(surface)
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

    def _draw_body_and_skeleton(self, surface: pygame.Surface) -> None:
        skin = (234, 190, 162)
        bone = (245, 239, 211)
        outline = (112, 100, 91)
        pygame.draw.circle(surface, skin, (505, 178), 45)
        pygame.draw.rect(surface, skin, (442, 220, 126, 235), border_radius=48)
        pygame.draw.line(surface, skin, (454, 256), (386, 410), 27)
        pygame.draw.line(surface, skin, (556, 256), (624, 410), 27)
        pygame.draw.line(surface, skin, (478, 430), (453, 545), 29)
        pygame.draw.line(surface, skin, (532, 430), (557, 545), 29)

        # Friendly schematic skeleton: enough structure to teach support without
        # turning the page into a medical plate.
        pygame.draw.circle(surface, bone, (505, 178), 31)
        pygame.draw.circle(surface, outline, (505, 178), 31, 3)
        pygame.draw.line(surface, bone, (505, 215), (505, 390), 10)
        pygame.draw.line(surface, outline, (505, 215), (505, 390), 2)
        for y, width in ((248, 46), (267, 52), (286, 55), (305, 51)):
            pygame.draw.arc(surface, bone, (505 - width, y - 15, width * 2, 42), 0.15, math.pi - 0.15, 7)

        shoulder_left = (475, 245)
        elbow_left = (430, 325)
        hand_left = (390, 405)
        pygame.draw.line(surface, bone, shoulder_left, elbow_left, 9)
        if self._arm_bent:
            hand_left = (485, 350)
        pygame.draw.line(surface, bone, elbow_left, hand_left, 8)
        pygame.draw.circle(surface, (226, 188, 92), elbow_left, 8)

        shoulder_right = (535, 245)
        elbow_right = (580, 325)
        pygame.draw.line(surface, bone, shoulder_right, elbow_right, 9)
        pygame.draw.line(surface, bone, elbow_right, (620, 405), 8)
        pygame.draw.circle(surface, (226, 188, 92), elbow_right, 8)

        hip_left = (489, 391)
        hip_right = (521, 391)
        pygame.draw.line(surface, bone, hip_left, (470, 470), 10)
        pygame.draw.line(surface, bone, (470, 470), (453, 540), 8)
        pygame.draw.line(surface, bone, hip_right, (540, 470), 10)
        pygame.draw.line(surface, bone, (540, 470), (557, 540), 8)

        if self._protect_age > 0.0:
            pygame.draw.circle(surface, (218, 159, 176), (505, 178), 18)
            pygame.draw.ellipse(surface, (224, 151, 160), (472, 258, 31, 58))
            pygame.draw.ellipse(surface, (224, 151, 160), (507, 258, 31, 58))
            pygame.draw.circle(surface, (199, 67, 81), (505, 326), 13)
            pygame.draw.circle(surface, (227, 188, 89), (505, 178), 38, 3)
            pygame.draw.ellipse(surface, (227, 188, 89), (454, 244, 102, 92), 3)

        if self._living_age > 0.0:
            pulse = 8 + int(4 * (1.0 + math.sin(self._time * 4.0)))
            for x, y in ((488, 265), (522, 285), (474, 468), (542, 468)):
                pygame.draw.circle(surface, (223, 114, 102), (x, y), pulse, 3)

        if self._marrow_age > 0.0:
            self._draw_bone_cutaway(surface)

    @staticmethod
    def _draw_bone_cutaway(surface: pygame.Surface) -> None:
        panel = pygame.Rect(600, 255, 165, 145)
        pygame.draw.rect(surface, (252, 249, 238), panel, border_radius=20)
        pygame.draw.rect(surface, (104, 89, 82), panel, 3, border_radius=20)
        shaft = pygame.Rect(650, 277, 65, 101)
        pygame.draw.rect(surface, (238, 228, 194), shaft, border_radius=28)
        pygame.draw.rect(surface, (171, 141, 112), shaft, 5, border_radius=28)
        inner = pygame.Rect(665, 290, 35, 75)
        pygame.draw.rect(surface, (198, 104, 114), inner, border_radius=16)
        for x, y in ((674, 304), (690, 315), (678, 332), (690, 347)):
            pygame.draw.circle(surface, (244, 190, 155), (x, y), 5)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: BonesDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "joints":
            pygame.draw.line(surface, (226, 188, 92), (cx - 22, cy - 18), (cx, cy), 8)
            pygame.draw.line(surface, (226, 188, 92), (cx, cy), (cx + 20, cy + 18), 8)
            pygame.draw.circle(surface, (118, 101, 86), (cx, cy), 7)
        elif item.discovery_id == "protect":
            pygame.draw.circle(surface, (238, 228, 194), (cx, cy - 6), 19)
            pygame.draw.arc(surface, (238, 228, 194), (cx - 24, cy + 3, 48, 32), 0.1, math.pi - 0.1, 5)
        elif item.discovery_id == "living":
            pygame.draw.rect(surface, (238, 228, 194), (cx - 9, cy - 25, 18, 50), border_radius=8)
            pygame.draw.circle(surface, (214, 100, 95), (cx + 19, cy), 8)
        else:
            pygame.draw.rect(surface, (238, 228, 194), (cx - 18, cy - 27, 36, 54), border_radius=16)
            pygame.draw.rect(surface, (198, 104, 114), (cx - 8, cy - 18, 16, 36), border_radius=7)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (253, 249, 238), item.center, 37)
            pygame.draw.circle(surface, (93, 80, 73), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (253, 249, 238), panel, border_radius=22)
        pygame.draw.rect(surface, (93, 80, 73), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (57, 52, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (57, 52, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
