"""Lungs entry: breathing mechanics, airways, gas exchange and activity response."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_breathe_button,
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
        draw_breathe_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class LungsDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    LungsDiscovery("breath", "lungs.breath", "encyclopedia.body.lungs.breath", (250, 190)),
    LungsDiscovery("airways", "lungs.airways", "encyclopedia.body.lungs.airways", (755, 190)),
    LungsDiscovery("exchange", "lungs.exchange", "encyclopedia.body.lungs.exchange", (250, 420)),
    LungsDiscovery("exercise", "lungs.exercise", "encyclopedia.body.lungs.exercise", (755, 420)),
)


class BreathingModel:
    """Own the bounded inhale/exhale and activity-rate teaching state."""

    def __init__(self) -> None:
        self.time = 0.0
        self.manual_inhale = False
        self.breath_demo_age = 0.0
        self.airways_age = 0.0
        self.exchange_age = 0.0
        self.exercise_age = 0.0

    @property
    def rate(self) -> float:
        return 1.7 if self.exercise_age > 0.0 else 1.0

    @property
    def expansion(self) -> float:
        if self.breath_demo_age > 0.0:
            return 1.0 if self.manual_inhale else -1.0
        return math.sin(self.time * 1.55 * self.rate)

    def update(self, dt: float) -> None:
        self.time += dt
        self.breath_demo_age = max(0.0, self.breath_demo_age - dt)
        self.airways_age = max(0.0, self.airways_age - dt)
        self.exchange_age = max(0.0, self.exchange_age - dt)
        self.exercise_age = max(0.0, self.exercise_age - dt)

    def toggle_breath(self) -> None:
        self.manual_inhale = not self.manual_inhale
        self.breath_demo_age = 3.0

    def reveal_airways(self) -> None:
        self.airways_age = 4.0

    def reveal_exchange(self) -> None:
        self.exchange_age = 4.5

    def exercise(self) -> None:
        self.exercise_age = 4.5


class LungsPage(EncyclopediaPage):
    page_id = "body.lungs"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = BreathingModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "lungs.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._breathe_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.body.lungs.intro")
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
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._breathe_hit.collidepoint(point):
                    self._trigger_breathe()
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
                cue = encyclopedia_focus_cue("body", "lungs", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == "breath":
                self._trigger_breathe()
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

    def _trigger_breathe(self) -> None:
        self._model.toggle_breath()
        self._caption_key = "lungs.breath"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("body", "lungs", "breath", "name"))
        self.context.audio.play("encyclopedia.body.lungs.breath")

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "breath":
            self._model.toggle_breath()
        elif discovery.discovery_id == "airways":
            self._model.reveal_airways()
        elif discovery.discovery_id == "exchange":
            self._model.reveal_exchange()
        else:
            self._model.exercise()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((237, 242, 246))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("lungs.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_body_and_lungs(surface)
        self._draw_hotspots(surface)
        # Standard navigation for discovery
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Main toy — big breathe button at bottom center
        inhaling = self._model.manual_inhale and self._model.breath_demo_age > 0
        exercising = self._model.exercise_age > 0
        self._breathe_hit = draw_breathe_button(
            surface, (512, 485), time=self._time, inhaling=inhaling, exercise=exercising
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

    def _draw_body_and_lungs(self, surface: pygame.Surface) -> None:
        skin = (235, 190, 161)
        skin_light = (245, 210, 185)
        skin_shadow = (210, 165, 138)
        # Head with highlight
        pygame.draw.circle(surface, skin, (505, 178), 40)
        pygame.draw.circle(surface, skin_light, (494, 166), 10)
        pygame.draw.circle(surface, skin, (505, 178), 40, 2)
        # Torso with soft shadow and rib hint
        torso = pygame.Rect(442, 222, 126, 235)
        pygame.draw.rect(surface, skin_shadow, torso.move(3, 5), border_radius=48)
        pygame.draw.rect(surface, skin, torso, border_radius=48)
        pygame.draw.rect(surface, skin_light, torso.inflate(-12, -12), border_radius=42, width=3)
        for ry in (240, 258, 276):
            pygame.draw.arc(surface, (218, 175, 160), (450, ry, 90, 16), 0.30, 2.84, 2)
        expansion = self._model.expansion
        lung_width = 46 + int(5 * expansion)
        lung_height = 96 + int(8 * expansion)
        left = pygame.Rect(505 - lung_width - 4, 265, lung_width, lung_height)
        right = pygame.Rect(509, 265, lung_width, lung_height)
        # Lung shadow + highlight for depth
        for rect in (left, right):
            shadow = pygame.Surface((rect.width + 10, rect.height + 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 22), shadow.get_rect())
            surface.blit(shadow, (rect.x - 3, rect.y + 4))
        pygame.draw.ellipse(surface, (210, 135, 145), left)
        pygame.draw.ellipse(surface, (210, 135, 145), right)
        pygame.draw.ellipse(surface, (221, 151, 161), left.inflate(-4, -4))
        pygame.draw.ellipse(surface, (221, 151, 161), right.inflate(-4, -4))
        pygame.draw.ellipse(surface, (235, 175, 182), left.inflate(-12, -12))
        pygame.draw.ellipse(surface, (235, 175, 182), right.inflate(-12, -12))

        diaphragm_y = 382 + int(9 * expansion)
        pygame.draw.arc(
            surface,
            (150, 104, 116),
            (453, diaphragm_y - 18, 104, 42),
            0.15,
            math.pi - 0.15,
            4,
        )

        if self._model.breath_demo_age > 0.0:
            direction = 1 if self._model.manual_inhale else -1
            for offset in (-20, 0, 20):
                x = 505 + offset
                y1 = 230 - direction * 16
                y2 = 245 + direction * 16
                pygame.draw.line(surface, (91, 151, 196), (x, y1), (x, y2), 4)
                pygame.draw.circle(surface, (91, 151, 196), (x, y2), 4)

        if self._model.airways_age > 0.0:
            pygame.draw.line(surface, (119, 102, 120), (505, 220), (505, 282), 8)
            self._draw_branch(surface, (505, 282), (475, 309), depth=3)
            self._draw_branch(surface, (505, 282), (535, 309), depth=3)

        if self._model.exchange_age > 0.0:
            self._draw_exchange_zoom(surface)

        if self._model.exercise_age > 0.0:
            for index in range(4):
                x = 575 + index * 15
                y = 255 + index * 28
                pygame.draw.line(surface, (213, 94, 84), (x, y + 8), (x + 20, y - 8), 5)
                pygame.draw.line(surface, (213, 94, 84), (x + 12, y - 2), (x + 28, y + 8), 4)

    def _draw_branch(
        self,
        surface: pygame.Surface,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        depth: int,
    ) -> None:
        width = max(2, depth + 1)
        pygame.draw.line(surface, (132, 102, 117), start, end, width)
        if depth <= 1:
            pygame.draw.circle(surface, (238, 183, 188), end, 5)
            return
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        next_y = end[1] + 22
        self._draw_branch(surface, end, (end[0] + dx // 2 - 8, next_y + dy // 5), depth=depth - 1)
        self._draw_branch(surface, end, (end[0] + dx // 2 + 8, next_y + dy // 5), depth=depth - 1)

    def _draw_exchange_zoom(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(590, 260, 180, 135)
        pygame.draw.rect(surface, (252, 247, 239), panel, border_radius=20)
        pygame.draw.rect(surface, (111, 91, 100), panel, 3, border_radius=20)
        centers = ((625, 310), (660, 290), (695, 315), (730, 292))
        for center in centers:
            pygame.draw.circle(surface, (242, 196, 199), center, 19)
            pygame.draw.circle(surface, (177, 117, 126), center, 19, 2)
        pygame.draw.line(surface, (126, 69, 89), (610, 350), (750, 350), 8)
        phase = (self._model.time * 0.55) % 1.0
        oxygen_x = 620 + int(105 * phase)
        carbon_x = 730 - int(95 * phase)
        pygame.draw.circle(surface, (202, 78, 79), (oxygen_x, 337), 7)
        pygame.draw.circle(surface, (102, 78, 98), (carbon_x, 323), 7)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: LungsDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "breath":
            pygame.draw.ellipse(surface, (221, 151, 161), (cx - 23, cy - 25, 20, 48))
            pygame.draw.ellipse(surface, (221, 151, 161), (cx + 3, cy - 25, 20, 48))
            pygame.draw.line(surface, (91, 151, 196), (cx, cy - 30), (cx, cy + 28), 4)
        elif item.discovery_id == "airways":
            pygame.draw.line(surface, (132, 102, 117), (cx, cy - 26), (cx, cy), 6)
            pygame.draw.line(surface, (132, 102, 117), (cx, cy), (cx - 18, cy + 22), 5)
            pygame.draw.line(surface, (132, 102, 117), (cx, cy), (cx + 18, cy + 22), 5)
        elif item.discovery_id == "exchange":
            pygame.draw.circle(surface, (242, 196, 199), (cx - 10, cy - 4), 14)
            pygame.draw.circle(surface, (202, 78, 79), (cx + 17, cy + 11), 7)
            pygame.draw.circle(surface, (102, 78, 98), (cx + 17, cy - 13), 7)
        else:
            pygame.draw.circle(surface, (228, 157, 163), (cx - 14, cy - 2), 13)
            pygame.draw.line(surface, (74, 70, 70), (cx + 2, cy + 16), (cx + 18, cy - 15), 7)
            pygame.draw.line(surface, (74, 70, 70), (cx + 6, cy + 4), (cx + 25, cy + 14), 7)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (253, 249, 239), item.center, 37)
            pygame.draw.circle(surface, (87, 68, 73), item.center, 37, 3)
            self._draw_hotspot_icon(surface, item)
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (253, 249, 239), panel, border_radius=22)
        pygame.draw.rect(surface, (87, 68, 73), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (57, 51, 55))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (57, 51, 55))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
