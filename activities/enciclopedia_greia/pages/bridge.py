"""Bridge entry: load paths, bridge forms, tension and compression."""

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
class BridgeDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    BridgeDiscovery("load", "bridge.load", "encyclopedia.machines.bridge.load", (250, 190)),
    BridgeDiscovery("shapes", "bridge.shapes", "encyclopedia.machines.bridge.shapes", (755, 190)),
    BridgeDiscovery("forces", "bridge.forces", "encyclopedia.machines.bridge.forces", (250, 420)),
    BridgeDiscovery("path", "bridge.path", "encyclopedia.machines.bridge.path", (755, 420)),
)


class BridgeLoadModel:
    """Own finite structure choice and load/path teaching state."""

    SHAPES = ("beam", "arch", "truss")

    def __init__(self) -> None:
        self.shape_index = 0
        self.load_position = 0.5
        self.load_age = 0.0
        self.forces_age = 0.0
        self.path_age = 0.0

    @property
    def shape(self) -> str:
        return self.SHAPES[self.shape_index]

    def update(self, dt: float) -> None:
        self.load_age = max(0.0, self.load_age - dt)
        self.forces_age = max(0.0, self.forces_age - dt)
        self.path_age = max(0.0, self.path_age - dt)

    def place_load(self) -> None:
        self.load_position += 0.22
        if self.load_position > 0.82:
            self.load_position = 0.18
        self.load_age = 4.5

    def next_shape(self) -> None:
        self.shape_index = (self.shape_index + 1) % len(self.SHAPES)
        self.load_age = 4.0

    def reveal_forces(self) -> None:
        self.forces_age = 4.5

    def reveal_path(self) -> None:
        self.path_age = 4.5


