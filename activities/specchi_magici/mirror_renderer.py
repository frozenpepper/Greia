"""Low-allocation Pygame presentation for Specchi Magici."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .mirror_art import MirrorArt
    from .mirror_model import GRID_COLS, GRID_ROWS, MosaicPuzzle, MirrorSession, Piece, REFERENCE_WIDTH
else:
    from mirror_art import MirrorArt
    from mirror_model import GRID_COLS, GRID_ROWS, MosaicPuzzle, MirrorSession, Piece, REFERENCE_WIDTH


CELL_SIZE: Final[int] = 52
BOARD_TOP: Final[int] = 64
BOARD_LEFT: Final[int] = 298
MIRROR_X: Final[int] = 512

UNDO_RECT: Final[pygame.Rect] = pygame.Rect(840, 480, 140, 76)


class MirrorRenderer:
    """Render the 8x6 symmetry grid, magic mirror beam, piece tray, and Lilli mascot."""

    def __init__(
        self,
        art: MirrorArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources

        self._undo_label = typography.render(
            resources.text("button.undo"),
            FontRole.TITLE,
            22,
            (255, 255, 255),
        )

    def draw_scene(
        self,
        target: pygame.Surface,
        session: MirrorSession,
        *,
        wobble_x: int = 0,
        shimmer: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_lilli(target)

        current = session.current_puzzle
        if current is None:
            return

        # 1. Draw 8x6 Grid Board & Magic Mirror Axis
        self._draw_board_and_mirror(target, session, wobble_x=wobble_x, shimmer=shimmer)

        # 2. Draw Prompt text
        self._draw_prompt(target)

        # 3. Draw Tray Pieces & Undo Button
        self._draw_tray_and_controls(target, session)

        # 4. Progress badge
        self._draw_progress_badge(target, session)

    def cell_rect(self, row: int, col: int) -> pygame.Rect:
        x_offset = (col * CELL_SIZE) if col < 4 else ((col - 4) * CELL_SIZE + 214)
        return pygame.Rect(BOARD_LEFT + x_offset, BOARD_TOP + row * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def cell_at(self, point: tuple[int, int]) -> tuple[int, int] | None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self.cell_rect(r, c)
                if rect.collidepoint(point):
                    return (r, c)
        return None

    def tray_item_at(self, point: tuple[int, int], session: MirrorSession) -> int | None:
        count = len(session.tray)
        if count == 0:
            return None
        spacing = 64
        tray_w = count * spacing
        start_x = 512 - tray_w // 2

        for i in range(count):
            rect = pygame.Rect(start_x + i * spacing - 4, 480, 56, 76)
            if rect.collidepoint(point):
                return i
        return None

    def undo_contains(self, point: tuple[int, int]) -> bool:
        return UNDO_RECT.collidepoint(point)

    def _draw_board_and_mirror(
        self,
        target: pygame.Surface,
        session: MirrorSession,
        *,
        wobble_x: int = 0,
        shimmer: bool = False,
    ) -> None:
        board_rect = pygame.Rect(BOARD_LEFT - 12 + wobble_x, BOARD_TOP - 12, 444, GRID_ROWS * CELL_SIZE + 24)
        pygame.draw.rect(target, (30, 18, 54), board_rect, border_radius=16)
        pygame.draw.rect(target, (147, 51, 234), board_rect, width=3, border_radius=16)

        # Draw Cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self.cell_rect(r, c).move(wobble_x, 0)
                # Left side is blue-tinted, right side is purple-tinted
                bg_col = (42, 28, 74) if c < 4 else (52, 32, 86)
                pygame.draw.rect(target, bg_col, rect.inflate(-2, -2), border_radius=6)
                pygame.draw.rect(target, (76, 48, 115), rect.inflate(-2, -2), width=1, border_radius=6)

                # Draw placed piece
                piece = session.grid.get((r, c))
                if piece is not None:
                    self._art.draw_piece(target, rect.centerx, rect.centery, 38, piece)

        # Central Magic Mirror Beam
        beam_rect = pygame.Rect(MIRROR_X - 5 + wobble_x, BOARD_TOP - 18, 10, GRID_ROWS * CELL_SIZE + 36)
        beam_col = (255, 255, 255) if shimmer else (56, 189, 248)
        pygame.draw.rect(target, beam_col, beam_rect, border_radius=5)
        pygame.draw.rect(target, (192, 132, 252), beam_rect.inflate(4, 4), width=2, border_radius=7)

    def _draw_tray_and_controls(self, target: pygame.Surface, session: MirrorSession) -> None:
        count = len(session.tray)
        if count > 0:
            spacing = 64
            tray_w = count * spacing
            start_x = 512 - tray_w // 2

            tray_bg = pygame.Rect(start_x - 16, 476, tray_w + 32, 84)
            pygame.draw.rect(target, (30, 18, 54), tray_bg, border_radius=18)
            pygame.draw.rect(target, (147, 51, 234), tray_bg, width=2, border_radius=18)

            for i, piece in enumerate(session.tray):
                cx = start_x + i * spacing + 28
                cy = 518
                is_selected = (session.selected_tray_index == i)

                if is_selected:
                    pygame.draw.circle(target, (56, 189, 248), (cx, cy), 28, 3)
                    pygame.draw.circle(target, (255, 255, 255), (cx, cy), 30, 1)

                self._art.draw_piece(target, cx, cy, 40, piece)

        # Undo button
        can_undo = len(session.undo_stack) > 0
        btn_col = (147, 51, 234) if can_undo else (75, 85, 99)
        pygame.draw.rect(target, btn_col, UNDO_RECT, border_radius=16)
        pygame.draw.rect(target, (255, 255, 255) if can_undo else (107, 114, 128), UNDO_RECT, width=2, border_radius=16)
        target.blit(
            self._undo_label,
            (
                UNDO_RECT.centerx - self._undo_label.get_width() // 2,
                UNDO_RECT.centery - self._undo_label.get_height() // 2,
            ),
        )

    def _draw_prompt(self, target: pygame.Surface) -> None:
        text = self._resources.text("prompt.place")
        prompt_surf = self._typography.render(text, FontRole.TITLE, 24, (233, 213, 255))
        target.blit(
            prompt_surf,
            (REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2, 400),
        )

    def _draw_lilli(self, target: pygame.Surface) -> None:
        if self._art.lilli is not None:
            target.blit(self._art.lilli, (20, 390))
        else:
            cx, cy = 90, 480
            pygame.draw.rect(target, (168, 85, 247), (cx - 40, cy - 40, 80, 80), border_radius=16)
            pygame.draw.circle(target, (255, 255, 255), (cx - 16, cy - 10), 10)
            pygame.draw.circle(target, (255, 255, 255), (cx + 16, cy - 10), 10)
            pygame.draw.arc(target, (255, 255, 255), (cx - 20, cy + 2, 40, 24), 3.4, 6.0, 4)

    def _draw_progress_badge(self, target: pygame.Surface, session: MirrorSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 180), badge_rect, border_radius=22)
        pygame.draw.rect(target, (233, 213, 255), badge_rect, width=2, border_radius=22)

        txt = f"{session.puzzle_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (233, 213, 255))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )
