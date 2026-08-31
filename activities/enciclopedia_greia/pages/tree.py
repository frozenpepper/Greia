"""Tree entry: roots, water transport, photosynthesis, transpiration, seasonal variety."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class TreeDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    TreeDiscovery("roots", "tree.roots", "encyclopedia.earth.tree.roots", (220, 185)),
    TreeDiscovery("water", "tree.water", "encyclopedia.earth.tree.water", (500, 165)),
    TreeDiscovery("photosynthesis", "tree.photosynthesis", "encyclopedia.earth.tree.photosynthesis", (780, 185)),
    TreeDiscovery("transpiration", "tree.transpiration", "encyclopedia.earth.tree.transpiration", (300, 425)),
    TreeDiscovery("seasons", "tree.seasons", "encyclopedia.earth.tree.seasons", (700, 425)),
)


class TreePage(EncyclopediaPage):
    page_id = "earth.tree"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "tree.intro"
        self._roots_visible = False
        self._water_age = 0.0
        self._photo_age = 0.0
        self._transpiration_age = 0.0
        self._season_state = 0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.tree.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        # Use helper that avoids ledger fragment
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._activate(self._selected)
        # Announce is handled by _activate's audio; no extra cue needed
        disc = DISCOVERIES[0]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        announce_focus_name(self.context.audio, cue)

    def update(self, dt: float) -> None:
        self._time += dt
        self._water_age = max(0.0, self._water_age - dt)
        self._photo_age = max(0.0, self._photo_age - dt)
        self._transpiration_age = max(0.0, self._transpiration_age - dt)

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
                cue = encyclopedia_focus_cue(disc.discovery_id, "name")
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
        # Announce is handled by _activate's audio; no extra cue needed
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
        if discovery.discovery_id == "roots":
            self._roots_visible = not self._roots_visible
        elif discovery.discovery_id == "water":
            self._roots_visible = True
            self._water_age = 4.5
        elif discovery.discovery_id == "photosynthesis":
            self._photo_age = 4.5
        elif discovery.discovery_id == "transpiration":
            self._transpiration_age = 4.5
        else:
            self._season_state = (self._season_state + 1) % 3
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((194, 226, 199))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("tree.title"),
            center=(500, 92),
            size=40,
            color=(55, 68, 50),
            role=FontRole.DISPLAY,
        )
        self._draw_tree(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="tree", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=145,
            variant="default",
            fallback_color=(247, 151, 77),
        )

    def _draw_tree(self, surface: pygame.Surface) -> None:
        ground_y = 405
        # Ground with subtle gradient and grass texture
        pygame.draw.rect(surface, (137, 101, 66), (0, ground_y, 1024, 195))
        pygame.draw.rect(surface, (108, 177, 92), (0, ground_y - 16, 1024, 22))
        for gx in range(0, 1024, 48):
            pygame.draw.line(surface, (122, 190, 106), (gx, ground_y - 6), (gx + 8, ground_y - 14), 2)
        trunk = pygame.Rect(474, 265, 58, 155)
        # Trunk with bark highlight and shadow
        pygame.draw.rect(surface, (105, 70, 44), trunk.move(3, 4), border_radius=12)
        pygame.draw.rect(surface, (126, 83, 53), trunk, border_radius=12)
        pygame.draw.rect(surface, (148, 108, 78), (trunk.x + 6, trunk.y + 8, 18, trunk.height - 16), border_radius=6)
        pygame.draw.line(surface, (105, 70, 44), (493, 310), (430, 255), 18)
        pygame.draw.line(surface, (126, 83, 53), (493, 310), (432, 257), 16)
        pygame.draw.line(surface, (105, 70, 44), (514, 318), (577, 260), 17)
        pygame.draw.line(surface, (126, 83, 53), (514, 318), (575, 262), 15)

        leaf_palette = (
            ((71, 153, 77), (91, 172, 85)),
            ((205, 132, 53), (225, 168, 67)),
            ((109, 164, 89), (74, 132, 77)),
        )[self._season_state]
        if self._season_state != 1:
            for x, y, radius, color_index in (
                (429, 243, 55, 0),
                (481, 214, 62, 1),
                (545, 232, 61, 0),
                (575, 275, 48, 1),
                (449, 287, 52, 1),
            ):
                pygame.draw.circle(surface, leaf_palette[color_index], (x, y), radius)
        else:
            # Autumn/leaf-fall state intentionally leaves part of the crown bare.
            for x, y, radius, color_index in ((444, 247, 44, 0), (505, 220, 49, 1), (559, 260, 40, 0)):
                pygame.draw.circle(surface, leaf_palette[color_index], (x, y), radius)
            for index in range(9):
                x = 416 + (index * 43) % 175
                y = 315 + (index * 29) % 88
                pygame.draw.ellipse(surface, (215, 145, 55), (x, y, 12, 7))

        # Evergreen comparison appears beside, not by morphing this broadleaf
        # tree into another species.
        if self._season_state == 2:
            pygame.draw.rect(surface, (111, 78, 50), (620, 330, 18, 80), border_radius=5)
            for y, width in ((330, 86), (355, 112), (382, 136)):
                pygame.draw.polygon(surface, (55, 121, 70), [(629, y - 60), (629 - width // 2, y + 30), (629 + width // 2, y + 30)])

        if self._roots_visible:
            root_color = (104, 72, 51)
            root_paths = (
                [(500, 415), (465, 455), (425, 482), (389, 514)],
                [(500, 415), (520, 455), (565, 480), (604, 516)],
                [(500, 415), (492, 467), (481, 526)],
                [(500, 420), (544, 443), (596, 451)],
            )
            for path in root_paths:
                pygame.draw.lines(surface, root_color, False, path, 7)
                end = path[-1]
                for offset in (-11, 11):
                    pygame.draw.line(surface, root_color, end, (end[0] + offset, end[1] + 17), 3)

        if self._water_age > 0:
            for index, x in enumerate((432, 475, 521, 571)):
                progress = (self._time * 0.75 + index * 0.18) % 1.0
                y = int(491 - progress * 210)
                pygame.draw.circle(surface, (66, 149, 201), (x, y), 5)
            pygame.draw.line(surface, (66, 149, 201), (500, 392), (500, 282), 5)
            pygame.draw.polygon(surface, (66, 149, 201), [(500, 270), (493, 286), (507, 286)])

        if self._photo_age > 0:
            pygame.draw.circle(surface, (251, 210, 66), (360, 185), 29)
            for angle_index in range(8):
                angle = angle_index * math.tau / 8
                pygame.draw.line(surface, (251, 210, 66), (360 + int(math.cos(angle) * 38), 185 + int(math.sin(angle) * 38)), (360 + int(math.cos(angle) * 52), 185 + int(math.sin(angle) * 52)), 4)
            for start in ((391, 203), (401, 221), (414, 239)):
                pygame.draw.line(surface, (244, 194, 63), start, (450, 250), 4)
            # Simple CO2-in / O2-out semantic particles, not an animal-breathing diagram.
            for x, label, color in ((604, "CO₂", (89, 101, 103)), (649, "O₂", (91, 153, 202))):
                draw_centered_text(surface, self.context.typography, label, center=(x, 222), size=16, color=color, role=FontRole.CONTROL)

        if self._transpiration_age > 0:
            for index in range(12):
                x = 430 + (index * 37) % 160
                y = 205 - int((self._time * 24 + index * 17) % 72)
                pygame.draw.arc(surface, (151, 205, 220), (x, y, 18, 26), 0.5, 2.7, 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 249, 232), item.center, 37)
            pygame.draw.circle(surface, (66, 68, 52), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "roots":
                pygame.draw.line(surface, (118, 79, 52), (cx, cy - 20), (cx, cy + 18), 6)
                pygame.draw.line(surface, (118, 79, 52), (cx, cy + 4), (cx - 18, cy + 23), 4)
                pygame.draw.line(surface, (118, 79, 52), (cx, cy + 5), (cx + 18, cy + 22), 4)
            elif item.discovery_id == "water":
                pygame.draw.circle(surface, (69, 151, 203), (cx, cy + 7), 10)
                pygame.draw.polygon(surface, (69, 151, 203), [(cx, cy - 25), (cx - 11, cy + 1), (cx + 11, cy + 1)])
            elif item.discovery_id == "photosynthesis":
                pygame.draw.circle(surface, (248, 204, 66), (cx - 10, cy - 7), 12)
                pygame.draw.ellipse(surface, (82, 161, 78), (cx + 1, cy - 4, 27, 17))
            elif item.discovery_id == "transpiration":
                pygame.draw.ellipse(surface, (82, 161, 78), (cx - 21, cy + 3, 34, 20))
                for off in (-5, 10, 23):
                    pygame.draw.arc(surface, (125, 191, 211), (cx + off - 9, cy - 25, 18, 25), 0.5, 2.7, 3)
            else:
                pygame.draw.circle(surface, (83, 159, 78), (cx - 13, cy), 14)
                pygame.draw.ellipse(surface, (220, 147, 54), (cx + 4, cy - 13, 22, 14))
                pygame.draw.polygon(surface, (56, 119, 70), [(cx + 15, cy - 23), (cx + 2, cy + 22), (cx + 28, cy + 22)])
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(300, 510, 410, 68)
        pygame.draw.rect(surface, (255, 249, 232), panel, border_radius=22)
        pygame.draw.rect(surface, (66, 68, 52), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (52, 57, 47))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (52, 57, 47))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
