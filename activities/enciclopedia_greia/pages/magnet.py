"""Magnet entry: interactive poles, attraction & repulsion, material response, and Earth compass."""

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
class MagnetDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MagnetDiscovery("poles", "magnet.poles", "encyclopedia.machines.magnet.poles", (240, 185)),
    MagnetDiscovery("materials", "magnet.materials", "encyclopedia.machines.magnet.materials", (765, 185)),
    MagnetDiscovery("distance", "magnet.distance", "encyclopedia.machines.magnet.distance", (240, 420)),
    MagnetDiscovery("field", "magnet.field", "encyclopedia.machines.magnet.field", (765, 420)),
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

        # Magnet physics & interactive positions
        self._left_x = 360
        self._magnet_y = 275
        self._magnet_w = 95
        self._magnet_h = 56

        # Right magnet can slide horizontally
        self._right_x = 540.0
        self._same_poles = False  # False = S vs N -> ATTRACT; True = S vs S -> REPEL
        self._dragging = False
        self._drag_offset_x = 0

        # Animation effects
        self._snap_sparkle_age = 0.0
        self._repel_wave_age = 0.0
        self._material_index = 0
        self._compass_angle = 0.0

        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._flip_button_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.magnet.intro")
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
        self._caption_key = DISCOVERIES[index].caption_key
        self._announce_selected()

    def _flip_poles(self) -> None:
        """Flip the right magnet poles (N <-> S)."""
        self._same_poles = not self._same_poles
        if self._same_poles:
            self._repel_wave_age = 1.5
            if self._right_x < 530:
                self._right_x = 575.0
        else:
            self._snap_sparkle_age = 0.5
            if self._right_x < 520:
                self._right_x = float(self._left_x + self._magnet_w)

    def _trigger_main(self) -> None:
        """Action button: flip poles and demonstrate attraction / repulsion!"""
        self._flip_poles()
        self._activate(self._selected)

    def update(self, dt: float) -> None:
        self._time += dt
        self._snap_sparkle_age = max(0.0, self._snap_sparkle_age - dt)
        self._repel_wave_age = max(0.0, self._repel_wave_age - dt)

        # Smooth compass needle oscillation towards North
        target_compass = 0.0 + math.sin(self._time * 2.0) * 8.0
        self._compass_angle += (target_compass - self._compass_angle) * min(1.0, dt * 5.0)

        # Magnet physics if not dragging
        min_x = self._left_x + self._magnet_w  # 455
        max_x = 610.0

        if not self._dragging:
            gap = self._right_x - min_x
            if not self._same_poles:
                # ATTRACT
                if gap < 70:
                    pull_speed = (70 - gap) * 12.0
                    self._right_x = max(float(min_x), self._right_x - pull_speed * dt)
                    if self._right_x <= min_x + 1.0:
                        if self._right_x != min_x:
                            self._snap_sparkle_age = 1.2
                        self._right_x = float(min_x)
            else:
                # REPEL
                if gap < 85:
                    push_speed = (85 - gap) * 14.0
                    self._right_x = min(max_x, self._right_x + push_speed * dt)
                    self._repel_wave_age = 1.2

        self._right_x = max(float(min_x), min(max_x, self._right_x))

    def handle_input(self, event: PageInput) -> None:
        min_x = self._left_x + self._magnet_w
        right_rect = pygame.Rect(int(self._right_x), self._magnet_y, self._magnet_w, self._magnet_h)

        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
            PageInputKind.POINTER_RELEASE,
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
                if self._flip_button_hit.collidepoint(point):
                    self._flip_poles()
                    return
                if right_rect.collidepoint(point) or pygame.Rect(int(min_x), self._magnet_y - 15, 200, self._magnet_h + 30).collidepoint(point):
                    self._dragging = True
                    self._drag_offset_x = int(self._right_x) - point[0]
                    return

            elif event.kind is PageInputKind.POINTER_RELEASE:
                if self._dragging:
                    self._dragging = False
                    return

            elif event.kind is PageInputKind.POINTER_MOVE:
                if self._dragging:
                    self._right_x = float(point[0] + self._drag_offset_x)
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
            if self._selected == 0:
                self._flip_poles()
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
            self._flip_poles()
        elif item.discovery_id == "materials":
            self._material_index = (self._material_index + 1) % 3
        elif item.discovery_id == "distance":
            if self._right_x > self._left_x + self._magnet_w + 40:
                self._right_x = float(self._left_x + self._magnet_w + 25)
            else:
                self._right_x = 590.0
        else:
            self._compass_angle = (self._compass_angle + 60.0) % 360.0
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((246, 243, 234))

        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("magnet.title"),
            center=(512, 50),
            size=36,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )

        self._draw_workbench_table(surface)

        disc = DISCOVERIES[self._selected]
        if disc.discovery_id == "field":
            self._draw_earth_compass_demo(surface)
        elif disc.discovery_id == "materials":
            self._draw_materials_demo(surface)
        else:
            self._draw_magnets_demo(surface)

        self._draw_hotspots(surface)

        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )

        self._action_hit = draw_machine_action_button(
            surface, (512, 460), machine="magnet", time=self._time, active=True
        )

        self._draw_caption(surface)

        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(925, 565),
            height=138,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_workbench_table(self, surface: pygame.Surface) -> None:
        table_rect = pygame.Rect(295, 142, 434, 290)
        shadow = pygame.Surface((table_rect.width + 10, table_rect.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (40, 30, 20, 45), shadow.get_rect(), border_radius=24)
        surface.blit(shadow, (table_rect.x - 5, table_rect.y + 4))

        pygame.draw.rect(surface, (238, 226, 204), table_rect, border_radius=22)
        pygame.draw.rect(surface, (155, 125, 95), table_rect, width=4, border_radius=22)

        pad_rect = pygame.Rect(310, 157, 404, 260)
        pygame.draw.rect(surface, (248, 244, 235), pad_rect, border_radius=16)
        pygame.draw.rect(surface, (210, 195, 175), pad_rect, width=2, border_radius=16)

    def _draw_magnets_demo(self, surface: pygame.Surface) -> None:
        t = self._time
        left_rect = pygame.Rect(self._left_x, self._magnet_y, self._magnet_w, self._magnet_h)
        rx = int(self._right_x)
        right_rect = pygame.Rect(rx, self._magnet_y, self._magnet_w, self._magnet_h)

        track_rect = pygame.Rect(self._left_x, self._magnet_y + self._magnet_h + 8, 250, 8)
        pygame.draw.rect(surface, (220, 210, 195), track_rect, border_radius=4)
        pygame.draw.rect(surface, (180, 168, 150), track_rect, width=1, border_radius=4)

        gap = rx - (self._left_x + self._magnet_w)

        if not self._same_poles:
            field_color = (65, 175, 95)
            for dy in (-14, -5, 5, 14):
                pygame.draw.line(surface, field_color, (self._left_x + self._magnet_w, self._magnet_y + 28 + dy), (rx, self._magnet_y + 28 + dy), 2)
            if gap > 12:
                mid_x = (self._left_x + self._magnet_w + rx) // 2
                pulse = math.sin(t * 10.0) * 3
                pygame.draw.polygon(surface, field_color, [(mid_x - 5 + pulse, self._magnet_y + 24), (mid_x + 2 + pulse, self._magnet_y + 28), (mid_x - 5 + pulse, self._magnet_y + 32)])
                pygame.draw.polygon(surface, field_color, [(mid_x + 5 - pulse, self._magnet_y + 24), (mid_x - 2 - pulse, self._magnet_y + 28), (mid_x + 5 - pulse, self._magnet_y + 32)])

            status_text = "POLI OPPOSTI: SI ATTRAGGONO!" if gap > 2 else "UNITI DALLA FORZA MAGNETICA!"
            status_color = (45, 140, 75)
        else:
            repel_color = (225, 75, 65)
            mid_x = (self._left_x + self._magnet_w + rx) // 2
            wave_pulse = int((math.sin(t * 12.0) * 0.5 + 0.5) * 6)
            for r_w in (10, 18, 26):
                pygame.draw.arc(surface, repel_color, (mid_x - r_w - wave_pulse, self._magnet_y + 12, r_w * 2, 32), 0.8, 2.3, 3)
                pygame.draw.arc(surface, repel_color, (mid_x - r_w + wave_pulse, self._magnet_y + 12, r_w * 2, 32), 3.9, 5.4, 3)

            status_text = "POLI UGUALI: SI RESPINGONO!"
            status_color = (205, 55, 45)

        rendered_status = self.context.typography.render(status_text, FontRole.BODY, 16, status_color)
        surface.blit(rendered_status, rendered_status.get_rect(center=(512, 195)))

        self._draw_bar_magnet(surface, left_rect, left_label="N", right_label="S", left_color=(225, 70, 60), right_color=(55, 125, 205))

        if not self._same_poles:
            r_left_lbl, r_right_lbl = "N", "S"
            r_left_col, r_right_col = (225, 70, 60), (55, 125, 205)
        else:
            r_left_lbl, r_right_lbl = "S", "N"
            r_left_col, r_right_col = (55, 125, 205), (225, 70, 60)

        self._draw_bar_magnet(surface, right_rect, left_label=r_left_lbl, right_label=r_right_lbl, left_color=r_left_col, right_color=r_right_col)

        if self._snap_sparkle_age > 0.0 or gap < 4:
            sparkle_x = self._left_x + self._magnet_w
            for s_idx in range(5):
                ang = t * 6.0 + s_idx * 1.25
                dist = 12 + math.sin(t * 15.0 + s_idx) * 5
                sx = sparkle_x + int(math.cos(ang) * dist)
                sy = self._magnet_y + 28 + int(math.sin(ang) * dist)
                pygame.draw.circle(surface, (255, 225, 60), (sx, sy), 3)

        btn_w, btn_h = 120, 30
        self._flip_button_hit = pygame.Rect(rx - 12, self._magnet_y + self._magnet_h + 24, btn_w, btn_h)
        pygame.draw.rect(surface, (255, 250, 240), self._flip_button_hit, border_radius=10)
        pygame.draw.rect(surface, (140, 115, 90), self._flip_button_hit, width=2, border_radius=10)
        flip_text = self.context.typography.render("GIRA POLI", FontRole.CONTROL, 14, (70, 55, 45))
        surface.blit(flip_text, flip_text.get_rect(center=self._flip_button_hit.center))

    def _draw_bar_magnet(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        left_label: str,
        right_label: str,
        left_color: tuple[int, int, int],
        right_color: tuple[int, int, int],
    ) -> None:
        half = rect.width // 2

        shadow = pygame.Surface((rect.width + 6, rect.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 35), shadow.get_rect(), border_radius=12)
        surface.blit(shadow, (rect.x - 2, rect.y + 4))

        pygame.draw.rect(surface, left_color, (rect.x, rect.y, half, rect.height), border_radius=10)
        pygame.draw.rect(surface, right_color, (rect.x + half, rect.y, half, rect.height), border_radius=10)
        pygame.draw.line(surface, (255, 255, 255, 150), (rect.x + half, rect.y + 2), (rect.x + half, rect.y + rect.height - 2), 2)

        # Highlight lines on top edge
        pygame.draw.line(surface, (255, 175, 165), (rect.x + 4, rect.y + 3), (rect.x + half - 2, rect.y + 3), 2)
        pygame.draw.line(surface, (155, 200, 255), (rect.x + half + 2, rect.y + 3), (rect.x + rect.width - 4, rect.y + 3), 2)

        pygame.draw.rect(surface, (60, 50, 45), rect, width=3, border_radius=10)

        for x, label in (
            (rect.x + half // 2, left_label),
            (rect.x + half + half // 2, right_label),
        ):
            # Subtle drop shadow for text
            t_shadow = self.context.typography.render(label, FontRole.CONTROL, 22, (40, 30, 30))
            surface.blit(t_shadow, t_shadow.get_rect(center=(x, rect.centery + 1)))
            text = self.context.typography.render(label, FontRole.CONTROL, 22, (255, 255, 255))
            surface.blit(text, text.get_rect(center=(x, rect.centery)))

    def _draw_materials_demo(self, surface: pygame.Surface) -> None:
        t = self._time
        dish_center = (410, 270)
        # Dish
        pygame.draw.ellipse(surface, (215, 228, 235), (dish_center[0] - 65, dish_center[1] - 45, 130, 90))
        pygame.draw.ellipse(surface, (165, 185, 195), (dish_center[0] - 65, dish_center[1] - 45, 130, 90), 3)

        samples = [
            ("ACCIAIO (Chiodo)", (125, 130, 138), True),
            ("LEGNO (Blocchetto)", (198, 148, 88), False),
            ("ALLUMINIO (Moneta)", (190, 195, 202), False),
        ]
        name, col, attracted = samples[self._material_index]

        mag_rect = pygame.Rect(565, 243, 90, 54)
        self._draw_bar_magnet(surface, mag_rect, left_label="N", right_label="S", left_color=(225, 70, 60), right_color=(55, 125, 205))

        if attracted:
            # Slides out of the dish and sticks to the magnet!
            sample_x = 532 - int(math.sin(t * 8.0) * 3)
            sample_y = 270
            pygame.draw.line(surface, col, (sample_x - 16, sample_y), (sample_x + 16, sample_y), 5)
            pygame.draw.circle(surface, (80, 85, 90), (sample_x + 16, sample_y), 6)
            pygame.draw.line(surface, (65, 175, 95), (sample_x + 20, sample_y), (560, sample_y), 3)
            res_text = "ATTIRATO! (Ferro e acciaio sono magnetici)"
            res_col = (45, 140, 75)
        elif self._material_index == 1:
            sample_x = 410
            sample_y = 270
            pygame.draw.rect(surface, col, (sample_x - 18, sample_y - 12, 36, 24), border_radius=4)
            pygame.draw.rect(surface, (140, 95, 55), (sample_x - 18, sample_y - 12, 36, 24), width=2, border_radius=4)
            res_text = "NON ATTIRATO (Il legno non reagisce)"
            res_col = (110, 90, 75)
        else:
            sample_x = 410
            sample_y = 270
            pygame.draw.circle(surface, col, (sample_x, sample_y), 16)
            pygame.draw.circle(surface, (145, 150, 158), (sample_x, sample_y), 16, 2)
            res_text = "NON ATTIRATO (Non tutti i metalli sono magnetici!)"
            res_col = (110, 90, 75)

        rendered_name = self.context.typography.render(name, FontRole.DISPLAY, 17, (60, 50, 45))
        surface.blit(rendered_name, rendered_name.get_rect(center=(410, 185)))

        rendered_res = self.context.typography.render(res_text, FontRole.BODY, 15, res_col)
        surface.blit(rendered_res, rendered_res.get_rect(center=(512, 365)))

    def _draw_earth_compass_demo(self, surface: pygame.Surface) -> None:
        earth_cx, earth_cy = 425, 265

        for r_w, r_h in ((55, 38), (80, 56), (102, 74)):
            field_rect = pygame.Rect(earth_cx - r_w, earth_cy - r_h, r_w * 2, r_h * 2)
            pygame.draw.arc(surface, (120, 175, 230), field_rect, 0.25, math.pi - 0.25, 2)
            pygame.draw.arc(surface, (120, 175, 230), field_rect, math.pi + 0.25, math.tau - 0.25, 2)

        pygame.draw.circle(surface, (65, 145, 215), (earth_cx, earth_cy), 42)
        pygame.draw.ellipse(surface, (85, 175, 95), (earth_cx - 18, earth_cy - 22, 28, 22))
        pygame.draw.ellipse(surface, (85, 175, 95), (earth_cx - 6, earth_cy + 5, 22, 24))
        pygame.draw.circle(surface, (45, 115, 175), (earth_cx, earth_cy), 42, 2)

        n_lbl = self.context.typography.render("N", FontRole.CONTROL, 14, (235, 75, 65))
        s_lbl = self.context.typography.render("S", FontRole.CONTROL, 14, (55, 125, 205))
        surface.blit(n_lbl, n_lbl.get_rect(center=(earth_cx, earth_cy - 48)))
        surface.blit(s_lbl, s_lbl.get_rect(center=(earth_cx, earth_cy + 48)))

        comp_cx, comp_cy = 595, 265
        pygame.draw.circle(surface, (215, 175, 80), (comp_cx, comp_cy), 38)
        pygame.draw.circle(surface, (155, 115, 40), (comp_cx, comp_cy), 38, 3)
        pygame.draw.circle(surface, (255, 250, 240), (comp_cx, comp_cy), 32)

        for ang in (0, math.pi/2, math.pi, 3*math.pi/2):
            dx = math.cos(ang) * 26
            dy = math.sin(ang) * 26
            pygame.draw.line(surface, (200, 190, 175), (comp_cx, comp_cy), (comp_cx + dx, comp_cy + dy), 1)

        c_rad = math.radians(self._compass_angle)
        needle_len = 24
        nx = math.sin(c_rad) * needle_len
        ny = -math.cos(c_rad) * needle_len

        pygame.draw.polygon(surface, (225, 65, 55), [
            (comp_cx, comp_cy),
            (comp_cx - 4, comp_cy),
            (comp_cx + nx, comp_cy + ny),
            (comp_cx + 4, comp_cy),
        ])
        pygame.draw.polygon(surface, (175, 185, 195), [
            (comp_cx, comp_cy),
            (comp_cx - 4, comp_cy),
            (comp_cx - nx, comp_cy - ny),
            (comp_cx + 4, comp_cy),
        ])
        pygame.draw.circle(surface, (235, 195, 75), (comp_cx, comp_cy), 4)

        comp_lbl = self.context.typography.render("LA BUSSOLA PUNTA A NORD", FontRole.BODY, 15, (60, 50, 45))
        surface.blit(comp_lbl, comp_lbl.get_rect(center=(512, 365)))

    @staticmethod
    def _draw_hotspot_icon(surface: pygame.Surface, item: MagnetDiscovery) -> None:
        cx, cy = item.center
        if item.discovery_id == "poles":
            pygame.draw.rect(surface, (225, 70, 60), (cx - 24, cy - 10, 24, 20), border_radius=4)
            pygame.draw.rect(surface, (55, 125, 205), (cx, cy - 10, 24, 20), border_radius=4)
            pygame.draw.rect(surface, (60, 50, 45), (cx - 24, cy - 10, 48, 20), width=2, border_radius=4)
        elif item.discovery_id == "materials":
            pygame.draw.circle(surface, (215, 225, 230), (cx, cy), 18)
            pygame.draw.line(surface, (110, 115, 125), (cx - 10, cy), (cx + 10, cy), 4)
            pygame.draw.circle(surface, (255, 215, 60), (cx + 14, cy - 8), 3)
        elif item.discovery_id == "distance":
            pygame.draw.rect(surface, (55, 125, 205), (cx - 22, cy - 8, 16, 16), border_radius=3)
            pygame.draw.rect(surface, (225, 70, 60), (cx + 6, cy - 8, 16, 16), border_radius=3)
            pygame.draw.line(surface, (65, 175, 95), (cx - 3, cy - 6), (cx + 3, cy - 6), 2)
            pygame.draw.line(surface, (65, 175, 95), (cx - 4, cy), (cx + 4, cy), 2)
            pygame.draw.line(surface, (65, 175, 95), (cx - 3, cy + 6), (cx + 3, cy + 6), 2)
        else:
            pygame.draw.circle(surface, (65, 145, 215), (cx, cy), 16)
            pygame.draw.arc(surface, (255, 255, 255), (cx - 22, cy - 14, 44, 28), 0.2, math.pi - 0.2, 2)
            pygame.draw.line(surface, (225, 65, 55), (cx, cy), (cx, cy - 12), 3)

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
