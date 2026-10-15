"""Acquario Magico — drawing helpers.

The renderer is a small set of stateless draw helpers plus the
:class:`AquariumRenderer` that owns the prepared tool label
surfaces and the resource surfaces used by the active frame.

Drawing rules:

- the day/night scene is a pre-baked background owned by
  :class:`AquariumAssetCache`; the renderer never regenerates it
- the sunlight ray layer is a small per-frame alpha surface
  (one layer, not per-ray)
- the per-creature sprite lookup uses
  ``assets.scaled(filename, w, h, facing_right)`` which is the
  measurement-validated 2026-08-22 cache
- the creature's spin transform is bounded (a 30° wobble, no
  continuous rotation): ``pygame.transform.rotate`` is therefore
  bounded to a small handful of entries in practice; the renderer
  does not pre-bake rotations because the angle depends on
  ``spin_t`` and a tiny ``sin(8x)*30`` envelope.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Optional

import pygame

from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .acquarium_assets import AquariumAssetCache
    from .acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ToolIndex
else:
    from acquarium_assets import AquariumAssetCache
    from acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ToolIndex


# The HUD pill starts clear of the trusted Home/Back region, which the
# platform reserves in full (both slots) so layout never jumps with context.
_HUD_LEFT = (
    ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    .protected_region.right
    + 8
)


@dataclass
class ToolLayout:
    """Pre-computed geometry of the bottom toolbar buttons.

    The renderer reads the same rectangles the lifecycle uses
    for hit-testing, so the visual and the input agree.
    """

    tool_y: int
    rects: list[tuple[pygame.Rect, int, tuple[int, int, int]]]

    @classmethod
    def default(cls) -> "ToolLayout":
        tool_y = REFERENCE_HEIGHT - 85
        rects: list[tuple[pygame.Rect, int, tuple[int, int, int]]] = [
            (pygame.Rect(100, tool_y, 180, 72), ToolIndex.SPAWN, (34, 197, 94)),
            (pygame.Rect(310, tool_y, 180, 72), ToolIndex.FEED, (249, 115, 22)),
            (pygame.Rect(520, tool_y, 180, 72), ToolIndex.BUBBLES, (56, 189, 248)),
            (pygame.Rect(730, tool_y, 180, 72), ToolIndex.DAY_NIGHT, (168, 85, 247)),
        ]
        return cls(tool_y=tool_y, rects=rects)


class AquariumRenderer:
    """Owner of the prepared label surfaces and draw routines.

    The renderer holds the cached typography label surfaces for
    the four tool buttons. The label surface key is the tool
    index (``0``..``3``) and the day/night label uses
    ``"night"``/``"day"`` keys for the toggle.
    """

    def __init__(
        self,
        assets: AquariumAssetCache,
        typography: GreiaTypography,
        label_text: dict[str, str],
    ) -> None:
        self._assets = assets
        self._typography = typography
        self._label_text = label_text
        self._label_surfaces: dict[Any, pygame.Surface] = {
            ToolIndex.SPAWN: typography.render(label_text["add_fish"], FontRole.DISPLAY, 16, (255, 255, 255)),
            ToolIndex.FEED: typography.render(label_text["feed"], FontRole.DISPLAY, 16, (255, 255, 255)),
            ToolIndex.BUBBLES: typography.render(label_text["bubbles"], FontRole.DISPLAY, 16, (255, 255, 255)),
            "night": typography.render(label_text["night"], FontRole.DISPLAY, 16, (255, 255, 255)),
            "day": typography.render(label_text["day"], FontRole.DISPLAY, 16, (255, 255, 255)),
        }
        self.tool_layout = ToolLayout.default()
        # Creature counter label: one surface per distinct count, bounded.
        self._count_surfaces: dict[int, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def draw_background(self, surface: pygame.Surface, glow_mode: bool, t_now: float) -> None:
        surface.blit(self._assets.background(glow_mode), (0, 0))
        if glow_mode:
            self._draw_night_jellies(surface, t_now)
        else:
            self._draw_day_sunbeams(surface, t_now)

    def _draw_night_jellies(self, surface: pygame.Surface, t_now: float) -> None:
        for jx, jy in [(220, 180), (780, 210), (480, 130)]:
            jelly_y = int(jy + math.sin(t_now * 1.8 + jx) * 14)
            pygame.draw.circle(surface, (168, 85, 247), (jx, jelly_y), 16)
            pygame.draw.circle(surface, (232, 121, 249), (jx, jelly_y), 10)

    def _draw_day_sunbeams(self, surface: pygame.Surface, t_now: float) -> None:
        ray_layer = pygame.Surface((REFERENCE_WIDTH, 420), pygame.SRCALPHA)
        for ray_i, rx in enumerate([160, 360, 580, 800]):
            sway = math.sin(t_now * 0.8 + ray_i * 1.5) * 20
            pts = [
                (rx - 15, 0),
                (rx + 25, 0),
                (rx + 55 + sway, 380),
                (rx - 25 + sway, 380),
            ]
            alpha = int(14 + math.sin(t_now * 1.4 + ray_i) * 5)
            pygame.draw.polygon(ray_layer, (254, 240, 138, alpha), pts)
        surface.blit(ray_layer, (0, 0))

    # ------------------------------------------------------------------
    # Decorative props
    # ------------------------------------------------------------------

    def draw_chest(
        self,
        surface: pygame.Surface,
        chest_rect: pygame.Rect,
        open_lift: float,
    ) -> None:
        chest_surf = self._assets.scaled("chest.png", 112, 88)
        if chest_surf is None:
            return
        if open_lift > 0:
            lift_y = int(chest_rect.top - 6)
            surface.blit(chest_surf, (chest_rect.left, lift_y))
            pygame.draw.circle(surface, (253, 224, 71), (chest_rect.centerx, lift_y + 35), 14)
            pygame.draw.circle(surface, (255, 255, 255), (chest_rect.centerx, lift_y + 35), 7)
        else:
            surface.blit(chest_surf, (chest_rect.left, chest_rect.top))

    # ------------------------------------------------------------------
    # Dynamic content
    # ------------------------------------------------------------------

    def draw_food(self, surface: pygame.Surface, pellets: list[dict[str, Any]]) -> None:
        for pellet in pellets:
            fx, fy, fsz = int(pellet["x"]), int(pellet["y"]), int(pellet["size"])
            pygame.draw.circle(surface, (245, 158, 11), (fx, fy), fsz)
            pygame.draw.circle(surface, (254, 240, 138), (fx - 1, fy - 1), max(1, fsz // 2))

    def draw_creatures(self, surface: pygame.Surface, creatures: list[dict[str, Any]]) -> None:
        for creature in creatures:
            species = creature["spec"]
            cx = int(creature["x"])
            cy = int(creature["y"])
            facing_right = creature["facing"] > 0
            cw = species.get("w", 72)
            ch = species.get("h", 54)
            if creature["puffed_t"] > 0 and species["id"] == "puffer":
                cw = int(cw * 1.4)
                ch = int(ch * 1.4)

            creature_surf = self._assets.scaled(
                f"{species['id']}.png", cw, ch, facing_right=facing_right
            )
            if creature_surf is not None:
                if creature["spin_t"] > 0:
                    rotation = int(math.sin(creature["spin_t"] * 8.0) * 30.0)
                    image = pygame.transform.rotate(creature_surf, rotation)
                else:
                    image = creature_surf
                surface.blit(image, image.get_rect(center=(cx, cy)))
            else:
                self._draw_creature_vector_fallback(surface, creature, cx, cy, facing_right)

            if creature["happy_t"] > 0:
                heart_y = int(cy - ch // 2 - 14 - math.sin(creature["happy_t"] * 4.0) * 4)
                pygame.draw.circle(surface, (244, 63, 94), (cx, heart_y), 7)
                pygame.draw.circle(surface, (255, 255, 255), (cx - 2, heart_y - 2), 3)

    def _draw_creature_vector_fallback(
        self,
        surface: pygame.Surface,
        creature: dict[str, Any],
        cx: int,
        cy: int,
        facing_right: bool,
    ) -> None:
        species = creature["spec"]
        base_size = species["size"]
        pygame.draw.ellipse(
            surface, species["color"], (cx - base_size, cy - base_size // 2, base_size * 2, base_size)
        )
        eye_x = cx + (base_size // 2 if facing_right else -base_size // 2)
        pygame.draw.circle(surface, (255, 255, 255), (eye_x, cy - base_size // 6), 6)
        pygame.draw.circle(surface, (15, 23, 42), (eye_x, cy - base_size // 6), 3)

    def draw_bubbles(self, surface: pygame.Surface, bubbles: list[dict[str, Any]]) -> None:
        for bubble in bubbles:
            bx, by, bsz = int(bubble["x"]), int(bubble["y"]), int(bubble["size"])
            pygame.draw.circle(surface, (255, 255, 255), (bx, by), bsz, 2)
            pygame.draw.circle(surface, (255, 255, 255), (bx - bsz // 3, by - bsz // 3), max(1, bsz // 4))

    def draw_particles(self, surface: pygame.Surface, particles: list[dict[str, Any]]) -> None:
        for particle in particles:
            current_size = max(1.5, particle["size"] * max(0.0, min(1.0, particle["life"])))
            pygame.draw.circle(
                surface, particle["color"], (int(particle["x"]), int(particle["y"])), int(current_size)
            )

    # ------------------------------------------------------------------
    # HUD + toolbar
    # ------------------------------------------------------------------

    def draw_hud(self, surface: pygame.Surface, creature_count: int) -> None:
        hud_pill = pygame.Rect(_HUD_LEFT, 16, 170, 56)
        pygame.draw.rect(surface, (255, 255, 255), hud_pill, border_radius=18)
        pygame.draw.rect(surface, (56, 189, 248), hud_pill, width=3, border_radius=18)
        pygame.draw.circle(surface, (56, 189, 248), (hud_pill.left + 28, hud_pill.centery), 16)
        mini = self._assets.scaled("clownfish.png", 26, 20)
        if mini is not None:
            surface.blit(mini, mini.get_rect(center=(hud_pill.left + 28, hud_pill.centery)))
        label = self._count_label(creature_count)
        surface.blit(label, (hud_pill.left + 54, hud_pill.centery - label.get_height() // 2))

    def _count_label(self, creature_count: int) -> pygame.Surface:
        cached = self._count_surfaces.get(creature_count)
        if cached is None:
            if len(self._count_surfaces) >= 32:
                self._count_surfaces.clear()
            cached = self._typography.render(
                f"{creature_count} / 20", FontRole.DISPLAY, 22, (2, 132, 199)
            )
            self._count_surfaces[creature_count] = cached
        return cached

    def draw_toolbar(
        self,
        surface: pygame.Surface,
        active_tool: int,
        glow_mode: bool,
        spawn_selector_idx: int,
    ) -> None:
        for button_rect, tool_idx, color in self.tool_layout.rects:
            is_active = active_tool == tool_idx
            button_color = color if not glow_mode or tool_idx != ToolIndex.DAY_NIGHT else (147, 51, 234)
            pygame.draw.rect(surface, button_color, button_rect, border_radius=20)
            pygame.draw.rect(
                surface,
                (254, 240, 138) if is_active else (255, 255, 255),
                button_rect,
                width=4 if is_active else 2,
                border_radius=20,
            )
            cx, cy = button_rect.centerx, button_rect.top + 24
            if tool_idx == ToolIndex.SPAWN:
                self._draw_spawn_button(surface, cx, cy, spawn_selector_idx)
                label = self._label_surfaces[ToolIndex.SPAWN]
            elif tool_idx == ToolIndex.FEED:
                self._draw_feed_button(surface, cx, cy)
                label = self._label_surfaces[ToolIndex.FEED]
            elif tool_idx == ToolIndex.BUBBLES:
                self._draw_bubbles_button(surface, cx, cy)
                label = self._label_surfaces[ToolIndex.BUBBLES]
            else:
                if glow_mode:
                    self._draw_night_button(surface, cx, cy, button_color)
                    label = self._label_surfaces["night"]
                else:
                    self._draw_day_button(surface, cx, cy)
                    label = self._label_surfaces["day"]
            surface.blit(label, (cx - label.get_width() // 2, button_rect.bottom - 24))

    def _draw_spawn_button(self, surface: pygame.Surface, cx: int, cy: int, spawn_selector_idx: int) -> None:
        if __package__:
            from .acquarium_content import SPECIES
        else:
            from acquarium_content import SPECIES

        current_species = SPECIES[spawn_selector_idx % len(SPECIES)]
        icon = self._assets.scaled(f"{current_species['id']}.png", 36, 28)
        if icon is not None:
            surface.blit(icon, icon.get_rect(center=(cx, cy)))

    @staticmethod
    def _draw_feed_button(surface: pygame.Surface, cx: int, cy: int) -> None:
        pygame.draw.circle(surface, (254, 240, 138), (cx - 8, cy), 7)
        pygame.draw.circle(surface, (245, 158, 11), (cx + 8, cy), 7)
        pygame.draw.circle(surface, (251, 146, 60), (cx, cy - 6), 6)

    @staticmethod
    def _draw_bubbles_button(surface: pygame.Surface, cx: int, cy: int) -> None:
        pygame.draw.circle(surface, (255, 255, 255), (cx - 8, cy + 4), 9, 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx + 8, cy - 4), 11, 2)

    @staticmethod
    def _draw_night_button(surface: pygame.Surface, cx: int, cy: int, button_color: tuple[int, int, int]) -> None:
        pygame.draw.circle(surface, (254, 240, 138), (cx, cy), 12)
        pygame.draw.circle(surface, button_color, (cx + 5, cy - 3), 10)

    @staticmethod
    def _draw_day_button(surface: pygame.Surface, cx: int, cy: int) -> None:
        pygame.draw.circle(surface, (254, 240, 138), (cx, cy), 11)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            pygame.draw.line(
                surface,
                (254, 240, 138),
                (cx + int(math.cos(rad) * 13), cy + int(math.sin(rad) * 13)),
                (cx + int(math.cos(rad) * 18), cy + int(math.sin(rad) * 18)),
                2,
            )


def now_seconds() -> float:
    """Single source of monotonic seconds for animation phases.

    Centralised so any future switch to a clamped monotonic
    clock (e.g. for pause/resume) only touches this one helper.
    """

    return time.monotonic()


def safe_now_seconds(fallback: float) -> float:
    """Return :func:`now_seconds` while surviving test patching.

    Helper tests that monkeypatch ``time.time`` or
    ``time.monotonic`` to validate phase determinism should not
    crash the renderer. This wrapper catches the import
    substitution so a mock that does not return a float still
    produces a usable number.
    """

    try:
        value = now_seconds()
    except Exception:
        return fallback
    return value if isinstance(value, (int, float)) else fallback


__all__ = [
    "AquariumRenderer",
    "ToolLayout",
    "now_seconds",
    "safe_now_seconds",
]
