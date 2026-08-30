"""Bounded asset caches and backdrop rendering for Teatrino.

Owns shadow/glow/backdrop surfaces. Each cache is bounded with explicit
invalidation support and preserves the convert_alpha() once pattern where
applicable. Backdrop surfaces are opaque RGB and pre-rendered once.
"""

from __future__ import annotations

import math

import pygame

if __package__:
    from .teatrino_content import (
        BG_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        STAGE_GOLD_LIGHT,
        STAGE_WOOD_BASE,
        STAGE_WOOD_TOP,
        WHITE,
    )
else:
    from teatrino_content import (
        BG_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STAGE_CURTAIN,
        STAGE_CURTAIN_DARK,
        STAGE_CURTAIN_LIGHT,
        STAGE_GOLD,
        STAGE_GOLD_LIGHT,
        STAGE_WOOD_BASE,
        STAGE_WOOD_TOP,
        WHITE,
    )

# Import mix helper from platform without creating a local framework.
try:
    from greia_platform.activity_ui import mix
except Exception:  # fallback for isolated tests

    def mix(a, b, t):  # type: ignore[no-redef]
        return tuple(int(ac * (1 - t) + bc * t) for ac, bc in zip(a, b))


# Bounded caches — explicit limits appropriate to Acer floor.
_MAX_SHADOW_CACHE = 16
_MAX_GLOW_CACHE = 16
_MAX_BACKDROP_CACHE = 8

_SHADOW_SURFACES: dict[int, pygame.Surface] = {}
_GLOW_SURFACES: dict[int, pygame.Surface] = {}
_BACKDROP_CACHE: dict[str, pygame.Surface] = {}


