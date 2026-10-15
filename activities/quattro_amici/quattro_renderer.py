"""Storybook presentation and graphics for Quattro Amici in Fila.

Renders high-contrast storybook natural scenery, wooden slotted board,
tactile embossed wooden discs, character mascot reactions, smooth gravity
drop animations, and celebratory rainbow victory ribbons.

Respects top-left system chrome clearance (ADR 0019).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .quattro_content import (
        COLOR_ACORN_CAP,
        COLOR_ACORN_STEM,
        COLOR_BANNER_BG,
        COLOR_BANNER_BORDER,
        COLOR_BOARD_DARK,
        COLOR_BOARD_HOLE,
        COLOR_BOARD_HOLE_RIM,
        COLOR_BOARD_LEG,
        COLOR_BOARD_LIGHT,
        COLOR_BOARD_WOOD,
        COLOR_CARROT_LEAF,
        COLOR_CARROT_LEAF_LIGHT,
        COLOR_FLASH_DARK,
        COLOR_FLASH_LIGHT,
        COLOR_FLASH_MAIN,
        COLOR_GOLD,
        COLOR_GRASS_TABLE,
        COLOR_HILL_DISTANT,
        COLOR_HILL_NEAR,
        COLOR_LEO_DARK,
        COLOR_LEO_LIGHT,
        COLOR_LEO_MAIN,
        COLOR_SKY_BOTTOM,
        COLOR_SKY_TOP,
        COLOR_TABLE_WOOD,
        COLOR_TABLE_WOOD_DARK,
        COLOR_TEXT_DARK,
        COLOR_TEXT_MUTED,
        COLOR_WIN_GLOW,
        LEVEL_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GameMode,
        GameStatus,
        Player,
    )
    from .quattro_model import QuattroModel
else:
    from quattro_content import (
        COLOR_ACORN_CAP,
        COLOR_ACORN_STEM,
        COLOR_BANNER_BG,
        COLOR_BANNER_BORDER,
        COLOR_BOARD_DARK,
        COLOR_BOARD_HOLE,
        COLOR_BOARD_HOLE_RIM,
        COLOR_BOARD_LEG,
        COLOR_BOARD_LIGHT,
        COLOR_BOARD_WOOD,
        COLOR_CARROT_LEAF,
        COLOR_CARROT_LEAF_LIGHT,
        COLOR_FLASH_DARK,
        COLOR_FLASH_LIGHT,
        COLOR_FLASH_MAIN,
        COLOR_GOLD,
        COLOR_GRASS_TABLE,
        COLOR_HILL_DISTANT,
        COLOR_HILL_NEAR,
        COLOR_LEO_DARK,
        COLOR_LEO_LIGHT,
        COLOR_LEO_MAIN,
        COLOR_SKY_BOTTOM,
        COLOR_SKY_TOP,
        COLOR_TABLE_WOOD,
        COLOR_TABLE_WOOD_DARK,
        COLOR_TEXT_DARK,
        COLOR_TEXT_MUTED,
        COLOR_WIN_GLOW,
        LEVEL_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        GameMode,
        GameStatus,
        Player,
    )
    from quattro_model import QuattroModel


@dataclass
class DropAnimation:
    """State of an in-flight falling token with bounce physics."""
    col: int
    target_row: int
    player: Player
    current_y: float
    target_y: float
    velocity_y: float = 0.0
    bounce_timer: float = 0.0
    settled: bool = False
    landed: bool = False
    _landing_pending: bool = False

    BOUNCE_SECONDS = 0.15

    def update(self, dt: float) -> bool:
        """Update animation by delta-time. Return True when settled.

        Two explicit phases: falling, then a short landing bounce. The bounce
        must never push the token back into the falling phase (it sits above
        the target), so the phase is tracked by ``landed`` rather than by
        comparing ``current_y`` with ``target_y``.
        """
        if self.settled:
            return True

        if not self.landed:
            # Gravity acceleration
            self.velocity_y += 1800.0 * dt
            self.current_y += self.velocity_y * dt
            if self.current_y >= self.target_y:
                self.current_y = self.target_y
                self.landed = True
                self._landing_pending = True
                self.bounce_timer = self.BOUNCE_SECONDS
            return False

        self.bounce_timer -= dt
        if self.bounce_timer <= 0.0:
            self.bounce_timer = 0.0
            self.current_y = self.target_y
            self.settled = True
        else:
            bounce_offset = (
                math.sin(self.bounce_timer / self.BOUNCE_SECONDS * math.pi) * 8.0
            )
            self.current_y = self.target_y - bounce_offset
        return self.settled

    def consume_landing(self) -> bool:
        """Return True exactly once, on the frame the token first hits the row."""
        if self._landing_pending:
            self._landing_pending = False
            return True
        return False


@dataclass
class Particle:
    """Confetti / sparkle particle for winning celebrations."""
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: float
    life: float
    max_life: float


class QuattroRenderer:
    """Renders the Quattro Amici match scene onto a Pygame surface."""

    def __init__(
        self,
        surface: pygame.Surface,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.surface = surface
        self.typography = typography
        self.resources = resources

        # Cached backdrop for performance on low-resource machines
        self._backdrop: pygame.Surface | None = None
        self._disc_cache: dict[tuple[int, Player], pygame.Surface] = {}
        self.particles: list[Particle] = []

    def invalidate_cache(self) -> None:
        """Clear cached surfaces."""
        self._backdrop = None
        self._disc_cache.clear()

    def render(
        self,
        model: QuattroModel,
        selected_col: int,
        active_drop: DropAnimation | None,
        cpu_thinking: bool,
    ) -> None:
        """Render complete frame onto target surface."""
        now = time.monotonic()
        self._draw_backdrop()
        board_rect, cell_size, hole_r = self._compute_board_layout(model)

        # Mascot characters
        self._draw_mascots(now, model, cpu_thinking)

        # Slotted wooden board and tokens
        self._draw_board_and_tokens(
            model, board_rect, cell_size, hole_r, active_drop, selected_col, now
        )

        # Winning rainbow connector and victory particles
        if model.status == GameStatus.WON:
            self._draw_win_beam(model, board_rect, cell_size, now)
            self._update_and_draw_particles(board_rect, dt=1.0 / 60.0)

        # Turn indicator banner and UI controls
        self._draw_turn_banner(model, cpu_thinking)
        self._draw_ui_buttons(model)

    def get_column_at_x(self, model: QuattroModel, mouse_x: float) -> int | None:
        """Return the board column corresponding to physical/logical X coordinate."""
        board_rect, cell_size, _ = self._compute_board_layout(model)
        if not (board_rect.left <= mouse_x <= board_rect.right):
            return None
        col = int((mouse_x - board_rect.left) // cell_size)
        return max(0, min(model.board.cols - 1, col))

    def _compute_board_layout(
        self, model: QuattroModel
    ) -> tuple[pygame.Rect, float, float]:
        """Compute pixel bounds of the board according to current grid size."""
        cols = model.board.cols
        rows = model.board.rows

        # Choose cell size based on grid dimensions to fit neatly
        if cols <= 5:
            cell_size = 76.0
        elif cols == 6:
            cell_size = 68.0
        else:
            cell_size = 64.0

        grid_w = cols * cell_size
        grid_h = rows * cell_size

        board_left = (REFERENCE_WIDTH - grid_w) / 2.0
        board_top = 135.0 + (384.0 - grid_h) / 2.0

        board_rect = pygame.Rect(
            int(board_left), int(board_top), int(grid_w), int(grid_h)
        )
        hole_radius = cell_size * 0.40
        return board_rect, cell_size, hole_radius

    def _draw_backdrop(self) -> None:
        """Draw sunny meadow backdrop (cached for Atom performance)."""
        if self._backdrop is None:
            self._backdrop = pygame.Surface(
                (REFERENCE_WIDTH, REFERENCE_HEIGHT)
            ).convert()
            # Sky vertical gradient
            for y in range(400):
                r = y / 400.0
                cr = int(COLOR_SKY_TOP[0] * (1.0 - r) + COLOR_SKY_BOTTOM[0] * r)
                cg = int(COLOR_SKY_TOP[1] * (1.0 - r) + COLOR_SKY_BOTTOM[1] * r)
                cb = int(COLOR_SKY_TOP[2] * (1.0 - r) + COLOR_SKY_BOTTOM[2] * r)
                pygame.draw.line(self._backdrop, (cr, cg, cb), (0, y), (REFERENCE_WIDTH, y))

            # Distant rolling hills
            pygame.draw.circle(self._backdrop, COLOR_HILL_DISTANT, (200, 480), 320)
            pygame.draw.circle(self._backdrop, COLOR_HILL_DISTANT, (820, 460), 300)

            # Near hills
            pygame.draw.circle(self._backdrop, COLOR_HILL_NEAR, (40, 520), 240)
            pygame.draw.circle(self._backdrop, COLOR_HILL_NEAR, (980, 500), 260)
            pygame.draw.circle(self._backdrop, COLOR_HILL_NEAR, (512, 580), 360)

            # Grass tabletop surface
            table_y = 480
            pygame.draw.rect(
                self._backdrop,
                COLOR_GRASS_TABLE,
                (0, table_y, REFERENCE_WIDTH, 24),
            )
            # Wooden table body
            pygame.draw.rect(
                self._backdrop,
                COLOR_TABLE_WOOD,
                (0, table_y + 24, REFERENCE_WIDTH, REFERENCE_HEIGHT - table_y - 24),
            )
            # Wood planks border line
            pygame.draw.line(
                self._backdrop,
                COLOR_TABLE_WOOD_DARK,
                (0, table_y + 24),
                (REFERENCE_WIDTH, table_y + 24),
                width=3,
            )
            for x in range(120, REFERENCE_WIDTH, 180):
                pygame.draw.line(
                    self._backdrop,
                    COLOR_TABLE_WOOD_DARK,
                    (x, table_y + 24),
                    (x, REFERENCE_HEIGHT),
                    width=2,
                )

        self.surface.blit(self._backdrop, (0, 0))

    def _draw_board_and_tokens(
        self,
        model: QuattroModel,
        board_rect: pygame.Rect,
        cell_size: float,
        hole_r: float,
        active_drop: DropAnimation | None,
        selected_col: int,
        now: float,
    ) -> None:
        """Render board wooden stand, apertures, and tokens."""
        # 1. Wooden Stand / Legs behind board
        leg_w = 40
        leg_h = 70
        foot_w = 90
        foot_h = 24
        # Left leg and foot
        pygame.draw.rect(
            self.surface,
            COLOR_BOARD_LEG,
            (board_rect.left - 24, board_rect.bottom - 40, leg_w, leg_h),
            border_radius=8,
        )
        pygame.draw.rect(
            self.surface,
            COLOR_BOARD_DARK,
            (board_rect.left - 45, board_rect.bottom + leg_h - 44, foot_w, foot_h),
            border_radius=10,
        )
        # Right leg and foot
        pygame.draw.rect(
            self.surface,
            COLOR_BOARD_LEG,
            (board_rect.right - 16, board_rect.bottom - 40, leg_w, leg_h),
            border_radius=8,
        )
        pygame.draw.rect(
            self.surface,
            COLOR_BOARD_DARK,
            (board_rect.right - 45, board_rect.bottom + leg_h - 44, foot_w, foot_h),
            border_radius=10,
        )

        # 2. Board Background Panel (behind holes)
        outer_pad = 18
        board_outer = pygame.Rect(
            board_rect.left - outer_pad,
            board_rect.top - outer_pad,
            board_rect.width + 2 * outer_pad,
            board_rect.height + 2 * outer_pad,
        )
        # Shadow
        pygame.draw.rect(
            self.surface,
            (40, 25, 10, 60),
            (board_outer.x, board_outer.y + 10, board_outer.width, board_outer.height),
            border_radius=28,
        )
        # Frame outer
        pygame.draw.rect(
            self.surface, COLOR_BOARD_DARK, board_outer, border_radius=26
        )
        pygame.draw.rect(
            self.surface,
            COLOR_BOARD_WOOD,
            (
                board_outer.x + 6,
                board_outer.y + 6,
                board_outer.width - 12,
                board_outer.height - 12,
            ),
            border_radius=22,
        )

        # 3. Draw stationary tokens inside slots
        disc_r = int(hole_r - 2)
        for r in range(model.board.rows):
            for c in range(model.board.cols):
                cx = int(board_rect.left + c * cell_size + cell_size / 2.0)
                cy = int(board_rect.top + r * cell_size + cell_size / 2.0)

                # Aperture depth slot
                pygame.draw.circle(self.surface, COLOR_BOARD_HOLE, (cx, cy), int(hole_r))

                player = model.board.grid[r][c]
                # If this cell is currently the target of an in-flight active drop, skip until it lands
                if (
                    active_drop is not None
                    and not active_drop.settled
                    and active_drop.col == c
                    and active_drop.target_row == r
                ):
                    continue

                if player != Player.EMPTY:
                    disc = self._get_cached_disc(disc_r, player)
                    self.surface.blit(disc, (cx - disc_r, cy - disc_r))

        # 4. Draw active falling token
        if active_drop is not None and not active_drop.settled:
            cx = int(board_rect.left + active_drop.col * cell_size + cell_size / 2.0)
            cy = int(active_drop.current_y)
            disc = self._get_cached_disc(disc_r, active_drop.player)
            self.surface.blit(disc, (cx - disc_r, cy - disc_r))

        # 5. Wooden front bezel / aperture rims
        for r in range(model.board.rows):
            for c in range(model.board.cols):
                cx = int(board_rect.left + c * cell_size + cell_size / 2.0)
                cy = int(board_rect.top + r * cell_size + cell_size / 2.0)
                # Outer ring bevel
                pygame.draw.circle(
                    self.surface, COLOR_BOARD_HOLE_RIM, (cx, cy), int(hole_r) + 2, width=3
                )

        # 6. Floating column selector & indicator arrow above board
        if (
            model.status == GameStatus.IN_PROGRESS
            and 0 <= selected_col < model.board.cols
            and active_drop is None
        ):
            sel_cx = int(board_rect.left + selected_col * cell_size + cell_size / 2.0)
            bounce_y = int(math.sin(now * 5.0) * 5.0)
            sel_cy = int(board_rect.top - 24 + bounce_y)

            # Floating player disc
            disc = self._get_cached_disc(int(disc_r * 0.75), model.current_player)
            self.surface.blit(disc, (sel_cx - disc.get_width() // 2, sel_cy - disc.get_height() // 2))

            # Downward indicator arrow
            arrow_pts = [
                (sel_cx - 9, sel_cy + 18),
                (sel_cx + 9, sel_cy + 18),
                (sel_cx, sel_cy + 27),
            ]
            arrow_col = COLOR_FLASH_MAIN if model.current_player == Player.FLASH else COLOR_LEO_MAIN
            pygame.draw.polygon(self.surface, arrow_col, arrow_pts)
            pygame.draw.polygon(self.surface, COLOR_BOARD_DARK, arrow_pts, width=2)

    def _get_cached_disc(self, radius: int, player: Player) -> pygame.Surface:
        """Retrieve or create an embossed wooden disc sprite."""
        key = (radius, player)
        if key in self._disc_cache:
            return self._disc_cache[key]

        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (radius, radius)

        if player == Player.FLASH:
            # Carrot Disc (Bright Orange)
            pygame.draw.circle(surf, COLOR_FLASH_DARK, (radius, radius + 2), radius - 1)
            pygame.draw.circle(surf, COLOR_FLASH_MAIN, center, radius - 2)
            pygame.draw.circle(surf, COLOR_FLASH_LIGHT, center, radius - 4, width=2)

            # Embossed Carrot Body
            cw = radius * 0.45
            ch = radius * 0.65
            carrot_pts = [
                (radius, radius + int(ch * 0.55)),
                (radius - int(cw * 0.5), radius - int(ch * 0.2)),
                (radius + int(cw * 0.5), radius - int(ch * 0.2)),
            ]
            pygame.draw.polygon(surf, COLOR_FLASH_DARK, carrot_pts)
            pygame.draw.polygon(surf, (255, 140, 40), carrot_pts, width=1)

            # Carrot Green Top
            pygame.draw.ellipse(
                surf,
                COLOR_CARROT_LEAF,
                (radius - 6, radius - int(ch * 0.5), 12, int(ch * 0.4)),
            )
            pygame.draw.ellipse(
                surf,
                COLOR_CARROT_LEAF_LIGHT,
                (radius - 12, radius - int(ch * 0.45), 10, int(ch * 0.35)),
            )
            pygame.draw.ellipse(
                surf,
                COLOR_CARROT_LEAF_LIGHT,
                (radius + 2, radius - int(ch * 0.45), 10, int(ch * 0.35)),
            )

        elif player == Player.LEO:
            # Acorn Disc (Vibrant Purple)
            pygame.draw.circle(surf, COLOR_LEO_DARK, (radius, radius + 2), radius - 1)
            pygame.draw.circle(surf, COLOR_LEO_MAIN, center, radius - 2)
            pygame.draw.circle(surf, COLOR_LEO_LIGHT, center, radius - 4, width=2)

            # Embossed Acorn Body
            aw = radius * 0.45
            ah = radius * 0.55
            # Nut bottom
            pygame.draw.ellipse(
                surf,
                COLOR_LEO_DARK,
                (radius - int(aw * 0.5), radius - int(ah * 0.1), int(aw), int(ah * 0.7)),
            )
            # Acorn Cap
            pygame.draw.ellipse(
                surf,
                COLOR_ACORN_CAP,
                (radius - int(aw * 0.55), radius - int(ah * 0.35), int(aw * 1.1), int(ah * 0.45)),
            )
            # Acorn Stem
            pygame.draw.rect(
                surf,
                COLOR_ACORN_STEM,
                (radius - 2, radius - int(ah * 0.55), 4, int(ah * 0.25)),
                border_radius=2,
            )

        self._disc_cache[key] = surf
        return surf

    def _draw_mascots(self, now: float, model: QuattroModel, cpu_thinking: bool) -> None:
        """Render animated Flash (left) and Leo (right) portraits."""
        # 1. Flash (Rabbit - Left)
        fx = 120
        fy = 390
        flash_bounce = math.sin(now * 3.0) * 4.0 if model.current_player == Player.FLASH else 0.0
        if model.status == GameStatus.WON and model.winner == Player.FLASH:
            flash_bounce = abs(math.sin(now * 8.0)) * 18.0

        self._draw_flash_portrait(fx, int(fy - flash_bounce), model)

        # 2. Leo (Owl - Right)
        lx = REFERENCE_WIDTH - 120
        ly = 390
        leo_bounce = math.sin(now * 3.0) * 4.0 if model.current_player == Player.LEO else 0.0
        if model.status == GameStatus.WON and model.winner == Player.LEO:
            leo_bounce = abs(math.sin(now * 8.0)) * 18.0

        self._draw_leo_portrait(lx, int(ly - leo_bounce), model, cpu_thinking, now)

    def _draw_flash_portrait(self, cx: int, cy: int, model: QuattroModel) -> None:
        """Render Flash the Rabbit with cute ears and carrot disc badge."""
        # Soft shadow
        pygame.draw.circle(self.surface, (30, 20, 10, 45), (cx, cy + 50), 38)

        # Long Rabbit Ears
        ear_h = 56
        # Left ear
        pygame.draw.ellipse(self.surface, (250, 245, 240), (cx - 28, cy - 80, 22, ear_h))
        pygame.draw.ellipse(self.surface, (255, 185, 200), (cx - 24, cy - 72, 14, ear_h - 14))
        # Right ear
        pygame.draw.ellipse(self.surface, (250, 245, 240), (cx + 6, cy - 80, 22, ear_h))
        pygame.draw.ellipse(self.surface, (255, 185, 200), (cx + 10, cy - 72, 14, ear_h - 14))

        # Head
        pygame.draw.circle(self.surface, (252, 250, 245), (cx, cy), 44)
        pygame.draw.circle(self.surface, (230, 220, 210), (cx, cy), 44, width=3)

        # Pink cheeks
        pygame.draw.circle(self.surface, (255, 190, 200), (cx - 24, cy + 8), 10)
        pygame.draw.circle(self.surface, (255, 190, 200), (cx + 24, cy + 8), 10)

        # Big sparkling eyes
        pygame.draw.circle(self.surface, (40, 30, 25), (cx - 15, cy - 6), 7)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx - 17, cy - 8), 3)
        pygame.draw.circle(self.surface, (40, 30, 25), (cx + 15, cy - 6), 7)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx + 13, cy - 8), 3)

        # Pink nose and smile
        pygame.draw.polygon(self.surface, (255, 130, 160), [(cx, cy + 6), (cx - 5, cy + 1), (cx + 5, cy + 1)])
        pygame.draw.arc(self.surface, (60, 45, 35), (cx - 12, cy + 6, 12, 10), math.pi, 2 * math.pi, width=2)
        pygame.draw.arc(self.surface, (60, 45, 35), (cx, cy + 6, 12, 10), math.pi, 2 * math.pi, width=2)

        # Name label badge below
        badge_rect = pygame.Rect(cx - 48, cy + 54, 96, 26)
        pygame.draw.rect(self.surface, (255, 250, 240), badge_rect, border_radius=12)
        border_col = COLOR_FLASH_MAIN if model.current_player == Player.FLASH else (180, 150, 130)
        pygame.draw.rect(self.surface, border_col, badge_rect, width=3, border_radius=12)
        lbl = self.typography.render("FLASH", FontRole.CONTROL, 16, COLOR_TEXT_DARK)
        self.surface.blit(lbl, (cx - lbl.get_width() // 2, cy + 58))

    def _draw_leo_portrait(
        self, cx: int, cy: int, model: QuattroModel, cpu_thinking: bool, now: float
    ) -> None:
        """Render Leo the Owl with tufts, big spectacles, and thinking wing."""
        # Shadow
        pygame.draw.circle(self.surface, (30, 20, 10, 45), (cx, cy + 50), 38)

        # Feather ear tufts
        pygame.draw.polygon(self.surface, (140, 95, 165), [(cx - 36, cy - 42), (cx - 24, cy - 20), (cx - 42, cy - 20)])
        pygame.draw.polygon(self.surface, (140, 95, 165), [(cx + 36, cy - 42), (cx + 24, cy - 20), (cx + 42, cy - 20)])

        # Owl Body / Head
        pygame.draw.circle(self.surface, (155, 110, 185), (cx, cy), 44)
        pygame.draw.circle(self.surface, (115, 75, 140), (cx, cy), 44, width=3)

        # Belly patch
        pygame.draw.ellipse(self.surface, (245, 240, 252), (cx - 22, cy + 6, 44, 34))

        # Golden Spectacles / Eyes
        spec_r = 15
        pygame.draw.circle(self.surface, (255, 255, 255), (cx - 16, cy - 6), spec_r)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx + 16, cy - 6), spec_r)
        # Spectacle golden frames
        pygame.draw.circle(self.surface, COLOR_GOLD, (cx - 16, cy - 6), spec_r + 2, width=3)
        pygame.draw.circle(self.surface, COLOR_GOLD, (cx + 16, cy - 6), spec_r + 2, width=3)
        pygame.draw.line(self.surface, COLOR_GOLD, (cx - 1, cy - 6), (cx + 1, cy - 6), width=3)

        # Pupils (looking slightly up/thinking when calculating)
        pupil_y = cy - 9 if cpu_thinking else cy - 6
        pygame.draw.circle(self.surface, (35, 25, 45), (cx - 16, pupil_y), 7)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx - 18, pupil_y - 2), 3)
        pygame.draw.circle(self.surface, (35, 25, 45), (cx + 16, pupil_y), 7)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx + 14, pupil_y - 2), 3)

        # Beak
        pygame.draw.polygon(self.surface, (255, 160, 30), [(cx, cy + 9), (cx - 6, cy + 2), (cx + 6, cy + 2)])

        # Thinking wing scratch chin
        if cpu_thinking:
            wing_bounce = math.sin(now * 12.0) * 4.0
            pygame.draw.ellipse(
                self.surface,
                (130, 85, 155),
                (cx - 30, int(cy + 4 + wing_bounce), 22, 14),
            )

        # Name label badge below
        badge_rect = pygame.Rect(cx - 48, cy + 54, 96, 26)
        pygame.draw.rect(self.surface, (255, 250, 240), badge_rect, border_radius=12)
        border_col = COLOR_LEO_MAIN if model.current_player == Player.LEO else (180, 150, 130)
        pygame.draw.rect(self.surface, border_col, badge_rect, width=3, border_radius=12)
        lbl = self.typography.render("LEO", FontRole.CONTROL, 16, COLOR_TEXT_DARK)
        self.surface.blit(lbl, (cx - lbl.get_width() // 2, cy + 58))

    def _draw_turn_banner(self, model: QuattroModel, cpu_thinking: bool) -> None:
        """Render top turn-indicator or victory announcement banner."""
        banner_w = 420
        banner_h = 56
        bx = (REFERENCE_WIDTH - banner_w) // 2
        by = 22

        banner_rect = pygame.Rect(bx, by, banner_w, banner_h)
        # Banner background with rounded pill shape
        pygame.draw.rect(self.surface, COLOR_BANNER_BG, banner_rect, border_radius=28)

        if model.status == GameStatus.WON:
            border_col = COLOR_FLASH_MAIN if model.winner == Player.FLASH else COLOR_LEO_MAIN
            text_key = "ui.win_flash" if model.winner == Player.FLASH else "ui.win_leo"
            disc_player = model.winner
        elif model.status == GameStatus.DRAW:
            border_col = COLOR_BANNER_BORDER
            text_key = "ui.draw"
            disc_player = None
        elif cpu_thinking and model.mode == GameMode.VS_CPU:
            border_col = COLOR_LEO_MAIN
            text_key = "ui.leo_thinking"
            disc_player = Player.LEO
        else:
            border_col = COLOR_FLASH_MAIN if model.current_player == Player.FLASH else COLOR_LEO_MAIN
            text_key = "ui.turn_flash" if model.current_player == Player.FLASH else "ui.turn_leo"
            disc_player = model.current_player

        pygame.draw.rect(self.surface, border_col, banner_rect, width=4, border_radius=28)

        # Disc badge inside banner
        text_str = self.resources.text(text_key)
        rendered_text = self.typography.render(
            text_str, FontRole.DISPLAY, 22, COLOR_TEXT_DARK
        )

        if disc_player is not None:
            disc = self._get_cached_disc(18, disc_player)
            total_content_w = disc.get_width() + 12 + rendered_text.get_width()
            start_x = bx + (banner_w - total_content_w) // 2
            self.surface.blit(disc, (start_x, by + (banner_h - disc.get_height()) // 2))
            self.surface.blit(
                rendered_text,
                (start_x + disc.get_width() + 12, by + (banner_h - rendered_text.get_height()) // 2),
            )
        else:
            self.surface.blit(
                rendered_text,
                (bx + (banner_w - rendered_text.get_width()) // 2, by + (banner_h - rendered_text.get_height()) // 2),
            )

    def _draw_ui_buttons(self, model: QuattroModel) -> None:
        """Render level selector buttons, mode toggle, and play again button."""
        # Top-right Level buttons: 1, 2, 3, 4
        btn_y = 26
        btn_w = 42
        btn_h = 42

        # 4 level buttons arranged near top-right
        for diff in (1, 2, 3, 4):
            btn_x = 730 + (diff - 1) * 50
            rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            is_active = (model.difficulty == diff)
            bg_col = COLOR_GOLD if is_active else (255, 250, 240)
            pygame.draw.rect(self.surface, bg_col, rect, border_radius=12)
            border_col = (140, 95, 45) if is_active else (190, 160, 130)
            pygame.draw.rect(self.surface, border_col, rect, width=3 if is_active else 2, border_radius=12)

            num_str = str(diff)
            lbl = self.typography.render(num_str, FontRole.TITLE, 20, COLOR_TEXT_DARK)
            self.surface.blit(lbl, (btn_x + (btn_w - lbl.get_width()) // 2, btn_y + (btn_h - lbl.get_height()) // 2))

        # Mode toggle button (top-right next to level buttons)
        mode_x = 936
        mode_rect = pygame.Rect(mode_x, btn_y, 74, btn_h)
        pygame.draw.rect(self.surface, (255, 250, 240), mode_rect, border_radius=12)
        pygame.draw.rect(self.surface, (180, 140, 100), mode_rect, width=2, border_radius=12)
        # Pictogram, not "1P"/"2P": one player disc (against Leo) or two
        # player discs (two friends), using the same cached discs as the board.
        players = (Player.FLASH,) if model.mode == GameMode.VS_CPU else (Player.FLASH, Player.LEO)
        discs = [self._get_cached_disc(14, player) for player in players]
        gap = 8
        total_w = sum(d.get_width() for d in discs) + gap * (len(discs) - 1)
        dx = mode_x + (74 - total_w) // 2
        for disc in discs:
            self.surface.blit(disc, (dx, btn_y + (btn_h - disc.get_height()) // 2))
            dx += disc.get_width() + gap

        # Bottom "Play Again" button when game is over
        if model.status != GameStatus.IN_PROGRESS:
            play_again_w = 220
            play_again_h = 50
            px = (REFERENCE_WIDTH - play_again_w) // 2
            py = 535
            pa_rect = pygame.Rect(px, py, play_again_w, play_again_h)
            pygame.draw.rect(self.surface, COLOR_GOLD, pa_rect, border_radius=25)
            pygame.draw.rect(self.surface, (160, 110, 20), pa_rect, width=3, border_radius=25)

            pa_str = self.resources.text("ui.play_again")
            pa_lbl = self.typography.render(pa_str, FontRole.TITLE, 20, COLOR_TEXT_DARK)
            self.surface.blit(pa_lbl, (px + (play_again_w - pa_lbl.get_width()) // 2, py + (play_again_h - pa_lbl.get_height()) // 2))

    def _draw_win_beam(
        self,
        model: QuattroModel,
        board_rect: pygame.Rect,
        cell_size: float,
        now: float,
    ) -> None:
        """Render a pulsating glowing rainbow beam connecting winning tokens."""
        if not model.winning_cells:
            return

        points: list[tuple[int, int]] = []
        for r, c in model.winning_cells:
            cx = int(board_rect.left + c * cell_size + cell_size / 2.0)
            cy = int(board_rect.top + r * cell_size + cell_size / 2.0)
            points.append((cx, cy))

        if len(points) >= 2:
            # Pulsating glow
            glow_w = int(12 + math.sin(now * 10.0) * 4.0)
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                # Rainbow outer line
                pygame.draw.line(self.surface, COLOR_WIN_GLOW, p1, p2, width=glow_w)
                pygame.draw.line(self.surface, COLOR_GOLD, p1, p2, width=6)
                pygame.draw.line(self.surface, (255, 255, 255), p1, p2, width=2)

        # Golden sparkle around each winning cell
        for px, py in points:
            sparkle_r = int(cell_size * 0.45 + math.sin(now * 8.0) * 4.0)
            pygame.draw.circle(self.surface, COLOR_WIN_GLOW, (px, py), sparkle_r, width=4)

    def spawn_win_particles(self, board_rect: pygame.Rect) -> None:
        """Spawn celebration confetti and stars."""
        import random
        colors = [
            COLOR_FLASH_MAIN,
            COLOR_LEO_MAIN,
            COLOR_GOLD,
            (255, 105, 180),
            (0, 225, 255),
            (76, 217, 100),
        ]
        rng = random.Random()
        for _ in range(35):
            self.particles.append(
                Particle(
                    x=board_rect.centerx + rng.uniform(-180, 180),
                    y=board_rect.centery + rng.uniform(-100, 100),
                    vx=rng.uniform(-120, 120),
                    vy=rng.uniform(-280, -80),
                    color=rng.choice(colors),
                    size=rng.uniform(6, 12),
                    life=rng.uniform(1.2, 2.5),
                    max_life=2.5,
                )
            )

    def _update_and_draw_particles(self, board_rect: pygame.Rect, dt: float) -> None:
        """Update and render falling celebration confetti."""
        surviving: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += 320.0 * dt  # Gravity
                pygame.draw.circle(
                    self.surface, p.color, (int(p.x), int(p.y)), int(p.size)
                )
                surviving.append(p)
        self.particles = surviving
