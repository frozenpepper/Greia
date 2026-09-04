"""Elephant entry: trunk dexterity, water, cooling ears and social touch."""

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
class ElephantDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    ElephantDiscovery("trunk", "elephant.trunk", "encyclopedia.animals.elephant.trunk", (260, 205)),
    ElephantDiscovery("water", "elephant.water", "encyclopedia.animals.elephant.water", (745, 205)),
    ElephantDiscovery("ears", "elephant.ears", "encyclopedia.animals.elephant.ears", (260, 410)),
    ElephantDiscovery("social", "elephant.social", "encyclopedia.animals.elephant.social", (745, 410)),
)


class ElephantPage(EncyclopediaPage):
    """Own a small deterministic elephant exhibit without simulation machinery."""

    page_id = "animals.elephant"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._trunk_state = 0
        self._water_age = 0.0
        self._ear_age = 0.0
        self._social_age = 0.0
        self._caption_key = "elephant.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._trunk_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.elephant.intro")
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
        self._water_age = max(0.0, self._water_age - dt)
        self._ear_age = max(0.0, self._ear_age - dt)
        self._social_age = max(0.0, self._social_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._trunk_hit.collidepoint(point):
                    self._trigger_trunk()
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
                cue = encyclopedia_focus_cue("animals", "elephant", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == "trunk":
                self._trigger_trunk()
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

    def _trigger_trunk(self) -> None:
        self._trunk_state = (self._trunk_state + 1) % 3
        self._water_age = 3.0 if self._trunk_state == 2 else 0.0
        self._caption_key = "elephant.trunk"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("animals", "elephant", "trunk", "name"))
        self.context.audio.play("encyclopedia.animals.elephant.trunk")

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "trunk":
            self._trunk_state = (self._trunk_state + 1) % 3
        elif discovery.discovery_id == "water":
            self._water_age = 3.0
        elif discovery.discovery_id == "ears":
            self._ear_age = 4.0
        else:
            self._social_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((213, 231, 203))
        pygame.draw.rect(surface, (156, 184, 112), (0, 430, 1024, 170))
        pygame.draw.ellipse(surface, (100, 166, 192), (690, 450, 220, 95))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("elephant.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_elephant(surface)
        self._draw_hotspots(surface)
        # Standard navigation for discovery
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Main toy — big trunk button
        self._trunk_hit = draw_animal_action_button(
            surface, (512, 460), animal="elephant", time=self._time, active=True
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

    def _draw_elephant(self, surface: pygame.Surface) -> None:
        body = (143, 153, 160)
        body_light = (168, 176, 182)
        body_shadow = (115, 124, 131)
        dark = (77, 79, 82)
        cx, cy = 500, 330
        # Soft ground shadow
        pygame.draw.ellipse(surface, (0, 0, 0, 24), (405, 462, 190, 16))
        pygame.draw.ellipse(surface, body_shadow, (405, 285, 190, 130))
        pygame.draw.ellipse(surface, body, (405, 283, 190, 130))
        pygame.draw.ellipse(surface, body_light, (418, 292, 60, 48))
        pygame.draw.circle(surface, body_shadow, (548, 282), 62)
        pygame.draw.circle(surface, body, (548, 280), 62)
        pygame.draw.circle(surface, body_light, (532, 262), 22)
        flap = math.sin(self._time * (5.0 if self._ear_age > 0 else 1.2))
        ear_w = 58 + int(abs(flap) * (13 if self._ear_age > 0 else 4))
        # Ears with inner pink and highlight
        pygame.draw.ellipse(surface, (108, 122, 133), (500 - ear_w, 245, ear_w, 90))
        pygame.draw.ellipse(surface, (126, 139, 149), (500 - ear_w + 4, 249, ear_w - 8, 82))
        pygame.draw.ellipse(surface, (178, 145, 155), (500 - ear_w + 14, 265, ear_w - 28, 50))
        pygame.draw.ellipse(surface, (108, 122, 133), (548, 245, ear_w, 90))
        pygame.draw.ellipse(surface, (126, 139, 149), (548 + 4, 249, ear_w - 8, 82))
        pygame.draw.ellipse(surface, (178, 145, 155), (548 + 14, 265, ear_w - 28, 50))

        for x in (438, 482, 548, 580):
            pygame.draw.line(surface, body, (x, 380), (x - 3, 465), 23)
            pygame.draw.ellipse(surface, body, (x - 15, 450, 31, 19))

        pygame.draw.circle(surface, dark, (568, 270), 4)
        pygame.draw.line(surface, (235, 234, 220), (588, 292), (605, 315), 6)

        trunk_paths = (
            ((575, 305), (602, 330), (611, 367), (593, 397)),
            ((575, 305), (606, 320), (635, 335), (660, 326)),
            ((575, 305), (603, 342), (618, 390), (642, 425)),
        )
        pygame.draw.lines(surface, body, False, trunk_paths[self._trunk_state], 19)
        for point in trunk_paths[self._trunk_state][1:]:
            pygame.draw.circle(surface, body, point, 9)

        if self._water_age > 0:
            progress = 1.0 - self._water_age / 3.0
            for index in range(14):
                t = index / 13
                x = 610 + int(120 * t)
                y = 375 - int(100 * math.sin(t * math.pi)) + int(progress * 5)
                pygame.draw.circle(surface, (91, 176, 216), (x, y), 4 + index % 2)

        if self._ear_age > 0:
            for index in range(5):
                y = 245 + index * 15
                pygame.draw.line(surface, (111, 184, 211), (465, y), (425 - index * 5, y - 4), 3)
                pygame.draw.line(surface, (111, 184, 211), (630, y), (670 + index * 5, y - 4), 3)

        if self._social_age > 0:
            second_x = 350
            pygame.draw.ellipse(surface, (158, 167, 173), (second_x - 42, 365, 90, 62))
            pygame.draw.circle(surface, (158, 167, 173), (second_x + 35, 365), 31)
            pygame.draw.lines(
                surface,
                (158, 167, 173),
                False,
                ((second_x + 53, 378), (second_x + 76, 370), (395, 350), (425, 344)),
                12,
            )
            pygame.draw.lines(surface, body, False, ((575, 305), (540, 330), (500, 340), (425, 344)), 11)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 250, 230), item.center, 37)
            pygame.draw.circle(surface, (75, 73, 68), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "trunk":
                pygame.draw.lines(surface, (143, 153, 160), False, ((cx - 17, cy - 20), (cx + 5, cy), (cx + 15, cy + 25)), 9)
            elif item.discovery_id == "water":
                for dx, dy in ((-16, 8), (-5, -8), (8, 5), (18, -12)):
                    pygame.draw.circle(surface, (91, 176, 216), (cx + dx, cy + dy), 6)
            elif item.discovery_id == "ears":
                pygame.draw.ellipse(surface, (143, 153, 160), (cx - 28, cy - 20, 24, 42))
                pygame.draw.ellipse(surface, (143, 153, 160), (cx + 4, cy - 20, 24, 42))
            else:
                pygame.draw.circle(surface, (143, 153, 160), (cx - 13, cy), 13)
                pygame.draw.circle(surface, (170, 177, 181), (cx + 13, cy), 11)
                pygame.draw.line(surface, (75, 73, 68), (cx - 2, cy + 5), (cx + 3, cy + 5), 5)
            if index == self._selected or index == self._hovered:
                draw_focus_patch(surface, rect, active=True, radius=16, time=self._time)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 250, 230), panel, border_radius=22)
        pygame.draw.rect(surface, (75, 73, 68), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 53, 49))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 53, 49))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
