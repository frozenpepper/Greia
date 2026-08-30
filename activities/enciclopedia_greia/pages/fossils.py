"""Fossils final-entry pilot: bounded brushing, body/trace evidence and burial clues."""

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
        draw_focus_patch,
        draw_history_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class FossilDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    FossilDiscovery("brush", "fossils.definition", "encyclopedia.history.fossils.definition", (260, 190)),
    FossilDiscovery("types", "fossils.types", "encyclopedia.history.fossils.types", (745, 190)),
    FossilDiscovery("burial", "fossils.burial", "encyclopedia.history.fossils.burial", (260, 420)),
    FossilDiscovery("clues", "fossils.clues", "encyclopedia.history.fossils.clues", (745, 420)),
)

_DIG_RECT = pygame.Rect(370, 180, 270, 270)
_COLUMNS = 4
_ROWS = 3
_CELL_W = _DIG_RECT.width // _COLUMNS
_CELL_H = _DIG_RECT.height // _ROWS


class FossilDigModel:
    """Own the finite sediment grid and one-time reveal semantics."""

    def __init__(self) -> None:
        self._cleared = [False] * (_COLUMNS * _ROWS)
        self._next_index = 0
        self._rare_announced = False
        self.burial_age = 0.0
        self.clue_age = 0.0
        self.types_age = 0.0

    @property
    def cleared_count(self) -> int:
        return sum(self._cleared)

    @property
    def complete(self) -> bool:
        return self.cleared_count == len(self._cleared)

    def is_cleared(self, index: int) -> bool:
        return self._cleared[index]

    def update(self, dt: float) -> None:
        self.burial_age = max(0.0, self.burial_age - dt)
        self.clue_age = max(0.0, self.clue_age - dt)
        self.types_age = max(0.0, self.types_age - dt)

    def clear(self, index: int) -> bool:
        if index < 0 or index >= len(self._cleared) or self._cleared[index]:
            return False
        self._cleared[index] = True
        if index == self._next_index:
            self._advance_next()
        return True

    def clear_next(self) -> bool:
        if self.complete:
            return False
        index = self._next_index
        self._cleared[index] = True
        self._advance_next()
        return True

    def consume_completion_announcement(self) -> bool:
        """Return True exactly once when the finite dig becomes complete."""

        if not self.complete or self._rare_announced:
            return False
        self._rare_announced = True
        return True

    def _advance_next(self) -> None:
        while self._next_index < len(self._cleared) and self._cleared[self._next_index]:
            self._next_index += 1

    def show_types(self) -> None:
        self.types_age = 3.5

    def show_burial(self) -> None:
        self.burial_age = 3.5

    def show_clues(self) -> None:
        self.clue_age = 3.5


