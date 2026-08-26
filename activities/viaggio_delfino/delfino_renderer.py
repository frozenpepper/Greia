"""One-pass renderer and child-facing HUD for Il Viaggio del Delfino.

The renderer owns presentation only: every surface it blits is prepared by
``DelfinoArtLibrary`` and all stable text is rendered through a bounded
typography cache. Localized wording is handed in per frame through
``HudView`` so this module stays locale-agnostic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import pygame

from greia_platform.typography import FontRole, GreiaTypography

try:
    from delfino_art import (
        DelfinoArtLibrary,
        FLIP_STEPS,
        INK,
        PEARL_SHELL_DARK,
        WHITE,
        _colorkey_surface,
    )
    from delfino_model import (
        JourneyState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SURFACE_Y,
    )
except ImportError:  # repository/package import context
    from .delfino_art import (
        DelfinoArtLibrary,
        FLIP_STEPS,
        INK,
        PEARL_SHELL_DARK,
        WHITE,
        _colorkey_surface,
    )
    from .delfino_model import (
        JourneyState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SURFACE_Y,
    )


#: Child-sized hit target for the Tito curiosity affordance (reference coords).
TITO_RECT: Final = pygame.Rect(930, 498, 76, 76)

_PILL_BORDER: Final = (250, 205, 95)


@dataclass(frozen=True, slots=True)
class HudView:
    """Everything locale-dependent the HUD needs for one frame."""

    pearls_count: int
    journey_fraction: float
    banner_text: str | None
    fact_caption: str | None
    tito_speaking: bool


class DelfinoRenderer:
    """Composites ocean world, dolphin, particles and HUD in one fast pass."""

    def __init__(self, art: DelfinoArtLibrary, typography: GreiaTypography) -> None:
        self._art = art
        self._typography = typography
        self._text_cache: dict[tuple[str, str, int, tuple[int, int, int]], pygame.Surface] = {}
        self._caption_cache: dict[str, tuple[pygame.Surface, list[str]]] = {}

    # ------------------------------------------------------------- helpers

    def _text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        key = (text, role.name, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, role, size, color)
        if len(self._text_cache) > 160:
            self._text_cache.clear()
        self._text_cache[key] = surf
        return surf

    def _wrapped_caption(self, caption: str) -> tuple[pygame.Surface, list[str]]:
        cached = self._caption_cache.get(caption)
        if cached is not None:
            return cached
        max_width = 470
        words = caption.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if self._text(candidate, FontRole.BODY, 20, INK).get_width() <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        panel_w = min(520, max(220, max(self._text(line, FontRole.BODY, 20, INK).get_width() for line in lines) + 44))
        panel_h = 26 * len(lines) + 34
        panel = _colorkey_surface(panel_w, panel_h)
        pygame.draw.rect(panel, (255, 252, 242), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, PEARL_SHELL_DARK, panel.get_rect(), 3, border_radius=18)
        y = 14
        for line in lines:
            line_surf = self._text(line, FontRole.BODY, 20, INK)
            panel.blit(line_surf, (22, y))
            y += 26
        entry = (panel, lines)
        if len(self._caption_cache) > 24:
            self._caption_cache.clear()
        self._caption_cache[caption] = entry
        return entry

    # ------------------------------------------------------------- warm-up

    def warm_banner(self, text: str) -> None:
        """Pre-render a chapter banner (text + shadow) before it is needed.

        The first DISPLAY-size rasterisation of a long localized string is
        expensive on the reference hardware; warming every chapter name at
        startup removes the hitch at exactly the celebration moment.
        """

        self._text(text, FontRole.DISPLAY, 34, (255, 250, 235))
        self._text(text, FontRole.DISPLAY, 34, (32, 84, 128))

    def warm_caption(self, caption: str) -> None:
        """Pre-build a fact caption panel before it is needed."""

        if caption:
            self._wrapped_caption(caption)

    # ---------------------------------------------------------------- world

    def render_world(self, surface: pygame.Surface, world: JourneyState) -> None:
        cam_x = world.dolphin.x - 220.0

        # 1. Baked sky/sea backdrop (single opaque blit).
        surface.blit(self._art.get_backdrop(), (0, 0))

        # 2. Parallax islands just above the horizon.
        islands = self._art.get_islands()
        iw = islands.get_width()
        ix = -int(cam_x * 0.16) % iw
        surface.blit(islands, (ix - iw, SURFACE_Y - 112))
        surface.blit(islands, (ix, SURFACE_Y - 112))

        # 3. Drifting clouds in the sky band.
        c1, c2, c3 = self._art.get_clouds()
        cw1 = c1.get_width() + 260
        cw2 = c2.get_width() + 320
        cw3 = c3.get_width() + 300
        surface.blit(c1, (int(150 - cam_x * 0.07) % cw1 - 130, 42))
        surface.blit(c2, (int(560 - cam_x * 0.11) % cw2 - 160, 88))
        surface.blit(c3, (int(980 - cam_x * 0.09) % cw3 - 150, 24))

        # 4. Far foam strip (slower than the world).
        self._blit_wave_strip(surface, cam_x * 0.75, SURFACE_Y - 4)

        # 5. Decor: kelp, corals, landmarks.
        for item in world.decor:
            sx = int(item.x - cam_x)
            if sx < -420 or sx > REFERENCE_WIDTH + 120:
                continue
            if item.kind == "kelp":
                strip = self._art.get_kelp_strip(300 if item.x % 2 < 1 else 380)
                surface.blit(strip, (sx - strip.get_width() // 2, 556 - strip.get_height()))
            elif item.kind == "coral":
                coral = self._art.get_coral()
                surface.blit(coral, (sx - coral.get_width() // 2, 566 - coral.get_height()))
            else:
                landmark = self._art.get_landmark(item.kind)
                surface.blit(
                    landmark,
                    (sx - landmark.get_width() // 2, 592 - landmark.get_height()),
                )

        # 6. Ambient bubbles.
        for bubble in world.bubbles:
            bx = int(bubble.x - cam_x)
            if -14 <= bx <= REFERENCE_WIDTH + 14:
                sprite = self._art.get_particle("bubble", bubble.size, WHITE)
                surface.blit(sprite, (bx - bubble.size // 2, int(bubble.y) - bubble.size // 2))

        # 7. Jellyfish.
        jelly_frames = self._art.get_jelly_frames()
        for jelly in world.jellies:
            sx = int(jelly.x - cam_x)
            if -120 <= sx <= REFERENCE_WIDTH + 120:
                pulse = int((jelly.drift_phase / (2 * 3.14159)) * 3) % 3
                frame = jelly_frames[pulse]
                surface.blit(frame, (sx - frame.get_width() // 2, int(jelly.effective_y) - frame.get_height() // 2))

        # 8. Pickups.
        pearl_sprite = self._art.get_pearl()
        pw, ph = pearl_sprite.get_size()
        for pearl in world.pearls:
            if pearl.collected:
                continue
            sx = int(pearl.x - cam_x)
            sy = int(pearl.effective_y)
            if -pw <= sx <= REFERENCE_WIDTH + pw:
                surface.blit(pearl_sprite, (sx - pw // 2, sy - ph // 2))
        star_sprite = self._art.get_starfish()
        sw, sh = star_sprite.get_size()
        for star in world.starfish:
            if star.collected:
                continue
            sx = int(star.x - cam_x)
            sy = int(star.y)
            if -sw <= sx <= REFERENCE_WIDTH + sw:
                surface.blit(star_sprite, (sx - sw // 2, sy - sh // 2))

        # 9. Dolphin: breach somersault frames while airborne, otherwise the
        # pose-bucket swim cycle (all rotations pre-baked).
        dolf = world.dolphin
        if dolf.airborne:
            step = int(round(dolf.flip_step_fraction * FLIP_STEPS)) % FLIP_STEPS
            sprite = self._art.get_flip_frame(step)
        else:
            pose = self._art.pose_for_motion(dolf.vertical_velocity, dolf.airborne)
            tail_step = int(round(dolf.tail_phase / (math.pi / 2))) % 4
            sprite = self._art.get_dolphin_frame(pose, tail_step)
        dsx = int(dolf.x - cam_x)
        dsy = int(dolf.y)
        if dolf.is_dashing and not dolf.airborne:
            # Wake streaks: length, offset, weight and shade all breathe with
            # the tail beat so the boost reads as moving water, not a decal.
            for i in range(4):
                dy = (-20, -7, 7, 20)[i]
                wobble = math.sin(dolf.tail_phase * 2.2 + i * 1.9) * 5.0
                length = 30 + int((math.sin(dolf.tail_phase * 3.4 + i * 2.1) * 0.5 + 0.5) * 34)
                gap = 86 + i * 11
                color = (235, 250, 255) if i % 2 == 0 else (196, 232, 248)
                y = dsy + dy + int(wobble)
                pygame.draw.line(
                    surface,
                    color,
                    (dsx - gap - length, y),
                    (dsx - gap, y),
                    3 if i % 2 == 0 else 2,
                )
        surface.blit(sprite, (dsx - sprite.get_width() // 2, dsy - sprite.get_height() // 2))

        # 10. Particles on top of the action.
        for particle in world.particles:
            px = int(particle.x - cam_x)
            py = int(particle.y)
            if -30 <= px <= REFERENCE_WIDTH + 30:
                size_bucket = (max(6, int(particle.size * particle.life)) // 4) * 4
                sprite_p = self._art.get_particle(particle.kind, size_bucket, particle.color)
                surface.blit(sprite_p, (px - sprite_p.get_width() // 2, py - sprite_p.get_height() // 2))

        # 11. Near foam strip over the action for depth.
        self._blit_wave_strip(surface, cam_x * 1.18, SURFACE_Y + 6)

    def _blit_wave_strip(self, surface: pygame.Surface, scroll: float, y: int) -> None:
        tile, _near_tile = self._art.get_wave_tiles()
        tw = tile.get_width()
        start = -int(scroll) % tw
        for x in range(start - tw, REFERENCE_WIDTH + tw, tw):
            surface.blit(tile, (x, y))

    # ------------------------------------------------------------------ HUD

    def draw_hud(self, surface: pygame.Surface, view: HudView) -> None:
        # Pearl counter pill (top-right, outside protected Home chrome).
        count_text = self._text(str(view.pearls_count), FontRole.TITLE, 26, (146, 96, 22))
        pill_w = 64 + count_text.get_width()
        pill = pygame.Rect(REFERENCE_WIDTH - pill_w - 20, 16, pill_w, 46)
        pygame.draw.rect(surface, (255, 253, 246), pill, border_radius=16)
        pygame.draw.rect(surface, _PILL_BORDER, pill, 3, border_radius=16)
        small_pearl = self._art.get_small_pearl()
        surface.blit(small_pearl, (pill.x + 12, pill.y + 5))
        surface.blit(count_text, (pill.x + 54, pill.y + (pill.height - count_text.get_height()) // 2))

        # Journey progress bar (bottom-centre, picture-based landmarks).
        bar = self._art.get_progress_bar()
        bar_rect = bar.get_rect(midbottom=(REFERENCE_WIDTH // 2 + 40, REFERENCE_HEIGHT - 12))
        surface.blit(bar, bar_rect)
        marker = self._art.get_marker()
        fraction = max(0.0, min(1.0, view.journey_fraction))
        marker_x = int(bar_rect.x + 12 + fraction * (bar_rect.width - 44))
        surface.blit(marker, (marker_x, bar_rect.y - 4))

        # Tito curiosity affordance (large circular portrait button).
        tito_center = TITO_RECT.center
        halo_color = (255, 214, 120) if view.tito_speaking else (255, 244, 214)
        pygame.draw.circle(surface, halo_color, tito_center, TITO_RECT.width // 2)
        pygame.draw.circle(surface, (238, 186, 92), tito_center, TITO_RECT.width // 2, 3)
        portrait = self._art.get_tito_portrait(58)
        surface.blit(portrait, portrait.get_rect(center=tito_center))
        if not view.tito_speaking:
            # Small speech-bubble nudge so the affordance reads as "talk".
            bubble_x, bubble_y = TITO_RECT.right - 18, TITO_RECT.top + 2
            pygame.draw.circle(surface, WHITE, (bubble_x, bubble_y), 11)
            pygame.draw.polygon(surface, WHITE, [(bubble_x - 6, bubble_y + 8), (bubble_x - 14, bubble_y + 18), (bubble_x + 2, bubble_y + 11)])
            pygame.draw.circle(surface, (238, 186, 92), (bubble_x, bubble_y), 11, 2)
            for i, dx in enumerate((-4, 1, 6)):
                pygame.draw.circle(surface, (196, 148, 84), (bubble_x + dx, bubble_y), 1 + (i == 1))

        # Chapter celebration banner (transient).
        if view.banner_text:
            banner = self._text(view.banner_text, FontRole.DISPLAY, 34, (255, 250, 235))
            shadow = self._text(view.banner_text, FontRole.DISPLAY, 34, (32, 84, 128))
            bw = banner.get_width() + 56
            box = pygame.Rect(0, 0, bw, 62)
            box.center = (REFERENCE_WIDTH // 2, 96)
            pygame.draw.rect(surface, (38, 116, 178), box, border_radius=20)
            pygame.draw.rect(surface, (250, 215, 120), box, 4, border_radius=20)
            surface.blit(shadow, shadow.get_rect(center=(box.centerx + 2, box.centery + 2)))
            surface.blit(banner, banner.get_rect(center=box.center))

        # Fact caption bubble anchored above the Tito button, clamped inside
        # the reference frame on both edges.
        if view.fact_caption:
            panel, _lines = self._wrapped_caption(view.fact_caption)
            anchor_x = TITO_RECT.centerx - panel.get_width() // 2 - 6
            anchor_x = max(16, min(anchor_x, REFERENCE_WIDTH - panel.get_width() - 16))
            anchor_y = TITO_RECT.top - panel.get_height() - 14
            surface.blit(panel, (anchor_x, anchor_y))
            pygame.draw.polygon(
                surface,
                (255, 252, 242),
                [
                    (TITO_RECT.centerx - 18, anchor_y + panel.get_height() - 2),
                    (TITO_RECT.centerx + 6, TITO_RECT.top - 4),
                    (TITO_RECT.centerx - 4, anchor_y + panel.get_height() - 14),
                ],
            )
