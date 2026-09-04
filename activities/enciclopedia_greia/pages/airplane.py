"""Airplane entry: child-friendly storybook airplane soaring in the clouds."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        draw_caption_ribbon,
        draw_machine_action_button,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        draw_caption_ribbon,
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
    AirplaneDiscovery("lift", "airplane.lift", "encyclopedia.machines.airplane.lift", (240, 185)),
    AirplaneDiscovery("myth", "airplane.myth", "encyclopedia.machines.airplane.myth", (765, 185)),
    AirplaneDiscovery("forces", "airplane.forces", "encyclopedia.machines.airplane.forces", (240, 420)),
    AirplaneDiscovery("thrust", "airplane.thrust", "encyclopedia.machines.airplane.thrust", (765, 420)),
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

        # Animation feature timers
        self._airflow_age = 0.0      # wings like birds / lift
        self._myth_age = 0.0         # high in clouds / rainbow trail
        self._forces_age = 0.0       # looking out window / tiny world
        self._thrust_age = 0.0       # spinning propeller / zoom
        self._loop_age = 0.0         # celebratory loop
        self._propeller_angle = 0.0

        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._plane_hit = pygame.Rect(380, 240, 260, 160)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.airplane.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("machines", disc.discovery_id, "name")
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._thrust_age = 6.0
        self._loop_age = 2.0
        self._activate(3)

    def update(self, dt: float) -> None:
        self._time += dt
        self._airflow_age = max(0.0, self._airflow_age - dt)
        self._myth_age = max(0.0, self._myth_age - dt)
        self._forces_age = max(0.0, self._forces_age - dt)
        self._thrust_age = max(0.0, self._thrust_age - dt)
        self._loop_age = max(0.0, self._loop_age - dt)

        # Propeller rotation speed
        spin_speed = 1800.0 if self._thrust_age > 0.0 else 600.0
        self._propeller_angle = (self._propeller_angle + dt * spin_speed) % 360.0

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
                if self._plane_hit.collidepoint(point):
                    self._trigger_main()
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
            self._airflow_age = 6.0
        elif item.discovery_id == "myth":
            self._myth_age = 6.0
        elif item.discovery_id == "forces":
            self._forces_age = 6.0
        else:
            self._thrust_age = 6.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        # 1. Cheerful Sunny Sky Background
        surface.fill((216, 238, 252))

        t = self._time

        # Warm Golden Sun in the upper left corner
        sun_x, sun_y = 135, 105
        # Soft glowing corona
        pygame.draw.circle(surface, (255, 245, 185), (sun_x, sun_y), 38)
        pygame.draw.circle(surface, (255, 218, 65), (sun_x, sun_y), 26)
        # Cute smiley face on sun
        pygame.draw.circle(surface, (180, 110, 20), (sun_x - 7, sun_y - 3), 2.5)
        pygame.draw.circle(surface, (180, 110, 20), (sun_x + 7, sun_y - 3), 2.5)
        pygame.draw.arc(surface, (180, 110, 20), (sun_x - 8, sun_y - 4, 16, 12), math.pi, math.tau, 2)

        # Drifting Fluffy Clouds
        for idx, (base_x, base_y, sz, speed) in enumerate([
            (80, 220, 60, 8.0),
            (420, 160, 75, 12.0),
            (780, 240, 68, 9.0),
            (260, 390, 55, 7.0),
            (680, 410, 70, 11.0),
        ]):
            cx = int((base_x + t * speed) % 1160) - 80
            self._draw_cloud(surface, cx, base_y, sz)

        # Title at the top
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("airplane.title"),
            center=(512, 68),
            size=36,
            color=(61, 44, 31),
            role=FontRole.DISPLAY,
        )

        # 2. Draw Airplane & Visual Features
        self._draw_airplane_scene(surface)

        # 3. Discovery Tokens
        self._draw_hotspots(surface)

        # 4. Navigation controls and action button
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="airplane", time=self._time, active=True
        )

        # 5. Caption Ribbon
        self._draw_caption(surface)

        # 6. Presenter Flash (happy)
        draw_presenter(
            surface,
            self.context.visuals,
            "flash",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(235, 139, 70),
        )

    def _draw_cloud(self, surface: pygame.Surface, cx: int, cy: int, size: int) -> None:
        s = pygame.Surface((size * 2, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 215), (size // 2, size // 2), size // 3)
        pygame.draw.circle(s, (255, 255, 255, 240), (size, size // 2 - 4), size // 2)
        pygame.draw.circle(s, (255, 255, 255, 215), (size + size // 2, size // 2), size // 3)
        surface.blit(s, (cx - size, cy - size // 2))

    def _draw_airplane_scene(self, surface: pygame.Surface) -> None:
        t = self._time

        # Gentle floating bob & tilt
        bob_y = math.sin(t * 2.5) * 7.0
        climb_angle = -0.12 if self._airflow_age > 0.0 else 0.0
        loop_offset_y = -math.sin(self._loop_age * math.pi) * 35.0 if self._loop_age > 0.0 else 0.0

        center_x = 512
        center_y = int(305 + bob_y + loop_offset_y)

        # Feature 2: High in the clouds (myth) -> Rainbow trail behind airplane tail
        if self._myth_age > 0.0:
            r_colors = [
                (245, 75, 75),   # Red
                (255, 158, 44),  # Orange
                (255, 228, 54),  # Yellow
                (92, 214, 110),  # Green
                (74, 178, 245),  # Cyan
                (175, 102, 238), # Violet
            ]
            trail_start_x = center_x + 95
            trail_start_y = center_y - 8
            for i, col in enumerate(r_colors):
                points = []
                for seg in range(12):
                    seg_x = trail_start_x + seg * 18
                    seg_y = trail_start_y + i * 4 + math.sin(t * 8.0 - seg * 0.4) * 8
                    points.append((seg_x, int(seg_y)))
                if len(points) >= 2:
                    pygame.draw.lines(surface, col, False, points, 4)

        # Feature 3: Looking out the window (forces) -> Miniature storybook landscape below
        if self._forces_age > 0.0:
            # Miniature rolling green land at bottom
            pygame.draw.ellipse(surface, (125, 188, 95), (320, 425, 384, 80))
            # Tiny red-roof cottages
            for hx, hy in ((430, 440), (510, 436), (580, 442)):
                pygame.draw.rect(surface, (255, 250, 240), (hx - 7, hy - 4, 14, 10))
                pygame.draw.polygon(surface, (220, 65, 55), [(hx - 9, hy - 4), (hx, hy - 12), (hx + 9, hy - 4)])
                pygame.draw.rect(surface, (255, 220, 60), (hx - 3, hy - 1, 6, 5))
            # Tiny cute trees
            for tx, ty in ((390, 444), (475, 438), (545, 438), (620, 444)):
                pygame.draw.circle(surface, (82, 155, 68), (tx, ty - 6), 6)
                pygame.draw.line(surface, (95, 65, 40), (tx, ty), (tx, ty + 4), 2)

        # Feature 1: Airflow over wings & upward Lift vector
        if self._airflow_age > 0.0:
            for offset in (-45, -20, 15, 40):
                stream_pts = []
                for seg in range(16):
                    sx = center_x - 170 + seg * 22
                    sy = center_y + offset + math.sin(t * 10.0 + seg * 0.5) * 5
                    stream_pts.append((sx, int(sy)))
                pygame.draw.lines(surface, (255, 255, 255), False, stream_pts, 3)
            # Upward Green Lift vector (PORTANZA)
            lift_pulse = int(math.sin(t * 12.0) * 4)
            pygame.draw.line(surface, (60, 205, 105), (center_x, center_y + 10), (center_x, center_y - 75 + lift_pulse), 4)
            pygame.draw.polygon(surface, (60, 205, 105), [(center_x - 7, center_y - 65 + lift_pulse), (center_x + 7, center_y - 65 + lift_pulse), (center_x, center_y - 82 + lift_pulse)])

        # THE CUTE STORYBOOK AIRPLANE
        self._draw_cute_airplane(surface, center_x, center_y, climb_angle)

        # Feature 4: Fast propeller (thrust) -> Forward yellow thrust vector & speed lines
        if self._thrust_age > 0.0:
            for sy in (center_y - 12, center_y, center_y + 12):
                streak_len = int(45 + math.sin(t * 25.0 + sy) * 15)
                streak_x = center_x - 130
                pygame.draw.line(surface, (255, 225, 80), (streak_x, sy), (streak_x - streak_len, sy), 3)
                pygame.draw.circle(surface, (255, 255, 255), (center_x + 105, sy + int(math.sin(t * 15.0) * 4)), 3)
            # Forward yellow thrust arrow (SPINTA)
            prop_x = center_x - 115
            t_pulse = int(math.sin(t * 14.0) * 4)
            pygame.draw.line(surface, (255, 195, 45), (prop_x, center_y), (prop_x - 55 + t_pulse, center_y), 4)
            pygame.draw.polygon(surface, (255, 195, 45), [(prop_x - 45 + t_pulse, center_y - 6), (prop_x - 45 + t_pulse, center_y + 6), (prop_x - 60 + t_pulse, center_y)])

        # Feature 3: Altitude & Clouds display (Cumuli vs Cirri)
        if self._forces_age > 0.0:
            # Altitude ladder on the left
            ladder_x = 120
            pygame.draw.line(surface, (120, 160, 190), (ladder_x, 220), (ladder_x, 440), 3)
            # High altitude marker: Cirri (8000m)
            pygame.draw.line(surface, (120, 160, 190), (ladder_x - 8, 230), (ladder_x + 8, 230), 2)
            for cx in range(ladder_x + 15, ladder_x + 85, 18):
                pygame.draw.line(surface, (255, 255, 255, 200), (cx, 226), (cx + 12, 232), 2)
            # Low altitude marker: Cumuli (2000m)
            pygame.draw.line(surface, (120, 160, 190), (ladder_x - 8, 410), (ladder_x + 8, 410), 2)
            pygame.draw.circle(surface, (255, 255, 255), (ladder_x + 35, 410), 12)
            pygame.draw.circle(surface, (255, 255, 255), (ladder_x + 50, 406), 16)
            pygame.draw.circle(surface, (255, 255, 255), (ladder_x + 65, 410), 11)

    def _draw_cute_airplane(self, surface: pygame.Surface, cx: int, cy: int, angle: float) -> None:
        t = self._time

        # Back Wing
        back_wing = [
            (cx - 20, cy - 18),
            (cx - 2, cy - 65),
            (cx + 28, cy - 60),
            (cx + 12, cy - 15),
        ]
        pygame.draw.polygon(surface, (32, 90, 155), back_wing)
        pygame.draw.polygon(surface, (22, 65, 115), back_wing, 2)
        # Red tip on back wing
        pygame.draw.polygon(surface, (220, 55, 45), [(cx - 2, cy - 65), (cx + 14, cy - 68), (cx + 28, cy - 60), (cx + 18, cy - 52)])

        # Tailfin with Rudder (Control surface)
        tail_poly = [
            (cx + 62, cy - 10),
            (cx + 96, cy - 58),
            (cx + 118, cy - 58),
            (cx + 102, cy - 6),
        ]
        pygame.draw.polygon(surface, (232, 68, 56), tail_poly)
        pygame.draw.polygon(surface, (168, 38, 28), tail_poly, 3)

        # Movable Rudder on the tail trailing edge
        rudder_deflection = int(math.sin(t * 8.0) * 4) if self._myth_age > 0.0 else 0
        rudder_poly = [
            (cx + 114, cy - 56),
            (cx + 124 + rudder_deflection, cy - 56),
            (cx + 108 + rudder_deflection, cy - 8),
            (cx + 100, cy - 8),
        ]
        pygame.draw.polygon(surface, (255, 205, 60) if self._myth_age > 0.0 else (205, 55, 45), rudder_poly)

        # Golden star on tailfin
        self._draw_star(surface, cx + 92, cy - 38, 6, (255, 225, 60))
        # Horizontal stabilizer with movable elevator
        pygame.draw.polygon(surface, (41, 108, 179), [(cx + 78, cy + 2), (cx + 114, cy - 8), (cx + 118, cy + 2), (cx + 84, cy + 7)])

        # Main Fuselage Body
        # Red lower fuselage
        fuse_rect = pygame.Rect(cx - 95, cy - 6, 195, 34)
        pygame.draw.ellipse(surface, (232, 68, 56), fuse_rect)
        # Cream upper cabin
        cabin_rect = pygame.Rect(cx - 85, cy - 26, 175, 34)
        pygame.draw.ellipse(surface, (255, 250, 238), cabin_rect)
        # Outer outlines
        pygame.draw.ellipse(surface, (168, 38, 28), fuse_rect, 3)
        pygame.draw.ellipse(surface, (168, 38, 28), cabin_rect, 3)
        # Golden dividing belt
        pygame.draw.line(surface, (255, 215, 60), (cx - 85, cy + 4), (cx + 85, cy + 4), 3)

        # Cockpit Panoramic Windshield
        cockpit_rect = pygame.Rect(cx - 82, cy - 22, 38, 22)
        pygame.draw.ellipse(surface, (95, 205, 250), cockpit_rect)
        pygame.draw.ellipse(surface, (35, 120, 175), cockpit_rect, 2)
        # Cartoon shine on windshield
        pygame.draw.arc(surface, (255, 255, 255), (cx - 78, cy - 20, 28, 14), 0.5, 2.5, 3)
        # Cute friendly pilot silhouette inside
        pygame.draw.circle(surface, (45, 65, 80), (cx - 62, cy - 11), 5)
        pygame.draw.ellipse(surface, (45, 65, 80), (cx - 66, cy - 4, 10, 6))

        # 3 Round Passenger Windows
        for i, wx in enumerate((cx - 24, cx + 8, cx + 40)):
            pygame.draw.circle(surface, (255, 238, 120), (wx, cy - 8), 8)
            pygame.draw.circle(surface, (168, 38, 28), (wx, cy - 8), 8, 2)
            pygame.draw.circle(surface, (255, 255, 255), (wx - 2, cy - 10), 2.5)

            # In window 2, smiling passenger waving if "forces" (window) is active!
            if i == 1 and self._forces_age > 0.0:
                pygame.draw.circle(surface, (180, 110, 60), (wx, cy - 8), 4)
                pygame.draw.circle(surface, (40, 30, 20), (wx - 1, cy - 9), 1)
                pygame.draw.circle(surface, (40, 30, 20), (wx + 1, cy - 9), 1)
                pygame.draw.circle(surface, (255, 255, 255), (wx + 4, cy - 10), 2)

        # Front Main Wing with Flap/Aileron
        front_wing = [
            (cx - 32, cy + 4),
            (cx - 10, cy + 62),
            (cx + 36, cy + 54),
            (cx + 18, cy + 4),
        ]
        pygame.draw.polygon(surface, (41, 108, 179), front_wing)
        pygame.draw.polygon(surface, (22, 65, 115), front_wing, 3)

        # Movable Flap/Aileron on the wing trailing edge
        flap_deflection = int(math.sin(t * 8.0) * 5) if self._myth_age > 0.0 else 0
        flap_poly = [
            (cx + 6, cy + 30),
            (cx + 20, cy + 56),
            (cx + 34 + flap_deflection, cy + 52 + flap_deflection),
            (cx + 18 + flap_deflection, cy + 28),
        ]
        pygame.draw.polygon(surface, (255, 205, 60) if self._myth_age > 0.0 else (32, 90, 155), flap_poly)
        pygame.draw.polygon(surface, (22, 65, 115), flap_poly, 2)

        # Red tip on front wing
        pygame.draw.polygon(surface, (232, 68, 56), [(cx - 10, cy + 62), (cx + 8, cy + 65), (cx + 20, cy + 56), (cx + 6, cy + 52)])
        # Green navigation light on wingtip
        pygame.draw.circle(surface, (80, 225, 120), (cx - 6, cy + 62), 3)

        # Nose Spinner & Propeller
        nose_rect = pygame.Rect(cx - 110, cy - 12, 24, 24)
        pygame.draw.ellipse(surface, (255, 199, 59), nose_rect)
        pygame.draw.ellipse(surface, (175, 115, 15), nose_rect, 2)

        # Spinning Propeller
        rad = math.radians(self._propeller_angle)
        prop_cx, prop_cy = cx - 106, cy
        # Propeller blades
        p_dx = math.cos(rad) * 28.0
        p_dy = math.sin(rad) * 28.0
        pygame.draw.line(surface, (255, 245, 205), (prop_cx - p_dx, prop_cy - p_dy), (prop_cx + p_dx, prop_cy + p_dy), 6)
        pygame.draw.line(surface, (255, 199, 59), (prop_cx - p_dx, prop_cy - p_dy), (prop_cx + p_dx, prop_cy + p_dy), 2)
        # Center hub cap
        pygame.draw.circle(surface, (232, 68, 56), (prop_cx, prop_cy), 5)
        pygame.draw.circle(surface, (168, 38, 28), (prop_cx, prop_cy), 5, 1)

    def _draw_star(self, surface: pygame.Surface, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
        points = []
        for i in range(10):
            r = radius if i % 2 == 0 else radius * 0.45
            ang = i * math.pi / 5.0 - math.pi / 2.0
            points.append((cx + int(math.cos(ang) * r), cy + int(math.sin(ang) * r)))
        pygame.draw.polygon(surface, color, points)

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: AirplaneDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "lift":
            # Wing with upward Lift arrow
            wing = [(cx - 18, cy + 10), (cx - 6, cy - 8), (cx + 18, cy - 6), (cx + 4, cy + 8)]
            pygame.draw.polygon(surface, (41, 108, 179), wing)
            pygame.draw.line(surface, (60, 205, 105), (cx, cy + 14), (cx, cy - 18), 3)
            pygame.draw.polygon(surface, (60, 205, 105), [(cx - 4, cy - 14), (cx + 4, cy - 14), (cx, cy - 20)])
        elif item.discovery_id == "myth":
            # Control surfaces: wing/tail flap with steering angle
            pygame.draw.polygon(surface, (232, 68, 56), [(cx - 10, cy + 10), (cx + 2, cy - 14), (cx + 16, cy - 14), (cx + 8, cy + 10)])
            # Flap tilting
            pygame.draw.polygon(surface, (255, 195, 45), [(cx + 2, cy - 14), (cx + 16, cy - 14), (cx + 18, cy - 2), (cx + 4, cy - 2)])
            pygame.draw.arc(surface, (255, 255, 255), (cx - 8, cy - 18, 24, 24), 0.2, 1.4, 2)
        elif item.discovery_id == "forces":
            # Cloud types: Cumulus down low, Cirrus up high
            # Lower cumulus
            pygame.draw.circle(surface, (255, 255, 255), (cx - 8, cy + 6), 8)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 4, cy + 4), 10)
            # Upper cirrus wisps
            pygame.draw.line(surface, (210, 235, 255), (cx - 12, cy - 12), (cx + 14, cy - 8), 2)
            pygame.draw.line(surface, (210, 235, 255), (cx - 6, cy - 6), (cx + 16, cy - 2), 2)
            # Altitude arrow
            pygame.draw.line(surface, (255, 195, 45), (cx - 14, cy + 12), (cx - 14, cy - 14), 2)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 17, cy - 11), (cx - 11, cy - 11), (cx - 14, cy - 16)])
        else:
            # Engine & propeller thrust forward
            pygame.draw.circle(surface, (255, 199, 59), (cx + 8, cy), 8)
            pygame.draw.line(surface, (255, 245, 205), (cx + 8, cy - 14), (cx + 8, cy + 14), 4)
            # Forward thrust arrow
            pygame.draw.line(surface, (255, 195, 45), (cx + 6, cy), (cx - 14, cy), 3)
            pygame.draw.polygon(surface, (255, 195, 45), [(cx - 10, cy - 4), (cx - 10, cy + 4), (cx - 16, cy)])

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 250, 238), item.center, 38)
            pygame.draw.circle(surface, (88, 68, 52), item.center, 38, 3)
            self._draw_hotspot_icon(surface, item)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
