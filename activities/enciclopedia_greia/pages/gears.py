"""Gears golden master: authored workshop board with semantic mechanism overlays."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_direction_toggle,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        draw_title,
        draw_turn_button,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_direction_toggle,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_pause_button,
        draw_speed_slider,
        draw_title,
        draw_turn_button,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class GearDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    GearDiscovery("teeth", "gears.teeth", "encyclopedia.machines.gears.teeth", (235, 195)),
    GearDiscovery(
        "direction",
        "gears.direction",
        "encyclopedia.machines.gears.direction",
        (775, 195),
    ),
    GearDiscovery("ratio", "gears.ratio", "encyclopedia.machines.gears.ratio", (235, 405)),
    GearDiscovery("rack", "gears.rack", "encyclopedia.machines.gears.rack", (775, 405)),
)


class GearTrainModel:
    """Own the finite interaction state shown over the authored mechanism board."""

    # Reusable toy: speed is child-controlled via slider, not hard-coded
    SPEED_LEVELS = (0.45, 0.85, 1.45)

    def __init__(self) -> None:
        self.driver_angle = 0.0
        self.direction = 1.0
        self.speed_level = 1
        self.speed = self.SPEED_LEVELS[self.speed_level]
        self.paused = False
        self.teeth_age = 0.0
        self.direction_age = 0.0
        self.ratio_age = 0.0
        self.rack_age = 0.0
        # Ambient idle wobble when paused — keeps page alive without obscuring
        self._idle_phase = 0.0

    def update(self, dt: float) -> None:
        if not self.paused:
            self.driver_angle += dt * self.speed * self.direction
        else:
            self._idle_phase += dt
        self.teeth_age = max(0.0, self.teeth_age - dt)
        self.direction_age = max(0.0, self.direction_age - dt)
        self.ratio_age = max(0.0, self.ratio_age - dt)
        self.rack_age = max(0.0, self.rack_age - dt)

    def set_speed_level(self, level: int) -> None:
        level = max(0, min(2, int(level)))
        self.speed_level = level
        self.speed = self.SPEED_LEVELS[level]
        self.paused = False

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def show_teeth(self) -> None:
        self.teeth_age = 3.2

    def reverse(self) -> None:
        self.direction *= -1.0
        self.direction_age = 3.2

    def show_ratio(self) -> None:
        self.ratio_age = 4.0

    def show_rack(self) -> None:
        self.rack_age = 4.0

    def nudge(self, delta_angle: float) -> None:
        """Direct drag — large hit, no pixel precision required."""
        self.driver_angle += delta_angle
        self.paused = False


class GearsPage(EncyclopediaPage):
    page_id = "machines.gears"

    # Live gear geometry — must match authored workbench positions used in reveals
    GEAR_SPECS = (
        ((385, 318), 64, 16),
        ((500, 318), 51, 13),
        ((592, 318), 41, 10),
    )

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = GearTrainModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "gears.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._turn_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._speed_hits: tuple[pygame.Rect, pygame.Rect, pygame.Rect] = (
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
        )
        self._pause_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._direction_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._dragging = False
        self._drag_center: tuple[int, int] | None = None
        self._drag_gear_idx: int = 0
        self._last_drag_angle: float | None = None

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.gears.intro")
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
            # Toy controls first — large hit areas, reliable
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._turn_hit.collidepoint(point):
                    self._model.toggle_pause()
                    if not self._model.paused:
                        self._model.driver_angle += 0.8 * self._model.direction
                    return
                if self._direction_hit.collidepoint(point):
                    self._model.reverse()
                    return
                # Direct gear touch/drag — check if press is on any gear
                for idx, (center, radius, _teeth) in enumerate(self.GEAR_SPECS):
                    dx = point[0] - center[0]
                    dy = point[1] - center[1]
                    if dx * dx + dy * dy <= (radius + 15) * (radius + 15):
                        self._dragging = True
                        self._drag_center = center
                        self._drag_gear_idx = idx
                        self._last_drag_angle = math.atan2(dy, dx)
                        self._model.paused = False
                        # Direct tap gives an impulse
                        self._model.nudge(0.3 * self._model.direction)
                        return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            if event.kind is PageInputKind.POINTER_MOVE:
                if self._dragging and self._drag_center is not None and self._last_drag_angle is not None:
                    cx, cy = self._drag_center
                    cur_angle = math.atan2(point[1] - cy, point[0] - cx)
                    delta = (cur_angle - self._last_drag_angle)
                    # Normalize to [-pi, pi]
                    delta = (delta + math.pi) % math.tau - math.pi
                    if self._drag_gear_idx == 1:
                        delta = -delta * (13 / 16)
                    elif self._drag_gear_idx == 2:
                        delta = delta * (10 / 16)
                    self._model.nudge(delta)
                    self._last_drag_angle = cur_angle
                    return
                hit = next(
                    (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                    None,
                )
                if hit is not None and hit != self._selected:
                    disc = DISCOVERIES[hit]
                    cue = encyclopedia_focus_cue("machines", "gears", disc.discovery_id, "name")
                    announce_focus_name(self.context.audio, cue)
                self._hovered = hit
                if hit is not None:
                    return
                self._dragging = False
                self._drag_center = None
                self._last_drag_angle = None
                return
            # POINTER_PRESS already handled toy hits above; now check discovery tokens
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
        else:
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
        if item.discovery_id == "teeth":
            self._model.show_teeth()
        elif item.discovery_id == "direction":
            self._model.reverse()
        elif item.discovery_id == "ratio":
            self._model.show_ratio()
        else:
            self._model.show_rack()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.machines.gears.workbench",
        ):
            surface.fill((239, 231, 205))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("gears.title"),
            self.context.palette.ink,
        )
        self._draw_live_gears(surface)
        self._draw_reveals(surface)
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_WORKSHOP_TAG,
            )
        # Standard navigation for discovery tokens
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        # Intuitive tactile mechanism controls
        self._draw_controls(surface)
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(880, 575),
            height=190,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_controls(self, surface: pygame.Surface) -> None:
        """Draw intuitive, child-friendly tactile workbench controls."""
        edge_dark = (61, 44, 31)

        # Dock background strip on workbench
        dock_rect = pygame.Rect(340, 442, 344, 48)
        pygame.draw.rect(surface, (0, 0, 0, 30), dock_rect.move(0, 3), border_radius=24)
        pygame.draw.rect(surface, (246, 238, 218), dock_rect, border_radius=24)
        pygame.draw.rect(surface, (140, 115, 85), dock_rect, width=2, border_radius=24)

        # Button 1: GIRA / PAUSA (Toggle play/pause)
        btn_play_rect = pygame.Rect(346, 446, 160, 40)
        self._turn_hit = btn_play_rect
        is_paused = self._model.paused
        play_fill = (225, 248, 225) if is_paused else (255, 242, 220)
        play_edge = (60, 150, 75) if is_paused else (190, 120, 45)
        pygame.draw.rect(surface, play_fill, btn_play_rect, border_radius=20)
        pygame.draw.rect(surface, play_edge, btn_play_rect, width=2, border_radius=20)

        # Play/Pause icon + label
        if is_paused:
            tri_pts = [
                (btn_play_rect.x + 22, btn_play_rect.centery - 10),
                (btn_play_rect.x + 36, btn_play_rect.centery),
                (btn_play_rect.x + 22, btn_play_rect.centery + 10),
            ]
            pygame.draw.polygon(surface, (50, 150, 65), tri_pts)
            label = self.context.typography.font(FontRole.CONTROL, 18).render(
                "GIRA", True, edge_dark
            )
        else:
            bx = btn_play_rect.x + 22
            by = btn_play_rect.centery - 9
            pygame.draw.rect(surface, (190, 110, 35), (bx, by, 5, 18), border_radius=2)
            pygame.draw.rect(surface, (190, 110, 35), (bx + 8, by, 5, 18), border_radius=2)
            label = self.context.typography.font(FontRole.CONTROL, 18).render(
                "PAUSA", True, edge_dark
            )
        surface.blit(label, (btn_play_rect.x + 50, btn_play_rect.centery - label.get_height() // 2))

        # Button 2: INVERTI (Reverse direction)
        btn_rev_rect = pygame.Rect(518, 446, 160, 40)
        self._direction_hit = btn_rev_rect
        pygame.draw.rect(surface, (255, 252, 245), btn_rev_rect, border_radius=20)
        pygame.draw.rect(surface, (120, 95, 70), btn_rev_rect, width=2, border_radius=20)

        # Circular curved arrow icon
        rev_cx = btn_rev_rect.x + 28
        rev_cy = btn_rev_rect.centery
        arc_rect = pygame.Rect(rev_cx - 11, rev_cy - 11, 22, 22)
        if self._model.direction > 0:
            pygame.draw.arc(surface, (180, 100, 35), arc_rect, 0.4, 5.4, 3)
            pygame.draw.polygon(
                surface,
                (180, 100, 35),
                [
                    (rev_cx + 10, rev_cy - 2),
                    (rev_cx + 16, rev_cy + 5),
                    (rev_cx + 6, rev_cy + 5),
                ],
            )
        else:
            pygame.draw.arc(surface, (180, 100, 35), arc_rect, 1.0, 6.0, 3)
            pygame.draw.polygon(
                surface,
                (180, 100, 35),
                [
                    (rev_cx - 10, rev_cy - 2),
                    (rev_cx - 16, rev_cy + 5),
                    (rev_cx - 6, rev_cy + 5),
                ],
            )

        rev_label = self.context.typography.font(FontRole.CONTROL, 18).render(
            "INVERTI", True, edge_dark
        )
        surface.blit(rev_label, (btn_rev_rect.x + 50, btn_rev_rect.centery - rev_label.get_height() // 2))

    def _draw_live_gears(self, surface: pygame.Surface) -> None:
        # Three meshed gears with mathematical mesh alignment
        base_angle = self._model.driver_angle
        n1, n2, n3 = 16, 13, 10
        angle1 = base_angle
        angle2 = -base_angle * (n1 / n2) + (math.pi / n2)
        angle3 = -angle2 * (n2 / n3) + (math.pi / n3)
        specs = [
            ((385, 318), 64, n1, angle1, (83, 145, 181), True),
            ((500, 318), 51, n2, angle2, (210, 175, 80), False),
            ((592, 318), 41, n3, angle3, (180, 130, 95), False),
        ]
        for center, radius, teeth, angle, color, has_crank in specs:
            self._draw_gear(surface, center, radius, teeth, angle, color, has_crank=has_crank)

    @classmethod
    def _draw_gear(
        cls,
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        teeth: int,
        angle: float,
        color: tuple[int, int, int],
        has_crank: bool = False,
    ) -> None:
        cx, cy = center
        d_th = math.tau / teeth
        ha = max(4.0, radius * 0.11)
        hf = max(5.0, radius * 0.12)
        r_tip = radius + ha
        r_root = radius - hf
        w_root = d_th * 0.28
        w_tip = d_th * 0.14
        edge_dark = (48, 42, 38)

        poly_points: list[tuple[int, int]] = []
        shadow_points: list[tuple[int, int]] = []
        shadow_ox, shadow_oy = 3, 5

        for i in range(teeth):
            th = angle + i * d_th
            # Valley bottom before tooth
            th_v1 = th - d_th * 0.5
            th_v2 = th - w_root
            x_v1 = cx + math.cos(th_v1) * r_root
            y_v1 = cy + math.sin(th_v1) * r_root
            poly_points.append((int(round(x_v1)), int(round(y_v1))))
            shadow_points.append((int(round(x_v1 + shadow_ox)), int(round(y_v1 + shadow_oy))))

            x_v2 = cx + math.cos(th_v2) * r_root
            y_v2 = cy + math.sin(th_v2) * r_root
            poly_points.append((int(round(x_v2)), int(round(y_v2))))
            shadow_points.append((int(round(x_v2 + shadow_ox)), int(round(y_v2 + shadow_oy))))

            # Rising flank to crest
            th_t1 = th - w_tip
            x_t1 = cx + math.cos(th_t1) * r_tip
            y_t1 = cy + math.sin(th_t1) * r_tip
            poly_points.append((int(round(x_t1)), int(round(y_t1))))
            shadow_points.append((int(round(x_t1 + shadow_ox)), int(round(y_t1 + shadow_oy))))

            # Crest right corner
            th_t2 = th + w_tip
            x_t2 = cx + math.cos(th_t2) * r_tip
            y_t2 = cy + math.sin(th_t2) * r_tip
            poly_points.append((int(round(x_t2)), int(round(y_t2))))
            shadow_points.append((int(round(x_t2 + shadow_ox)), int(round(y_t2 + shadow_oy))))

            # Falling flank back to root
            th_v3 = th + w_root
            x_v3 = cx + math.cos(th_v3) * r_root
            y_v3 = cy + math.sin(th_v3) * r_root
            poly_points.append((int(round(x_v3)), int(round(y_v3))))
            shadow_points.append((int(round(x_v3 + shadow_ox)), int(round(y_v3 + shadow_oy))))

        # 1. Soft Drop Shadow
        if len(shadow_points) >= 3:
            shadow_surf = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
            pygame.draw.polygon(shadow_surf, (0, 0, 0, 35), shadow_points)
            surface.blit(shadow_surf, (0, 0))

        # 2. Solid Cogwheel Body
        pygame.draw.polygon(surface, color, poly_points)
        pygame.draw.polygon(surface, edge_dark, poly_points, 2)

        # 3. Tooth bevel / highlights
        highlight_color = (255, 255, 255, 60)
        for i in range(teeth):
            th = angle + i * d_th
            th_t1 = th - w_tip
            th_t2 = th + w_tip
            x_t1 = int(round(cx + math.cos(th_t1) * r_tip))
            y_t1 = int(round(cy + math.sin(th_t1) * r_tip))
            x_t2 = int(round(cx + math.cos(th_t2) * r_tip))
            y_t2 = int(round(cy + math.sin(th_t2) * r_tip))
            pygame.draw.line(surface, highlight_color, (x_t1, y_t1), (x_t2, y_t2), 2)

        # 4. Outer Rim Bevel
        r_rim = int(r_root * 0.94)
        pygame.draw.circle(surface, _shade(color, 1.15), center, r_rim, 2)
        pygame.draw.circle(surface, edge_dark, center, r_rim - 2, 2)

        # 5. Recessed Web Face
        r_web = r_rim - 4
        web_color = _shade(color, 0.88)
        pygame.draw.circle(surface, web_color, center, r_web)

        # 6. Spoke Cutout Holes
        spoke_count = 5 if radius >= 60 else (4 if radius >= 50 else 3)
        hole_r = max(5, int(radius * 0.16))
        hole_dist = int(radius * 0.52)
        board_color = (239, 231, 205)
        for j in range(spoke_count):
            h_th = angle + j * (math.tau / spoke_count)
            hx = cx + int(math.cos(h_th) * hole_dist)
            hy = cy + int(math.sin(h_th) * hole_dist)
            pygame.draw.circle(surface, board_color, (hx, hy), hole_r)
            pygame.draw.circle(surface, edge_dark, (hx, hy), hole_r, 2)
            pygame.draw.circle(surface, (255, 255, 255, 50), (hx, hy + 1), hole_r - 1, 1)

        # 7. Center Axle Hub & Brass Ring
        hub_r = max(11, int(radius * 0.28))
        pygame.draw.circle(surface, (205, 170, 95), center, hub_r + 2)
        pygame.draw.circle(surface, edge_dark, center, hub_r + 2, 2)
        pygame.draw.circle(surface, (245, 220, 140), center, hub_r - 2)
        pin_r = max(4, hub_r // 2)
        pygame.draw.circle(surface, (50, 45, 40), center, pin_r)
        pygame.draw.circle(surface, (80, 75, 70), center, max(2, pin_r - 2))
        pygame.draw.circle(surface, (255, 255, 255), (center[0] - 2, center[1] - 2), 2)

        # 8. Tactile Hand-Crank Knob on Driver Gear
        if has_crank:
            crank_dist = int(radius * 0.65)
            kx = cx + int(math.cos(angle + 0.35) * crank_dist)
            ky = cy + int(math.sin(angle + 0.35) * crank_dist)
            # Arm
            pygame.draw.line(surface, edge_dark, center, (kx, ky), 10)
            pygame.draw.line(surface, (190, 155, 80), center, (kx, ky), 6)
            pygame.draw.line(surface, (235, 210, 130), center, (kx, ky), 2)
            # Knob
            pygame.draw.circle(surface, (0, 0, 0, 45), (kx + 2, ky + 3), 14)
            pygame.draw.circle(surface, (180, 140, 70), (kx, ky), 14)
            pygame.draw.circle(surface, edge_dark, (kx, ky), 14, 2)
            pygame.draw.circle(surface, (220, 125, 55), (kx, ky), 11)
            pygame.draw.circle(surface, (255, 185, 110), (kx - 3, ky - 3), 5)
            pygame.draw.circle(surface, (255, 255, 255), (kx - 4, ky - 4), 2)


    def _recent(self, discovery_id: str) -> bool:
        ages = {
            "teeth": self._model.teeth_age,
            "direction": self._model.direction_age,
            "ratio": self._model.ratio_age,
            "rack": self._model.rack_age,
        }
        return ages[discovery_id] > 0

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._model.teeth_age > 0:
            # The authored train has exactly two mesh boundaries. Keep the
            # teaching highlight tied to those real tooth-contact points.
            contact_points = ((450, 318), (550, 318))
            for point in contact_points:
                pygame.draw.circle(surface, (255, 228, 91), point, 20, 6)
                pygame.draw.circle(surface, (255, 170, 60), point, 8, 3)
            for index, point in enumerate(contact_points):
                ax, ay = point
                ax -= 6
                ay -= 28
                if index % 2 == 0:
                    ax2, ay2 = ax + 12, ay
                else:
                    ax2, ay2 = ax - 12, ay
                pygame.draw.line(surface, (255, 170, 60), (ax, ay), (ax2, ay2), 4)
                if index % 2 == 0:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 - 7, ay2 - 5), (ax2 - 7, ay2 + 5)],
                    )
                else:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 + 7, ay2 - 5), (ax2 + 7, ay2 + 5)],
                    )

        if self._model.direction_age > 0:
            specs = (
                ((385, 318), 72, self._model.direction),
                ((500, 318), 58, -self._model.direction),
                ((592, 318), 47, self._model.direction),
            )
            for center, radius, _direction in specs:
                rect = pygame.Rect(
                    center[0] - radius,
                    center[1] - radius,
                    radius * 2,
                    radius * 2,
                )
                pygame.draw.arc(surface, (255, 221, 89), rect, 0.3, 1.9, 5)

        if self._model.ratio_age > 0:
            for x, count in ((385, 2), (500, 3), (592, 4)):
                for index in range(count):
                    pygame.draw.rect(
                        surface,
                        (255, 218, 80),
                        (x - 30 + index * 18, 205, 11, 20),
                        border_radius=4,
                    )

        if self._model.rack_age > 0:
            offset = int(math.sin(self._model.driver_angle * 2.2) * 28)
            pygame.draw.line(
                surface,
                (255, 220, 86),
                (690 + offset, 410),
                (815 + offset, 410),
                6,
            )
            pygame.draw.polygon(
                surface,
                (255, 220, 86),
                [
                    (815 + offset, 410),
                    (799 + offset, 399),
                    (799 + offset, 421),
                ],
            )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        edge_dark = (48, 42, 38)
        if discovery_id == "teeth":
            # Two interlocking cogs with yellow star sparkle
            pygame.draw.polygon(
                surface,
                (83, 145, 181),
                [(cx - 20, cy - 14), (cx - 4, cy - 8), (cx - 4, cy + 8), (cx - 20, cy + 14)],
            )
            pygame.draw.polygon(
                surface,
                edge_dark,
                [(cx - 20, cy - 14), (cx - 4, cy - 8), (cx - 4, cy + 8), (cx - 20, cy + 14)],
                2,
            )
            pygame.draw.polygon(
                surface,
                (210, 175, 80),
                [(cx + 20, cy - 14), (cx + 4, cy - 8), (cx + 4, cy + 8), (cx + 20, cy + 14)],
            )
            pygame.draw.polygon(
                surface,
                edge_dark,
                [(cx + 20, cy - 14), (cx + 4, cy - 8), (cx + 4, cy + 8), (cx + 20, cy + 14)],
                2,
            )
            pygame.draw.circle(surface, (255, 235, 90), (cx, cy), 6)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 3)

        elif discovery_id == "direction":
            # Two rotating gears with arrows
            pygame.draw.circle(surface, (83, 145, 181), (cx - 12, cy), 13)
            pygame.draw.circle(surface, edge_dark, (cx - 12, cy), 13, 2)
            pygame.draw.circle(surface, (210, 175, 80), (cx + 12, cy), 13)
            pygame.draw.circle(surface, edge_dark, (cx + 12, cy), 13, 2)
            pygame.draw.arc(surface, (225, 120, 40), (cx - 23, cy - 18, 20, 20), 0.5, 3.5, 3)
            pygame.draw.arc(surface, (225, 120, 40), (cx + 3, cy - 2, 20, 20), 3.6, 6.6, 3)

        elif discovery_id == "ratio":
            # Big gear and small gear meshed together
            pygame.draw.circle(surface, (83, 145, 181), (cx - 10, cy), 18)
            pygame.draw.circle(surface, edge_dark, (cx - 10, cy), 18, 2)
            pygame.draw.circle(surface, (210, 175, 80), (cx + 16, cy), 9)
            pygame.draw.circle(surface, edge_dark, (cx + 16, cy), 9, 2)
            pygame.draw.circle(surface, (245, 220, 140), (cx - 10, cy), 5)
            pygame.draw.circle(surface, (245, 220, 140), (cx + 16, cy), 3)

        else:  # rack
            # Pinion gear meshed with horizontal toothed rack
            pygame.draw.circle(surface, (155, 117, 183), (cx, cy - 8), 14)
            pygame.draw.circle(surface, edge_dark, (cx, cy - 8), 14, 2)
            pygame.draw.circle(surface, (245, 220, 140), (cx, cy - 8), 4)
            pygame.draw.rect(surface, (102, 84, 67), (cx - 22, cy + 9, 44, 7), border_radius=2)
            pygame.draw.rect(surface, edge_dark, (cx - 22, cy + 9, 44, 7), 2, border_radius=2)
            for tx in (-16, -8, 0, 8, 16):
                pygame.draw.rect(surface, (102, 84, 67), (cx + tx - 2, cy + 5, 4, 5))
                pygame.draw.rect(surface, edge_dark, (cx + tx - 2, cy + 5, 4, 5), 1)

