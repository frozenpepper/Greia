from __future__ import annotations

import math
import random

import pygame

from greia_platform.child_text import display_text
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .pasticceria_content import (
        BAKERY_COUNTER,
        BAKERY_WALL,
        COUNTER_TOP,
        DARK_TEXT,
        GOLD,
        PINK,
        PLATE_COLOR,
        PLATE_RIM,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_COLOR,
        TOPPINGS,
        WHITE,
    )
else:
    from pasticceria_content import (
        BAKERY_COUNTER,
        BAKERY_WALL,
        COUNTER_TOP,
        DARK_TEXT,
        GOLD,
        PINK,
        PLATE_COLOR,
        PLATE_RIM,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_COLOR,
        TOPPINGS,
        WHITE,
    )

# Bounded cache sizes appropriate to Acer floor.
_MAX_TEXT_CACHE = 64
_MAX_ICON_CACHE = 32
_MAX_PARTICLES = 96


class Particle:
    """Transient visual particle owned by the renderer."""

    def __init__(self, x: float, y: float, symbol: str, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        self.symbol = symbol
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 6.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.05)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.life > 0:
            sz = max(12, int(28 * self.life))
            p_surf = typography.render(self.symbol, FontRole.DISPLAY, sz, self.color)
            surface.blit(p_surf, (int(self.x) - p_surf.get_width() // 2, int(self.y) - p_surf.get_height() // 2))


class PasticceriaRenderer:
    """Own Pasticceria Pygame presentation, geometry and bounded transient effects.

    Static bakery room/counter, mode tabs and HUD chrome are prepared once
    and reused. Per-frame font/scale/decode work is avoided via bounded caches
    that invalidate when the reference canvas or locale context changes.
    """

    def __init__(
        self,
        typography: GreiaTypography,
        resources=None,
        active_locale: str = "it",
    ) -> None:
        self._typography = typography
        self._resources = resources
        self._active_locale = active_locale
        self._backdrop: pygame.Surface = self._build_backdrop()
        self._backdrop_converted = False
        # Bounded caches: text surfaces and topping icons.
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        self._icon_cache: dict[tuple[str, int], pygame.Surface] = {}
        # Reusable halo for placed toppings (64x64) – built once, convert_alpha once.
        self._halo: pygame.Surface | None = None
        self._halo_converted = False
        # Bounded transient particles.
        self._particles: list[Particle] = []

    # -- cache management --
    def on_resize(self) -> None:
        """Invalidate display-dependent conversions after a VIDEORESIZE."""
        self._backdrop_converted = False
        self._halo_converted = False

    def _ensure_converted(self) -> None:
        # convert() requires an initialized display; defer until first render.
        if not self._backdrop_converted and pygame.display.get_surface() is not None:
            try:
                self._backdrop = self._backdrop.convert()
                self._backdrop_converted = True
            except pygame.error:
                pass
        if self._halo is not None and not self._halo_converted and pygame.display.get_surface() is not None:
            try:
                self._halo = self._halo.convert_alpha()
                self._halo_converted = True
            except pygame.error:
                pass

    def _build_backdrop(self) -> pygame.Surface:
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(BAKERY_WALL)
        for wx in range(0, REFERENCE_WIDTH, 40):
            pygame.draw.rect(surface, (255, 232, 220), (wx, 0, 20, 110))
        pygame.draw.rect(surface, BAKERY_COUNTER, (0, 460, REFERENCE_WIDTH, 140))
        pygame.draw.rect(surface, COUNTER_TOP, (0, 450, REFERENCE_WIDTH, 20))
        return surface

    def _get_halo(self) -> pygame.Surface:
        if self._halo is None:
            halo = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 255, 255, 220), (32, 32), 26)
            pygame.draw.circle(halo, (200, 160, 130, 180), (32, 32), 26, width=2)
            self._halo = halo
            self._halo_converted = False
            self._ensure_converted()
        return self._halo

    def _cached_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        key = (text, role, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._typography.render(text, role, size, color)
        # Bounded insertion: evict oldest when full.
        if len(self._text_cache) >= _MAX_TEXT_CACHE:
            # Remove arbitrary first entry (dict keeps insertion order).
            first = next(iter(self._text_cache))
            del self._text_cache[first]
        self._text_cache[key] = rendered
        return rendered

    def _cached_icon(self, icon: str, size: int) -> pygame.Surface:
        key = (icon, size)
        cached = self._icon_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._typography.render(icon, FontRole.DISPLAY, size, DARK_TEXT)
        if len(self._icon_cache) >= _MAX_ICON_CACHE:
            first = next(iter(self._icon_cache))
            del self._icon_cache[first]
        self._icon_cache[key] = rendered
        return rendered

    def _localized(self, key: str, fallback_it: str, fallback_en: str) -> str:
        # Prefer localized resources when available; fall back to display_text handling.
        if self._resources is not None:
            try:
                return self._resources.text(key)
            except Exception:
                pass
        # display_text applies uppercase policy; choose fallback by locale.
        raw = fallback_it if self._active_locale == "it" else fallback_en
        return display_text(raw)

    # -- particles --
    @property
    def particles(self) -> list[Particle]:
        return self._particles

    def update(self, dt: float = 0.035) -> None:
        # Particles use their own decay, not dt, to preserve original feel; dt kept for API symmetry.
        self._particles = [p for p in self._particles if p.update()]

    def spawn_at(self, x: float, y: float, symbol: str, color: tuple[int, int, int], count: int = 1) -> None:
        for _ in range(count):
            self._particles.append(Particle(x, y, symbol, color))
        if len(self._particles) > _MAX_PARTICLES:
            self._particles = self._particles[-_MAX_PARTICLES:]

    def spawn_random_center(self, symbol_choices: list[str], color: tuple[int, int, int], count: int) -> None:
        for _ in range(count):
            self.spawn_at(465, 340, random.choice(symbol_choices), color, 1)

    # -- main render entry --
    def render(
        self,
        surface: pygame.Surface,
        model,
        feedback_text: str | None = None,
    ) -> None:
        """Render the full logical canvas (1024x600) into surface."""
        self._ensure_converted()
        # 1. Bakery Room & Counter (backdrop)
        surface.blit(self._backdrop, (0, 0))

        # 2. Header Mode Tabs
        mode = model.mode
        btn1_c = GOLD if mode == "orders" else WHITE
        btn2_c = GOLD if mode == "patterns" else WHITE
        btn3_c = GOLD if mode == "free" else WHITE
        for b_name, b_col, b_x in [
            ("🧁 Ordini" if self._active_locale == "it" else "🧁 Orders", btn1_c, 230),
            ("🍪 Sequenze" if self._active_locale == "it" else "🍪 Patterns", btn2_c, 405),
            ("🎨 Libero" if self._active_locale == "it" else "🎨 Free", btn3_c, 580),
        ]:
            b_rect = pygame.Rect(b_x, 12, 160, 52)
            pygame.draw.rect(surface, b_col, b_rect, border_radius=16)
            pygame.draw.rect(surface, (200, 160, 130), b_rect, width=2, border_radius=16)
            m_surf = self._cached_text(b_name, FontRole.TITLE, 22, DARK_TEXT)
            surface.blit(m_surf, m_surf.get_rect(center=b_rect.center))

        # 3. Top-Right HUD Badge
        hud_badge = pygame.Rect(REFERENCE_WIDTH - 250, 12, 235, 52)
        pygame.draw.rect(surface, WHITE, hud_badge, border_radius=16)
        pygame.draw.rect(surface, (200, 160, 130), hud_badge, width=2, border_radius=16)
        hud_txt = f"⭐ {model.stars}   🏆 {model.score}"
        h_surf = self._cached_text(hud_txt, FontRole.TITLE, 24, (180, 90, 20))
        surface.blit(h_surf, h_surf.get_rect(center=hud_badge.center))

        # 4. Mode Content Rendering
        if mode in {"orders", "free"}:
            if mode == "orders":
                ticket_rect = pygame.Rect(20, 90, 250, 350)
                pygame.draw.rect(surface, WHITE, ticket_rect, border_radius=20)
                pygame.draw.rect(surface, (255, 200, 220), ticket_rect, width=3, border_radius=20)
                pygame.draw.rect(surface, PINK, (20, 90, 250, 50), border_top_left_radius=20, border_top_right_radius=20)
                r_title = self._cached_text(
                    display_text("📋 Ricetta Dolce" if self._active_locale == "it" else "📋 Sweet Order"),
                    FontRole.TITLE,
                    22,
                    WHITE,
                )
                surface.blit(r_title, r_title.get_rect(center=(145, 115)))

                for o_idx, (t_id, t_qty) in enumerate(model.current_order):
                    icon_sym = next(t[1] for t in TOPPINGS if t[0] == t_id)
                    oy = 155 + o_idx * 135
                    item_rect = pygame.Rect(32, oy, 226, 125)
                    pygame.draw.rect(surface, (255, 248, 240), item_rect, border_radius=16)
                    pygame.draw.rect(surface, (245, 215, 195), item_rect, width=2, border_radius=16)
                    t_str = f"{t_qty} x {icon_sym}"
                    txt_o = self._cached_text(t_str, FontRole.DISPLAY, 44, DARK_TEXT)
                    surface.blit(txt_o, txt_o.get_rect(center=(145, oy + 38)))
                    visual_row = " ".join([icon_sym] * t_qty)
                    vis_surf = self._cached_text(visual_row, FontRole.DISPLAY, 28, DARK_TEXT)
                    surface.blit(vis_surf, vis_surf.get_rect(center=(145, oy + 88)))
            else:
                ticket_rect = pygame.Rect(20, 90, 250, 220)
                pygame.draw.rect(surface, WHITE, ticket_rect, border_radius=20)
                pygame.draw.rect(surface, (255, 200, 220), ticket_rect, width=3, border_radius=20)
                f_title = self._cached_text(
                    display_text("🎨 Decora a piacere!" if self._active_locale == "it" else "🎨 Decorate freely!"),
                    FontRole.TITLE,
                    22,
                    DARK_TEXT,
                )
                surface.blit(f_title, f_title.get_rect(center=(145, 200)))

            # Center Plate & Cake
            pygame.draw.ellipse(surface, PLATE_RIM, (280, 235, 390, 220))
            pygame.draw.ellipse(surface, PLATE_COLOR, (295, 245, 360, 200))
            pygame.draw.ellipse(surface, (230, 180, 120), (320, 265, 310, 160))
            pygame.draw.ellipse(surface, (255, 175, 200), (335, 275, 280, 130))
            pygame.draw.ellipse(surface, WHITE, (360, 290, 230, 90))

            halo_surf = self._get_halo()
            for t_id, t_icon, tx, ty in model.placed_toppings:
                surface.blit(halo_surf, (tx - 32, ty - 32))
                t_surf = self._cached_icon(t_icon, 40)
                surface.blit(t_surf, t_surf.get_rect(center=(tx, ty)))

            # Right Pantry Shelf
            pantry_card = pygame.Rect(705, 90, 295, 350)
            pygame.draw.rect(surface, SHELF_COLOR, pantry_card, border_radius=20)
            p_title = self._cached_text(
                display_text("Dispensa Topping" if self._active_locale == "it" else "Pantry Toppings"),
                FontRole.TITLE,
                22,
                WHITE,
            )
            surface.blit(p_title, p_title.get_rect(center=(852, 115)))

            for idx, (t_id, t_icon, _) in enumerate(TOPPINGS):
                col_idx = idx % 2
                row_idx = idx // 2
                bx = 720 + col_idx * 135
                by = 140 + row_idx * 95
                b_rect = pygame.Rect(bx, by, 125, 85)
                pygame.draw.rect(surface, WHITE, b_rect, border_radius=16)
                pygame.draw.rect(surface, (240, 215, 190), b_rect, width=2, border_radius=16)
                i_surf = self._cached_icon(t_icon, 50)
                surface.blit(i_surf, i_surf.get_rect(center=b_rect.center))

            # 🧹 Pulisci (Clean) Button
            clean_rect = pygame.Rect(710, 455, 130, 95)
            pygame.draw.rect(surface, (230, 240, 250), clean_rect, border_radius=18)
            pygame.draw.rect(surface, (180, 205, 230), clean_rect, width=3, border_radius=18)
            c_icon = self._cached_text("🧹", FontRole.DISPLAY, 48, DARK_TEXT)
            c_label = self._cached_text(display_text("Pulisci" if self._active_locale == "it" else "Clear"), FontRole.TITLE, 18, DARK_TEXT)
            surface.blit(c_icon, c_icon.get_rect(center=(clean_rect.centerx, clean_rect.centery - 14)))
            surface.blit(c_label, c_label.get_rect(center=(clean_rect.centerx, clean_rect.centery + 24)))

            # 🔔 SERVI! (Serve) Button
            serve_rect = pygame.Rect(855, 455, 145, 95)
            pygame.draw.rect(surface, GOLD, serve_rect, border_radius=18)
            pygame.draw.rect(surface, (220, 150, 20), serve_rect, width=3, border_radius=18)
            s_icon = self._cached_text("🔔", FontRole.DISPLAY, 48, DARK_TEXT)
            s_label = self._cached_text("SERVI!" if self._active_locale == "it" else "SERVE!", FontRole.DISPLAY, 20, DARK_TEXT)
            surface.blit(s_icon, s_icon.get_rect(center=(serve_rect.centerx, serve_rect.centery - 14)))
            surface.blit(s_label, s_label.get_rect(center=(serve_rect.centerx, serve_rect.centery + 24)))

        elif mode == "patterns":
            seq, _, candidates = model.current_pattern
            pygame.draw.rect(surface, WHITE, (120, 120, 784, 210), border_radius=24)
            pygame.draw.rect(surface, PINK, (120, 120, 784, 210), width=3, border_radius=24)
            p_prompt = self._cached_text(
                display_text("Quale biscotto completa la sequenza?" if self._active_locale == "it" else "Which cookie completes the pattern?"),
                FontRole.TITLE,
                26,
                DARK_TEXT,
            )
            surface.blit(p_prompt, p_prompt.get_rect(center=(512, 160)))

            total_items = len(seq) + 1
            start_x = 512 - (total_items * 55)
            for s_i, sym in enumerate(seq):
                ck_rect = pygame.Rect(start_x + s_i * 110, 205, 95, 95)
                pygame.draw.rect(surface, (255, 245, 230), ck_rect, border_radius=18)
                pygame.draw.rect(surface, (230, 180, 130), ck_rect, width=3, border_radius=18)
                ck_sym = self._cached_icon(sym, 48)
                surface.blit(ck_sym, ck_sym.get_rect(center=ck_rect.center))

            slot_rect = pygame.Rect(start_x + len(seq) * 110, 205, 95, 95)
            pygame.draw.rect(surface, (255, 235, 160), slot_rect, border_radius=18)
            pygame.draw.rect(surface, GOLD, slot_rect, width=4, border_radius=18)
            q_sym = self._cached_text("?", FontRole.DISPLAY, 48, DARK_TEXT)
            surface.blit(q_sym, q_sym.get_rect(center=slot_rect.center))

            for c_i, cand_sym in enumerate(candidates):
                cx = 330 + c_i * 135
                cy = 380
                c_rect = pygame.Rect(cx, cy, 110, 110)
                pygame.draw.rect(surface, WHITE, c_rect, border_radius=20)
                pygame.draw.rect(surface, PINK, c_rect, width=3, border_radius=20)
                cand_s = self._cached_icon(cand_sym, 52)
                surface.blit(cand_s, cand_s.get_rect(center=c_rect.center))

        # Particles
        for p in self._particles:
            p.draw(surface, self._typography)

        # Feedback Toast
        effective_feedback = feedback_text if feedback_text is not None else model.feedback_text
        if effective_feedback:
            f_rect = pygame.Rect(262, 510, 500, 52)
            pygame.draw.rect(surface, WHITE, f_rect, border_radius=18)
            pygame.draw.rect(surface, PINK, f_rect, width=3, border_radius=18)
            t_msg = self._cached_text(effective_feedback, FontRole.TITLE, 26, DARK_TEXT)
            surface.blit(t_msg, t_msg.get_rect(center=f_rect.center))


__all__ = ["PasticceriaRenderer", "Particle"]
