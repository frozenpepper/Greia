"""Piccola Serra — rendering helpers and bounded caches.

Owns draw helpers, text caching (bounded, invalidate on resize) and the
full greenhouse scene. No storage or event IO. Text rendering uses
GreiaTypography with a small bounded LRU cache; image decoding/scaling
would be cached with convert() once if assets were used (kept bounded).
"""

from __future__ import annotations

import math
from typing import Any, Final, Mapping

import pygame

from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, POT_RECT_TUPLES, TOOL_DEFS
else:
    from serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, POT_RECT_TUPLES, TOOL_DEFS

_MAX_TEXT_CACHE = 64

# Pot rects as pygame.Rect for hit-testing/rendering reuse.
POT_RECTS: list[pygame.Rect] = [pygame.Rect(*t) for t in POT_RECT_TUPLES]


# Child-visible controls start clear of the trusted Home/Back region, which
# the platform reserves in full (both slots) so layout never jumps by context.
_CHROME_CLEAR_X: Final = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region.right + 18


class SerraRenderer:
    """Own greenhouse presentation: cached text and stateless draw helpers.

    Caches are bounded and survive only for the locale/text they were built
    for. ``invalidate`` clears text caches after a VIDEORESIZE or locale
    change. Image/scale caches would follow the same pattern (convert once,
    bounded) if runtime assets were added.
    """

    def __init__(
        self,
        typography: GreiaTypography,
        tool_labels: Mapping[str, str] | None = None,
    ) -> None:
        self._typography = typography
        # Renderer-only use remains icon-neutral; the Activity supplies locale
        # text resolved once per launch, not during every animation frame.
        self._tool_labels = dict(tool_labels or {
            "tool.seeds": "🌱", "tool.water": "💧",
            "tool.sun": "☀️", "tool.harvest": "🧺",
        })
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        self._text_order: list[tuple[str, FontRole, int, tuple[int, int, int]]] = []
        self._hud_value: int | None = None
        self._hud_surface: pygame.Surface | None = None

    # -- cache management -----------------------------------------------

    def invalidate(self) -> None:
        """Clear scaled/text caches after the viewport changes size."""
        self._text_cache.clear()
        self._text_order.clear()
        self._hud_surface = None
        self._hud_value = None

    def _cached_text(
        self, text: str, role: FontRole, size: int, color: tuple[int, int, int]
    ) -> pygame.Surface:
        key = (text, role, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._typography.render(text, role, size, color)
        if len(self._text_cache) >= _MAX_TEXT_CACHE:
            oldest = self._text_order.pop(0)
            self._text_cache.pop(oldest, None)
        self._text_cache[key] = rendered
        self._text_order.append(key)
        return rendered

    # -- high-level scene -----------------------------------------------

    def render(
        self,
        surface: pygame.Surface,
        model: Any,
        active_tool: int,
        t_now: float,
    ) -> None:
        """Render the complete greenhouse scene onto the reference canvas."""
        self._draw_background(surface)
        self._draw_pots_and_plants(surface, model, active_tool, t_now)
        self._draw_particles(surface, model.particles)
        self._draw_hud(surface, model.harvest_count, model.target_harvest)
        self._draw_toolbar(surface, active_tool)

    # -- background -----------------------------------------------------

    def _draw_background(self, surface: pygame.Surface) -> None:
        surface.fill((224, 242, 254))
        pygame.draw.circle(surface, (187, 247, 208), (200, 360), 240)
        pygame.draw.circle(surface, (134, 239, 172), (800, 380), 280)
        for gx in range(0, REFERENCE_WIDTH, 200):
            pygame.draw.line(surface, (255, 255, 255), (gx, 0), (gx, 340), 4)
        pygame.draw.line(surface, (255, 255, 255), (0, 160), (REFERENCE_WIDTH, 160), 4)
        pygame.draw.rect(surface, (180, 83, 9), (40, 330, REFERENCE_WIDTH - 80, 160), border_radius=12)
        pygame.draw.rect(surface, (146, 64, 14), (40, 330, REFERENCE_WIDTH - 80, 20), border_radius=6)
        pygame.draw.rect(surface, (254, 243, 199), (0, 480, REFERENCE_WIDTH, 120))

    # -- pots and plants ------------------------------------------------

    def _draw_pots_and_plants(
        self, surface: pygame.Surface, model: Any, active_tool: int, t_now: float
    ) -> None:
        for idx, pot in enumerate(model.pots):
            r_pot = POT_RECTS[idx]
            px = r_pot.centerx
            py = r_pot.bottom - 40

            pygame.draw.polygon(
                surface,
                (194, 65, 12),
                [(px - 45, py), (px + 45, py), (px + 36, py + 65), (px - 36, py + 65)],
            )
            pygame.draw.rect(surface, (234, 88, 12), (px - 50, py - 10, 100, 16), border_radius=4)
            pygame.draw.ellipse(surface, (69, 26, 3), (px - 44, py - 8, 88, 12))
            if pot.get("water_level", 0) > 0:
                pygame.draw.ellipse(surface, (56, 189, 248), (px - 40, py - 6, 80, 8))

            stage = int(pot["stage"])
            plant = pot["plant"]
            if stage == 1:
                pygame.draw.circle(surface, (254, 240, 138), (px, py - 2), 4)
            elif stage == 2:
                pygame.draw.line(surface, (34, 197, 94), (px, py - 2), (px, py - 25), 4)
                pygame.draw.ellipse(surface, (74, 222, 128), (px - 14, py - 30, 14, 8))
                pygame.draw.ellipse(surface, (74, 222, 128), (px, py - 30, 14, 8))
            elif stage == 3:
                pygame.draw.line(surface, (34, 197, 94), (px, py - 2), (px, py - 55), 6)
                pygame.draw.ellipse(surface, (74, 222, 128), (px - 20, py - 40, 20, 10))
                pygame.draw.ellipse(surface, (74, 222, 128), (px, py - 48, 20, 10))
                assert plant is not None
                pygame.draw.circle(surface, plant["petal_color"], (px, py - 60), 12)
            elif stage == 4:
                assert plant is not None
                pygame.draw.line(surface, (34, 197, 94), (px, py - 2), (px, py - 75), 7)
                pygame.draw.ellipse(surface, (74, 222, 128), (px - 26, py - 50, 26, 12))
                pygame.draw.ellipse(surface, (74, 222, 128), (px, py - 60, 26, 12))
                fx = px
                fy = py - 85
                petal_r = 16
                for ang in range(0, 360, 45):
                    rad = math.radians(ang)
                    ptx = fx + math.cos(rad) * 18
                    pty = fy + math.sin(rad) * 18
                    pygame.draw.circle(surface, plant["petal_color"], (int(ptx), int(pty)), petal_r)
                pygame.draw.circle(surface, plant["center_color"], (fx, fy), 18)
                pygame.draw.circle(surface, (255, 255, 255), (fx - 4, fy - 4), 4)

            if not model.is_victory:
                self._draw_thought_bubble(surface, px, idx, stage, active_tool, t_now)

    def _draw_thought_bubble(
        self, surface: pygame.Surface, px: int, idx: int, stage: int, active_tool: int, t_now: float
    ) -> None:
        # Keep single source of stage->tool truth without importing model
        # at runtime (avoids circular/context issues); mirrors serra_model.
        if stage == 0:
            needed_tool = 0
        elif stage == 1:
            needed_tool = 1
        elif stage == 2:
            needed_tool = 2
        elif stage == 3:
            needed_tool = 1
        else:
            needed_tool = 3
        is_matching = active_tool == needed_tool
        bob = int(math.sin(t_now * 4.0 + idx) * 3.0)
        bx = px
        by = 130 + bob
        dark = (30, 41, 59)
        white = (255, 255, 255)
        pygame.draw.circle(surface, white, (bx, by + 45), 5)
        pygame.draw.circle(surface, dark, (bx, by + 45), 5, 2)
        pygame.draw.circle(surface, white, (bx, by + 30), 7)
        pygame.draw.circle(surface, dark, (bx, by + 30), 7, 2)
        bubble_border = (34, 197, 94) if is_matching else (203, 213, 225)
        border_w = 4 if is_matching else 2
        for ox, oy, rad in [(-16, 0, 18), (16, 0, 18), (0, -10, 20), (0, 10, 18)]:
            pygame.draw.circle(surface, white, (bx + ox, by + oy), rad)
            pygame.draw.circle(surface, bubble_border, (bx + ox, by + oy), rad, border_w)
        for ox, oy, rad in [(-16, 0, 16), (16, 0, 16), (0, -10, 18), (0, 10, 16)]:
            pygame.draw.circle(surface, white, (bx + ox, by + oy), rad)

        if needed_tool == 0:
            pygame.draw.circle(surface, (180, 83, 9), (bx, by + 5), 7)
            pygame.draw.circle(surface, dark, (bx, by + 5), 7, 2)
            pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(bx - 10, by - 12, 10, 7))
            pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(bx, by - 12, 10, 7))
            pygame.draw.ellipse(surface, dark, pygame.Rect(bx - 10, by - 12, 10, 7), 1)
            pygame.draw.ellipse(surface, dark, pygame.Rect(bx, by - 12, 10, 7), 1)
        elif needed_tool == 1:
            pygame.draw.circle(surface, (14, 165, 233), (bx, by + 4), 9)
            pygame.draw.polygon(surface, (14, 165, 233), [(bx - 8, by + 2), (bx + 8, by + 2), (bx, by - 11)])
            pygame.draw.circle(surface, dark, (bx, by + 4), 9, 2)
            pygame.draw.circle(surface, (255, 255, 255), (bx - 3, by + 2), 3)
        elif needed_tool == 2:
            pygame.draw.circle(surface, (234, 179, 8), (bx, by), 10)
            pygame.draw.circle(surface, dark, (bx, by), 10, 2)
            for sang in (0, 45, 90, 135, 180, 225, 270, 315):
                srad = math.radians(sang)
                pygame.draw.line(
                    surface,
                    (217, 119, 6),
                    (bx + int(math.cos(srad) * 11), by + int(math.sin(srad) * 11)),
                    (bx + int(math.cos(srad) * 16), by + int(math.sin(srad) * 16)),
                    3,
                )
        elif needed_tool == 3:
            pygame.draw.circle(surface, (239, 68, 68), (bx, by + 3), 10)
            pygame.draw.circle(surface, dark, (bx, by + 3), 10, 2)
            pygame.draw.circle(surface, (255, 255, 255), (bx - 3, by), 3)
            pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(bx - 3, by - 11, 7, 5))
            pygame.draw.ellipse(surface, dark, pygame.Rect(bx - 3, by - 11, 7, 5), 1)

    # -- particles, hud, toolbar ----------------------------------------

    def _draw_particles(self, surface: pygame.Surface, particles: list[dict[str, Any]]) -> None:
        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, float(p["life"]))))
            pygame.draw.circle(surface, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

    def _draw_hud(self, surface: pygame.Surface, harvest_count: int, target_harvest: int) -> None:
        star_pill = pygame.Rect(_CHROME_CLEAR_X, 16, 140, 56)
        pygame.draw.rect(surface, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surface, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surface, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        # Cache the harvest text surface by value.
        if self._hud_value != harvest_count or self._hud_surface is None:
            self._hud_value = harvest_count
            self._hud_surface = self._cached_text(
                f"{harvest_count}/{target_harvest}", FontRole.DISPLAY, 28, (180, 83, 9)
            )
        assert self._hud_surface is not None
        surface.blit(
            self._hud_surface, (star_pill.left + 54, star_pill.centery - self._hud_surface.get_height() // 2)
        )

    def _draw_toolbar(self, surface: pygame.Surface, active_tool: int) -> None:
        tool_y = REFERENCE_HEIGHT - 85
        for tx, t_idx, label_key, col in TOOL_DEFS:
            b_rect = pygame.Rect(tx, tool_y, 180, 72)
            is_sel = active_tool == t_idx
            bg_col = col if is_sel else (255, 255, 255)
            border_w = 5 if is_sel else 2
            pygame.draw.rect(surface, bg_col, b_rect, border_radius=20)
            pygame.draw.rect(surface, col, b_rect, width=border_w, border_radius=20)
            cx = b_rect.centerx
            cy = b_rect.top + 28
            if t_idx == 0:
                seed_col = (255, 255, 255) if is_sel else (22, 101, 52)
                leaf_col = (220, 252, 231) if is_sel else (34, 197, 94)
                pygame.draw.circle(surface, seed_col, (cx, cy + 6), 8)
                pygame.draw.line(surface, leaf_col, (cx, cy + 6), (cx, cy - 8), 3)
                pygame.draw.ellipse(surface, leaf_col, pygame.Rect(cx - 14, cy - 14, 14, 8))
                pygame.draw.ellipse(surface, leaf_col, pygame.Rect(cx, cy - 14, 14, 8))
            elif t_idx == 1:
                can_col = (255, 255, 255) if is_sel else (2, 132, 199)
                drop_col = (224, 242, 254) if is_sel else (56, 189, 248)
                pygame.draw.rect(surface, can_col, pygame.Rect(cx - 14, cy - 8, 22, 18), border_radius=4)
                pygame.draw.line(surface, can_col, (cx + 8, cy - 3), (cx + 20, cy - 11), 4)
                pygame.draw.arc(surface, can_col, pygame.Rect(cx - 24, cy - 10, 14, 16), 1.5, 4.7, 3)
                pygame.draw.circle(surface, drop_col, (cx + 22, cy - 1), 3)
                pygame.draw.circle(surface, drop_col, (cx + 24, cy + 7), 4)
            elif t_idx == 2:
                sun_col = (255, 255, 255) if is_sel else (234, 179, 8)
                ray_col = (254, 240, 138) if is_sel else (202, 138, 4)
                pygame.draw.circle(surface, sun_col, (cx, cy), 13)
                for ang in (0, 45, 90, 135, 180, 225, 270, 315):
                    rad = math.radians(ang)
                    pygame.draw.line(
                        surface,
                        ray_col,
                        (cx + int(math.cos(rad) * 14), cy + int(math.sin(rad) * 14)),
                        (cx + int(math.cos(rad) * 19), cy + int(math.sin(rad) * 19)),
                        2,
                    )
            elif t_idx == 3:
                bask_col = (255, 255, 255) if is_sel else (194, 65, 12)
                pygame.draw.polygon(
                    surface,
                    bask_col,
                    [(cx - 16, cy - 2), (cx + 16, cy - 2), (cx + 11, cy + 14), (cx - 11, cy + 14)],
                )
                pygame.draw.arc(surface, bask_col, pygame.Rect(cx - 13, cy - 16, 26, 20), 0, 3.14, 3)
                pygame.draw.circle(surface, (239, 68, 68), (cx - 4, cy - 5), 5)
                pygame.draw.circle(surface, (234, 179, 8), (cx + 5, cy - 5), 5)
            lbl_surf = self._cached_text(self._tool_labels.get(label_key, "✦"), FontRole.DISPLAY, 18, (255, 255, 255) if is_sel else col)
            surface.blit(lbl_surf, (cx - lbl_surf.get_width() // 2, b_rect.bottom - lbl_surf.get_height() - 4))


__all__ = ["SerraRenderer", "POT_RECTS"]
