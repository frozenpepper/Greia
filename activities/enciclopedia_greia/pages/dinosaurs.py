"""Dinosaurs entry: diversity, deep time, living birds and fossil evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
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
        draw_authored_scene,
        draw_caption_ribbon,
        draw_focus_patch,
        draw_history_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class DinosaurDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    DinosaurDiscovery("diversity", "dinosaurs.diversity", "encyclopedia.history.dinosaurs.diversity", (250, 190)),
    DinosaurDiscovery("time", "dinosaurs.time", "encyclopedia.history.dinosaurs.time", (755, 190)),
    DinosaurDiscovery("birds", "dinosaurs.birds", "encyclopedia.history.dinosaurs.birds", (250, 420)),
    DinosaurDiscovery("evidence", "dinosaurs.evidence", "encyclopedia.history.dinosaurs.evidence", (755, 420)),
)


class DinosaursPage(EncyclopediaPage):
    page_id = "history.dinosaurs"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "dinosaurs.intro"
        self._silhouette = 0
        self._time_age = 0.0
        self._birds_age = 0.0
        self._evidence_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.dinosaurs.intro")
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
        self._time_age = max(0.0, self._time_age - dt)
        self._birds_age = max(0.0, self._birds_age - dt)
        self._evidence_age = max(0.0, self._evidence_age - dt)

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
        if item.discovery_id == "diversity":
            self._silhouette = (self._silhouette + 1) % 3
        elif item.discovery_id == "time":
            self._time_age = 5.0
        elif item.discovery_id == "birds":
            self._birds_age = 5.0
        else:
            self._evidence_age = 5.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        # Authored valley with all three dinosaur body plans side by side.
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.history.dinosaurs.valley",
        )
        if not authored:
            # Contained procedural fallback when the runtime PNG is absent.
            surface.fill((239, 229, 198))
        draw_centered_text(surface, self.context.typography, self.context.resources.text("dinosaurs.title"), center=(500, 92), size=40, color=self.context.palette.ink, role=FontRole.DISPLAY)
        self._draw_scene(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_history_action_button(
            surface, (512, 460), history="dinosaurs", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default")

    # Where the authored valley shows each body plan, in silhouette order
    # (two-legged meat eater, three-horn, long neck): the live "diversity"
    # pointer bobs just above that dinosaur's head.
    AUTHORED_POINTER_TIPS = ((468, 226), (562, 330), (656, 174))

    def _draw_authored_pointer(self, surface: pygame.Surface) -> None:
        tip_x, tip_y = self.AUTHORED_POINTER_TIPS[self._silhouette]
        tip_y -= int((math.sin(self._time * 4.0) + 1.0) * 4)
        points = [(tip_x, tip_y), (tip_x - 14, tip_y - 20), (tip_x + 14, tip_y - 20)]
        pygame.draw.polygon(surface, (255, 211, 92), points)
        pygame.draw.polygon(surface, (75, 55, 47), points, 3)

    def _draw_scene(self, surface: pygame.Surface, *, authored: bool = False) -> None:
        if authored:
            self._draw_authored_pointer(surface)
            self._draw_overlays(surface)
            return
        # Ground with subtle texture
        pygame.draw.rect(surface, (177, 194, 126), (330, 365, 350, 92), border_radius=24)
        for gx in range(340, 670, 48):
            pygame.draw.line(surface, (190, 208, 140), (gx, 395), (gx + 8, 410), 2)
        center = (505, 327)
        colors = ((111, 151, 92), (173, 128, 86), (104, 145, 111))
        color = colors[self._silhouette]
        shadow_col = (90, 120, 75) if self._silhouette == 0 else (140, 105, 70) if self._silhouette == 1 else (80, 115, 85)
        # Soft ground shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 22), (center[0] - 80, 398, 160, 16))
        if self._silhouette == 0:  # tyrannosaur-like biped
            pygame.draw.ellipse(surface, shadow_col, (446, 290, 118, 58))
            pygame.draw.ellipse(surface, color, (448, 288, 118, 58))
            pygame.draw.circle(surface, shadow_col, (570, 287), 30)
            pygame.draw.circle(surface, color, (570, 285), 30)
            pygame.draw.circle(surface, (255, 255, 255, 18), (562, 272), 14)
            pygame.draw.line(surface, shadow_col, (462, 324), (407, 300), 20)
            pygame.draw.line(surface, color, (460, 322), (405, 298), 20)
            pygame.draw.line(surface, shadow_col, (482, 338), (467, 394), 15)
            pygame.draw.line(surface, color, (480, 336), (465, 392), 15)
            pygame.draw.line(surface, shadow_col, (527, 338), (542, 394), 15)
            pygame.draw.line(surface, color, (525, 336), (540, 392), 15)
        elif self._silhouette == 1:  # ceratopsian-like quadruped
            pygame.draw.ellipse(surface, shadow_col, (432, 302, 145, 62))
            pygame.draw.ellipse(surface, color, (430, 300, 145, 62))
            pygame.draw.circle(surface, shadow_col, (586, 312), 34)
            pygame.draw.circle(surface, color, (586, 310), 34)
            pygame.draw.circle(surface, (255, 255, 255, 16), (578, 296), 16)
            pygame.draw.polygon(surface, shadow_col, [(573, 287), (607, 267), (603, 300)])
            pygame.draw.polygon(surface, color, [(573, 285), (607, 265), (603, 298)])
            for x in (455, 492, 535, 565):
                pygame.draw.line(surface, shadow_col, (x, 344), (x - 4, 392), 13)
                pygame.draw.line(surface, color, (x, 342), (x - 4, 390), 13)
        else:  # sauropod-like long neck
            pygame.draw.ellipse(surface, shadow_col, (427, 312, 140, 55))
            pygame.draw.ellipse(surface, color, (425, 310, 140, 55))
            pygame.draw.line(surface, shadow_col, (547, 324), (597, 247), 25)
            pygame.draw.line(surface, color, (545, 322), (595, 245), 25)
            pygame.draw.circle(surface, shadow_col, (602, 238), 16)
            pygame.draw.circle(surface, color, (602, 236), 16)
            pygame.draw.circle(surface, (255, 255, 255, 14), (596, 228), 8)
            pygame.draw.line(surface, shadow_col, (440, 327), (384, 294), 20)
            pygame.draw.line(surface, color, (438, 325), (382, 292), 20)
            for x in (450, 485, 530, 555):
                pygame.draw.line(surface, shadow_col, (x, 347), (x - 3, 395), 13)
                pygame.draw.line(surface, color, (x, 345), (x - 3, 393), 13)
        self._draw_overlays(surface)

    def _draw_overlays(self, surface: pygame.Surface) -> None:
        """Time, bird and evidence discovery overlays (live in both modes)."""
        if self._time_age > 0.0:
            pygame.draw.line(surface, (92, 72, 55), (365, 230), (645, 230), 5)
            pygame.draw.circle(surface, (114, 149, 90), (405, 230), 12)
            pygame.draw.circle(surface, (217, 171, 97), (605, 230), 12)
            draw_centered_text(surface, self.context.typography, "66 000 000", center=(405, 205), size=16, color=(78, 65, 54))
            pygame.draw.circle(surface, (232, 188, 143), (605, 195), 10)

        if self._birds_age > 0.0:
            wing = 10 + int(math.sin(self._time * 5.0) * 4)
            pygame.draw.ellipse(surface, (77, 113, 157), (635, 245, 42, 24))
            pygame.draw.line(surface, (77, 113, 157), (651, 257), (635, 257 - wing), 6)
            pygame.draw.line(surface, (77, 113, 157), (661, 257), (679, 257 - wing), 6)
            pygame.draw.polygon(surface, (220, 159, 69), [(678, 252), (691, 258), (678, 263)])

        if self._evidence_age > 0.0:
            pygame.draw.rect(surface, (198, 171, 126), (350, 395, 310, 70), border_radius=18)
            for x in range(390, 610, 45):
                pygame.draw.circle(surface, (239, 226, 193), (x, 430), 13, 5)
            pygame.draw.line(surface, (239, 226, 193), (390, 430), (608, 430), 7)

    @staticmethod
    def _draw_icon(surface: pygame.Surface, item: DinosaurDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "diversity":
            for dx, radius in ((-18, 10), (0, 15), (20, 8)):
                pygame.draw.circle(surface, (111, 151, 92), (cx + dx, cy), radius)
        elif item.discovery_id == "time":
            pygame.draw.line(surface, (101, 82, 61), (cx - 26, cy), (cx + 26, cy), 5)
            pygame.draw.circle(surface, (111, 151, 92), (cx - 18, cy), 7)
            pygame.draw.circle(surface, (221, 171, 105), (cx + 19, cy), 7)
        elif item.discovery_id == "birds":
            pygame.draw.ellipse(surface, (77, 113, 157), (cx - 16, cy - 8, 32, 17))
            pygame.draw.line(surface, (77, 113, 157), (cx - 5, cy), (cx - 24, cy - 15), 5)
            pygame.draw.line(surface, (77, 113, 157), (cx + 5, cy), (cx + 24, cy - 15), 5)
        else:
            pygame.draw.circle(surface, (202, 176, 132), (cx, cy), 23)
            pygame.draw.circle(surface, (248, 238, 207), (cx, cy), 12, 5)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 248, 226), item.center, 37)
            pygame.draw.circle(surface, (91, 73, 57), item.center, 37, 3)
            self._draw_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        # Shared adaptive ribbon: wraps long captions instead of overflowing.
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
