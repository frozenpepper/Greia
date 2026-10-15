"""Low-allocation, high-polish Pygame presentation for Specchi Magici."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizationError, LocalizedResources
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

LISTEN_BTN_RECT: Final[pygame.Rect] = pygame.Rect(135, 492, 160, 50)
UNDO_RECT: Final[pygame.Rect] = pygame.Rect(720, 492, 140, 50)
MASCOT_RECT: Final[pygame.Rect] = pygame.Rect(20, 435, 110, 110)


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
        # Resolved once: the speaker pictogram stays even if the caption is absent.
        try:
            caption = resources.text("button.listen").strip()
        except LocalizationError:
            caption = ""
        self._listen_text = f"🔊 {caption}" if caption else "🔊"
        self._undo_text = f"↩️ {self._caption('button.undo')}".strip()
        self._prompt_text = self._caption("prompt.place")

    def _caption(self, key: str) -> str:
        try:
            return self._resources.text(key).strip()
        except LocalizationError:
            return ""

    def draw_scene(
        self,
        target: pygame.Surface,
        session: MirrorSession,
        *,
        wobble_x: int = 0,
        shimmer: bool = False,
        hovered_cell: tuple[int, int] | None = None,
        hovered_tray_idx: int | None = None,
        hovered_undo: bool = False,
    ) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_lilli(target)

        current = session.current_puzzle
        if current is None:
            return

        # 1. Draw 8x6 Grid Board & Magic Mirror Axis
        self._draw_board_and_mirror(
            target,
            session,
            wobble_x=wobble_x,
            shimmer=shimmer,
            hovered_cell=hovered_cell,
        )

        # 2. Draw Prompt text
        self._draw_prompt(target)

        # 3. Draw Tray Pieces & Undo Button
        self._draw_tray_and_controls(
            target,
            session,
            hovered_tray_idx=hovered_tray_idx,
            hovered_undo=hovered_undo,
        )

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
        spacing = 68
        tray_w = count * spacing
        start_x = 512 - tray_w // 2

        for i in range(count):
            rect = pygame.Rect(start_x + i * spacing - 4, 476, 60, 80)
            if rect.collidepoint(point):
                return i
        return None

    def listen_contains(self, point: tuple[int, int]) -> bool:
        return LISTEN_BTN_RECT.collidepoint(point) or MASCOT_RECT.collidepoint(point)

    def undo_contains(self, point: tuple[int, int]) -> bool:
        return UNDO_RECT.collidepoint(point)

    def _draw_board_and_mirror(
        self,
        target: pygame.Surface,
        session: MirrorSession,
        *,
        wobble_x: int = 0,
        shimmer: bool = False,
        hovered_cell: tuple[int, int] | None = None,
    ) -> None:
        board_rect = pygame.Rect(BOARD_LEFT - 14 + wobble_x, BOARD_TOP - 14, 448, GRID_ROWS * CELL_SIZE + 28)
        # Drop shadow
        pygame.draw.rect(target, (10, 5, 20), board_rect.move(0, 8), border_radius=20)

        # Ornate golden baroque frame
        pygame.draw.rect(target, (245, 158, 11), board_rect, width=6, border_radius=20)
        pygame.draw.rect(target, (217, 119, 6), board_rect.inflate(-6, -6), width=2, border_radius=16)
        pygame.draw.rect(target, (20, 12, 38), board_rect.inflate(-10, -10), border_radius=14)

        # Corner golden rosettes
        for cx, cy in [
            (board_rect.left + 8, board_rect.top + 8),
            (board_rect.right - 8, board_rect.top + 8),
            (board_rect.left + 8, board_rect.bottom - 8),
            (board_rect.right - 8, board_rect.bottom - 8),
        ]:
            pygame.draw.circle(target, (251, 191, 36), (cx, cy), 8)
            pygame.draw.circle(target, (180, 83, 9), (cx, cy), 8, 2)

        # Draw Cells
        selected_piece = (
            session.tray[session.selected_tray_index]
            if (session.selected_tray_index is not None and session.selected_tray_index < len(session.tray))
            else None
        )

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self.cell_rect(r, c).move(wobble_x, 0)
                is_hovered = ((r, c) == hovered_cell)

                # Left side (crystal blue tint), Right side (amethyst purple tint)
                bg_col = (30, 24, 60) if c < 4 else (42, 26, 74)
                pygame.draw.rect(target, bg_col, rect.inflate(-2, -2), border_radius=8)

                border_c = (56, 189, 248) if is_hovered else (65, 45, 95)
                border_w = 3 if is_hovered else 1
                pygame.draw.rect(target, border_c, rect.inflate(-2, -2), width=border_w, border_radius=8)

                # Draw placed piece
                piece = session.grid.get((r, c))
                if piece is not None:
                    self._art.draw_piece(target, rect.centerx, rect.centery, 38, piece)
                elif is_hovered and c >= 4 and selected_piece is not None:
                    # Ghost preview of selected piece on target cell
                    ghost = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    self._art.draw_piece(ghost, CELL_SIZE // 2, CELL_SIZE // 2, 34, selected_piece)
                    ghost.set_alpha(140)
                    target.blit(ghost, rect.topleft)

        # Central Magic Mirror Shimmer Beam
        beam_rect = pygame.Rect(MIRROR_X - 6 + wobble_x, BOARD_TOP - 20, 12, GRID_ROWS * CELL_SIZE + 40)
        # Soft glowing outer aura
        for r in range(16, 4, -3):
            alpha = int(45 * (1.0 - r / 16.0))
            aura = pygame.Surface((r * 2, beam_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(aura, (56, 189, 248, alpha), (0, 0, r * 2, beam_rect.height), border_radius=r)
            target.blit(aura, (MIRROR_X - r + wobble_x, BOARD_TOP - 20))

        beam_col = (255, 255, 255) if shimmer else (186, 230, 253)
        pygame.draw.rect(target, beam_col, beam_rect, border_radius=6)
        pygame.draw.rect(target, (56, 189, 248), beam_rect, width=2, border_radius=6)

    def _draw_tray_and_controls(
        self,
        target: pygame.Surface,
        session: MirrorSession,
        *,
        hovered_tray_idx: int | None = None,
        hovered_undo: bool = False,
    ) -> None:
        count = len(session.tray)
        if count > 0:
            spacing = 68
            tray_w = count * spacing
            start_x = 512 - tray_w // 2

            tray_bg = pygame.Rect(start_x - 16, 474, tray_w + 32, 88)
            pygame.draw.rect(target, (10, 5, 20), tray_bg.move(0, 6), border_radius=22)
            pygame.draw.rect(target, (24, 14, 46), tray_bg, border_radius=22)
            pygame.draw.rect(target, (147, 51, 234), tray_bg, width=3, border_radius=22)

            for i, piece in enumerate(session.tray):
                cx = start_x + i * spacing + 30
                cy = 518
                is_selected = (session.selected_tray_index == i)
                is_hovered = (i == hovered_tray_idx)
                draw_cy = cy - 4 if (is_hovered or is_selected) else cy

                if is_selected:
                    pygame.draw.circle(target, (56, 189, 248), (cx, draw_cy), 30, 4)
                    pygame.draw.circle(target, (255, 255, 255), (cx, draw_cy), 32, 2)
                elif is_hovered:
                    pygame.draw.circle(target, (216, 180, 254), (cx, draw_cy), 28, 3)

                self._art.draw_piece(target, cx, draw_cy, 42, piece)

        # Undo button
        can_undo = len(session.undo_stack) > 0
        u_draw = UNDO_RECT.move(0, -4) if (hovered_undo and can_undo) else UNDO_RECT

        # Drop shadow
        pygame.draw.rect(target, (10, 5, 20), UNDO_RECT.move(0, 4), border_radius=25)

        if can_undo:
            btn_col = (147, 51, 234)
            border_col = (251, 191, 36)
            text_col = (255, 255, 255)
        else:
            btn_col = (30, 41, 59)
            border_col = (51, 65, 85)
            text_col = (100, 116, 139)

        pygame.draw.rect(target, btn_col, u_draw, border_radius=25)
        pygame.draw.rect(target, border_col, u_draw, width=3 if can_undo else 2, border_radius=25)

        undo_surf = self._typography.render(self._undo_text, FontRole.TITLE, 18, text_col)
        target.blit(
            undo_surf,
            (
                u_draw.centerx - undo_surf.get_width() // 2,
                u_draw.centery - undo_surf.get_height() // 2,
            ),
        )

    def _draw_prompt(self, target: pygame.Surface) -> None:
        prompt_surf = self._typography.render(self._prompt_text, FontRole.TITLE, 26, (254, 240, 138))
        p_x = REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2
        p_y = 405
        banner = pygame.Rect(p_x - 24, p_y - 6, prompt_surf.get_width() + 48, prompt_surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 200), banner, border_radius=16)
        pygame.draw.rect(target, (217, 119, 6), banner, width=2, border_radius=16)
        target.blit(prompt_surf, (p_x, p_y))

    def _draw_lilli(self, target: pygame.Surface) -> None:
        if self._art.lilli is not None:
            target.blit(self._art.lilli, (25, 435))

        # Speech replay capsule beside Lilli
        pygame.draw.rect(target, (10, 5, 20), LISTEN_BTN_RECT.move(0, 4), border_radius=25)
        pygame.draw.rect(target, (254, 240, 138), LISTEN_BTN_RECT, border_radius=25)
        pygame.draw.rect(target, (217, 119, 6), LISTEN_BTN_RECT, width=3, border_radius=25)

        l_surf = self._typography.render(self._listen_text, FontRole.TITLE, 18, (120, 53, 15))
        target.blit(
            l_surf,
            (LISTEN_BTN_RECT.centerx - l_surf.get_width() // 2, LISTEN_BTN_RECT.centery - l_surf.get_height() // 2),
        )

    def _draw_progress_badge(self, target: pygame.Surface, session: MirrorSession) -> None:
        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt = f"{session.puzzle_index + 1} / 6"
        txt_surf = self._typography.render(txt, FontRole.TITLE, 22, (254, 240, 138))
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )

