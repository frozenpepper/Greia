from __future__ import annotations

import math
import random

import pygame

from greia_platform.localization import LocalizationError
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

# Semantic label keys resolved once; capitals come from the case policy.
# Tab/action labels are resolved by the shared control kit wiring.
_LABEL_KEYS = (
    "panel.order",
    "panel.free",
    "panel.pantry",
    "prompt.pattern",
)


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

    Static bakery room/counter is prepared once and reused; interactive
    controls come from the shared control kit (ADR 0037). Per-frame font/scale/decode work is avoided via bounded caches
    that invalidate when the reference canvas or locale context changes.
    """

    def __init__(
        self,
        typography: GreiaTypography,
        resources=None,
    ) -> None:
        self._typography = typography
        self._resources = resources
        # A missing bundle or key degrades to pictograms, never to a fixed language.
        self._labels = {key: self._resolve(key) for key in _LABEL_KEYS}
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

    def _resolve(self, key: str) -> str:
        if self._resources is None:
            return ""
        try:
            return self._resources.text(key).strip()
        except LocalizationError:
            return ""

    def _caption(self, lead: str, key: str) -> str:
        """Join an optional pictogram with a resolved label."""
        return " ".join(part for part in (lead, self._labels.get(key, "")) if part)

    def _fit_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
        max_width: int,
        *,
        min_size: int = 13,
    ) -> pygame.Surface:
        """Cached text that shrinks (never clips) to fit longer translations."""
        current = size
        surf = self._cached_text(text, role, current, color)
        while surf.get_width() > max_width and current > min_size:
            current -= 1
            surf = self._cached_text(text, role, current, color)
        return surf

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
        """Render the bakery scene (1024x600 logical) without kit controls.

        Tabs, HUD chips, pantry/candidate tiles, Clear/Serve and the feedback
        banner are shared control-kit controls drawn by the app's
        ``ControlLayer`` (ADR 0037). ``feedback_text`` is accepted for
        compatibility; feedback is presented by the kit banner.
        """
        del feedback_text
        self._ensure_converted()
        surface.blit(self._backdrop, (0, 0))

        mode = model.mode
        if mode in {"orders", "free"}:
            if mode == "orders":
                ticket_rect = pygame.Rect(20, 90, 250, 350)
                pygame.draw.rect(surface, WHITE, ticket_rect, border_radius=20)
                pygame.draw.rect(surface, (255, 200, 220), ticket_rect, width=3, border_radius=20)
                pygame.draw.rect(surface, PINK, (20, 90, 250, 50), border_top_left_radius=20, border_top_right_radius=20)
                r_title = self._fit_text(
                    self._caption("📋", "panel.order"), FontRole.TITLE, 22, WHITE, 226
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
                f_title = self._fit_text(
                    self._caption("🎨", "panel.free"), FontRole.TITLE, 22, DARK_TEXT, 226
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

            # Right pantry shelf (the topping tiles are kit IconButtons).
            pantry_card = pygame.Rect(705, 90, 295, 350)
            pygame.draw.rect(surface, SHELF_COLOR, pantry_card, border_radius=20)
            p_title = self._fit_text(
                self._labels["panel.pantry"], FontRole.TITLE, 22, WHITE, 270
            )
            surface.blit(p_title, p_title.get_rect(center=(852, 115)))

        elif mode == "patterns":
            seq, _, _candidates = model.current_pattern
            pygame.draw.rect(surface, WHITE, (120, 120, 784, 210), border_radius=24)
            pygame.draw.rect(surface, PINK, (120, 120, 784, 210), width=3, border_radius=24)
            p_prompt = self._fit_text(
                self._labels["prompt.pattern"], FontRole.TITLE, 26, DARK_TEXT, 740
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

    def render_effects(self, surface: pygame.Surface) -> None:
        """Draw transient particles above scene, controls and cast."""
        for p in self._particles:
            p.draw(surface, self._typography)


__all__ = ["PasticceriaRenderer", "Particle"]
