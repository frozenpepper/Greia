"""Airplane entry: lift, four forces, thrust and an explicit lift-myth correction."""

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
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_focus_patch,
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class AirplaneDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    AirplaneDiscovery("lift", "airplane.lift", "encyclopedia.machines.airplane.lift", (250, 190)),
    AirplaneDiscovery("myth", "airplane.myth", "encyclopedia.machines.airplane.myth", (755, 190)),
    AirplaneDiscovery("forces", "airplane.forces", "encyclopedia.machines.airplane.forces", (250, 420)),
    AirplaneDiscovery("thrust", "airplane.thrust", "encyclopedia.machines.airplane.thrust", (755, 420)),
)


class AirplanePage(EncyclopediaPage):
    page_id = "machines.airplane"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "airplane.intro"
        self._airflow_age = 0.0
        self._myth_age = 0.0
        self._forces_age = 0.0
        self._thrust_age = 0.0
        self._angle_step = 0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.airplane.intro")
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
        self._airflow_age = max(0.0, self._airflow_age - dt)
        self._myth_age = max(0.0, self._myth_age - dt)
        self._forces_age = max(0.0, self._forces_age - dt)
        self._thrust_age = max(0.0, self._thrust_age - dt)

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
                cue = encyclopedia_focus_cue("machines", disc.discovery_id, "name")
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
        if item.discovery_id == "lift":
            self._airflow_age = 5.0
            self._angle_step = (self._angle_step + 1) % 3
        elif item.discovery_id == "myth":
            self._myth_age = 5.0
        elif item.discovery_id == "forces":
            self._forces_age = 5.0
        else:
            self._thrust_age = 5.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((222, 239, 249))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("airplane.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_airplane(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 485), machine="airplane", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "flash",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(235, 139, 70),
        )

    def _draw_airplane(self, surface: pygame.Surface) -> None:
        center = (510, 330)
        pygame.draw.ellipse(surface, (237, 238, 231), (390, 306, 250, 54))
        pygame.draw.polygon(surface, (217, 222, 220), [(485, 330), (430, 396), (518, 349)])
        pygame.draw.polygon(surface, (217, 222, 220), [(520, 330), (590, 267), (535, 346)])
        pygame.draw.polygon(surface, (196, 204, 207), [(615, 316), (648, 286), (638, 337)])
        pygame.draw.circle(surface, (102, 151, 190), (420, 332), 17)

        wing_angle = (-0.12, 0.0, 0.12)[self._angle_step]
        if self._airflow_age > 0.0:
            for offset in (-58, -30, 0, 30, 58):
                start = (335, center[1] + offset)
                mid = (500, center[1] + offset + int(math.sin(wing_angle) * 22))
                end = (690, center[1] + offset - int(18 * math.cos(offset / 80)))
                pygame.draw.line(surface, (75, 156, 202), start, mid, 3)
                pygame.draw.line(surface, (75, 156, 202), mid, end, 3)
            pygame.draw.polygon(surface, (76, 168, 104), [(505, 230), (491, 255), (500, 250), (500, 286), (510, 286), (510, 250), (519, 255)])

        if self._forces_age > 0.0:
            self._arrow(surface, (510, 292), (510, 205), (77, 166, 105))
            self._arrow(surface, (510, 369), (510, 455), (164, 112, 86))
            self._arrow(surface, (638, 330), (725, 330), (230, 142, 64))
            self._arrow(surface, (390, 330), (305, 330), (104, 123, 176))

        if self._thrust_age > 0.0:
            for y in (320, 332, 344):
                length = 35 + int((1.0 + math.sin(self._time * 7.0 + y)) * 10)
                pygame.draw.line(surface, (230, 142, 64), (390, y), (390 - length, y), 4)
            # Small glider comparison: wings still interact with air without an engine.
            pygame.draw.ellipse(surface, (244, 244, 235), (650, 395, 92, 18))
            pygame.draw.polygon(surface, (211, 218, 217), [(690, 403), (666, 430), (704, 407)])

        if self._myth_age > 0.0:
            panel = pygame.Rect(345, 205, 330, 88)
            pygame.draw.rect(surface, (252, 248, 235), panel, border_radius=18)
            pygame.draw.rect(surface, (100, 87, 80), panel, 3, border_radius=18)
            pygame.draw.line(surface, (80, 150, 198), (382, 250), (626, 224), 4)
            pygame.draw.line(surface, (80, 150, 198), (382, 250), (585, 267), 4)
            pygame.draw.circle(surface, (80, 150, 198), (606, 226), 6)
            pygame.draw.circle(surface, (80, 150, 198), (550, 264), 6)
            pygame.draw.line(surface, (212, 76, 78), (627, 217), (652, 273), 7)
            pygame.draw.line(surface, (212, 76, 78), (652, 217), (627, 273), 7)

    @staticmethod
    def _arrow(surface: pygame.Surface, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
        pygame.draw.line(surface, color, start, end, 6)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        left = (end[0] - int(math.cos(angle - 0.55) * 18), end[1] - int(math.sin(angle - 0.55) * 18))
        right = (end[0] - int(math.cos(angle + 0.55) * 18), end[1] - int(math.sin(angle + 0.55) * 18))
        pygame.draw.polygon(surface, color, [end, left, right])

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: AirplaneDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "lift":
            pygame.draw.polygon(surface, (205, 213, 214), [(cx - 28, cy + 6), (cx + 27, cy - 5), (cx + 17, cy + 10), (cx - 23, cy + 15)])
            AirplanePage._arrow(surface, (cx, cy + 20), (cx, cy - 26), (77, 166, 105))
        elif item.discovery_id == "myth":
            pygame.draw.line(surface, (80, 150, 198), (cx - 27, cy - 9), (cx + 22, cy - 18), 3)
            pygame.draw.line(surface, (80, 150, 198), (cx - 27, cy - 9), (cx + 8, cy + 15), 3)
            pygame.draw.line(surface, (212, 76, 78), (cx + 13, cy - 22), (cx + 31, cy + 22), 5)
            pygame.draw.line(surface, (212, 76, 78), (cx + 31, cy - 22), (cx + 13, cy + 22), 5)
        elif item.discovery_id == "forces":
            for end, color in (((cx, cy - 28), (77, 166, 105)), ((cx, cy + 28), (164, 112, 86)), ((cx + 28, cy), (230, 142, 64)), ((cx - 28, cy), (104, 123, 176))):
                AirplanePage._arrow(surface, (cx, cy), end, color)
        else:
            pygame.draw.ellipse(surface, (216, 221, 221), (cx - 25, cy - 10, 50, 20))
            pygame.draw.line(surface, (230, 142, 64), (cx - 28, cy), (cx - 40, cy), 5)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (252, 249, 235), item.center, 37)
            pygame.draw.circle(surface, (77, 73, 69), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (252, 249, 235), panel, border_radius=22)
        pygame.draw.rect(surface, (77, 73, 69), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (53, 52, 50))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (53, 52, 50))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