class FossilsPage(EncyclopediaPage):
    page_id = "history.fossils"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = FossilDigModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "fossils.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.fossils.intro")
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
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "brush":
            self._clear_next()
        elif discovery.discovery_id == "types":
            self._model.show_types()
        elif discovery.discovery_id == "burial":
            self._model.show_burial()
        else:
            self._model.show_clues()
        self.context.audio.play(discovery.cue_id)

    def _clear_cell(self, index: int) -> None:
        if self._model.clear(index):
            self._after_clear()

    def _clear_next(self) -> None:
        if self._model.clear_next():
            self._after_clear()

    def _after_clear(self) -> None:
        if self._model.consume_completion_announcement():
            self._caption_key = "fossils.rare"
            self.context.audio.play("encyclopedia.history.fossils.rare")

    @staticmethod
    def _cell_at(point: tuple[int, int]) -> int | None:
        if not _DIG_RECT.collidepoint(point):
            return None
        col = min(_COLUMNS - 1, (point[0] - _DIG_RECT.x) // _CELL_W)
        row = min(_ROWS - 1, (point[1] - _DIG_RECT.y) // _CELL_H)
        return row * _COLUMNS + col

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((237, 218, 177))
        pygame.draw.rect(surface, (154, 112, 73), (0, 470, 1024, 130))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("fossils.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_dig(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_history_action_button(
            surface, (512, 485), history="fossils", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="default",
            fallback_color=(205, 155, 83),
        )

    def _draw_dig(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (206, 174, 124), _DIG_RECT, border_radius=20)
        self._draw_hidden_fossils(surface)

        for index in range(_COLUMNS * _ROWS):
            if self._model.is_cleared(index):
                continue
            row, col = divmod(index, _COLUMNS)
            rect = pygame.Rect(
                _DIG_RECT.x + col * _CELL_W,
                _DIG_RECT.y + row * _CELL_H,
                _CELL_W,
                _CELL_H,
            )
            shade = 188 + (index % 3) * 8
            pygame.draw.rect(
                surface,
                (shade, 151, 102),
                rect.inflate(-2, -2),
                border_radius=8,
            )
            for pebble in range(3):
                px = rect.x + 15 + ((index * 17 + pebble * 19) % max(20, rect.width - 30))
                py = rect.y + 16 + ((index * 11 + pebble * 23) % max(20, rect.height - 30))
                pygame.draw.circle(surface, (148, 113, 82), (px, py), 3 + pebble)

        pygame.draw.rect(surface, (92, 71, 55), _DIG_RECT, 4, border_radius=20)

        if self._model.burial_age > 0:
            for index in range(9):
                x = 390 + (index * 31) % 230
                fall = int((1.0 - min(1.0, self._model.burial_age / 3.5)) * 120)
                y = 145 + (index % 3) * 12 + fall
                pygame.draw.circle(surface, (166, 127, 88), (x, y), 6 + index % 3)

        if self._model.types_age > 0:
            pygame.draw.ellipse(surface, (255, 223, 117), (410, 238, 92, 70), 5)
            pygame.draw.ellipse(surface, (255, 223, 117), (535, 335, 72, 82), 5)

        if self._model.clue_age > 0:
            for y in (205, 280, 355, 430):
                pygame.draw.line(surface, (249, 222, 128), (375, y), (635, y), 4)

    @staticmethod
    def _draw_hidden_fossils(surface: pygame.Surface) -> None:
        center = (455, 275)
        for radius in (38, 30, 22, 14):
            pygame.draw.arc(
                surface,
                (103, 82, 63),
                (center[0] - radius, center[1] - radius, radius * 2, radius * 2),
                0.2,
                math.pi * 1.75,
                6,
            )
        footprint = (565, 365)
        pygame.draw.ellipse(surface, (103, 82, 63), (footprint[0] - 20, footprint[1] - 8, 40, 55))
        for dx, dy in ((-22, -30), (-8, -40), (8, -40), (22, -28)):
            pygame.draw.circle(surface, (103, 82, 63), (footprint[0] + dx, footprint[1] + dy), 8)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 247, 222), item.center, 37)
            pygame.draw.circle(surface, (88, 67, 52), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "brush":
                pygame.draw.line(surface, (113, 75, 48), (cx - 18, cy + 19), (cx + 8, cy - 10), 9)
                pygame.draw.ellipse(surface, (225, 191, 116), (cx + 2, cy - 24, 25, 18))
            elif item.discovery_id == "types":
                pygame.draw.arc(surface, (139, 105, 73), (cx - 25, cy - 20, 38, 38), 0.1, math.pi * 1.8, 5)
                pygame.draw.ellipse(surface, (139, 105, 73), (cx + 7, cy - 3, 22, 29))
            elif item.discovery_id == "burial":
                for row in range(3):
                    pygame.draw.line(
                        surface,
                        (157, 113 + row * 12, 78),
                        (cx - 24, cy - 15 + row * 14),
                        (cx + 24, cy - 15 + row * 14),
                        7,
                    )
            else:
                pygame.draw.circle(surface, (249, 222, 128), (cx - 5, cy - 4), 15, 4)
                pygame.draw.line(surface, (88, 67, 52), (cx + 7, cy + 8), (cx + 22, cy + 23), 7)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 247, 222), panel, border_radius=22)
        pygame.draw.rect(surface, (88, 67, 52), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (58, 47, 40))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (58, 47, 40))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
