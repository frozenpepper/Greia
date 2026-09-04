"""Frog entry: common life cycle, metamorphosis, moist skin and diversity."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_animal_action_button,
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
        draw_animal_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class FrogDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    FrogDiscovery("cycle", "frog.cycle", "encyclopedia.animals.frog.cycle", (255, 200)),
    FrogDiscovery("metamorphosis", "frog.metamorphosis", "encyclopedia.animals.frog.metamorphosis", (750, 200)),
    FrogDiscovery("skin", "frog.skin", "encyclopedia.animals.frog.skin", (255, 415)),
    FrogDiscovery("variety", "frog.variety", "encyclopedia.animals.frog.variety", (750, 415)),
)

_STAGE_COUNT = 4


class FrogLifeCycleModel:
    """Own the finite common-cycle sequence and non-stage diversity reveal."""

    def __init__(self) -> None:
        self.stage = 0
        self.metamorphosis_progress = 0.0
        self.skin_age = 0.0
        self.variety_age = 0.0
        self.variety_mode = 0

    def update(self, dt: float) -> None:
        self.skin_age = max(0.0, self.skin_age - dt)
        self.variety_age = max(0.0, self.variety_age - dt)
        if self.metamorphosis_progress <= 0.0:
            return
        next_progress = self.metamorphosis_progress + dt * 0.4
        if next_progress >= 1.0:
            # Settle the demonstration into the froglet stage. The finite model
            # never remains in an artificial permanent "animation complete" state.
            self.stage = 2
            self.metamorphosis_progress = 0.0
        else:
            self.metamorphosis_progress = next_progress

    def advance_stage(self) -> None:
        self.stage = (self.stage + 1) % _STAGE_COUNT
        self.metamorphosis_progress = 0.0

    def demonstrate_metamorphosis(self) -> None:
        self.stage = 1
        self.metamorphosis_progress = 0.01

    def show_skin(self) -> None:
        self.skin_age = 4.0

    def toggle_variety(self) -> None:
        self.variety_mode = 1 - self.variety_mode
        self.variety_age = 4.5


class FrogPage(EncyclopediaPage):
    page_id = "animals.frog"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = FrogLifeCycleModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "frog.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.frog.intro")
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
        self._model.advance_stage()
        self._caption_key = "frog.cycle"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("animals", "frog", "cycle", "name"))
        self.context.audio.play("encyclopedia.animals.frog.cycle")

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
                cue = encyclopedia_focus_cue("animals", "frog", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == "cycle":
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
        if discovery.discovery_id == "cycle":
            self._model.advance_stage()
        elif discovery.discovery_id == "metamorphosis":
            self._model.demonstrate_metamorphosis()
        elif discovery.discovery_id == "skin":
            self._model.show_skin()
        else:
            self._model.toggle_variety()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((201, 231, 204))
        pygame.draw.rect(surface, (91, 169, 183), (0, 425, 1024, 175))
        pygame.draw.ellipse(surface, (128, 188, 102), (-80, 380, 650, 140))
        for index in range(7):
            x = 80 + index * 135
            pygame.draw.ellipse(surface, (95, 158, 88), (x, 430 + (index % 2) * 24, 95, 28))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("frog.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_stage(surface)
        self._draw_skin_reveal(surface)
        self._draw_variety_reveal(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_animal_action_button(
            surface, (512, 460), animal="frog", time=self._time, active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_stage(self, surface: pygame.Surface) -> None:
        cx, cy = 510, 330
        stage = self._model.stage
        if self._model.metamorphosis_progress > 0.0:
            self._draw_metamorphosis(surface, cx, cy)
            return
        if stage == 0:
            for index in range(7):
                angle = index * math.pi * 2 / 7
                x = cx + int(math.cos(angle) * 43)
                y = cy + int(math.sin(angle) * 30)
                pygame.draw.circle(surface, (235, 243, 220), (x, y), 15)
                pygame.draw.circle(surface, (72, 92, 62), (x, y), 6)
        elif stage == 1:
            self._draw_tadpole(surface, (cx, cy), legs=0, tail_scale=1.0)
        elif stage == 2:
            self._draw_tadpole(surface, (cx, cy), legs=4, tail_scale=0.45)
        else:
            self._draw_frog(surface, (cx, cy), scale=1.0)

        for index in range(_STAGE_COUNT):
            x = 450 + index * 40
            color = (246, 205, 72) if index == stage else (100, 139, 93)
            pygame.draw.circle(surface, color, (x, 455), 8)

    def _draw_metamorphosis(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        progress = self._model.metamorphosis_progress
        legs = 0
        if progress > 0.28:
            legs = 2
        if progress > 0.62:
            legs = 4
        tail_scale = max(0.12, 1.0 - progress * 0.85)
        self._draw_tadpole(surface, (cx, cy), legs=legs, tail_scale=tail_scale)

    @staticmethod
    def _draw_tadpole(
        surface: pygame.Surface,
        center: tuple[int, int],
        *,
        legs: int,
        tail_scale: float,
    ) -> None:
        cx, cy = center
        body = (91, 151, 82)
        pygame.draw.ellipse(surface, body, (cx - 48, cy - 35, 96, 70))
        tail_length = int(105 * tail_scale)
        pygame.draw.polygon(
            surface,
            (82, 137, 76),
            [(cx + 38, cy - 12), (cx + 45 + tail_length, cy), (cx + 38, cy + 12)],
        )
        pygame.draw.circle(surface, (37, 45, 34), (cx - 20, cy - 10), 5)
        pygame.draw.circle(surface, (37, 45, 34), (cx + 2, cy - 10), 5)
        if legs >= 2:
            pygame.draw.line(surface, body, (cx + 5, cy + 25), (cx - 22, cy + 63), 12)
            pygame.draw.line(surface, body, (cx + 25, cy + 22), (cx + 48, cy + 58), 12)
        if legs >= 4:
            pygame.draw.line(surface, body, (cx - 18, cy + 8), (cx - 48, cy + 30), 9)
            pygame.draw.line(surface, body, (cx + 13, cy + 8), (cx + 48, cy + 28), 9)

    @staticmethod
    def _draw_frog(surface: pygame.Surface, center: tuple[int, int], *, scale: float) -> None:
        cx, cy = center
        body = (93, 173, 86)
        body_light = (118, 190, 110)
        body_shadow = (68, 138, 62)
        body_w = int(110 * scale)
        body_h = int(70 * scale)
        # Body with shadow and highlight
        pygame.draw.ellipse(surface, (0, 0, 0, 22), (cx - body_w // 2 + 3, cy - body_h // 2 + 4, body_w, body_h))
        pygame.draw.ellipse(surface, body, (cx - body_w // 2, cy - body_h // 2, body_w, body_h))
        pygame.draw.ellipse(surface, body_light, (cx - body_w // 2 + 8, cy - body_h // 2 + 6, body_w - 16, body_h // 2))
        pygame.draw.ellipse(surface, body_shadow, (cx - body_w // 2, cy + 4, body_w, body_h // 2))
        eye_offset = int(34 * scale)
        eye_radius = max(8, int(15 * scale))
        for ex in (-eye_offset, eye_offset):
            pygame.draw.circle(surface, body_shadow, (cx + ex, cy - body_h // 2 + 2), eye_radius)
            pygame.draw.circle(surface, body, (cx + ex, cy - body_h // 2), eye_radius)
            pygame.draw.circle(surface, (247, 247, 229), (cx + ex, cy - body_h // 2), max(5, int(8 * scale)))
            pygame.draw.circle(surface, (255, 255, 255, 90), (cx + ex - 2, cy - body_h // 2 - 2), max(2, int(3 * scale)))
            pygame.draw.circle(surface, (38, 48, 36), (cx + ex, cy - body_h // 2), max(2, int(4 * scale)))
            pygame.draw.circle(surface, (255, 255, 255, 40), (cx + ex - 1, cy - body_h // 2 - 1), 1)
        # Legs with highlight
        for lx, ly, rx, ry in ((-35, 18, -77, 55), (35, 18, 77, 55), (-28, 5, -62, 18), (28, 5, 62, 18)):
            pygame.draw.line(surface, body_shadow, (cx + lx, cy + ly + 1), (cx + rx, cy + ry + 1), max(8, int(13 * scale)))
            pygame.draw.line(surface, body, (cx + lx, cy + ly), (cx + rx, cy + ry), max(7, int(12 * scale)))
            pygame.draw.line(surface, body_light, (cx + lx, cy + ly), (cx + (lx + rx) // 2, cy + (ly + ry) // 2), max(3, int(6 * scale)))

    def _draw_skin_reveal(self, surface: pygame.Surface) -> None:
        if self._model.skin_age <= 0:
            return
        panel = pygame.Rect(380, 180, 260, 100)
        pygame.draw.rect(surface, (239, 248, 226), panel, border_radius=20)
        pygame.draw.rect(surface, (62, 86, 59), panel, 3, border_radius=20)
        for index in range(10):
            x = 400 + (index * 23) % 210
            y = 205 + (index % 3) * 23
            pygame.draw.circle(surface, (84, 168, 108), (x, y), 10)
            pygame.draw.circle(surface, (125, 197, 221), (x + 5, y - 8), 4)
        for y in (205, 228, 251):
            pygame.draw.line(surface, (125, 197, 221), (397, y), (367, y - 8), 3)

    def _draw_variety_reveal(self, surface: pygame.Surface) -> None:
        if self._model.variety_age <= 0:
            return
        panel = pygame.Rect(370, 175, 280, 115)
        pygame.draw.rect(surface, (248, 245, 220), panel, border_radius=20)
        pygame.draw.rect(surface, (70, 79, 57), panel, 3, border_radius=20)
        if self._model.variety_mode == 0:
            pygame.draw.ellipse(surface, (91, 169, 183), (400, 220, 115, 40))
            for index in range(5):
                pygame.draw.circle(surface, (235, 243, 220), (420 + index * 19, 218), 10)
                pygame.draw.circle(surface, (70, 92, 61), (420 + index * 19, 218), 4)
        else:
            pygame.draw.ellipse(surface, (235, 242, 219), (395, 235, 105, 32))
            pygame.draw.polygon(surface, (123, 181, 95), [(410, 236), (447, 190), (484, 236)])
            pygame.draw.ellipse(surface, (240, 245, 226), (525, 214, 86, 45))
            for index in range(4):
                pygame.draw.circle(surface, (224, 235, 212), (548 + index * 12, 230 + (index % 2) * 7), 8)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (247, 250, 229), item.center, 37)
            pygame.draw.circle(surface, (66, 75, 56), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "cycle":
                for offset, radius in ((-20, 7), (0, 10), (21, 13)):
                    pygame.draw.circle(surface, (91, 169, 83), (cx + offset, cy), radius)
                pygame.draw.line(surface, (75, 112, 68), (cx - 13, cy), (cx - 5, cy), 4)
                pygame.draw.line(surface, (75, 112, 68), (cx + 10, cy), (cx + 14, cy), 4)
            elif item.discovery_id == "metamorphosis":
                pygame.draw.ellipse(surface, (91, 151, 82), (cx - 25, cy - 13, 42, 26))
                pygame.draw.line(surface, (91, 151, 82), (cx + 14, cy), (cx + 29, cy + 18), 7)
                pygame.draw.line(surface, (91, 151, 82), (cx - 4, cy + 11), (cx - 20, cy + 28), 6)
            elif item.discovery_id == "skin":
                pygame.draw.circle(surface, (93, 173, 86), (cx, cy + 4), 20)
                for dx, dy in ((-18, -18), (4, -24), (20, -10)):
                    pygame.draw.circle(surface, (125, 197, 221), (cx + dx, cy + dy), 5)
            else:
                pygame.draw.ellipse(surface, (91, 169, 183), (cx - 29, cy + 4, 26, 14))
                pygame.draw.polygon(surface, (123, 181, 95), [(cx + 2, cy + 15), (cx + 14, cy - 15), (cx + 28, cy + 15)])
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (247, 250, 229), panel, border_radius=22)
        pygame.draw.rect(surface, (66, 75, 56), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (51, 57, 47))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (51, 57, 47))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
