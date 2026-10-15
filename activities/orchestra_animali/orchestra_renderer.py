"""Orchestra Animali — presentation owner.

Owns the pre-baked stage backdrop (single bounded surface, ``convert()``
once, invalidated on resize) and every draw helper for instruments,
particles, rainbow piano keys and HUD. No gameplay or IO lives here.
"""

from __future__ import annotations

import math

import pygame

from greia_platform.activity_ui import mix
from greia_platform.typography import FontRole

if __package__:
    from .orchestra_content import (
        DARK_TEXT,
        KEYBOARD_SHORTCUTS,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_GOLD,
        STAGE_GOLD,
        STAGE_WALL_BOTTOM,
        STAGE_WALL_TOP,
        STAGE_WOOD_BOTTOM,
        STAGE_WOOD_TOP,
        WHITE,
    )
    from .orchestra_model import InstrumentCard, Particle
else:  # pragma: no cover - runtime/script fallback
    from orchestra_content import (
        DARK_TEXT,
        KEYBOARD_SHORTCUTS,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_GOLD,
        STAGE_GOLD,
        STAGE_WALL_BOTTOM,
        STAGE_WALL_TOP,
        STAGE_WOOD_BOTTOM,
        STAGE_WOOD_TOP,
        WHITE,
    )
    from orchestra_model import InstrumentCard, Particle


BACKING_IMPORT_RECT = pygame.Rect(140, 12, 70, 56)
BACKING_PLAY_RECT = pygame.Rect(220, 12, 120, 56)