class BridgePage(EncyclopediaPage):
    page_id = "machines.bridge"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = BridgeLoadModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "bridge.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.bridge.intro")
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
        self._time = getattr(self, '_time', 0.0) + dt
        self._model.update(dt)

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
        if item.discovery_id == "load":
            self._model.place_load()
        elif item.discovery_id == "shapes":
            self._model.next_shape()
        elif item.discovery_id == "forces":
            self._model.reveal_forces()
        else:
            self._model.reveal_path()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((234, 242, 246))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("bridge.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_bridge(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="bridge", time=getattr(self, '_time', 0.0), active=True
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

    def _draw_bridge(self, surface: pygame.Surface) -> None:
        left_x, right_x = 350, 665
        deck_y = 350
        # Towers with highlight and shadow
        for tx in (left_x - 30, right_x - 15):
            pygame.draw.rect(surface, (120, 95, 72), (tx + 2, deck_y + 12, 45, 100))
            pygame.draw.rect(surface, (142, 115, 89), (tx, deck_y + 10, 45, 100))
            pygame.draw.rect(surface, (165, 138, 110), (tx + 4, deck_y + 14, 14, 92))
        pygame.draw.line(surface, (70, 73, 74), (left_x, deck_y + 2), (right_x, deck_y + 2), 12)
        pygame.draw.line(surface, (83, 86, 86), (left_x, deck_y), (right_x, deck_y), 10)
        pygame.draw.line(surface, (110, 112, 112), (left_x, deck_y - 2), (right_x, deck_y - 2), 2)

        shape = self._model.shape
        if shape == "beam":
            pygame.draw.rect(surface, (91, 137, 173), (left_x, deck_y - 18, right_x - left_x, 22), border_radius=6)
        elif shape == "arch":
            pygame.draw.arc(surface, (91, 137, 173), (left_x, deck_y - 175, right_x - left_x, 210), math.pi, math.tau, 12)
            for x in range(left_x + 35, right_x, 45):
                rel = (x - left_x) / (right_x - left_x)
                arch_y = deck_y - int(math.sin(rel * math.pi) * 100)
                pygame.draw.line(surface, (91, 137, 173), (x, deck_y), (x, arch_y), 4)
        else:
            top_y = 245
            pygame.draw.line(surface, (91, 137, 173), (left_x, deck_y), (right_x, deck_y), 8)
            points = [(left_x + i * 52, top_y if i % 2 else deck_y) for i in range(7)]
            points[-1] = (right_x, deck_y)
            for a, b in zip(points, points[1:]):
                pygame.draw.line(surface, (91, 137, 173), a, b, 7)
            pygame.draw.line(surface, (91, 137, 173), (left_x + 52, top_y), (right_x - 52, top_y), 7)

        load_x = int(left_x + (right_x - left_x) * self._model.load_position)
        pygame.draw.rect(surface, (230, 157, 68), (load_x - 24, deck_y - 58, 48, 43), border_radius=8)
        pygame.draw.circle(surface, (70, 69, 67), (load_x - 14, deck_y - 12), 7)
        pygame.draw.circle(surface, (70, 69, 67), (load_x + 14, deck_y - 12), 7)

        if self._model.load_age > 0.0:
            self._arrow(surface, (load_x, deck_y - 70), (load_x, deck_y - 18), (205, 92, 81))
            # Teaching exaggeration: tiny deformation marker, not a scale prediction.
            pygame.draw.arc(surface, (205, 92, 81), (left_x, deck_y - 3, right_x - left_x, 18), 0.1, math.pi - 0.1, 2)

        if self._model.forces_age > 0.0:
            if shape == "truss":
                for i in range(5):
                    x1 = left_x + 25 + i * 55
                    color = (204, 86, 88) if i % 2 else (75, 145, 185)
                    pygame.draw.line(surface, color, (x1, deck_y - 4), (x1 + 45, 257 if i % 2 == 0 else 335), 6)
            elif shape == "arch":
                pygame.draw.arc(surface, (75, 145, 185), (left_x + 8, deck_y - 165, right_x - left_x - 16, 196), math.pi + 0.05, math.tau - 0.05, 7)
            else:
                pygame.draw.line(surface, (75, 145, 185), (left_x + 10, deck_y - 6), (load_x, deck_y - 6), 6)
                pygame.draw.line(surface, (204, 86, 88), (load_x, deck_y - 6), (right_x - 10, deck_y - 6), 6)

        if self._model.path_age > 0.0:
            path_points = [(load_x, deck_y - 4), (load_x - 55, deck_y + 3), (left_x, deck_y + 8), (left_x - 5, deck_y + 85)]
            for a, b in zip(path_points, path_points[1:]):
                self._arrow(surface, a, b, (239, 190, 68))
            path_points = [(load_x, deck_y - 4), (load_x + 55, deck_y + 3), (right_x, deck_y + 8), (right_x + 5, deck_y + 85)]
            for a, b in zip(path_points, path_points[1:]):
                self._arrow(surface, a, b, (239, 190, 68))

    @staticmethod
    def _arrow(surface: pygame.Surface, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
        pygame.draw.line(surface, color, start, end, 5)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        left = (end[0] - int(math.cos(angle - 0.6) * 14), end[1] - int(math.sin(angle - 0.6) * 14))
        right = (end[0] - int(math.cos(angle + 0.6) * 14), end[1] - int(math.sin(angle + 0.6) * 14))
        pygame.draw.polygon(surface, color, [end, left, right])

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: BridgeDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "load":
            pygame.draw.line(surface, (91, 137, 173), (cx - 28, cy + 16), (cx + 28, cy + 16), 6)
            pygame.draw.rect(surface, (230, 157, 68), (cx - 13, cy - 20, 26, 23), border_radius=5)
            BridgePage._arrow(surface, (cx, cy - 28), (cx, cy + 8), (205, 92, 81))
        elif item.discovery_id == "shapes":
            pygame.draw.line(surface, (91, 137, 173), (cx - 30, cy + 17), (cx + 30, cy + 17), 5)
            pygame.draw.arc(surface, (91, 137, 173), (cx - 28, cy - 20, 56, 42), math.pi, math.tau, 4)
        elif item.discovery_id == "forces":
            pygame.draw.line(surface, (75, 145, 185), (cx - 25, cy + 20), (cx + 4, cy - 20), 6)
            pygame.draw.line(surface, (204, 86, 88), (cx + 4, cy - 20), (cx + 28, cy + 20), 6)
        else:
            for off in (-12, 0, 12):
                BridgePage._arrow(surface, (cx, cy - 25 + off), (cx, cy + 20 + off // 2), (239, 190, 68))

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (252, 249, 234), item.center, 37)
            pygame.draw.circle(surface, (75, 72, 67), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (252, 249, 234), panel, border_radius=22)
        pygame.draw.rect(surface, (75, 72, 67), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (53, 52, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (53, 52, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
