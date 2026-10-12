"""Game view renderer and HUD presentation for Nascondino nel Bosco."""

from __future__ import annotations

import math
from typing import Any, Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography
from greia_platform.ui_preferences import InterfaceSize

try:
    from woodland_art import WoodlandArtLibrary
    from woodland_model import (
        ALL_ANIMALS,
        ANIMALS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WoodlandGameState,
    )
except ImportError:
    from .woodland_art import WoodlandArtLibrary
    from .woodland_model import (
        ALL_ANIMALS,
        ANIMALS_BY_ID,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WoodlandGameState,
    )


def compute_hud_layout(interface_size: str | InterfaceSize = InterfaceSize.NORMAL) -> dict[str, Any]:
    """Compute responsive HUD bounds calibrated for child interaction."""
    if isinstance(interface_size, str):
        try:
            interface_size = InterfaceSize(interface_size)
        except ValueError:
            interface_size = InterfaceSize.NORMAL

    if interface_size == InterfaceSize.LARGE:
        card_w = 380
        card_h = 104
        card_top = 10
        font_size = 26
        portrait_size = 76
        text_offset_x = 175
        star_radius = 9
        star_spacing_x = 20
        star_spacing_y = 30
        star_offset_right = 40
        star_offset_top = 28
        mag_radius = 20
        mag_thick = 4
    elif interface_size == InterfaceSize.COMPACT:
        card_w = 320
        card_h = 88
        card_top = 16
        font_size = 20
        portrait_size = 64
        text_offset_x = 150
        star_radius = 7
        star_spacing_x = 16
        star_spacing_y = 24
        star_offset_right = 32
        star_offset_top = 24
        mag_radius = 16
        mag_thick = 3
    else:  # NORMAL
        card_w = 350
        card_h = 94
        card_top = 14
        font_size = 24
        portrait_size = 68
        text_offset_x = 162
        star_radius = 8
        star_spacing_x = 18
        star_spacing_y = 28
        star_offset_right = 36
        star_offset_top = 26
        mag_radius = 18
        mag_thick = 4

    target_card = (REFERENCE_WIDTH // 2 - card_w // 2, card_top, card_w, card_h)
    star_pill = (80, 16, 130, 56)

    return {
        "interface_size": interface_size.value,
        "target_card_rect": target_card,
        "font_px": font_size,
        "portrait_size": portrait_size,
        "text_offset_x": text_offset_x,
        "star_radius": star_radius,
        "star_spacing_x": star_spacing_x,
        "star_spacing_y": star_spacing_y,
        "star_offset_right": star_offset_right,
        "star_offset_top": star_offset_top,
        "mag_radius": mag_radius,
        "mag_thick": mag_thick,
        "star_pill_rect": star_pill,
    }


class WoodlandRenderer:
    """High-performance compositor for Nascondino gameplay frames."""

    def __init__(
        self,
        art: WoodlandArtLibrary,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.art = art
        self.typography = typography
        self.resources = resources
        self._text_cache: dict[tuple[str, int, tuple[int, int, int]], pygame.Surface] = {}
        self._last_stars: int = -1
        self._cached_stars_surf: pygame.Surface | None = None

    def draw_active_game(
        self,
        target_surface: pygame.Surface,
        state: WoodlandGameState,
        interface_size: InterfaceSize,
        t_now: float,
        selected_spot_id: str | None = None,
    ) -> None:
        """Render the complete active game frame in one optimized pass."""
        # 1. Fast opaque background blit
        bg = self.art.get_background()
        target_surface.blit(bg, (0, 0))

        # 2. Grounded peeking clues
        for spot in state.spots:
            animal_id = state.hiding_map.get(spot.spot_id)
            if animal_id is not None and spot.spot_id not in state.found_spot_ids:
                self.art.draw_peeking_clue(target_surface, spot, animal_id, t_now)

        # Visible keyboard focus; no extra image allocation.
        if selected_spot_id is not None:
            for spot in state.spots:
                if spot.spot_id == selected_spot_id:
                    focus = pygame.Rect(spot.rect_tuple).inflate(12, 12)
                    pygame.draw.ellipse(target_surface, (15, 23, 42), focus, 7)
                    pygame.draw.ellipse(target_surface, (56, 189, 248), focus, 4)
                    break

        # 3. Leaping animal animation (if active)
        leap = state.leaping_animal
        if leap is not None:
            t = leap.t / leap.duration  # Normalized 0.0 -> 1.0
            anim_sz = int(72 + math.sin(t * math.pi) * 44)
            anim_y = leap.cy - math.sin(t * math.pi) * 130.0
            portrait = self.art.get_animal_portrait(leap.animal_id, anim_sz)
            target_surface.blit(
                portrait,
                (leap.cx - anim_sz // 2, int(anim_y) - anim_sz // 2),
            )

        # 4. Sparkle particles
        for p in state.particles:
            color = p.color
            pygame.draw.circle(
                target_surface,
                color,
                (int(p.x), int(p.y)),
                max(1, int(p.size * p.life)),
            )

        # 5. Top Center Target Card
        layout = compute_hud_layout(interface_size)
        target_card = pygame.Rect(layout["target_card_rect"])
        pygame.draw.rect(target_surface, (255, 252, 245), target_card, border_radius=24)
        pygame.draw.rect(target_surface, (234, 179, 8), target_card, width=4, border_radius=24)

        # Magnifying glass icon on left
        mag_r = layout["mag_radius"]
        mag_th = layout["mag_thick"]
        pygame.draw.circle(
            target_surface,
            (59, 130, 246),
            (target_card.left + 34, target_card.centery - 5),
            mag_r,
            mag_th,
        )
        pygame.draw.line(
            target_surface,
            (59, 130, 246),
            (target_card.left + 46, target_card.centery + 7),
            (target_card.left + 60, target_card.centery + 21),
            mag_th + 1,
        )

        # Target Animal Large Portrait
        target_portrait = self.art.get_animal_portrait(
            state.target_animal_id, layout["portrait_size"]
        )
        target_surface.blit(
            target_portrait,
            (
                target_card.left + 62,
                target_card.centery - layout["portrait_size"] // 2,
            ),
        )

        # Localized Animal Name Text
        animal_def = ANIMALS_BY_ID.get(state.target_animal_id)
        name_key = animal_def.name_key if animal_def else f"animal.{state.target_animal_id}"
        name_str = self.resources.text(name_key).upper()
        name_surf = self._render_cached_text(
            name_str, FontRole.DISPLAY, layout["font_px"], (180, 83, 9)
        )
        target_surface.blit(
            name_surf,
            (
                target_card.left + layout["text_offset_x"],
                target_card.centery - name_surf.get_height() // 2,
            ),
        )

        # Progress Stars on Target Card
        for s in range(state.total_to_find):
            st_x = (
                target_card.right
                - layout["star_offset_right"]
                + (s % 2) * layout["star_spacing_x"]
            )
            st_y = (
                target_card.top
                + layout["star_offset_top"]
                + (s // 2) * layout["star_spacing_y"]
            )
            if s < state.found_count:
                pygame.draw.circle(target_surface, (234, 179, 8), (st_x, st_y), layout["star_radius"])
            else:
                pygame.draw.circle(
                    target_surface, (203, 213, 225), (st_x, st_y), layout["star_radius"], 2
                )

        # 6. Star Pill (Top Left)
        star_pill = pygame.Rect(layout["star_pill_rect"])
        pygame.draw.rect(target_surface, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(target_surface, (234, 179, 8), star_pill, width=3, border_radius=18)
        pygame.draw.circle(
            target_surface, (234, 179, 8), (star_pill.left + 28, star_pill.centery), 15
        )
        pygame.draw.circle(
            target_surface, (254, 240, 138), (star_pill.left + 28, star_pill.centery), 7
        )

        if state.total_stars != self._last_stars or self._cached_stars_surf is None:
            self._last_stars = state.total_stars
            self._cached_stars_surf = self.typography.render(
                str(state.total_stars), FontRole.DISPLAY, 26, (180, 83, 9)
            )
        target_surface.blit(
            self._cached_stars_surf,
            (star_pill.left + 54, star_pill.centery - self._cached_stars_surf.get_height() // 2),
        )

    def _render_cached_text(
        self, text: str, role: FontRole, size: int, color: tuple[int, int, int]
    ) -> pygame.Surface:
        key = (text, size, color)
        surf = self._text_cache.get(key)
        if surf is None:
            surf = self.typography.render(text, role, size, color)
            self._text_cache[key] = surf
        return surf
