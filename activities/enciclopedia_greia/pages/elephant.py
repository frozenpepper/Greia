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
            center=(512, 50),
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
        body = (148, 164, 178)
        body_dark = (116, 130, 142)
        body_light = (176, 192, 204)
        pink = (255, 185, 198)
        tusk_col = (255, 252, 240)
        dark_ink = (40, 34, 30)

        # Ground soft shadow
        shadow_surf = pygame.Surface((280, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (30, 24, 18, 45), (0, 0, 280, 36))
        surface.blit(shadow_surf, (370, 442))

        # 1. Back Legs (darker shade for depth)
        for lx in (430, 520):
            leg_rect = pygame.Rect(lx, 340, 42, 115)
            pygame.draw.rect(surface, body_dark, leg_rect, border_radius=14)
            # 3 cute white toenails
            for ti in range(3):
                pygame.draw.circle(surface, (240, 240, 235), (lx + 9 + ti * 12, 452), 6)

        # 2. Cute wagging tail with tuft
        tail_wag = math.sin(self._time * 2.5) * 6
        tail_start = (395, 315)
        tail_mid = (372, 345 + tail_wag * 0.5)
        tail_end = (368 + tail_wag, 375)
        pygame.draw.lines(surface, body_dark, False, [tail_start, tail_mid, tail_end], 6)
        pygame.draw.circle(surface, (85, 75, 70), (int(tail_end[0]), int(tail_end[1])), 8)

        # 3. Big cuddly round body
        body_rect = pygame.Rect(388, 255, 195, 150)
        pygame.draw.ellipse(surface, body, body_rect)
        pygame.draw.ellipse(surface, body_dark, body_rect, 3)
        # Soft top highlight on back
        pygame.draw.arc(surface, body_light, pygame.Rect(398, 260, 160, 90), 0.5, 2.7, 6)

        # 4. Front Legs (brighter, rounded sturdy pillars)
        for lx in (465, 555):
            leg_rect = pygame.Rect(lx, 335, 46, 120)
            pygame.draw.rect(surface, body, leg_rect, border_radius=16)
            pygame.draw.rect(surface, body_dark, leg_rect, width=3, border_radius=16)
            # Top knee shadow
            pygame.draw.arc(surface, body_dark, pygame.Rect(lx + 8, 385, 30, 20), 0.2, 2.9, 2)
            # 3 cute rounded toenails
            for ti in range(3):
                pygame.draw.circle(surface, (255, 255, 250), (lx + 10 + ti * 13, 452), 7)
                pygame.draw.circle(surface, (180, 175, 165), (lx + 10 + ti * 13, 452), 7, 1)

        # 5. Back ear (behind head, flapping)
        flap = math.sin(self._time * (6.5 if self._ear_age > 0 else 1.6))
        back_ear_w = 46 + int(flap * (16 if self._ear_age > 0 else 5))
        back_ear_rect = pygame.Rect(535 - back_ear_w // 2, 215, max(20, back_ear_w), 85)
        pygame.draw.ellipse(surface, body_dark, back_ear_rect)
        pygame.draw.ellipse(surface, (140, 110, 120), back_ear_rect.inflate(-8, -14))

        # 6. Big friendly round head
        head_cx, head_cy = 575, 275
        head_r = 58
        pygame.draw.circle(surface, body, (head_cx, head_cy), head_r)
        pygame.draw.circle(surface, body_dark, (head_cx, head_cy), head_r, 3)
        # Soft cheek blush
        blush_surf = pygame.Surface((36, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(blush_surf, (255, 150, 170, 75), (0, 0, 36, 24))
        surface.blit(blush_surf, (head_cx + 12, head_cy + 12))

        # 7. Front Floppy Ear (expressive, with animated flapping and cute pink interior)
        ear_w = 68 + int(abs(flap) * (20 if self._ear_age > 0 else 6))
        ear_rect = pygame.Rect(520 - ear_w // 2, 222, ear_w, 98)
        pygame.draw.ellipse(surface, body, ear_rect)
        pygame.draw.ellipse(surface, body_dark, ear_rect, 3)
        inner_ear_rect = ear_rect.inflate(-18, -26)
        if inner_ear_rect.width > 6 and inner_ear_rect.height > 6:
            pygame.draw.ellipse(surface, pink, inner_ear_rect)
            # Soft ear highlight
            pygame.draw.arc(surface, (255, 255, 255, 180), inner_ear_rect, 0.6, 2.5, 3)

        # 8. Charming curved creamy tusk
        tusk_poly = [
            (head_cx + 34, head_cy + 26),
            (head_cx + 62, head_cy + 42),
            (head_cx + 58, head_cy + 48),
            (head_cx + 28, head_cy + 34),
        ]
        pygame.draw.polygon(surface, tusk_col, tusk_poly)
        pygame.draw.polygon(surface, (180, 160, 130), tusk_poly, 2)
        pygame.draw.circle(surface, tusk_col, (head_cx + 60, head_cy + 45), 3)

        # 9. Big, lovable, expressive cartoon eye
        eye_cx, eye_cy = head_cx + 22, head_cy - 12
        # White sclera
        pygame.draw.ellipse(surface, (255, 255, 255), (eye_cx - 10, eye_cy - 12, 20, 24))
        pygame.draw.ellipse(surface, dark_ink, (eye_cx - 10, eye_cy - 12, 20, 24), 2)
        # Deep dark warm iris
        pygame.draw.circle(surface, (32, 42, 54), (eye_cx + 2, eye_cy), 7)
        # Bright sparkly white catchlights
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx + 4, eye_cy - 3), 3)
        pygame.draw.circle(surface, (255, 255, 255), (eye_cx, eye_cy + 3), 1)
        # Cute curved eyebrow
        pygame.draw.arc(surface, dark_ink, pygame.Rect(eye_cx - 8, eye_cy - 22, 18, 12), 0.4, 2.8, 3)
        # Sweet smile near base of trunk
        pygame.draw.arc(surface, (140, 45, 60), pygame.Rect(head_cx + 26, head_cy + 18, 16, 12), math.pi * 0.9, 0, 3)

        # 10. Expressive, smooth, segmented trunk
        trunk_base = (head_cx + 42, head_cy + 16)
        if self._trunk_state == 0:
            # Friendly resting curl up
            p1 = trunk_base
            p2 = (head_cx + 64, head_cy + 38)
            p3 = (head_cx + 74, head_cy + 74)
            p4 = (head_cx + 60, head_cy + 102)
            p5 = (head_cx + 72, head_cy + 108)  # tip curled up
            trunk_pts = [p1, p2, p3, p4, p5]
            trunk_widths = [24, 21, 18, 15, 13]
        elif self._trunk_state == 1:
            # Joyous high trumpet salute!
            p1 = trunk_base
            p2 = (head_cx + 68, head_cy + 18)
            p3 = (head_cx + 94, head_cy - 10)
            p4 = (head_cx + 108, head_cy - 45)
            p5 = (head_cx + 98, head_cy - 65)  # tip curling back
            trunk_pts = [p1, p2, p3, p4, p5]
            trunk_widths = [24, 22, 18, 15, 12]
        else:
            # Water spraying pose: trunk curled forward toward pond
            p1 = trunk_base
            p2 = (head_cx + 68, head_cy + 35)
            p3 = (head_cx + 86, head_cy + 65)
            p4 = (head_cx + 108, head_cy + 82)
            p5 = (head_cx + 124, head_cy + 76)
            trunk_pts = [p1, p2, p3, p4, p5]
            trunk_widths = [24, 21, 18, 15, 13]

        for i in range(len(trunk_pts) - 1):
            pt_a = trunk_pts[i]
            pt_b = trunk_pts[i + 1]
            w = trunk_widths[i]
            pygame.draw.line(surface, body, pt_a, pt_b, w)
            pygame.draw.circle(surface, body, pt_a, w // 2)
            pygame.draw.circle(surface, body, pt_b, w // 2)
            # Subtle trunk wrinkles
            pygame.draw.circle(surface, body_dark, pt_a, w // 2, 1)

        # 11. Water spray effects when trunk is active or water toy triggered
        if self._water_age > 0:
            tip = trunk_pts[-1]
            progress = 1.0 - self._water_age / 3.0
            for index in range(20):
                t = index / 19.0
                drop_x = tip[0] + int(140 * t) + int(math.sin(self._time * 10 + index) * 8)
                drop_y = tip[1] - int(75 * math.sin(t * math.pi)) + int(t * 110) + int(progress * 10)
                drop_r = 3 + (index % 4)
                pygame.draw.circle(surface, (95, 195, 245), (drop_x, drop_y), drop_r)
                pygame.draw.circle(surface, (220, 245, 255), (drop_x - 1, drop_y - 1), max(1, drop_r - 2))

        # 12. Cooling ear wind ripples when ears flapping
        if self._ear_age > 0:
            for index in range(5):
                y = 230 + index * 16
                wave_x = int(math.sin(self._time * 8 + index) * 6)
                pygame.draw.arc(surface, (120, 205, 235), pygame.Rect(440 + wave_x, y, 40, 20), 0.5, 2.5, 3)
                pygame.draw.arc(surface, (120, 205, 235), pygame.Rect(630 + wave_x, y, 40, 20), 0.5, 2.5, 3)

        # 13. Social touch: cute little baby elephant greeting
        if self._social_age > 0:
            second_x = 340
            pygame.draw.ellipse(surface, (168, 180, 190), (second_x - 45, 360, 85, 60))
            pygame.draw.circle(surface, (168, 180, 190), (second_x + 35, 360), 28)
            pygame.draw.circle(surface, dark_ink, (second_x + 42, 354), 3)
            # Intertwining baby trunk
            pygame.draw.lines(
                surface,
                (168, 180, 190),
                False,
                [(second_x + 50, 368), (second_x + 72, 362), (390, 345), (420, 340)],
                10,
            )
            # Floating friendly hearts
            heart_y = int(320 - (4.0 - self._social_age) * 15)
            pygame.draw.circle(surface, (255, 110, 135), (380, heart_y), 6)
            pygame.draw.circle(surface, (255, 110, 135), (388, heart_y), 6)
            pygame.draw.polygon(surface, (255, 110, 135), [(374, heart_y + 2), (394, heart_y + 2), (384, heart_y + 12)])


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
