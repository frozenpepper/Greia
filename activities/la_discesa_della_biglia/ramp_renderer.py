"""La Discesa della Biglia — rendering layer.

The renderer draws the cached backdrop, the playfield border, the
marble, the placed tools, the basket (animated when the basket
moves), the tool palette, and the per-frame HUD (best time, level
label, current attempt time). All drawing happens on the
reference 1024x600 viewport; the platform scales the result to
the actual device viewport.

The renderer is a stateful object that the lifecycle layer drives.
It owns no Greia lifecycle: no event emission, no storage, no
profile handling. Pre-reader safety (large icons, no text-only
instructions, generous hit targets) is encoded in the layout
constants and the palette geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .ramp_content import (
        LEVELS,
        MARBLE_COLOR,
        MARBLE_OUTLINE,
        MARBLE_RADIUS,
        MARBLE_START,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SLOPE_TILT_DEGREES,
        SPRING_RADIUS,
        TOOL_BUMPER_RADIUS,
        TOOL_CATALOGUE,
        TOOL_PALETTE_TOP,
        TOOL_RADIUS,
        ToolKind,
        Level,
        PlacedTool,
    )
else:
    from ramp_content import (
        LEVELS,
        MARBLE_COLOR,
        MARBLE_OUTLINE,
        MARBLE_RADIUS,
        MARBLE_START,
        PLAYFIELD_BOTTOM,
        PLAYFIELD_LEFT,
        PLAYFIELD_RIGHT,
        PLAYFIELD_TOP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SLOPE_TILT_DEGREES,
        SPRING_RADIUS,
        TOOL_BUMPER_RADIUS,
        TOOL_CATALOGUE,
        TOOL_PALETTE_TOP,
        TOOL_RADIUS,
        ToolKind,
        Level,
        PlacedTool,
    )


PALETTE_BUTTON_SIZE: Final = 96
PALETTE_BUTTON_GAP: Final = 22
PALETTE_FIRST_X: Final = (REFERENCE_WIDTH - (
    PALETTE_BUTTON_SIZE * len(TOOL_CATALOGUE)
    + PALETTE_BUTTON_GAP * (len(TOOL_CATALOGUE) - 1)
)) // 2

BACKDROP_COLOR: Final = (236, 245, 255)
PLAYFIELD_BORDER: Final = (148, 163, 184)
PLAYFIELD_FILL: Final = (250, 250, 252)
GRID_COLOR: Final = (228, 234, 244)
BASKET_COLOR: Final = (250, 204, 21)
BASKET_DARK: Final = (180, 83, 9)
BASKET_LIP: Final = (245, 158, 11)
SLOPE_TINT: Final = (245, 158, 11)
BUMPER_TINT: Final = (255, 255, 255)
FAN_TINT: Final = (224, 242, 254)
SPRING_TINT: Final = (220, 252, 231)


def _tool_color(kind: ToolKind) -> tuple[int, int, int]:
    if kind == ToolKind.SLOPE:
        return SLOPE_TINT
    if kind == ToolKind.BUMPER:
        return BUMPER_TINT
    if kind == ToolKind.FAN:
        return FAN_TINT
    if kind == ToolKind.SPRING:
        return SPRING_TINT
    return BACKDROP_COLOR


@dataclass
class RampRenderer:
    """Owns the per-frame drawing for the Activity.

    The lifecycle layer passes the current engine state and the
    current localizer + typography each frame. The renderer reads
    them and blits the result.
    """

    surface: pygame.Surface
    font: pygame.font.Font | None
    palette_selected: int
    palette_buttons: list[pygame.Rect]
    play_btn_rect: pygame.Rect
    reset_btn_rect: pygame.Rect
    next_btn_rect: pygame.Rect
    back_btn_rect: pygame.Rect
    drag_origin: tuple[int, int] | None
    drag_kind: ToolKind | None
    drag_pos: tuple[int, int] | None
    backdrop_cache: pygame.Surface

    @classmethod
    def build(
        cls,
        surface: pygame.Surface,
    ) -> "RampRenderer":
        palette_buttons: list[pygame.Rect] = []
        for i in range(len(TOOL_CATALOGUE)):
            x = PALETTE_FIRST_X + i * (PALETTE_BUTTON_SIZE + PALETTE_BUTTON_GAP)
            y = TOOL_PALETTE_TOP
            palette_buttons.append(
                pygame.Rect(x, y, PALETTE_BUTTON_SIZE, PALETTE_BUTTON_SIZE)
            )
        # Right side controls
        reset_btn = pygame.Rect(
            REFERENCE_WIDTH - 200, 14, 88, 44
        )
        next_btn = pygame.Rect(
            REFERENCE_WIDTH - 200, 14, 88, 44
        )
        back_btn = pygame.Rect(
            REFERENCE_WIDTH - 304, 14, 88, 44
        )
        # Center play button
        play_btn = pygame.Rect(
            REFERENCE_WIDTH - 304, 14, 88, 44
        )
        backdrop = cls._render_backdrop()
        return cls(
            surface=surface,
            font=None,
            palette_selected=0,
            palette_buttons=palette_buttons,
            play_btn_rect=play_btn,
            reset_btn_rect=reset_btn,
            next_btn_rect=next_btn,
            back_btn_rect=back_btn,
            drag_origin=None,
            drag_kind=None,
            drag_pos=None,
            backdrop_cache=backdrop,
        )

    @staticmethod
    def _render_backdrop() -> pygame.Surface:
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surf.fill(BACKDROP_COLOR)
        # Subtle vertical gradient: warm at the top, cool at the bottom
        for y in range(0, REFERENCE_HEIGHT, 2):
            ratio = y / REFERENCE_HEIGHT
            r = int(244 * (1 - ratio) + 230 * ratio)
            g = int(248 * (1 - ratio) + 240 * ratio)
            b = int(255 * (1 - ratio) + 248 * ratio)
            pygame.draw.rect(surf, (r, g, b), (0, y, REFERENCE_WIDTH, 2))
        # Grid inside the playfield
        spacing = 32
        for gx in range(PLAYFIELD_LEFT, PLAYFIELD_RIGHT + 1, spacing):
            pygame.draw.line(
                surf, GRID_COLOR,
                (gx, PLAYFIELD_TOP), (gx, PLAYFIELD_BOTTOM), 1
            )
        for gy in range(PLAYFIELD_TOP, PLAYFIELD_BOTTOM + 1, spacing):
            pygame.draw.line(
                surf, GRID_COLOR,
                (PLAYFIELD_LEFT, gy), (PLAYFIELD_RIGHT, gy), 1
            )
        return surf

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(
        self,
        level: Level,
        level_index: int,
        tools: list[PlacedTool],
        marble: tuple[float, float, float, float],  # x, y, vx, vy
        elapsed: float,
        finished: bool,
        outcome: str | None,
        best_time: float | None,
        text_fn,  # callable(text, color) -> pygame.Surface
    ) -> None:
        surf = self.surface
        surf.blit(self.backdrop_cache, (0, 0))
        self._draw_playfield_frame()
        self._draw_basket(level, elapsed)
        self._draw_obstacles(level)
        self._draw_tools(tools)
        self._draw_marble(*marble, finished=finished, outcome=outcome)
        self._draw_palette()
        self._draw_drag_ghost(level)
        self._draw_top_bar(level, level_index, elapsed, finished, best_time, text_fn)
        self._draw_action_buttons(finished, outcome, text_fn)
        self._draw_result_banner(finished, outcome, elapsed, best_time, text_fn)

    def _draw_playfield_frame(self) -> None:
        # Soft inner panel
        rect = pygame.Rect(
            PLAYFIELD_LEFT - 4, PLAYFIELD_TOP - 4,
            PLAYFIELD_RIGHT - PLAYFIELD_LEFT + 8,
            PLAYFIELD_BOTTOM - PLAYFIELD_TOP + 8,
        )
        pygame.draw.rect(self.surface, PLAYFIELD_FILL, rect, border_radius=18)
        pygame.draw.rect(self.surface, PLAYFIELD_BORDER, rect, width=2, border_radius=18)

    def _draw_basket(self, level: Level, elapsed: float) -> None:
        if level.basket_moves and level.basket_period > 0:
            phase = (elapsed / level.basket_period) * 2.0 * math.pi
            bx = level.basket_x + level.basket_amplitude * math.sin(phase)
            by = level.basket_y
        else:
            bx, by = level.basket_x, level.basket_y
        r = level.basket_radius
        # Open basket: the top half is the rim, the bottom half is the cup.
        # Rim
        pygame.draw.arc(
            self.surface, BASKET_LIP,
            pygame.Rect(int(bx - r), int(by - r * 0.9), int(r * 2), int(r * 0.9)),
            0, math.pi, max(4, int(r * 0.18))
        )
        # Cup
        cup_rect = pygame.Rect(
            int(bx - r * 0.85), int(by - r * 0.1),
            int(r * 1.7), int(r * 1.1),
        )
        pygame.draw.rect(self.surface, BASKET_COLOR, cup_rect, border_radius=12)
        pygame.draw.rect(self.surface, BASKET_DARK, cup_rect, width=3, border_radius=12)
        # Drop-off pulse (gentle breathing) so the basket invites taps
        pulse = int(1.5 + math.sin(elapsed * 3.0) * 1.5)
        pygame.draw.rect(
            self.surface, BASKET_DARK,
            cup_rect.inflate(pulse * 2, pulse * 2), width=2, border_radius=14,
        )

    def _draw_obstacles(self, level: Level) -> None:
        for ox, oy, orad in level.obstacles:
            pygame.draw.circle(self.surface, (148, 163, 184), (int(ox), int(oy)), int(orad))
            pygame.draw.circle(self.surface, (71, 85, 105), (int(ox), int(oy)), int(orad), 2)
            # Little cross to make them look like boulders, not targets
            pygame.draw.line(
                self.surface, (71, 85, 105),
                (int(ox - orad * 0.4), int(oy - orad * 0.4)),
                (int(ox + orad * 0.4), int(oy + orad * 0.4)), 2,
            )
            pygame.draw.line(
                self.surface, (71, 85, 105),
                (int(ox + orad * 0.4), int(oy - orad * 0.4)),
                (int(ox - orad * 0.4), int(oy + orad * 0.4)), 2,
            )

    def _draw_tools(self, tools: list[PlacedTool]) -> None:
        for tool in tools:
            kind = tool.spec.kind
            color = _tool_color(kind)
            x, y = int(tool.x), int(tool.y)
            if kind == ToolKind.SLOPE:
                # Sloped rectangle
                length = 76
                thickness = 16
                surf = pygame.Surface((length, thickness), pygame.SRCALPHA)
                pygame.draw.rect(surf, (180, 130, 70), (0, 0, length, thickness), border_radius=6)
                pygame.draw.rect(surf, (120, 90, 50), (0, 0, length, thickness), width=2, border_radius=6)
                # Wood grain
                for gx in range(8, length, 12):
                    pygame.draw.line(surf, (140, 100, 60), (gx, 3), (gx, thickness - 3), 1)
                rotated = pygame.transform.rotate(surf, -math.degrees(tool.angle))
                rect = rotated.get_rect(center=(x, y))
                self.surface.blit(rotated, rect)
            elif kind == ToolKind.BUMPER:
                # Spring bumper: red rubber ball with white stripe
                pygame.draw.circle(self.surface, (220, 38, 38), (x, y), TOOL_BUMPER_RADIUS)
                pygame.draw.circle(self.surface, (127, 29, 29), (x, y), TOOL_BUMPER_RADIUS, 3)
                pygame.draw.line(
                    self.surface, (255, 255, 255),
                    (x - TOOL_BUMPER_RADIUS + 4, y),
                    (x + TOOL_BUMPER_RADIUS - 4, y), 4,
                )
            elif kind == ToolKind.FAN:
                # Fan: blue box with rotating blades
                size = 44
                rect = pygame.Rect(x - size // 2, y - size // 2, size, size)
                pygame.draw.rect(self.surface, (56, 189, 248), rect, border_radius=10)
                pygame.draw.rect(self.surface, (12, 74, 110), rect, width=2, border_radius=10)
                # Three blades (rotated by elapsed would be ideal; we
                # just draw a static "fan" so the rendering is cheap).
                cx, cy = x, y
                for ang in (0, 120, 240):
                    rad = math.radians(ang)
                    bx = cx + math.cos(rad) * 14
                    by = cy + math.sin(rad) * 14
                    pygame.draw.line(self.surface, (12, 74, 110), (cx, cy), (int(bx), int(by)), 4)
                pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy), 4)
            elif kind == ToolKind.SPRING:
                # Spring: green coil
                pygame.draw.circle(self.surface, (220, 252, 231), (x, y), SPRING_RADIUS)
                pygame.draw.circle(self.surface, (22, 101, 52), (x, y), SPRING_RADIUS, 3)
                # Inner coil suggestion
                pygame.draw.circle(self.surface, (187, 247, 208), (x, y), SPRING_RADIUS - 6, 2)
                pygame.draw.circle(self.surface, (22, 101, 52), (x, y), 4)

    def _draw_marble(
        self, x: float, y: float, vx: float, vy: float,
        finished: bool, outcome: str | None,
    ) -> None:
        # A marble that left the playfield (a miss) stays visible at the edge it
        # fell past instead of being drawn over the tool palette or off-screen.
        cx = int(min(max(x, PLAYFIELD_LEFT + MARBLE_RADIUS), PLAYFIELD_RIGHT - MARBLE_RADIUS))
        cy = int(min(max(y, PLAYFIELD_TOP + MARBLE_RADIUS), PLAYFIELD_BOTTOM - MARBLE_RADIUS))
        # Soft shadow
        pygame.draw.ellipse(
            self.surface, (30, 41, 59, 60),
            (cx - MARBLE_RADIUS, cy + MARBLE_RADIUS - 4,
             MARBLE_RADIUS * 2, 8),
        )
        # Marble
        pygame.draw.circle(self.surface, MARBLE_COLOR, (cx, cy), MARBLE_RADIUS)
        pygame.draw.circle(self.surface, MARBLE_OUTLINE, (cx, cy), MARBLE_RADIUS, 2)
        # Highlight
        pygame.draw.circle(
            self.surface, (255, 255, 255, 180),
            (cx - 4, cy - 5), 4
        )
        # Pulsing aura when not finished
        if not finished:
            t = pygame.time.get_ticks() / 1000.0
            pulse = int(2 + abs(math.sin(t * 2.5)) * 4)
            aura = pygame.Surface(
                (MARBLE_RADIUS * 2 + pulse * 4, MARBLE_RADIUS * 2 + pulse * 4),
                pygame.SRCALPHA,
            )
            pygame.draw.circle(
                aura, (245, 158, 11, 50),
                (aura.get_width() // 2, aura.get_height() // 2),
                MARBLE_RADIUS + pulse,
            )
            self.surface.blit(
                aura, (cx - aura.get_width() // 2, cy - aura.get_height() // 2)
            )

    def _draw_palette(self) -> None:
        for i, rect in enumerate(self.palette_buttons):
            spec = TOOL_CATALOGUE[i]
            is_selected = (i == self.palette_selected)
            color = _tool_color(spec.kind)
            shadow = rect.move(0, 4)
            pygame.draw.rect(self.surface, (180, 190, 210), shadow, border_radius=18)
            pygame.draw.rect(self.surface, color, rect, border_radius=18)
            border_col = (180, 83, 9) if is_selected else (148, 163, 184)
            border_w = 5 if is_selected else 2
            pygame.draw.rect(
                self.surface, border_col, rect, width=border_w, border_radius=18
            )
            # Tool icon in the center of the button
            cx, cy = rect.center
            if spec.kind == ToolKind.SLOPE:
                sl = pygame.Surface((46, 12), pygame.SRCALPHA)
                pygame.draw.rect(sl, (120, 90, 50), (0, 0, 46, 12), border_radius=4)
                rotated = pygame.transform.rotate(sl, -18)
                self.surface.blit(rotated, rotated.get_rect(center=(cx, cy)))
            elif spec.kind == ToolKind.BUMPER:
                pygame.draw.circle(self.surface, (220, 38, 38), (cx, cy), 16)
                pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy), 16, 2)
            elif spec.kind == ToolKind.FAN:
                pygame.draw.rect(
                    self.surface, (56, 189, 248),
                    pygame.Rect(cx - 16, cy - 12, 32, 24), border_radius=6
                )
                for ang in (0, 120, 240):
                    rad = math.radians(ang)
                    bx = cx + math.cos(rad) * 8
                    by = cy + math.sin(rad) * 8
                    pygame.draw.line(
                        self.surface, (12, 74, 110),
                        (cx, cy), (int(bx), int(by)), 3,
                    )
            elif spec.kind == ToolKind.SPRING:
                pygame.draw.circle(self.surface, (220, 252, 231), (cx, cy), 16)
                pygame.draw.circle(self.surface, (22, 101, 52), (cx, cy), 16, 2)

    def _draw_drag_ghost(self, level: Level) -> None:
        if self.drag_kind is None or self.drag_pos is None:
            return
        x, y = self.drag_pos
        if self.drag_kind == ToolKind.SLOPE:
            length = 76
            thickness = 16
            surf = pygame.Surface((length, thickness), pygame.SRCALPHA)
            pygame.draw.rect(surf, (180, 130, 70, 180), (0, 0, length, thickness), border_radius=6)
            pygame.draw.rect(surf, (120, 90, 50, 220), (0, 0, length, thickness), width=2, border_radius=6)
            # Preview the tilt the slope will have once placed
            tilt = SLOPE_TILT_DEGREES * (1.0 if level.basket_x >= x else -1.0)
            surf = pygame.transform.rotate(surf, -tilt)
            self.surface.blit(surf, surf.get_rect(center=(x, y)))
        elif self.drag_kind == ToolKind.BUMPER:
            ghost = pygame.Surface(
                (TOOL_BUMPER_RADIUS * 2, TOOL_BUMPER_RADIUS * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(ghost, (220, 38, 38, 180), (TOOL_BUMPER_RADIUS, TOOL_BUMPER_RADIUS), TOOL_BUMPER_RADIUS)
            self.surface.blit(ghost, (x - TOOL_BUMPER_RADIUS, y - TOOL_BUMPER_RADIUS))
        elif self.drag_kind == ToolKind.FAN:
            ghost = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.rect(ghost, (56, 189, 248, 180), (0, 0, 44, 44), border_radius=10)
            self.surface.blit(ghost, (x - 22, y - 22))
        elif self.drag_kind == ToolKind.SPRING:
            ghost = pygame.Surface(
                (SPRING_RADIUS * 2, SPRING_RADIUS * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(ghost, (220, 252, 231, 200), (SPRING_RADIUS, SPRING_RADIUS), SPRING_RADIUS)
            self.surface.blit(ghost, (x - SPRING_RADIUS, y - SPRING_RADIUS))

    def _draw_top_bar(
        self,
        level: Level,
        level_index: int,
        elapsed: float,
        finished: bool,
        best_time: float | None,
        text_fn,
    ) -> None:
        # Star pill (best time)
        star_pill = pygame.Rect(80, 16, 200, 56)
        pygame.draw.rect(self.surface, (255, 255, 255), star_pill, border_radius=20)
        pygame.draw.rect(self.surface, (234, 179, 8), star_pill, width=3, border_radius=20)
        pygame.draw.circle(self.surface, (234, 179, 8), (star_pill.left + 28, star_pill.centery), 16)
        if best_time is not None:
            txt = text_fn(self._format_time(best_time), (180, 83, 9))
        else:
            txt = text_fn("--", (148, 163, 184))
        self.surface.blit(
            txt, (star_pill.left + 54, star_pill.centery - txt.get_height() // 2)
        )
        # Level label (centered)
        level_label = f"L{level_index + 1}/{len(LEVELS)}"
        ltxt = text_fn(level_label, (71, 85, 105))
        self.surface.blit(ltxt, (star_pill.right + 18, star_pill.centery - ltxt.get_height() // 2))
        # Current attempt timer (right)
        timer_pill = pygame.Rect(REFERENCE_WIDTH - 332, 16, 144, 56)
        pygame.draw.rect(self.surface, (255, 255, 255), timer_pill, border_radius=20)
        pygame.draw.rect(self.surface, (56, 189, 248), timer_pill, width=3, border_radius=20)
        pygame.draw.circle(self.surface, (56, 189, 248), (timer_pill.left + 28, timer_pill.centery), 14)
        timer_text = self._format_time(elapsed if not finished else elapsed)
        ttxt = text_fn(timer_text, (12, 74, 110))
        self.surface.blit(
            ttxt, (timer_pill.left + 52, timer_pill.centery - ttxt.get_height() // 2)
        )

    def _draw_action_buttons(self, finished: bool, outcome: str | None, text_fn) -> None:
        # Left "back" / "reset" / "play" pill (only when applicable)
        # "PULISCI" = clear all placed tools
        clear_btn = pygame.Rect(80, 84, 200, 48)
        pygame.draw.rect(self.surface, (241, 245, 249), clear_btn, border_radius=18)
        pygame.draw.rect(self.surface, (148, 163, 184), clear_btn, width=3, border_radius=18)
        ctxt = text_fn("ui.clear", (71, 85, 105))
        self.surface.blit(ctxt, ctxt.get_rect(center=clear_btn.center))
        # "FAI CADERE!" = run / drop
        go_btn = pygame.Rect(REFERENCE_WIDTH - 280, 84, 200, 48)
        col = (34, 197, 94) if not finished else (148, 163, 184)
        pygame.draw.rect(self.surface, col, go_btn, border_radius=18)
        pygame.draw.rect(self.surface, (22, 101, 52), go_btn, width=3, border_radius=18)
        gtxt = text_fn("ui.drop", (255, 255, 255))
        self.surface.blit(gtxt, gtxt.get_rect(center=go_btn.center))

    def _draw_result_banner(
        self,
        finished: bool,
        outcome: str | None,
        elapsed: float,
        best_time: float | None,
        text_fn,
    ) -> None:
        if not finished:
            return
        # Big centered banner
        if outcome == "hit":
            title = "ui.win"
            title_color = (22, 101, 52)
            sub = self._format_time(elapsed)
            if best_time is not None and abs(best_time - elapsed) < 0.05:
                sub = f"{text_fn.resolve('ui.new_best')}  {sub}"
        else:
            title = "ui.miss"
            title_color = (180, 83, 9)
            sub = "ui.retry"
        banner = pygame.Rect(0, 0, 720, 120)
        banner.center = (REFERENCE_WIDTH // 2, REFERENCE_HEIGHT // 2)
        pygame.draw.rect(self.surface, (255, 255, 255), banner, border_radius=24)
        pygame.draw.rect(self.surface, title_color, banner, width=4, border_radius=24)
        title_surf = text_fn(title, title_color)
        sub_surf = text_fn(sub, (71, 85, 105))
        self.surface.blit(
            title_surf, title_surf.get_rect(center=(banner.centerx, banner.centery - 22))
        )
        self.surface.blit(
            sub_surf, sub_surf.get_rect(center=(banner.centerx, banner.centery + 26))
        )

    @staticmethod
    def _format_time(seconds: float) -> str:
        s = max(0.0, seconds)
        return f"{s:4.1f}s"
