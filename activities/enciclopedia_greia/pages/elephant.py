"""Elephant entry: trunk dexterity, water, cooling ears and social touch."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
    from .storybook_ink import inked_ellipse, inked_limb
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step
    from pages.storybook_ink import inked_ellipse, inked_limb


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
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.animals.elephant.waterhole",
        )
        if not authored:
            # Procedural fallback while the authored runtime rendition is absent.
            surface.fill((213, 231, 203))
            pygame.draw.rect(surface, (156, 184, 112), (0, 430, 1024, 170))
            pygame.draw.ellipse(surface, (100, 166, 192), (690, 450, 220, 95))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("elephant.title"),
            self.context.palette.ink,
        )
        self._draw_elephant(surface, authored=authored)
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
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_elephant(self, surface: pygame.Surface, *, authored: bool) -> None:
        body = (163, 174, 186)
        body_dark = (134, 146, 159)
        pink = (242, 182, 191)
        head_cx, head_cy = 575, 275
        flap = math.sin(self._time * (6.5 if self._ear_age > 0 else 1.6))
        if not authored:
            self._draw_procedural_body(surface, flap)
        # Live puppet parts: the authored scene bakes the body, legs, back ear,
        # head, eye and tusk; the front ear and the trunk move, so they stay live
        # and are inked in the same recipe as the SVG master.
        ear_w = 68 + int(abs(flap) * (20 if self._ear_age > 0 else 6))
        ear_rect = pygame.Rect(520 - ear_w // 2, 222, ear_w, 98)
        inked_ellipse(surface, body, ear_rect)
        inner_ear_rect = ear_rect.inflate(-20, -28)
        if inner_ear_rect.width > 6 and inner_ear_rect.height > 6:
            inner_ear_rect.x += 3
            pygame.draw.ellipse(surface, pink, inner_ear_rect)
        pygame.draw.arc(surface, (211, 219, 226), ear_rect.inflate(-10, -12), 1.7, 2.9, 3)

        trunk_base = (head_cx + 42, head_cy + 16)
        if self._trunk_state == 0:
            # Friendly resting curl up
            trunk_pts = [
                trunk_base,
                (head_cx + 64, head_cy + 38),
                (head_cx + 74, head_cy + 74),
                (head_cx + 60, head_cy + 102),
                (head_cx + 72, head_cy + 108),  # tip curled up
            ]
            trunk_widths = [30, 25, 21, 17, 14]
        elif self._trunk_state == 1:
            # Joyous high trumpet salute!
            trunk_pts = [
                trunk_base,
                (head_cx + 68, head_cy + 18),
                (head_cx + 94, head_cy - 10),
                (head_cx + 108, head_cy - 45),
                (head_cx + 98, head_cy - 65),  # tip curling back
            ]
            trunk_widths = [30, 26, 21, 17, 13]
        else:
            # Water spraying pose: trunk curled forward toward pond
            trunk_pts = [
                trunk_base,
                (head_cx + 68, head_cy + 35),
                (head_cx + 86, head_cy + 65),
                (head_cx + 108, head_cy + 82),
                (head_cx + 124, head_cy + 76),
            ]
            trunk_widths = [30, 25, 21, 17, 14]
        inked_limb(surface, body, trunk_pts, trunk_widths)
        # Soft trunk wrinkles read as a trunk rather than a tube.
        for (ax, ay), (bx, by), width in zip(trunk_pts[1:-1], trunk_pts[2:], trunk_widths[1:]):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / length * width * 0.32, dx / length * width * 0.32
            for t in (0.35, 0.65):
                mx, my = ax + dx * t, ay + dy * t
                pygame.draw.line(surface, body_dark, (mx - nx, my - ny), (mx + nx, my + ny), 2)

        # Water spray effects when trunk is active or water toy triggered
        if self._water_age > 0:
            tip = trunk_pts[-1]
            progress = 1.0 - self._water_age / 3.0
            for index in range(20):
                t = index / 19.0
                drop_x = tip[0] + int(140 * t) + int(math.sin(self._time * 10 + index) * 8)
                drop_y = tip[1] - int(75 * math.sin(t * math.pi)) + int(t * 110) + int(progress * 10)
                drop_r = 3 + (index % 4)
                pygame.draw.circle(surface, (74, 145, 216), (drop_x, drop_y), drop_r + 1)
                pygame.draw.circle(surface, (178, 222, 245), (drop_x - 1, drop_y - 1), max(1, drop_r - 1))

        # Cooling ear wind ripples when ears flapping
        if self._ear_age > 0:
            for index in range(5):
                y = 230 + index * 16
                wave_x = int(math.sin(self._time * 8 + index) * 6)
                pygame.draw.arc(surface, (74, 145, 216), pygame.Rect(440 + wave_x, y, 40, 20), 0.5, 2.5, 3)
                pygame.draw.arc(surface, (74, 145, 216), pygame.Rect(630 + wave_x, y, 40, 20), 0.5, 2.5, 3)

        # Social touch: a calf greets the adult, trunk to trunk.
        if self._social_age > 0:
            second_x = 340
            calf = (178, 188, 198)
            inked_limb(
                surface,
                calf,
                [(second_x + 50, 368), (second_x + 72, 362), (390, 345), (420, 340)],
                [12, 10, 9],
            )
            inked_ellipse(surface, calf, pygame.Rect(second_x - 45, 360, 85, 60))
            for leg_x in (second_x - 30, second_x + 12):
                pygame.draw.rect(surface, (75, 55, 47), (leg_x - 2, 400, 20, 32), border_radius=7)
                pygame.draw.rect(surface, calf, (leg_x + 1, 400, 14, 29), border_radius=6)
            inked_ellipse(surface, calf, pygame.Rect(second_x - 2, 334, 30, 44))
            pygame.draw.ellipse(surface, (242, 182, 191), (second_x + 4, 342, 16, 28))
            inked_ellipse(surface, calf, pygame.Rect(second_x + 7, 332, 56, 56))
            pygame.draw.circle(surface, (52, 44, 53), (second_x + 42, 354), 4)
            pygame.draw.circle(surface, (255, 255, 255), (second_x + 43, 352), 1)
            # Floating friendly hearts
            heart_y = int(320 - (4.0 - self._social_age) * 15)
            pygame.draw.circle(surface, (216, 86, 131), (380, heart_y), 6)
            pygame.draw.circle(surface, (216, 86, 131), (388, heart_y), 6)
            pygame.draw.polygon(surface, (216, 86, 131), [(374, heart_y + 2), (394, heart_y + 2), (384, heart_y + 12)])

    def _draw_procedural_body(self, surface: pygame.Surface, flap: float) -> None:
        """Fallback elephant body used only when the authored scene is missing."""

        body = (148, 164, 178)
        body_dark = (116, 130, 142)
        tusk_col = (255, 252, 240)
        dark_ink = (40, 34, 30)
        head_cx, head_cy = 575, 275
        pygame.draw.ellipse(surface, (126, 150, 104), (350, 440, 280, 36))
        for lx in (430, 520):
            pygame.draw.rect(surface, body_dark, pygame.Rect(lx, 340, 42, 115), border_radius=14)
        tail_wag = math.sin(self._time * 2.5) * 6
        tail_end = (368 + tail_wag, 375)
        pygame.draw.lines(surface, body_dark, False, [(395, 315), (372, 345 + tail_wag * 0.5), tail_end], 6)
        pygame.draw.circle(surface, (85, 75, 70), (int(tail_end[0]), int(tail_end[1])), 8)
        body_rect = pygame.Rect(388, 255, 195, 150)
        pygame.draw.ellipse(surface, body, body_rect)
        pygame.draw.ellipse(surface, body_dark, body_rect, 3)
        for lx in (465, 555):
            leg_rect = pygame.Rect(lx, 335, 46, 120)
            pygame.draw.rect(surface, body, leg_rect, border_radius=16)
            pygame.draw.rect(surface, body_dark, leg_rect, width=3, border_radius=16)
            for ti in range(3):
                pygame.draw.circle(surface, (255, 255, 250), (lx + 10 + ti * 13, 452), 7)
        back_ear_w = 46 + int(flap * (16 if self._ear_age > 0 else 5))
        back_ear_rect = pygame.Rect(535 - back_ear_w // 2, 215, max(20, back_ear_w), 85)
        pygame.draw.ellipse(surface, body_dark, back_ear_rect)
        pygame.draw.circle(surface, body, (head_cx, head_cy), 58)
        pygame.draw.circle(surface, body_dark, (head_cx, head_cy), 58, 3)
        tusk_poly = [
            (head_cx + 34, head_cy + 26),
            (head_cx + 62, head_cy + 42),
            (head_cx + 58, head_cy + 48),
            (head_cx + 28, head_cy + 34),
        ]
        pygame.draw.polygon(surface, tusk_col, tusk_poly)
        eye_cx, eye_cy = head_cx + 22, head_cy - 12
        pygame.draw.ellipse(surface, dark_ink, (eye_cx - 7, eye_cy - 9, 14, 18))
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx + 2, eye_cy - 4), 3)

    def _is_recent(self, discovery_id: str) -> bool:
        return (
            (discovery_id == "water" and self._water_age > 0)
            or (discovery_id == "ears" and self._ear_age > 0)
            or (discovery_id == "social" and self._social_age > 0)
        )

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._is_recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_FELT_TAG,
            )

    @staticmethod
    def _draw_icon(surface: pygame.Surface, center: tuple[int, int], discovery_id: str) -> None:
        cx, cy = center
        cy += 4  # sit below the felt tag's pin
        grey = (143, 153, 160)
        if discovery_id == "trunk":
            pygame.draw.lines(surface, grey, False, ((cx - 17, cy - 20), (cx + 5, cy), (cx + 15, cy + 25)), 9)
        elif discovery_id == "water":
            for dx, dy in ((-16, 8), (-5, -8), (8, 5), (18, -12)):
                pygame.draw.circle(surface, (91, 176, 216), (cx + dx, cy + dy), 6)
        elif discovery_id == "ears":
            pygame.draw.ellipse(surface, grey, (cx - 28, cy - 20, 24, 42))
            pygame.draw.ellipse(surface, grey, (cx + 4, cy - 20, 24, 42))
        else:
            pygame.draw.circle(surface, grey, (cx - 13, cy), 13)
            pygame.draw.circle(surface, (170, 177, 181), (cx + 13, cy), 11)
            pygame.draw.line(surface, (75, 73, 68), (cx - 2, cy + 5), (cx + 3, cy + 5), 5)
