from __future__ import annotations

"""High-contrast storybook renderer for La Torre delle Forme.

Draws the cozy wooden tower frame, tactile wooden toy blocks with beveled
highlights and friendly face/star engravings, Lilli the builder cat with her
yellow hardhat, on-screen chunky buttons, particle sparkles, and celebration
overlay. Strictly respects the top-left system chrome clearance.
"""

from dataclasses import dataclass
import math
import random
from typing import Any
import pygame

from greia_platform.child_text import display_text
from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .torre_content import (
        CELL_SIZE,
        COLOR_ARCH,
        COLOR_BACKGROUND,
        COLOR_BAR_2,
        COLOR_BAR_3,
        COLOR_CELL_BG,
        COLOR_CELL_GRID,
        COLOR_CORNER_L,
        COLOR_FRAME_INNER,
        COLOR_FRAME_OUTER,
        COLOR_PANEL_BG,
        COLOR_PANEL_BORDER,
        COLOR_RAINBOW,
        COLOR_ROOF,
        COLOR_SQUARE,
        GRID_COLS,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TOWER_HEIGHT,
        TOWER_WIDTH,
        TOWER_X,
        TOWER_Y,
        ShapeDefinition,
        TowerMode,
    )
    from .torre_model import TorreModel
else:
    from torre_content import (
        CELL_SIZE,
        COLOR_ARCH,
        COLOR_BACKGROUND,
        COLOR_BAR_2,
        COLOR_BAR_3,
        COLOR_CELL_BG,
        COLOR_CELL_GRID,
        COLOR_CORNER_L,
        COLOR_FRAME_INNER,
        COLOR_FRAME_OUTER,
        COLOR_PANEL_BG,
        COLOR_PANEL_BORDER,
        COLOR_RAINBOW,
        COLOR_ROOF,
        COLOR_SQUARE,
        GRID_COLS,
        GRID_ROWS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        TOWER_HEIGHT,
        TOWER_WIDTH,
        TOWER_X,
        TOWER_Y,
        ShapeDefinition,
        TowerMode,
    )
    from torre_model import TorreModel


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: float
    life: float
    max_life: float