def get_shadow_surface(size: int) -> pygame.Surface:
    cached = _SHADOW_SURFACES.get(size)
    if cached is None:
        cached = pygame.Surface((size, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(cached, (0, 0, 0, 85), (0, 0, size, 20))
        if len(_SHADOW_SURFACES) >= _MAX_SHADOW_CACHE:
            # Evict oldest entry (dict preserves insertion order).
            _SHADOW_SURFACES.pop(next(iter(_SHADOW_SURFACES)))
        _SHADOW_SURFACES[size] = cached
    return cached


def get_glow_surface(size: int) -> pygame.Surface:
    cached = _GLOW_SURFACES.get(size)
    if cached is None:
        dim = size + 30
        cached = pygame.Surface((dim, dim), pygame.SRCALPHA)
        pygame.draw.circle(cached, (254, 240, 138, 80), (dim // 2, dim // 2), (size + 20) // 2)
        if len(_GLOW_SURFACES) >= _MAX_GLOW_CACHE:
            _GLOW_SURFACES.pop(next(iter(_GLOW_SURFACES)))
        _GLOW_SURFACES[size] = cached
    return cached


def _render_cottage(surf: pygame.Surface) -> None:
    for y in range(0, 430, 4):
        col = mix((100, 195, 255), (210, 240, 255), y / 430.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 4))
    pygame.draw.circle(surf, (255, 245, 160), (840, 90), 54)
    pygame.draw.circle(surf, (255, 215, 0), (840, 90), 44)
    for ang_deg in range(0, 360, 30):
        ang = math.radians(ang_deg)
        x1 = 840 + math.cos(ang) * 58
        y1 = 90 + math.sin(ang) * 58
        x2 = 840 + math.cos(ang) * 82
        y2 = 90 + math.sin(ang) * 82
        pygame.draw.line(surf, (255, 220, 50), (x1, y1), (x2, y2), 4)
    rb_colors = [
        (239, 68, 68),
        (249, 115, 22),
        (234, 179, 8),
        (34, 197, 94),
        (59, 130, 246),
        (168, 85, 247),
    ]
    for r_idx, r_col in enumerate(rb_colors):
        pygame.draw.arc(surf, r_col, (60, 40 + r_idx * 6, 780, 560), 0.2, math.pi - 0.2, 7)
    for cx, cy, r in ((220, 110, 36), (260, 100, 44), (300, 110, 34), (720, 130, 32), (755, 122, 40), (790, 132, 30)):
        pygame.draw.circle(surf, WHITE, (cx, cy), r)
    pygame.draw.circle(surf, (110, 205, 90), (220, 480), 260)
    pygame.draw.circle(surf, (85, 185, 65), (820, 490), 280)
    pygame.draw.circle(surf, (125, 215, 105), (512, 540), 320)
    cot_x, cot_y, cot_w, cot_h = 420, 220, 184, 175
    pygame.draw.rect(surf, (245, 195, 120), (cot_x, cot_y, cot_w, cot_h), border_radius=12)
    pygame.draw.rect(surf, (135, 75, 25), (cot_x, cot_y, cot_w, cot_h), width=4, border_radius=12)
    for by in (cot_y + 45, cot_y + 90, cot_y + 135):
        pygame.draw.line(surf, (160, 95, 35), (cot_x, by), (cot_x + cot_w, by), 4)
    pygame.draw.rect(surf, (148, 163, 184), (cot_x + 120, cot_y - 65, 36, 70), border_radius=4)
    pygame.draw.rect(surf, (71, 85, 105), (cot_x + 116, cot_y - 70, 44, 10), border_radius=3)
    for sm_x, sm_y, sm_r in ((cot_x + 138, cot_y - 85, 12), (cot_x + 148, cot_y - 110, 16), (cot_x + 162, cot_y - 138, 20)):
        pygame.draw.circle(surf, (255, 255, 255, 200), (sm_x, sm_y), sm_r)
    roof_poly = [(cot_x - 30, cot_y + 10), (cot_x + cot_w // 2, cot_y - 85), (cot_x + cot_w + 30, cot_y + 10)]
    pygame.draw.polygon(surf, (220, 38, 38), roof_poly)
    pygame.draw.polygon(surf, (153, 27, 27), roof_poly, 4)
    for rx in range(cot_x - 10, cot_x + cot_w + 10, 24):
        pygame.draw.circle(surf, (239, 68, 68), (rx, cot_y + 6), 12)
    for wx in (cot_x + 22, cot_x + 110):
        pygame.draw.rect(surf, (254, 240, 138), (wx, cot_y + 35, 46, 52), border_radius=8)
        pygame.draw.rect(surf, (120, 65, 20), (wx, cot_y + 35, 46, 52), width=3, border_radius=8)
        pygame.draw.line(surf, (120, 65, 20), (wx + 23, cot_y + 35), (wx + 23, cot_y + 87), 2)
        pygame.draw.line(surf, (120, 65, 20), (wx, cot_y + 61), (wx + 46, cot_y + 61), 2)
        pygame.draw.rect(surf, (136, 70, 20), (wx - 6, cot_y + 84, 58, 16), border_radius=4)
        for fx in range(wx - 2, wx + 50, 11):
            f_col = (244, 114, 182) if (fx % 2 == 0) else (250, 204, 21)
            pygame.draw.circle(surf, f_col, (fx, cot_y + 82), 6)
            pygame.draw.circle(surf, WHITE, (fx, cot_y + 82), 2)
    door_x = cot_x + cot_w // 2 - 20
    pygame.draw.rect(surf, (161, 98, 7), (door_x, cot_y + 100, 40, 75), border_top_left_radius=18, border_top_right_radius=18)
    pygame.draw.rect(surf, (69, 26, 3), (door_x, cot_y + 100, 40, 75), width=3, border_top_left_radius=18, border_top_right_radius=18)
    pygame.draw.circle(surf, (254, 240, 138), (door_x + 30, cot_y + 140), 4)
    for px, py, pr in ((door_x + 20, cot_y + 185, 14), (door_x + 15, cot_y + 205, 16), (door_x + 28, cot_y + 215, 15)):
        pygame.draw.ellipse(surf, (203, 213, 225), (px - pr, py - 6, pr * 2, 14))
        pygame.draw.ellipse(surf, (148, 163, 184), (px - pr, py - 6, pr * 2, 14), 2)
    flower_spots = [
        (160, 400, (239, 68, 68)),
        (210, 415, (244, 114, 182)),
        (270, 395, (250, 204, 21)),
        (340, 420, (168, 85, 247)),
        (680, 410, (250, 204, 21)),
        (740, 395, (239, 68, 68)),
        (800, 418, (244, 114, 182)),
        (860, 402, (59, 130, 246)),
    ]
    for fx, fy, fcol in flower_spots:
        pygame.draw.line(surf, (22, 101, 52), (fx, fy + 24), (fx, fy), 4)
        pygame.draw.circle(surf, fcol, (fx, fy), 12)
        pygame.draw.circle(surf, (254, 240, 138), (fx, fy), 5)
    for btx, bty, bcol in ((310, 260, (244, 114, 182)), (710, 240, (56, 189, 248)), (820, 280, (250, 204, 21))):
        pygame.draw.ellipse(surf, bcol, (btx - 8, bty - 8, 8, 12))
        pygame.draw.ellipse(surf, bcol, (btx + 2, bty - 8, 8, 12))
        pygame.draw.line(surf, (40, 30, 20), (btx, bty - 6), (btx, bty + 6), 2)


def _render_castle(surf: pygame.Surface) -> None:
    for y in range(0, 430, 6):
        col = mix((30, 27, 75), (49, 46, 129), y / 430.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))
    for px in range(120, 920, 140):
        pygame.draw.rect(surf, (24, 24, 48), (px, 0, 48, 430))
        pygame.draw.rect(surf, (45, 45, 80), (px, 0, 48, 430), 2)
    for wx in (260, 476, 692):
        pygame.draw.rect(surf, (255, 230, 140), (wx, 110, 72, 130), border_top_left_radius=36, border_top_right_radius=36)
        pygame.draw.rect(surf, (60, 40, 20), (wx, 110, 72, 130), width=4, border_top_left_radius=36, border_top_right_radius=36)
        pygame.draw.line(surf, (60, 40, 20), (wx + 36, 110), (wx + 36, 240), 3)
        pygame.draw.line(surf, (60, 40, 20), (wx, 175), (wx + 72, 175), 3)
        pygame.draw.circle(surf, (239, 68, 68), (wx + 36, 140), 14)
    for bx, bcol in ((190, (185, 28, 28)), (820, (30, 64, 175))):
        poly = [(bx, 100), (bx + 40, 100), (bx + 40, 220), (bx + 20, 200), (bx, 220)]
        pygame.draw.polygon(surf, bcol, poly)
        pygame.draw.polygon(surf, STAGE_GOLD, poly, 2)
        pygame.draw.circle(surf, STAGE_GOLD, (bx + 20, 140), 6)
    for ch_x in (360, 660):
        pygame.draw.line(surf, STAGE_GOLD, (ch_x, 0), (ch_x, 70), 3)
        pygame.draw.ellipse(surf, STAGE_GOLD, (ch_x - 30, 65, 60, 16), 3)
        for fx in (ch_x - 22, ch_x, ch_x + 22):
            pygame.draw.circle(surf, (255, 245, 180), (fx, 62), 6)
            pygame.draw.circle(surf, (245, 130, 30), (fx, 62), 3)


def _render_ocean(surf: pygame.Surface) -> None:
    for y in range(0, 430, 6):
        col = mix((10, 40, 90), (16, 120, 175), y / 430.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))
    for rx, rw in ((240, 60), (450, 90), (680, 75)):
        beam_poly = [(rx, 0), (rx + rw, 0), (rx + rw + 70, 430), (rx - 40, 430)]
        beam_surf = pygame.Surface((REFERENCE_WIDTH, 430), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (255, 255, 255, 24), beam_poly)
        surf.blit(beam_surf, (0, 0))
    for kx in (160, 210, 800, 860):
        for seg in range(7):
            ky = 430 - seg * 45
            kx_off = int(math.sin(seg * 1.2) * 18)
            pygame.draw.ellipse(surf, (15, 110, 75), (kx + kx_off - 12, ky - 30, 24, 38))
    for cx, cr, col in ((280, 55, (244, 114, 182)), (340, 45, (251, 146, 60)), (670, 60, (168, 85, 247)), (740, 48, (234, 88, 12))):
        pygame.draw.circle(surf, col, (cx, 420), cr)
    pygame.draw.rect(surf, (120, 70, 30), (480, 390, 64, 36), border_radius=6)
    pygame.draw.rect(surf, STAGE_GOLD, (480, 390, 64, 36), width=3, border_radius=6)
    pygame.draw.circle(surf, STAGE_GOLD, (512, 408), 5)


def _render_forest(surf: pygame.Surface) -> None:
    for y in range(0, 430, 6):
        col = mix((16, 32, 38), (28, 72, 60), y / 430.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))
    pygame.draw.circle(surf, (255, 250, 210), (512, 115), 52)
    pygame.draw.circle(surf, (255, 255, 240), (512, 115), 45)
    pygame.draw.circle(surf, (18, 52, 42), (200, 340), 170)
    pygame.draw.circle(surf, (18, 52, 42), (824, 340), 170)
    pygame.draw.circle(surf, (28, 85, 65), (512, 220), 120)
    for mx, mcol in ((300, (236, 72, 153)), (340, (45, 212, 191)), (680, (250, 204, 21)), (720, (192, 132, 252))):
        pygame.draw.rect(surf, (255, 245, 230), (mx - 4, 395, 8, 30), border_radius=3)
        pygame.draw.ellipse(surf, mcol, (mx - 18, 385, 36, 20))
        pygame.draw.circle(surf, WHITE, (mx - 6, 392), 3)


def _render_sky(surf: pygame.Surface) -> None:
    for y in range(0, 430, 6):
        col = mix((40, 24, 75), (90, 50, 135), y / 430.0)
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 6))
    pygame.draw.circle(surf, (254, 240, 138), (720, 110), 48)
    pygame.draw.circle(surf, (40, 24, 75), (700, 100), 44)
    pygame.draw.circle(surf, (249, 115, 22), (280, 120), 30)
    pygame.draw.ellipse(surf, (254, 215, 170), (235, 114, 90, 12), width=3)
    for cx, cy in ((200, 350), (512, 330), (800, 360)):
        for ox, oy, r in ((-35, 10, 32), (0, -10, 42), (35, 10, 32)):
            pygame.draw.circle(surf, (240, 230, 255), (cx + ox, cy + oy), r)


