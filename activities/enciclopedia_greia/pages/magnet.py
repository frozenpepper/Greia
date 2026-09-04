"""Magnet entry: poles, material response, distance force, field schematic."""

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
class MagnetDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MagnetDiscovery("poles", "magnet.poles", "encyclopedia.machines.magnet.poles", (250, 190)),
    MagnetDiscovery("materials", "magnet.materials", "encyclopedia.machines.magnet.materials", (755, 190)),
    MagnetDiscovery("distance", "magnet.distance", "encyclopedia.machines.magnet.distance", (250, 420)),
    MagnetDiscovery("field", "magnet.field", "encyclopedia.machines.magnet.field", (755, 420)),
)


class MagnetPage(EncyclopediaPage):
    page_id = "machines.magnet"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "magnet.intro"
        self._same_poles = False
        self._material_index = 0
        self._distance_age = 0.0
        self._field_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.magnet.intro")
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
        self._distance_age = max(0.0, self._distance_age - dt)
        self._field_age = max(0.0, self._field_age - dt)

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
        if item.discovery_id == "poles":
            self._same_poles = not self._same_poles
        elif item.discovery_id == "materials":
            self._material_index = (self._material_index + 1) % 4
        elif item.discovery_id == "distance":
            self._distance_age = 4.5
        else:
            self._field_age = 4.5
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((235, 239, 233))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("magnet.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_demo(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="magnet", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_demo(self, surface: pygame.Surface) -> None:
        left = pygame.Rect(395, 292, 95, 52)
        right = pygame.Rect(520, 292, 95, 52)
        self._draw_bar_magnet(surface, left, reverse=False)
        # Left magnet faces right with its blue pole. A normal right magnet
        # therefore presents red (opposite) for attraction; reversing it makes
        # blue face blue for the same-pole repulsion state.
        self._draw_bar_magnet(surface, right, reverse=self._same_poles)

        if self._same_poles:
            pygame.draw.line(surface, (219, 91, 83), (500, 303), (485, 290), 5)
            pygame.draw.line(surface, (219, 91, 83), (510, 303), (525, 290), 5)
            pygame.draw.line(surface, (219, 91, 83), (500, 333), (485, 346), 5)
            pygame.draw.line(surface, (219, 91, 83), (510, 333), (525, 346), 5)
        else:
            pygame.draw.line(surface, (79, 151, 102), (495, 318), (515, 318), 5)
            pygame.draw.polygon(surface, (79, 151, 102), [(507, 309), (519, 318), (507, 327)])

        if self._distance_age > 0.0:
            pulse = int((1.0 + math.sin(self._time * 4.0)) * 5)
            for x in range(493, 519, 8):
                pygame.draw.circle(surface, (236, 184, 65), (x, 318), 3 + pulse // 4)

        if self._field_age > 0.0:
            for inset in (12, 25, 38):
                pygame.draw.arc(surface, (103, 128, 181), (355 - inset, 235 - inset // 2, 300 + inset * 2, 165 + inset), 0.15, math.pi - 0.15, 2)
                pygame.draw.arc(surface, (103, 128, 181), (355 - inset, 286 - inset // 2, 300 + inset * 2, 165 + inset), math.pi + 0.15, math.tau - 0.15, 2)

        self._draw_material_sample(surface)

    def _draw_bar_magnet(self, surface: pygame.Surface, rect: pygame.Rect, *, reverse: bool) -> None:
        half = rect.width // 2
        first = (87, 133, 199) if reverse else (213, 81, 82)
        second = (213, 81, 82) if reverse else (87, 133, 199)
        # Soft shadow
        shadow = pygame.Surface((rect.width + 8, rect.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 28), shadow.get_rect(), border_radius=10)
        surface.blit(shadow, (rect.x - 2, rect.y + 3))
        pygame.draw.rect(surface, first, (rect.x, rect.y, half, rect.height), border_radius=10)
        pygame.draw.rect(surface, second, (rect.x + half, rect.y, rect.width - half, rect.height), border_radius=10)
        # Top highlight
        pygame.draw.rect(surface, (255, 255, 255, 38), (rect.x + 4, rect.y + 4, rect.width - 8, rect.height // 3), border_radius=6)
        pygame.draw.rect(surface, (75, 70, 67), rect, 3, border_radius=10)
        # Constant pole labels go through the injected cached Greia typography
        # service instead of constructing a new font in the frame draw path.
        for x, label in (
            (rect.x + half // 2, "N"),
            (rect.x + half + half // 2, "S"),
        ):
            text = self.context.typography.render(
                label,
                FontRole.CONTROL,
                22,
                (255, 255, 255),
            )
            surface.blit(text, text.get_rect(center=(x, rect.centery)))

    def _draw_material_sample(self, surface: pygame.Surface) -> None:
        samples = (
            ((118, 120, 125), True),
            ((184, 190, 197), False),
            ((191, 117, 69), False),
            ((135, 137, 142), True),
        )
        color, responds = samples[self._material_index]
        x = 690 if not responds else 650 - int((1.0 + math.sin(self._time * 3.0)) * 12)
        pygame.draw.circle(surface, color, (x, 334), 22)
        pygame.draw.circle(surface, (74, 70, 67), (x, 334), 22, 3)
        self._draw_bar_magnet(surface, pygame.Rect(745, 309, 85, 48), reverse=False)
        if responds:
            pygame.draw.line(surface, (79, 151, 102), (x + 26, 334), (738, 334), 4)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: MagnetDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "poles":
            pygame.draw.rect(surface, (213, 81, 82), (cx - 28, cy - 12, 28, 24), border_radius=6)
            pygame.draw.rect(surface, (87, 133, 199), (cx, cy - 12, 28, 24), border_radius=6)
        elif item.discovery_id == "materials":
            for dx, color in ((-18, (121, 123, 128)), (0, (190, 119, 69)), (18, (184, 190, 197))):
                pygame.draw.circle(surface, color, (cx + dx, cy), 9)
        elif item.discovery_id == "distance":
            pygame.draw.rect(surface, (213, 81, 82), (cx - 28, cy - 9, 18, 18), border_radius=4)
            pygame.draw.rect(surface, (87, 133, 199), (cx + 10, cy - 9, 18, 18), border_radius=4)
            pygame.draw.line(surface, (236, 184, 65), (cx - 3, cy), (cx + 3, cy), 4)
        else:
            pygame.draw.rect(surface, (213, 81, 82), (cx - 15, cy - 8, 30, 16), border_radius=4)
            for radius in (22, 29):
                pygame.draw.arc(surface, (103, 128, 181), (cx - radius, cy - radius // 2, radius * 2, radius), 0.1, math.pi - 0.1, 2)
                pygame.draw.arc(surface, (103, 128, 181), (cx - radius, cy - radius // 2, radius * 2, radius), math.pi + 0.1, math.tau - 0.1, 2)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (252, 248, 232), item.center, 37)
            pygame.draw.circle(surface, (73, 71, 66), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (252, 248, 232), panel, border_radius=22)
        pygame.draw.rect(surface, (73, 71, 66), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (53, 52, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (53, 52, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
