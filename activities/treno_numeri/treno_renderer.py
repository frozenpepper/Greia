"""Treno Numeri — rendering helpers and bounded asset caches.

Owns image decode/scale caching (convert() once, bounded, invalidate on resize)
and stateless fruit drawing plus the full scene composition. No storage or
event IO. Text rendering uses GreiaTypography with a small bounded text cache.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pygame

from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH

ASSETS_DIR = Path(__file__).parent / "assets" / "runtime"

_MAX_IMAGE_CACHE = 16
_MAX_SCALE_CACHE = 48
_MAX_TEXT_CACHE = 64


class TrenoRenderer:
    """Own Treno presentation: cached assets, fruit drawing and scene render.

    Caches are bounded and survive only for the integer scale/size they were
    built for. ``invalidate`` clears scaled variants after a VIDEORESIZE;
    original decoded images remain cached.
    """

    def __init__(self, typography: GreiaTypography) -> None:
        self._typography = typography
        self._image_cache: dict[str, pygame.Surface | None] = {}
        self._scale_cache: dict[tuple[str, int, int], pygame.Surface | None] = {}
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        self._text_order: list[tuple[str, FontRole, int, tuple[int, int, int]]] = []
        self._star_value: int | None = None
        self._star_surface: pygame.Surface | None = None

    # -- cache management -------------------------------------------------

    def invalidate(self) -> None:
        """Clear scaled/text caches after the viewport changes size."""

        self._scale_cache.clear()
        self._text_cache.clear()
        self._text_order.clear()
        self._star_surface = None
        self._star_value = None

    def _load_asset_surface(self, filename: str) -> pygame.Surface | None:
        cached = self._image_cache.get(filename)
        if filename in self._image_cache:
            return cached
        if len(self._image_cache) >= _MAX_IMAGE_CACHE:
            # Evict oldest entry (dict preserves insertion order).
            oldest = next(iter(self._image_cache))
            del self._image_cache[oldest]
        path = ASSETS_DIR / filename
        if path.exists():
            try:
                surface = pygame.image.load(str(path)).convert_alpha()
            except Exception:
                surface = None
        else:
            surface = None
        self._image_cache[filename] = surface
        return surface

    def _get_scaled_asset(self, filename: str, width: int, height: int) -> pygame.Surface | None:
        key = (filename, width, height)
        if key in self._scale_cache:
            return self._scale_cache[key]
        if len(self._scale_cache) >= _MAX_SCALE_CACHE:
            oldest = next(iter(self._scale_cache))
            del self._scale_cache[oldest]
        orig = self._load_asset_surface(filename)
        if orig is not None:
            try:
                scaled = pygame.transform.smoothscale(orig, (width, height))
            except Exception:
                scaled = None
        else:
            scaled = None
        self._scale_cache[key] = scaled
        return scaled

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

    # -- public draw helpers ----------------------------------------------

    def draw_fruit(self, surface: pygame.Surface, fruit_id: str, cx: int, cy: int, size: int) -> None:
        asset_name = f"fruit_{fruit_id}.png"
        scaled = self._get_scaled_asset(asset_name, size, size)
        if scaled is not None:
            surface.blit(scaled, (cx - size // 2, cy - size // 2))
            return
        r = size // 2
        dark = (30, 41, 59)
        if fruit_id == "apple":
            pygame.draw.circle(surface, (239, 68, 68), (cx - r // 4, cy), r * 4 // 5)
            pygame.draw.circle(surface, (220, 38, 38), (cx + r // 4, cy), r * 4 // 5)
            pygame.draw.circle(surface, dark, (cx - r // 4, cy), r * 4 // 5, 2)
            pygame.draw.circle(surface, dark, (cx + r // 4, cy), r * 4 // 5, 2)
            pygame.draw.rect(surface, (120, 53, 15), (cx - 2, cy - r, 4, r // 2), border_radius=2)
            pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(cx + 2, cy - r + 2, r // 2, r // 3))
        elif fruit_id == "banana":
            pygame.draw.arc(
                surface,
                (234, 179, 8),
                pygame.Rect(cx - r, cy - r, r * 2, r * 2),
                0.6,
                2.6,
                max(4, r // 2),
            )
            pygame.draw.circle(surface, (161, 98, 7), (cx + r * 2 // 3, cy - r // 3), max(2, r // 6))
        elif fruit_id == "carrot":
            pts = [(cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), (cx, cy + r)]
            pygame.draw.polygon(surface, (249, 115, 22), pts)
            pygame.draw.polygon(surface, dark, pts, 2)
            pygame.draw.polygon(surface, (34, 197, 94), [(cx - 4, cy - r // 2), (cx - 8, cy - r), (cx, cy - r // 2)])
            pygame.draw.polygon(surface, (34, 197, 94), [(cx + 4, cy - r // 2), (cx + 8, cy - r), (cx, cy - r // 2)])
        else:  # strawberry
            pts = [(cx - r * 3 // 4, cy - r // 3), (cx + r * 3 // 4, cy - r // 3), (cx, cy + r)]
            pygame.draw.polygon(surface, (244, 63, 94), pts)
            pygame.draw.polygon(surface, dark, pts, 2)
            pygame.draw.polygon(
                surface,
                (34, 197, 94),
                [(cx - r // 2, cy - r // 2), (cx + r // 2, cy - r // 2), (cx, cy - r * 3 // 4)],
            )

    # -- full scene -------------------------------------------------------

    def render(
        self,
        surface: pygame.Surface,
        model: Any,
        train_offset_x: float,
        smoke_particles: list[dict[str, Any]],
        flying_items: list[dict[str, Any]],
        celebration_particles: list[dict[str, Any]],
        total_stars: int,
        t_now: float,
    ) -> None:
        """Render the complete Treno scene onto the reference canvas ``surface``."""

        # 1. Sky & Sun
        surface.fill((186, 230, 253))
        sun_cx, sun_cy = 150, 100
        sun_ang_base = t_now * 0.5
        for ray_i in range(12):
            ang = sun_ang_base + ray_i * (math.pi / 6.0)
            rx1 = sun_cx + math.cos(ang) * 46
            ry1 = sun_cy + math.sin(ang) * 46
            rx2 = sun_cx + math.cos(ang) * 62
            ry2 = sun_cy + math.sin(ang) * 62
            pygame.draw.line(surface, (253, 224, 71), (int(rx1), int(ry1)), (int(rx2), int(ry2)), 4)
        pygame.draw.circle(surface, (254, 240, 138), (sun_cx, sun_cy), 44)
        pygame.draw.circle(surface, (250, 204, 21), (sun_cx, sun_cy), 38)
        pygame.draw.circle(surface, (161, 98, 7), (sun_cx - 10, sun_cy - 4), 4)
        pygame.draw.circle(surface, (161, 98, 7), (sun_cx + 10, sun_cy - 4), 4)
        pygame.draw.arc(surface, (161, 98, 7), (sun_cx - 12, sun_cy - 4, 24, 18), math.pi, 0, 3)

        # Distant Cumulus Clouds
        for _c_idx, (cl_x, cl_y, cl_w, cl_h) in enumerate(
            [(380, 70, 140, 50), (680, 95, 180, 60), (880, 50, 120, 44)]
        ):
            cx_drift = int((cl_x - t_now * 4.0) % (REFERENCE_WIDTH + 300)) - 100
            pygame.draw.ellipse(surface, (255, 255, 255), (cx_drift, cl_y, cl_w, cl_h))
            pygame.draw.ellipse(surface, (241, 245, 249), (cx_drift + 10, cl_y - 12, cl_w - 40, cl_h))

        # 2. Layered Countryside Hills
        pygame.draw.ellipse(surface, (134, 239, 172), pygame.Rect(-120, 240, 650, 260))
        pygame.draw.ellipse(surface, (110, 231, 183), pygame.Rect(380, 230, 780, 280))
        pygame.draw.ellipse(surface, (74, 222, 128), pygame.Rect(120, 290, 520, 220))
        pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(580, 300, 500, 220))

        # Ground Meadow
        pygame.draw.rect(surface, (22, 163, 74), (0, 390, REFERENCE_WIDTH, 210))
        pygame.draw.rect(surface, (21, 128, 61), (0, 420, REFERENCE_WIDTH, 180))

        for fx, fy in [(60, 405), (280, 412), (520, 402), (760, 410), (940, 404)]:
            pygame.draw.circle(surface, (254, 240, 138), (fx, fy), 6)
            pygame.draw.circle(surface, (244, 63, 94), (fx - 4, fy - 3), 4)
            pygame.draw.circle(surface, (244, 63, 94), (fx + 4, fy - 3), 4)
            pygame.draw.circle(surface, (244, 63, 94), (fx, fy + 4), 4)

        # 3. Railway Track & Ballast Bed
        pygame.draw.rect(surface, (100, 116, 139), (0, 370, REFERENCE_WIDTH, 24))
        for gx in range(0, REFERENCE_WIDTH, 16):
            pygame.draw.circle(surface, (71, 85, 105), (gx + 8, 382), 4)
        for tx_idx in range(0, REFERENCE_WIDTH, 34):
            pygame.draw.rect(surface, (120, 53, 15), (tx_idx, 366, 16, 30), border_radius=3)
            pygame.draw.rect(surface, (69, 26, 3), (tx_idx + 2, 368, 12, 26), width=1, border_radius=2)
        pygame.draw.rect(surface, (148, 163, 184), (0, 368, REFERENCE_WIDTH, 6))
        pygame.draw.rect(surface, (241, 245, 249), (0, 368, REFERENCE_WIDTH, 2))
        pygame.draw.rect(surface, (71, 85, 105), (0, 374, REFERENCE_WIDTH, 3))

        # 4. Smoke Particles (behind train)
        for p in smoke_particles:
            alpha_surf = pygame.Surface((int(p["radius"] * 2), int(p["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(
                alpha_surf,
                (255, 255, 255, int(p["alpha"])),
                (int(p["radius"]), int(p["radius"])),
                int(p["radius"]),
            )
            pygame.draw.circle(
                alpha_surf,
                (226, 232, 240, int(p["alpha"] * 0.6)),
                (int(p["radius"] - 2), int(p["radius"] - 2)),
                int(p["radius"] * 0.7),
            )
            surface.blit(alpha_surf, (p["x"] - p["radius"], p["y"] - p["radius"]))

        # 5. Train Rendering (wagon + locomotive + conductor + wheels)
        tx = train_offset_x
        wheel_ang = tx * 0.12

        # A. Cargo Wagon (behind on left)
        wagon_x = 100 + tx
        wagon_surf = self._get_scaled_asset("wagon.png", 260, 162)
        if wagon_surf is not None:
            surface.blit(wagon_surf, (int(wagon_x), 215))
        else:
            pygame.draw.rect(surface, (217, 119, 6), (wagon_x, 240, 260, 130), border_radius=14)
        for idx in range(model.loaded_count):
            fx = wagon_x + 42 + (idx % 5) * 44
            fy = 285 + (idx // 5) * 36
            self.draw_fruit(surface, model.current_fruit["id"], int(fx), int(fy), 38)
        w_small_surf = self._get_scaled_asset("wheel_small.png", 46, 46)
        for wgw in (wagon_x + 55, wagon_x + 205):
            if w_small_surf is not None:
                rot_w = pygame.transform.rotate(w_small_surf, math.degrees(wheel_ang))
                surface.blit(rot_w, rot_w.get_rect(center=(int(wgw), 378)))
            else:
                pygame.draw.circle(surface, (30, 41, 59), (int(wgw), 378), 20)
                pygame.draw.circle(surface, (234, 179, 8), (int(wgw), 378), 12)

        # B. Locomotive
        loco_x = 360 + tx
        loco_surf = self._get_scaled_asset("locomotive.png", 340, 255)
        if loco_surf is not None:
            surface.blit(loco_surf, (int(loco_x), 130))
        else:
            pygame.draw.rect(surface, (239, 68, 68), (loco_x + 90, 210, 220, 150), border_radius=18)
            pygame.draw.rect(surface, (59, 130, 246), (loco_x, 180, 130, 180), border_radius=16)
        dani_surf = self._get_scaled_asset("conductor_dani.png", 66, 66)
        if dani_surf is not None:
            # need train_state for bob; infer from model plus external state
            # The caller passes celebration via particles; approximate train_state
            dani_y_bob = int(math.sin(t_now * 6.0) * 2.0)
            # expose train_state via attribute if present, else default 0
            ts = getattr(model, "train_state", "loading")
            if ts in ("arriving", "departing"):
                dani_y_bob = int(math.sin(t_now * 6.0) * 2.0)
            elif ts == "celebrating":
                dani_y_bob = -6 + int(math.sin(t_now * 12.0) * 5.0)
            else:
                dani_y_bob = 0
            surface.blit(dani_surf, (int(loco_x + 40), 195 + dani_y_bob))
        w_large_surf = self._get_scaled_asset("wheel_large.png", 66, 66)
        for wx in (loco_x + 130, loco_x + 205, loco_x + 280):
            if w_large_surf is not None:
                rot_wl = pygame.transform.rotate(w_large_surf, math.degrees(wheel_ang))
                surface.blit(rot_wl, rot_wl.get_rect(center=(int(wx), 378)))
            else:
                pygame.draw.circle(surface, (30, 41, 59), (int(wx), 378), 24)
                pygame.draw.circle(surface, (234, 179, 8), (int(wx), 378), 16)
        rod_y_off = math.sin(wheel_ang) * 9
        rod_x_off = math.cos(wheel_ang) * 9
        rod_p1 = (int(loco_x + 130 + rod_x_off), int(378 + rod_y_off))
        rod_p2 = (int(loco_x + 280 + rod_x_off), int(378 + rod_y_off))
        pygame.draw.line(surface, (148, 163, 184), rod_p1, rod_p2, 7)
        pygame.draw.line(surface, (51, 65, 85), rod_p1, rod_p2, 2)
        pygame.draw.circle(surface, (254, 240, 138), rod_p1, 5)
        pygame.draw.circle(surface, (254, 240, 138), rod_p2, 5)

        # 6. Flying Fruits
        for item in flying_items:
            t = item["t"]
            cx = item["start_x"] + (item["target_x"] - item["start_x"]) * t
            cy = item["start_y"] + (item["target_y"] - item["start_y"]) * t - math.sin(t * math.pi) * 140.0
            pygame.draw.ellipse(surface, (30, 41, 59, 80), (int(cx - 16), int(cy + 24), 32, 12))
            self.draw_fruit(surface, item["fruit"], int(cx), int(cy), 48)

        # 7. Top Station Equation Billboard
        goal_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 280, 14, 560, 94)
        pygame.draw.rect(surface, (255, 252, 245), goal_rect, border_radius=24)
        pygame.draw.rect(surface, (234, 179, 8), goal_rect, width=4, border_radius=24)
        pygame.draw.rect(
            surface, (254, 240, 138), (goal_rect.left + 6, goal_rect.top + 6, goal_rect.width - 12, 10), border_radius=5
        )
        if model.mode == "addition":
            num_a_surf = self._cached_text(str(model.val_a), FontRole.DISPLAY, 48, (217, 119, 6))
            surface.blit(num_a_surf, (goal_rect.left + 28, goal_rect.centery - num_a_surf.get_height() // 2))
            self.draw_fruit(surface, model.current_fruit["id"], goal_rect.left + 78, goal_rect.centery, 38)
            plus_surf = self._cached_text("+", FontRole.DISPLAY, 48, (100, 116, 139))
            surface.blit(plus_surf, (goal_rect.left + 114, goal_rect.centery - plus_surf.get_height() // 2))
            num_b_surf = self._cached_text(str(model.val_b), FontRole.DISPLAY, 48, (217, 119, 6))
            surface.blit(num_b_surf, (goal_rect.left + 158, goal_rect.centery - num_b_surf.get_height() // 2))
            self.draw_fruit(surface, model.current_fruit["id"], goal_rect.left + 208, goal_rect.centery, 38)
            eq_surf = self._cached_text("=", FontRole.DISPLAY, 48, (100, 116, 139))
            surface.blit(eq_surf, (goal_rect.left + 244, goal_rect.centery - eq_surf.get_height() // 2))
            num_tgt_surf = self._cached_text(str(model.target_count), FontRole.DISPLAY, 54, (22, 101, 52))
            surface.blit(num_tgt_surf, (goal_rect.left + 295, goal_rect.centery - num_tgt_surf.get_height() // 2))
            self.draw_fruit(surface, model.current_fruit["id"], goal_rect.left + 355, goal_rect.centery, 46)
            for s in range(model.target_count):
                slot_x = goal_rect.left + 405 + s * 26
                slot_y = goal_rect.centery
                if s < model.loaded_count:
                    pygame.draw.circle(surface, (34, 197, 94), (slot_x, slot_y), 11)
                    pygame.draw.circle(surface, (255, 255, 255), (slot_x - 3, slot_y - 3), 3)
                else:
                    pygame.draw.circle(surface, (203, 213, 225), (slot_x, slot_y), 11, 3)
        else:  # count mode
            num_tgt_surf = self._cached_text(
                f"{model.loaded_count} / {model.target_count}", FontRole.DISPLAY, 52, (22, 101, 52)
            )
            surface.blit(num_tgt_surf, (goal_rect.left + 60, goal_rect.centery - num_tgt_surf.get_height() // 2))
            self.draw_fruit(surface, model.current_fruit["id"], goal_rect.left + 280, goal_rect.centery, 52)
            for s in range(model.target_count):
                slot_x = goal_rect.left + 340 + s * 34
                slot_y = goal_rect.centery
                if s < model.loaded_count:
                    pygame.draw.circle(surface, (34, 197, 94), (slot_x, slot_y), 12)
                    pygame.draw.circle(surface, (255, 255, 255), (slot_x - 3, slot_y - 3), 4)
                else:
                    pygame.draw.circle(surface, (203, 213, 225), (slot_x, slot_y), 12, 3)

        # 8. Bottom Fruit Cargo Crates
        crate_surf = self._get_scaled_asset("crate_basket.png", 200, 130)
        if model.mode == "addition":
            b_a = pygame.Rect(80, 430, 200, 130)
            if crate_surf is not None:
                surface.blit(crate_surf, (b_a.left, b_a.top))
            else:
                pygame.draw.rect(surface, (254, 243, 199), b_a, border_radius=20)
                pygame.draw.rect(surface, (217, 119, 6), b_a, width=4, border_radius=20)
            lbl_a = self._cached_text(str(model.val_a), FontRole.DISPLAY, 46, (180, 83, 9))
            surface.blit(lbl_a, (b_a.centerx - 52, b_a.centery - lbl_a.get_height() // 2))
            for i in range(model.val_a):
                self.draw_fruit(
                    surface, model.current_fruit["id"], b_a.centerx + 10 + (i % 2) * 36, b_a.centery - 15 + (i // 2) * 30, 36
                )
            b_b = pygame.Rect(320, 430, 200, 130)
            if crate_surf is not None:
                surface.blit(crate_surf, (b_b.left, b_b.top))
            else:
                pygame.draw.rect(surface, (254, 243, 199), b_b, border_radius=20)
                pygame.draw.rect(surface, (217, 119, 6), b_b, width=4, border_radius=20)
            lbl_b = self._cached_text(str(model.val_b), FontRole.DISPLAY, 46, (180, 83, 9))
            surface.blit(lbl_b, (b_b.centerx - 52, b_b.centery - lbl_b.get_height() // 2))
            for i in range(model.val_b):
                self.draw_fruit(
                    surface, model.current_fruit["id"], b_b.centerx + 10 + (i % 2) * 36, b_b.centery - 15 + (i // 2) * 30, 36
                )
        else:
            b_c = pygame.Rect(120, 430, 280, 130)
            crate_large_surf = self._get_scaled_asset("crate_basket.png", 280, 130)
            if crate_large_surf is not None:
                surface.blit(crate_large_surf, (b_c.left, b_c.top))
            else:
                pygame.draw.rect(surface, (254, 243, 199), b_c, border_radius=20)
                pygame.draw.rect(surface, (217, 119, 6), b_c, width=4, border_radius=20)
            self.draw_fruit(surface, model.current_fruit["id"], b_c.centerx - 45, b_c.centery, 52)
            lbl_one = self._cached_text("+1", FontRole.DISPLAY, 48, (22, 101, 52))
            surface.blit(lbl_one, (b_c.centerx + 25, b_c.centery - lbl_one.get_height() // 2))

        # 9. Top Star Pill (HUD)
        star_pill = pygame.Rect(80, 16, 130, 56)
        pygame.draw.rect(surface, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surface, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(surface, (234, 179, 8), (star_pill.left + 30, star_pill.centery), 16)
        if self._star_value != total_stars or self._star_surface is None:
            self._star_value = total_stars
            self._star_surface = self._typography.render(str(total_stars), FontRole.DISPLAY, 28, (180, 83, 9))
        # also cache via bounded dict for consistency? keep direct small cache
        surface.blit(
            self._star_surface, (star_pill.left + 58, star_pill.centery - self._star_surface.get_height() // 2)
        )

        # 10. Celebration Stars Burst
        for p in celebration_particles:
            pygame.draw.circle(surface, p["color"], (int(p["x"]), int(p["y"])), int(p["size"]))
            pygame.draw.circle(surface, (255, 255, 255), (int(p["x"] - 2), int(p["y"] - 2)), int(p["size"] // 3))


__all__ = ["TrenoRenderer"]