class OrchestraRenderer:
    """Stage renderer with one bounded backdrop cache."""

    def __init__(self, typography) -> None:
        self._typography = typography
        self._bg_cached: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Backdrop cache — one surface, bounded, convert() once
    # ------------------------------------------------------------------

    def _create_stage_surface(self) -> pygame.Surface:
        surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        for y in range(0, 430, 8):
            ratio = y / 430.0
            col = mix(STAGE_WALL_TOP, STAGE_WALL_BOTTOM, ratio)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 8))
        for y in range(430, REFERENCE_HEIGHT, 6):
            ratio = (y - 430) / float(REFERENCE_HEIGHT - 430)
            col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BOTTOM, ratio)
            pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))
        for px in range(0, REFERENCE_WIDTH, 120):
            pygame.draw.line(surf, (80, 45, 20), (px, 430), (px, REFERENCE_HEIGHT), 2)
        pygame.draw.line(surf, STAGE_GOLD, (0, 430), (REFERENCE_WIDTH, 430), 4)
        pygame.draw.polygon(surf, STAGE_CURTAIN_DARK, [(0, 0), (140, 0), (90, 440), (0, 440)])
        pygame.draw.polygon(surf, STAGE_CURTAIN, [(0, 0), (120, 0), (70, 430), (0, 430)])
        pygame.draw.polygon(
            surf, STAGE_CURTAIN_DARK, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 140, 0), (REFERENCE_WIDTH - 90, 440), (REFERENCE_WIDTH, 440)]
        )
        pygame.draw.polygon(
            surf, STAGE_CURTAIN, [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 120, 0), (REFERENCE_WIDTH - 70, 430), (REFERENCE_WIDTH, 430)]
        )
        pygame.draw.line(surf, STAGE_CURTAIN_GOLD, (70, 0), (35, 430), 3)
        pygame.draw.line(surf, STAGE_CURTAIN_GOLD, (REFERENCE_WIDTH - 70, 0), (REFERENCE_WIDTH - 35, 430), 3)
        for vx in range(120, 900, 130):
            pygame.draw.circle(surf, STAGE_CURTAIN, (vx + 65, 30), 75)
            pygame.draw.circle(surf, STAGE_CURTAIN_GOLD, (vx + 65, 30), 75, width=3)
        try:
            if pygame.display.get_init():
                surf = surf.convert()
        except Exception:
            pass
        return surf

    def background(self) -> pygame.Surface:
        if self._bg_cached is None:
            self._bg_cached = self._create_stage_surface()
        return self._bg_cached

    def invalidate_background(self) -> None:
        self._bg_cached = None

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.blit(self.background(), (0, 0))

    # ------------------------------------------------------------------
    # Instruments
    # ------------------------------------------------------------------

    def draw_instruments(self, surface: pygame.Surface, instruments: list[InstrumentCard]) -> None:
        for inst in instruments:
            ox = int(inst.x)
            oy = int(inst.y)
            if inst.jump_timer > 0:
                oy += int(-math.sin(inst.jump_timer * math.pi) * 22.0)
            else:
                oy += int(math.sin(inst.phase) * 3.0)
            pygame.draw.ellipse(surface, (15, 12, 25), (ox - 48, int(inst.y) + 42, 96, 22))
            pygame.draw.ellipse(surface, (180, 115, 60), (ox - 52, oy + 32, 104, 28))
            pygame.draw.ellipse(surface, STAGE_GOLD, (ox - 52, oy + 32, 104, 28), width=3)
            avatar_bg = (255, 255, 255)
            border_col = STAGE_GOLD if inst.jump_timer > 0 else inst.color
            border_w = 5 if inst.jump_timer > 0 else 3
            if inst.jump_timer > 0:
                pygame.draw.circle(surface, (254, 240, 138), (ox, oy), int(inst.radius + 8), width=4)
            pygame.draw.circle(surface, avatar_bg, (ox, oy), int(inst.radius))
            pygame.draw.circle(surface, border_col, (ox, oy), int(inst.radius), width=border_w)
            char_surf = self._typography.render(inst.icon, FontRole.DISPLAY, 54, DARK_TEXT)
            surface.blit(char_surf, (ox - char_surf.get_width() // 2, oy - char_surf.get_height() // 2 - 6))
            if not inst.label:
                continue
            lbl_surf = self._typography.render(inst.label, FontRole.CONTROL, 14, (255, 255, 255))
            badge_w = max(80, lbl_surf.get_width() + 16)
            badge_rect = pygame.Rect(ox - badge_w // 2, oy + 30, badge_w, 24)
            pygame.draw.rect(surface, (30, 24, 45), badge_rect, border_radius=8)
            pygame.draw.rect(surface, STAGE_GOLD if inst.jump_timer > 0 else (203, 213, 225), badge_rect, width=2, border_radius=8)
            surface.blit(lbl_surf, (badge_rect.centerx - lbl_surf.get_width() // 2, badge_rect.centery - lbl_surf.get_height() // 2))

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def draw_particles(self, surface: pygame.Surface, particles: list[Particle]) -> None:
        for p in particles:
            if p.life > 0:
                sz = max(12, int(p.size * p.life))
                txt_surf = self._typography.render(p.symbol, FontRole.BODY, sz, p.color)
                surface.blit(txt_surf, (int(p.x) - txt_surf.get_width() // 2, int(p.y) - txt_surf.get_height() // 2))

    # ------------------------------------------------------------------
    # Piano keys
    # ------------------------------------------------------------------

    def draw_piano_keys(self, surface: pygame.Surface, key_highlight_timers: list[float], note_labels: list[str]) -> None:
        for k_i in range(8):
            kx = 64 + k_i * 112
            key_rect = pygame.Rect(kx, 440, 104, 130)
            hl = key_highlight_timers[k_i]
            base_col = RAINBOW_COLORS[k_i]
            pygame.draw.rect(surface, (20, 15, 25), (kx + 3, 444, 104, 130), border_radius=14)
            fill_col = mix(base_col, WHITE, 0.4) if hl > 0 else base_col
            pygame.draw.rect(surface, fill_col, key_rect, border_radius=14)
            pygame.draw.rect(surface, WHITE, (kx + 8, 446, 88, 14), border_radius=6)
            pygame.draw.rect(surface, (30, 41, 59), key_rect, width=3, border_radius=14)
            badge_rect = pygame.Rect(kx + 32, 448, 40, 22)
            pygame.draw.rect(surface, (255, 250, 240), badge_rect, border_radius=6)
            pygame.draw.rect(surface, (30, 41, 59), badge_rect, width=1, border_radius=6)
            sc_surf = self._typography.render(KEYBOARD_SHORTCUTS[k_i], FontRole.CONTROL, 14, DARK_TEXT)
            surface.blit(sc_surf, (badge_rect.centerx - sc_surf.get_width() // 2, badge_rect.centery - sc_surf.get_height() // 2))
            note_str = note_labels[k_i]
            n_surf = self._typography.render(note_str, FontRole.DISPLAY, 26, (255, 255, 255) if hl <= 0 else DARK_TEXT)
            surface.blit(n_surf, (kx + 52 - n_surf.get_width() // 2, 490))

    # ------------------------------------------------------------------
    # HUD + title — kept clear of trusted Home chrome (x < 120)
    # ------------------------------------------------------------------
    @staticmethod
    def backing_import_contains(point: tuple[int, int]) -> bool:
        return BACKING_IMPORT_RECT.collidepoint(point)

    @staticmethod
    def backing_play_contains(point: tuple[int, int]) -> bool:
        return BACKING_PLAY_RECT.collidepoint(point)


    def draw_hud(
        self,
        surface: pygame.Surface,
        stars: int,
        *,
        title: str = "",
        backing_enabled: bool = False,
        backing_state: str = "empty",
        backing_import_enabled: bool = True,
        backing_import_state: str = "",
    ) -> None:
        import_border = (
            (110, 115, 128)
            if not backing_import_enabled
            else (220, 38, 38)
            if backing_import_state == "error"
            else (16, 185, 129)
            if backing_import_state == "imported"
            else (56, 189, 248)
        )
        import_fill = (
            (61, 65, 76)
            if not backing_import_enabled
            else (205, 240, 224)
            if backing_import_state in {"pending", "imported"}
            else (238, 248, 255)
        )
        pygame.draw.rect(
            surface, import_fill, BACKING_IMPORT_RECT, border_radius=14
        )
        pygame.draw.rect(
            surface,
            import_border,
            BACKING_IMPORT_RECT,
            width=3,
            border_radius=14,
        )
        ix, iy = BACKING_IMPORT_RECT.center
        # Music note + down arrow: bring a saved recording/song into Orchestra.
        import_icon = DARK_TEXT if backing_import_enabled else (160, 164, 174)
        pygame.draw.circle(surface, import_icon, (ix - 11, iy + 8), 5)
        pygame.draw.line(
            surface, import_icon, (ix - 6, iy + 7), (ix - 6, iy - 14), 3
        )
        pygame.draw.line(
            surface, import_icon, (ix - 6, iy - 14), (ix + 2, iy - 11), 3
        )
        pygame.draw.line(
            surface, import_border, (ix + 15, iy - 13), (ix + 15, iy + 9), 4
        )
        pygame.draw.lines(
            surface,
            import_border,
            False,
            [(ix + 7, iy + 1), (ix + 15, iy + 10), (ix + 23, iy + 1)],
            4,
        )

        play_fill = (232, 246, 236) if backing_enabled else (61, 65, 76)
        play_border = (34, 197, 94) if backing_enabled else (110, 115, 128)
        if backing_state == "playing":
            play_fill = (205, 240, 224)
        elif backing_state == "paused":
            play_fill = (254, 240, 138)
        pygame.draw.rect(
            surface, play_fill, BACKING_PLAY_RECT, border_radius=14
        )
        pygame.draw.rect(
            surface,
            play_border,
            BACKING_PLAY_RECT,
            width=3,
            border_radius=14,
        )
        px, py = BACKING_PLAY_RECT.center
        icon_color = DARK_TEXT if backing_enabled else (160, 164, 174)
        if backing_state == "playing":
            pygame.draw.rect(
                surface, icon_color, (px - 12, py - 12, 8, 24), border_radius=2
            )
            pygame.draw.rect(
                surface, icon_color, (px + 4, py - 12, 8, 24), border_radius=2
            )
        else:
            pygame.draw.polygon(
                surface,
                icon_color,
                [(px - 8, py - 14), (px - 8, py + 14), (px + 16, py)],
            )

        title_rect = pygame.Rect(360, 16, 304, 52)
        pygame.draw.rect(surface, (255, 250, 240), title_rect, border_radius=14)
        pygame.draw.rect(surface, (30, 41, 59), title_rect, width=2, border_radius=14)
        title_str = " ".join(part for part in ("🎵", title, "🎶") if part)
        t_surf = self._typography.render(title_str, FontRole.TITLE, 20, DARK_TEXT)
        surface.blit(t_surf, (title_rect.centerx - t_surf.get_width() // 2, title_rect.centery - t_surf.get_height() // 2))
        hud_rect = pygame.Rect(820, 12, 160, 56)
        pygame.draw.rect(surface, (255, 250, 240), hud_rect, border_radius=16)
        pygame.draw.rect(surface, (234, 179, 8), hud_rect, width=3, border_radius=16)
        pygame.draw.circle(surface, (234, 179, 8), (hud_rect.left + 30, hud_rect.centery), 16)
        hud_surf = self._typography.render(str(stars), FontRole.DISPLAY, 26, (180, 90, 20))
        surface.blit(hud_surf, (hud_rect.left + 58, hud_rect.centery - hud_surf.get_height() // 2))


__all__ = ["BACKING_IMPORT_RECT", "BACKING_PLAY_RECT", "OrchestraRenderer"]