def _generate_backdrop_surface(bg_id: str) -> pygame.Surface:
    surf = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
    if bg_id == "cottage":
        _render_cottage(surf)
    elif bg_id == "castle":
        _render_castle(surf)
    elif bg_id == "ocean":
        _render_ocean(surf)
    elif bg_id == "forest":
        _render_forest(surf)
    elif bg_id == "sky":
        _render_sky(surf)
    for y in range(430, REFERENCE_HEIGHT):
        col = mix(STAGE_WOOD_TOP, STAGE_WOOD_BASE, (y - 430) / (REFERENCE_HEIGHT - 430))
        pygame.draw.rect(surf, col, (0, y, REFERENCE_WIDTH, 1))
    for px in range(0, REFERENCE_WIDTH + 80, 80):
        pygame.draw.line(surf, (90, 45, 15), (px, 430), (int(px * 1.1 - 40), REFERENCE_HEIGHT), 2)
    pygame.draw.rect(surf, STAGE_GOLD, (0, 430, REFERENCE_WIDTH, 4))
    return surf


def render_backdrop_surface(bg_id: str) -> pygame.Surface:
    """Pre-render multi-layered storybook scenery to a static surface.

    Returns a cached opaque surface when available to avoid per-frame
    allocations. Cache is bounded and can be invalidated on resize.
    """
    cached = _BACKDROP_CACHE.get(bg_id)
    if cached is not None:
        return cached
    surf = _generate_backdrop_surface(bg_id)
    # Convert once pattern: opaque backdrops use convert() for fast blits.
    # Keep as fallback if display not initialized (e.g., headless tests).
    try:
        surf = surf.convert()
    except Exception:
        pass
    if len(_BACKDROP_CACHE) >= _MAX_BACKDROP_CACHE:
        _BACKDROP_CACHE.pop(next(iter(_BACKDROP_CACHE)))
    _BACKDROP_CACHE[bg_id] = surf
    return surf


def clear_backdrop_cache() -> None:
    _BACKDROP_CACHE.clear()


def clear_shadow_caches() -> None:
    _SHADOW_SURFACES.clear()
    _GLOW_SURFACES.clear()


def clear_all_caches() -> None:
    clear_backdrop_cache()
    clear_shadow_caches()


__all__ = [
    "get_shadow_surface",
    "get_glow_surface",
    "render_backdrop_surface",
    "clear_backdrop_cache",
    "clear_shadow_caches",
    "clear_all_caches",
]