def _draw_symbol(
    surface: pygame.Surface,
    kind: str,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a language-neutral control pictogram as shapes.

    The Greia text font has no arrow glyphs, so characters such as the
    triangles/rotation arrow would render as missing-glyph boxes.
    """
    cx, cy = center
    r = size // 2
    if kind == "left":
        pts = [(cx - r, cy), (cx + r // 2 + 2, cy - r), (cx + r // 2 + 2, cy + r)]
    elif kind == "right":
        pts = [(cx + r, cy), (cx - r // 2 - 2, cy - r), (cx - r // 2 - 2, cy + r)]
    elif kind == "down":
        pts = [(cx, cy + r), (cx - r, cy - r // 2 - 2), (cx + r, cy - r // 2 - 2)]
    elif kind == "rotate":
        box = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
        pygame.draw.arc(surface, color, box, math.radians(40), math.radians(320), 5)
        hx = cx + int(r * math.cos(math.radians(40)))
        hy = cy - int(r * math.sin(math.radians(40)))
        pygame.draw.polygon(surface, color, [(hx + 8, hy - 5), (hx - 9, hy - 10), (hx + 1, hy + 11)])
        return
    else:
        return
    pygame.draw.polygon(surface, color, pts)


class TorreRenderer:
    """Storybook wooden toy graphics renderer for Torre delle Forme."""

    def __init__(
        self,
        typography: GreiaTypography,
        resources: LocalizedResources | None = None,
    ) -> None:
        self.typography = typography
        self.resources = resources
        self._strings: dict[tuple[str, tuple[tuple[str, object], ...]], str] = {}
        self._text_surfaces: dict[tuple, pygame.Surface] = {}
        self.particles: list[Particle] = []

        # Interactive UI Rectangles
        # Mode buttons (top right, safe from top-left chrome)
        self.mode_free_rect = pygame.Rect(600, 16, 126, 48)
        self.mode_slow_rect = pygame.Rect(734, 16, 126, 48)
        self.mode_chal_rect = pygame.Rect(868, 16, 136, 48)

        # Mode 1 Free Build Shelf & Buttons
        self.shelf_rects = [
            pygame.Rect(640, 200, 100, 100),
            pygame.Rect(760, 200, 100, 100),
            pygame.Rect(880, 200, 100, 100),
        ]
        self.new_shapes_rect = pygame.Rect(720, 320, 180, 52)

        # Modes 2 & 3 Steering Buttons (Large touch targets >= 78px)
        self.rotate_button_rect = pygame.Rect(770, 350, 84, 84)
        self.left_button_rect = pygame.Rect(660, 460, 84, 84)
        self.down_button_rect = pygame.Rect(770, 460, 84, 84)
        self.right_button_rect = pygame.Rect(880, 460, 84, 84)

        # Celebration Replay Button
        self.replay_button_rect = pygame.Rect(370, 420, 284, 76)

    def _t(self, key: str, **variables: object) -> str:
        """Resolve one localized UI string once per distinct (key, values).

        ``LocalizedResources.text`` already applies the child letter-case
        policy. A missing resource renders nothing; there is deliberately no
        fixed-language fallback sentence.
        """
        if self.resources is None:
            return ""
        cache_key = (key, tuple(sorted(variables.items())))
        cached = self._strings.get(cache_key)
        if cached is None:
            try:
                cached = self.resources.text(key, variables or None)
            except Exception:
                cached = ""
            if len(self._strings) >= 64:
                self._strings.clear()
            self._strings[cache_key] = cached
        return cached

    def _render_text(
        self,
        text: str,
        size: int,
        color: tuple[int, int, int],
        role: FontRole = FontRole.BODY,
        max_width: int | None = None,
    ) -> pygame.Surface:
        """Render one cached line, shrunk (to a floor) to fit ``max_width``."""
        key = (text, size, color, role, max_width)
        cached = self._text_surfaces.get(key)
        if cached is None:
            fitted = size
            if max_width is not None:
                while fitted > 10 and self.typography.measure(text, role, fitted).width > max_width:
                    fitted -= 1
            if len(self._text_surfaces) >= 128:
                self._text_surfaces.clear()
            cached = self.typography.render(text, role, fitted, color)
            self._text_surfaces[key] = cached
        return cached

    def spawn_particles(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 8,
        vx_range: tuple[float, float] = (-3.0, 3.0),
        vy_range: tuple[float, float] = (-4.0, -1.0),
        size_range: tuple[float, float] = (4.0, 8.0),
        life: float = 0.8,
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=random.uniform(*vx_range),
                    vy=random.uniform(*vy_range),
                    color=color,
                    size=random.uniform(*size_range),
                    life=life,
                    max_life=life,
                )
            )

    def update_particles(self, dt: float = 0.033) -> None:
        remaining: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 4.0 * dt  # Gentle gravity
            p.life -= dt
            if p.life > 0:
                remaining.append(p)
        self.particles = remaining[:60]

    def draw(
        self,
        surface: pygame.Surface,
        model: TorreModel,
        elapsed: float,
        now: float,
    ) -> None:
        # 1. Warm workshop background
        self._draw_background(surface)

        # 2. Wooden Tower Frame and Grid
        self._draw_tower_frame(surface, model, now)

        # 3. Lilli the builder cat on the left
        self._draw_lilli(surface, model, now)

        # 4. Right side UI (Mode tabs, meters, controls)
        self._draw_controls_and_meters(surface, model, now)

        # 5. Particles
        self._draw_particles(surface)

        # 6. Celebration modal if active
        if model.is_celebrating:
            self._draw_celebration(surface, model, now)

    def _draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BACKGROUND)

        # Wooden workshop floor at bottom
        floor_rect = pygame.Rect(0, 544, REFERENCE_WIDTH, 56)
        pygame.draw.rect(surface, (168, 120, 80), floor_rect)
        pygame.draw.line(surface, (110, 68, 38), (0, 544), (REFERENCE_WIDTH, 544), 3)

        # Floor plank lines and nail pegs
        for x in range(120, REFERENCE_WIDTH, 140):
            pygame.draw.line(surface, (140, 95, 60), (x, 544), (x, 600), 2)
            pygame.draw.circle(surface, (90, 55, 30), (x - 6, 554), 2)
            pygame.draw.circle(surface, (90, 55, 30), (x + 6, 554), 2)

        # Subtle decorative wall bunting / garlands at top (between x=220 and 590)
        bunting_y = 36
        for bx in range(230, 560, 55):
            color = random.choice([COLOR_SQUARE, COLOR_BAR_2, COLOR_ROOF, COLOR_ARCH])
            # Hanging mini wooden triangle pennants
            pts = [(bx, bunting_y), (bx + 35, bunting_y), (bx + 18, bunting_y + 22)]
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (120, 80, 45), pts, 2)
        pygame.draw.line(surface, (120, 80, 45), (220, bunting_y), (580, bunting_y), 2)

    def _draw_tower_frame(
        self, surface: pygame.Surface, model: TorreModel, now: float
    ) -> None:
        # Outer wooden beams
        frame_rect = pygame.Rect(
            TOWER_X - 10, TOWER_Y - 10, TOWER_WIDTH + 20, TOWER_HEIGHT + 20
        )
        # Drop shadow
        pygame.draw.rect(
            surface, (0, 0, 0, 45), frame_rect.move(4, 5), border_radius=14
        )
        # Outer dark wood
        pygame.draw.rect(surface, COLOR_FRAME_OUTER, frame_rect, border_radius=14)
        # Inner warm wood border
        inner_beam = pygame.Rect(
            TOWER_X - 4, TOWER_Y - 4, TOWER_WIDTH + 8, TOWER_HEIGHT + 8
        )
        pygame.draw.rect(surface, COLOR_FRAME_INNER, inner_beam, border_radius=10)

        # Grid background
        grid_rect = pygame.Rect(TOWER_X, TOWER_Y, TOWER_WIDTH, TOWER_HEIGHT)
        pygame.draw.rect(surface, COLOR_CELL_BG, grid_rect, border_radius=6)

        # Subtle grid lines
        for c in range(1, GRID_COLS):
            x = TOWER_X + c * CELL_SIZE
            pygame.draw.line(surface, COLOR_CELL_GRID, (x, TOWER_Y), (x, TOWER_Y + TOWER_HEIGHT), 1)
        for r in range(1, GRID_ROWS):
            y = TOWER_Y + r * CELL_SIZE
            pygame.draw.line(surface, COLOR_CELL_GRID, (TOWER_X, y), (TOWER_X + TOWER_WIDTH, y), 1)

        # Height milestone markers on the left of the tower frame
        milestones = [3, 6, 8, 10]
        for row_h in milestones:
            # row 10 is at y = TOWER_Y (top), row 1 is at y = TOWER_Y + 9*CELL_SIZE
            marker_y = TOWER_Y + (GRID_ROWS - row_h) * CELL_SIZE + CELL_SIZE // 2
            # Little wooden flag tab
            flag_rect = pygame.Rect(TOWER_X - 32, marker_y - 10, 24, 20)
            pygame.draw.rect(surface, (217, 119, 6), flag_rect, border_radius=4)
            label = self._render_text(str(row_h), 14, (255, 255, 255), FontRole.TITLE)
            surface.blit(label, label.get_rect(center=flag_rect.center))

        # Mode 1: Draw Blueprint ghost sockets
        if model.mode == TowerMode.FREE_BUILD:
            for bp in model.blueprints:
                if not bp.is_filled:
                    self._draw_blueprint_socket(surface, bp, now)

        # Draw placed blocks in grid
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = model.grid[r][c]
                if cell is not None:
                    bx = TOWER_X + c * CELL_SIZE + 2
                    by = TOWER_Y + r * CELL_SIZE + 2
                    bw = CELL_SIZE - 4
                    bh = CELL_SIZE - 4
                    self._draw_block(surface, bx, by, bw, bh, cell.color, cell.shape_id, cell.is_rainbow, now)

        # Draw Ghost Landing Preview in falling modes
        if model.mode != TowerMode.FREE_BUILD and model.active_shape is not None and not model.is_celebrating:
            ghost_row = model.active_row
            while model._is_valid_position(model.active_col, ghost_row + 1, model.active_blocks):
                ghost_row += 1
            if ghost_row != model.active_row:
                for dx, dy in model.active_blocks:
                    gx = TOWER_X + (model.active_col + dx) * CELL_SIZE + 2
                    gy = TOWER_Y + (ghost_row + dy) * CELL_SIZE + 2
                    gw = CELL_SIZE - 4
                    gh = CELL_SIZE - 4
                    # Translucent dashed outline
                    ghost_rect = pygame.Rect(gx, gy, gw, gh)
                    pygame.draw.rect(surface, (200, 180, 160), ghost_rect, width=2, border_radius=8)

        # Draw Active falling piece
        if model.active_shape is not None and not model.is_celebrating:
            for dx, dy in model.active_blocks:
                bx = TOWER_X + (model.active_col + dx) * CELL_SIZE + 2
                by = TOWER_Y + (model.active_row + dy) * CELL_SIZE + 2
                bw = CELL_SIZE - 4
                bh = CELL_SIZE - 4
                self._draw_block(
                    surface,
                    bx,
                    by,
                    bw,
                    bh,
                    model.active_shape.color,
                    model.active_shape.shape_id,
                    model.active_shape.is_rainbow,
                    now,
                )

    def _draw_block(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        color: tuple[int, int, int],
        shape_id: str,
        is_rainbow: bool,
        now: float,
    ) -> None:
        block_rect = pygame.Rect(x, y, w, h)
        radius = 8

        # Rainbow color cycling if star
        if is_rainbow:
            hue = (now * 2.0) % 1.0
            # Simple vibrant rainbow cycle
            r = int(127 * (1 + math.sin(hue * 2 * math.pi)))
            g = int(127 * (1 + math.sin(hue * 2 * math.pi + 2.094)))
            b = int(127 * (1 + math.sin(hue * 2 * math.pi + 4.188)))
            color = (max(80, r), max(80, g), max(80, b))

        # Block drop shadow inside cell
        pygame.draw.rect(surface, (0, 0, 0, 30), block_rect.move(1, 2), border_radius=radius)

        # Main block body
        pygame.draw.rect(surface, color, block_rect, border_radius=radius)

        # Beveled top highlight (warm 3D wooden toy block feel)
        hl_rect = pygame.Rect(x + 2, y + 2, w - 4, max(4, h // 3))
        hl_color = (
            min(255, color[0] + 45),
            min(255, color[1] + 45),
            min(255, color[2] + 45),
        )
        pygame.draw.rect(surface, hl_color, hl_rect, border_radius=max(2, radius - 2))

        # Bottom shade
        sh_rect = pygame.Rect(x + 2, y + h - 6, w - 4, 4)
        sh_color = (
            max(0, color[0] - 40),
            max(0, color[1] - 40),
            max(0, color[2] - 40),
        )
        pygame.draw.rect(surface, sh_color, sh_rect, border_radius=2)

        # Outer border
        border_col = (
            max(0, color[0] - 60),
            max(0, color[1] - 60),
            max(0, color[2] - 60),
        )
        pygame.draw.rect(surface, border_col, block_rect, width=2, border_radius=radius)

        # Friendly engraved decoration
        cx, cy = block_rect.center
        if is_rainbow:
            # Golden sparkling star
            pts = []
            for i in range(10):
                sr = 10 if i % 2 == 0 else 5
                ang = i * math.pi / 5 - math.pi / 2
                pts.append((cx + sr * math.cos(ang), cy + sr * math.sin(ang)))
            pygame.draw.polygon(surface, (255, 255, 255), pts)
            pygame.draw.polygon(surface, (217, 119, 6), pts, 1)
        elif shape_id == "square":
            # Friendly smiling eyes
            pygame.draw.circle(surface, (60, 40, 20), (cx - 6, cy - 2), 2)
            pygame.draw.circle(surface, (60, 40, 20), (cx + 6, cy - 2), 2)
            pygame.draw.arc(surface, (60, 40, 20), pygame.Rect(cx - 5, cy - 2, 10, 6), 3.14, 0, 2)
        elif shape_id == "roof_wedge":
            # Little wooden roof ridge lines
            pygame.draw.line(surface, hl_color, (x + 6, y + h // 2), (x + w - 6, y + h // 2), 2)
        else:
            # Wooden peg center dot
            pygame.draw.circle(surface, border_col, (cx, cy), 3)

    def _draw_blueprint_socket(
        self, surface: pygame.Surface, bp: Any, now: float
    ) -> None:
        pulse = 0.5 + 0.5 * math.sin(now * 4.0)
        glow_alpha = int(90 + 40 * pulse)
        socket_col = (147, 197, 253, glow_alpha)

        for dx, dy in bp.blocks:
            c = bp.anchor_col + dx
            r = bp.anchor_row + dy
            bx = TOWER_X + c * CELL_SIZE + 2
            by = TOWER_Y + r * CELL_SIZE + 2
            bw = CELL_SIZE - 4
            bh = CELL_SIZE - 4
            rect = pygame.Rect(bx, by, bw, bh)
            # Dashed pattern / blueprint silhouette
            pygame.draw.rect(surface, (186, 230, 253), rect, border_radius=8)
            pygame.draw.rect(surface, (59, 130, 246), rect, width=2, border_radius=8)
            # Cross blueprint hatch
            pygame.draw.line(surface, (147, 197, 253), (bx + 6, by + 6), (bx + bw - 6, by + bh - 6), 1)

    def _draw_lilli(
        self, surface: pygame.Surface, model: TorreModel, now: float
    ) -> None:
        # Lilli stands at left: x=105, y=420 (top of head around 360, floor at 544)
        cat_cx = 105
        bob = math.sin(now * 3.0) * 3.0
        cat_cy = 430 + int(bob)

        # Cheering jump if celebrating
        if model.is_celebrating:
            cat_cy -= int(abs(math.sin(now * 6.0)) * 16.0)

        # Cat Body (cream)
        pygame.draw.ellipse(surface, (255, 248, 235), pygame.Rect(cat_cx - 32, cat_cy + 10, 64, 76))
        pygame.draw.ellipse(surface, (120, 85, 60), pygame.Rect(cat_cx - 32, cat_cy + 10, 64, 76), 3)

        # Cat Head
        pygame.draw.circle(surface, (255, 248, 235), (cat_cx, cat_cy), 36)
        pygame.draw.circle(surface, (120, 85, 60), (cat_cx, cat_cy), 36, 3)

        # Cat Ears (pointed with pink inner)
        # Left ear
        pygame.draw.polygon(
            surface,
            (255, 248, 235),
            [(cat_cx - 32, cat_cy - 12), (cat_cx - 20, cat_cy - 48), (cat_cx - 4, cat_cy - 26)],
        )
        pygame.draw.polygon(
            surface,
            (120, 85, 60),
            [(cat_cx - 32, cat_cy - 12), (cat_cx - 20, cat_cy - 48), (cat_cx - 4, cat_cy - 26)],
            3,
        )
        pygame.draw.polygon(
            surface,
            (244, 162, 178),
            [(cat_cx - 26, cat_cy - 14), (cat_cx - 20, cat_cy - 42), (cat_cx - 8, cat_cy - 26)],
        )

        # Right ear
        pygame.draw.polygon(
            surface,
            (255, 248, 235),
            [(cat_cx + 4, cat_cy - 26), (cat_cx + 20, cat_cy - 48), (cat_cx + 32, cat_cy - 12)],
        )
        pygame.draw.polygon(
            surface,
            (120, 85, 60),
            [(cat_cx + 4, cat_cy - 26), (cat_cx + 20, cat_cy - 48), (cat_cx + 32, cat_cy - 12)],
            3,
        )
        pygame.draw.polygon(
            surface,
            (244, 162, 178),
            [(cat_cx + 8, cat_cy - 26), (cat_cx + 20, cat_cy - 42), (cat_cx + 26, cat_cy - 14)],
        )

        # Yellow Builder Hardhat on Lilli's head!
        helmet_rect = pygame.Rect(cat_cx - 32, cat_cy - 44, 64, 30)
        pygame.draw.ellipse(surface, (250, 204, 21), helmet_rect)
        pygame.draw.ellipse(surface, (180, 83, 9), helmet_rect, 3)
        # Helmet brim
        brim_rect = pygame.Rect(cat_cx - 36, cat_cy - 24, 72, 10)
        pygame.draw.rect(surface, (245, 158, 11), brim_rect, border_radius=4)
        pygame.draw.rect(surface, (180, 83, 9), brim_rect, width=2, border_radius=4)
        # Highlight ridge
        pygame.draw.line(surface, (254, 240, 138), (cat_cx, cat_cy - 42), (cat_cx, cat_cy - 24), 4)

        # Eyes: Happy arc eyes (^ ^)
        if model.is_celebrating:
            # Star eyes
            pts = []
            for i in range(10):
                sr = 7 if i % 2 == 0 else 3
                ang = i * math.pi / 5 - math.pi / 2
                pts.append((cat_cx - 12 + sr * math.cos(ang), cat_cy - 4 + sr * math.sin(ang)))
            pygame.draw.polygon(surface, (217, 119, 6), pts)
            pts = []
            for i in range(10):
                sr = 7 if i % 2 == 0 else 3
                ang = i * math.pi / 5 - math.pi / 2
                pts.append((cat_cx + 12 + sr * math.cos(ang), cat_cy - 4 + sr * math.sin(ang)))
            pygame.draw.polygon(surface, (217, 119, 6), pts)
        else:
            pygame.draw.arc(surface, (78, 56, 40), pygame.Rect(cat_cx - 20, cat_cy - 8, 14, 12), 0.2, 2.94, 3)
            pygame.draw.arc(surface, (78, 56, 40), pygame.Rect(cat_cx + 6, cat_cy - 8, 14, 12), 0.2, 2.94, 3)

        # Pink Nose
        pygame.draw.polygon(surface, (244, 114, 182), [(cat_cx - 4, cat_cy + 5), (cat_cx + 4, cat_cy + 5), (cat_cx, cat_cy + 10)])

        # Smile
        pygame.draw.arc(surface, (78, 56, 40), pygame.Rect(cat_cx - 9, cat_cy + 6, 9, 8), 3.14, 0, 2)
        pygame.draw.arc(surface, (78, 56, 40), pygame.Rect(cat_cx, cat_cy + 6, 9, 8), 3.14, 0, 2)

        # Whiskers
        pygame.draw.line(surface, (120, 85, 60), (cat_cx - 18, cat_cy + 6), (cat_cx - 32, cat_cy + 4), 2)
        pygame.draw.line(surface, (120, 85, 60), (cat_cx - 18, cat_cy + 11), (cat_cx - 31, cat_cy + 15), 2)
        pygame.draw.line(surface, (120, 85, 60), (cat_cx + 18, cat_cy + 6), (cat_cx + 32, cat_cy + 4), 2)
        pygame.draw.line(surface, (120, 85, 60), (cat_cx + 18, cat_cy + 11), (cat_cx + 31, cat_cy + 15), 2)

        # Paws: Left and Right
        if model.is_celebrating:
            # Both paws cheering up in the air!
            pygame.draw.circle(surface, (255, 248, 235), (cat_cx - 32, cat_cy - 12), 12)
            pygame.draw.circle(surface, (120, 85, 60), (cat_cx - 32, cat_cy - 12), 12, 2)
            pygame.draw.circle(surface, (255, 248, 235), (cat_cx + 32, cat_cy - 12), 12)
            pygame.draw.circle(surface, (120, 85, 60), (cat_cx + 32, cat_cy - 12), 12, 2)
            # Little party horn!
            horn_pts = [(cat_cx + 4, cat_cy + 8), (cat_cx + 28, cat_cy - 2), (cat_cx + 26, cat_cy + 14)]
            pygame.draw.polygon(surface, (239, 68, 68), horn_pts)
            pygame.draw.polygon(surface, (180, 20, 20), horn_pts, 2)
        else:
            # Cheering right paw raised towards tower
            pygame.draw.circle(surface, (255, 248, 235), (cat_cx + 30, cat_cy + 22), 11)
            pygame.draw.circle(surface, (120, 85, 60), (cat_cx + 30, cat_cy + 22), 11, 2)
            pygame.draw.circle(surface, (255, 248, 235), (cat_cx - 26, cat_cy + 34), 11)
            pygame.draw.circle(surface, (120, 85, 60), (cat_cx - 26, cat_cy + 34), 11, 2)

        # Speech / Name banner below Lilli
        badge_rect = pygame.Rect(cat_cx - 50, 510, 100, 28)
        pygame.draw.rect(surface, (255, 252, 245), badge_rect, border_radius=14)
        pygame.draw.rect(surface, (148, 98, 56), badge_rect, width=2, border_radius=14)
        lbl = self._render_text(display_text("Lilli"), 16, (78, 56, 40), FontRole.TITLE)
        surface.blit(lbl, lbl.get_rect(center=badge_rect.center))

    def _draw_controls_and_meters(
        self, surface: pygame.Surface, model: TorreModel, now: float
    ) -> None:
        # Mode Selection Tabs (Top Right)
        modes = [
            (TowerMode.FREE_BUILD, self.mode_free_rect, "mode.free_build"),
            (TowerMode.SLOW_FALL, self.mode_slow_rect, "mode.slow_fall"),
            (TowerMode.TOWER_CHALLENGE, self.mode_chal_rect, "mode.challenge"),
        ]
        for m_val, rect, key in modes:
            is_active = model.mode == m_val
            bg = (245, 158, 11) if is_active else (255, 250, 240)
            border = (180, 83, 9) if is_active else (200, 170, 140)
            text_col = (255, 255, 255) if is_active else (110, 75, 45)

            pygame.draw.rect(surface, bg, rect, border_radius=16)
            pygame.draw.rect(surface, border, rect, width=3 if is_active else 2, border_radius=16)
            lbl = self._render_text(self._t(key), 16, text_col, FontRole.CONTROL, rect.width - 16)
            surface.blit(lbl, lbl.get_rect(center=rect.center))

        # Star & Height Meter Panel (x=620..990, y=78..130)
        panel_rect = pygame.Rect(620, 78, 384, 56)
        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=16)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, panel_rect, width=2, border_radius=16)

        # Stars count
        stars_str = self._t("hud.stars", stars=model.total_stars)
        stars_lbl = self._render_text(stars_str, 20, (217, 119, 6), FontRole.TITLE, 130)
        surface.blit(stars_lbl, (644, 94))

        # Height meter
        h_str = self._t("hud.height", height=model.current_height, goal=10)
        h_lbl = self._render_text(h_str, 20, (30, 64, 175), FontRole.TITLE, 210)
        surface.blit(h_lbl, (780, 94))

        # Mode Specific Content:
        if model.mode == TowerMode.FREE_BUILD:
            self._draw_free_build_shelf(surface, model, now)
        else:
            self._draw_falling_steering_buttons(surface, model)

    def _draw_free_build_shelf(
        self, surface: pygame.Surface, model: TorreModel, now: float
    ) -> None:
        # Wooden shelf plank (x=620..990, y=180..310)
        shelf_base = pygame.Rect(620, 280, 384, 24)
        pygame.draw.rect(surface, (168, 120, 80), shelf_base, border_radius=6)
        pygame.draw.rect(surface, (110, 68, 38), shelf_base, width=2, border_radius=6)

        # Shelf label
        shelf_title = self._render_text(self._t("hint.pick_block"), 16, (110, 75, 45), FontRole.TITLE, 364)
        surface.blit(shelf_title, (640, 154))

        # 3 Shelf slots
        for idx, rect in enumerate(self.shelf_rects):
            is_selected = model.selected_shelf_idx == idx
            pygame.draw.rect(surface, (255, 252, 245), rect, border_radius=14)
            b_col = (245, 158, 11) if is_selected else (210, 185, 155)
            pygame.draw.rect(surface, b_col, rect, width=4 if is_selected else 2, border_radius=14)

            # Draw miniature shape inside slot
            if idx < len(model.shelf_shapes):
                shape = model.shelf_shapes[idx]
                self._draw_mini_shape(surface, rect.centerx, rect.centery, shape, now)

        # "Nuove Forme" button
        btn = self.new_shapes_rect
        pygame.draw.rect(surface, (34, 197, 94), btn, border_radius=14)
        pygame.draw.rect(surface, (21, 128, 61), btn, width=3, border_radius=14)
        btn_lbl = self._render_text(
            self._t("btn.clean"), 18, (255, 255, 255), FontRole.CONTROL, btn.width - 20
        )
        surface.blit(btn_lbl, btn_lbl.get_rect(center=btn.center))

    def _draw_mini_shape(
        self, surface: pygame.Surface, cx: int, cy: int, shape: ShapeDefinition, now: float
    ) -> None:
        mini_sz = 24
        # Calculate bounding box of shape
        max_dx = max(x for x, y in shape.blocks)
        max_dy = max(y for x, y in shape.blocks)
        total_w = (max_dx + 1) * mini_sz
        total_h = (max_dy + 1) * mini_sz
        start_x = cx - total_w // 2
        start_y = cy - total_h // 2

        for dx, dy in shape.blocks:
            bx = start_x + dx * mini_sz
            by = start_y + dy * mini_sz
            self._draw_block(surface, bx, by, mini_sz - 2, mini_sz - 2, shape.color, shape.shape_id, shape.is_rainbow, now)

    def _draw_falling_steering_buttons(
        self, surface: pygame.Surface, model: TorreModel
    ) -> None:
        # 1. Rotate button [↻] (in Mode 3)
        if model.mode == TowerMode.TOWER_CHALLENGE:
            r_rect = self.rotate_button_rect
            # Tactile circular yellow button
            pygame.draw.circle(surface, (0, 0, 0, 30), (r_rect.centerx + 2, r_rect.centery + 4), r_rect.width // 2)
            pygame.draw.circle(surface, (250, 204, 21), r_rect.center, r_rect.width // 2)
            pygame.draw.circle(surface, (217, 119, 6), r_rect.center, r_rect.width // 2, 4)
            _draw_symbol(surface, "rotate", r_rect.center, 36, (120, 53, 15))

        # 2. Steering buttons: Left [◀], Down [▼], Right [▶]
        buttons = [
            (self.left_button_rect, "left", (59, 130, 246), (29, 78, 216)),
            (self.down_button_rect, "down", (34, 197, 94), (21, 128, 61)),
            (self.right_button_rect, "right", (59, 130, 246), (29, 78, 216)),
        ]
        for rect, sym, fill, border in buttons:
            pygame.draw.rect(surface, (0, 0, 0, 30), rect.move(2, 4), border_radius=20)
            pygame.draw.rect(surface, fill, rect, border_radius=20)
            pygame.draw.rect(surface, border, rect, width=4, border_radius=20)
            _draw_symbol(surface, sym, rect.center, 34, (255, 255, 255))

    def _draw_particles(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p.life / p.max_life))))
            part_surf = pygame.Surface((int(p.size * 2), int(p.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(part_surf, (*p.color, alpha), (int(p.size), int(p.size)), int(p.size))
            surface.blit(part_surf, (int(p.x - p.size), int(p.y - p.size)))

    def _draw_celebration(
        self, surface: pygame.Surface, model: TorreModel, now: float
    ) -> None:
        # Semi-transparent warm golden curtain
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((254, 243, 199, 175))
        surface.blit(overlay, (0, 0))

        # Joyful celebration banner modal
        banner_rect = pygame.Rect(180, 160, 664, 300)
        # Drop shadow
        pygame.draw.rect(surface, (0, 0, 0, 50), banner_rect.move(4, 6), border_radius=28)
        # Wooden banner body
        pygame.draw.rect(surface, (255, 252, 245), banner_rect, border_radius=28)
        pygame.draw.rect(surface, (217, 119, 6), banner_rect, width=6, border_radius=28)

        # Title text
        t_lbl = self._render_text(
            self._t("celebration.title"), 26, (120, 53, 15), FontRole.TITLE, banner_rect.width - 48
        )
        surface.blit(t_lbl, t_lbl.get_rect(center=(banner_rect.centerx, banner_rect.top + 50)))

        # Subtitle
        s_lbl = self._render_text(
            self._t("celebration.subtitle"), 20, (78, 56, 40), FontRole.BODY, banner_rect.width - 48
        )
        surface.blit(s_lbl, s_lbl.get_rect(center=(banner_rect.centerx, banner_rect.top + 95)))

        # Height & Stars achievement
        achieve_str = self._t(
            "celebration.achievement", stars=model.total_stars, height=model.current_height
        )
        a_lbl = self._render_text(
            achieve_str, 20, (30, 64, 175), FontRole.TITLE, banner_rect.width - 48
        )
        surface.blit(a_lbl, a_lbl.get_rect(center=(banner_rect.centerx, banner_rect.top + 140)))

        # Chunky yellow Replay button [Costruisci Ancora 🔄]
        btn_rect = self.replay_button_rect
        pulse = 1.0 + 0.04 * math.sin(now * 5.0)
        pw = int(btn_rect.width * pulse)
        ph = int(btn_rect.height * pulse)
        p_rect = pygame.Rect(0, 0, pw, ph)
        p_rect.center = btn_rect.center

        pygame.draw.rect(surface, (0, 0, 0, 35), p_rect.move(3, 5), border_radius=24)
        pygame.draw.rect(surface, (250, 204, 21), p_rect, border_radius=24)
        pygame.draw.rect(surface, (217, 119, 6), p_rect, width=5, border_radius=24)

        r_lbl = self._render_text(
            self._t("btn.replay"), 24, (120, 53, 15), FontRole.TITLE, btn_rect.width - 28
        )
        surface.blit(r_lbl, r_lbl.get_rect(center=p_rect.center))

    def hit_test_grid(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """Convert reference canvas point to tower grid (col, row)."""
        x, y = pos
        if TOWER_X <= x < TOWER_X + TOWER_WIDTH and TOWER_Y <= y < TOWER_Y + TOWER_HEIGHT:
            col = (x - TOWER_X) // CELL_SIZE
            row = (y - TOWER_Y) // CELL_SIZE
            if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                return col, row
        return None
