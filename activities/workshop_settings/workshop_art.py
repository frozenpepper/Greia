"""Bounded picture factory for My Greia.

Every surface the experience shows is built here once per (content, size) and
kept in hard-bounded LRU caches, so drawing a frame is blits only:

* core icons (avatars, Collection pictograms) through ``get_icon_path``;
* curated wallpaper scenes and the storybook meadow through the shared visual
  catalogue; full-size sources are decoded, scaled and released immediately
  (never kept resident), which matters at 1024x600 per scene on the Acer floor;
* small pictorial swatches drawn in code from theme tokens: a mini meadow whose
  sky is a room colour, a sparkle star in a sparkle colour, letter pills for
  the Big/Small choice and the four tab pictures.
"""

from __future__ import annotations

from collections.abc import Callable
import math
from pathlib import Path

import pygame

from greia_platform.activity_api import get_icon_path, get_shared_visual_path
from greia_platform.activity_controls import ControlKit, INK, mix
from greia_platform.child_text import display_text
from greia_platform.typography import FontRole
from greia_platform.ui_core import BoundedCache
from greia_platform.ui_preferences import InterfaceSize

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import (
        CAPTION_CREAM,
        CAPTION_INK,
        CAPTION_SHADOW,
        CURATED_WALLPAPERS,
        HOME_SCENE_ID,
        MAX_PICTURE_CACHE,
        MAX_PREVIEW_CACHE,
        MEADOW_CHOICE,
    )
except ImportError:
    from workshop_content import (  # type: ignore[no-redef]
        CAPTION_CREAM,
        CAPTION_INK,
        CAPTION_SHADOW,
        CURATED_WALLPAPERS,
        HOME_SCENE_ID,
        MAX_PICTURE_CACHE,
        MAX_PREVIEW_CACHE,
        MEADOW_CHOICE,
    )

Rgb = tuple[int, int, int]
Size = tuple[int, int]
SAMPLE_TEXT = "ABC"
WHITE: Rgb = (255, 255, 255)
LARGE_PIXELS = 120_000
CHECK_GREEN: Rgb = (89, 184, 106)


def rounded(surface: pygame.Surface, radius: int, *, outline: Rgb | None = INK, width: int = 3) -> pygame.Surface:
    """Return ``surface`` clipped to a rounded rectangle with an ink outline.

    The mask is supersampled once so corners stay smooth like the rsvg art.
    """

    w, h = surface.get_size()
    scale = 2
    mask_big = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    pygame.draw.rect(mask_big, (255, 255, 255, 255), mask_big.get_rect(), border_radius=radius * scale)
    mask = pygame.transform.smoothscale(mask_big, (w, h))
    result = pygame.Surface((w, h), pygame.SRCALPHA)
    result.blit(surface, (0, 0))
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    if outline is not None and width > 0:
        ring_big = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
        pygame.draw.rect(ring_big, outline, ring_big.get_rect(), width=width * scale, border_radius=radius * scale)
        result.blit(pygame.transform.smoothscale(ring_big, (w, h)), (0, 0))
    return result


class MyGreiaArt:
    """Own every My Greia picture, built once per content and size."""

    def __init__(
        self,
        kit: ControlKit,
        typography,
        *,
        icon_resolver: Callable[[str, int], Path] = get_icon_path,
        visual_resolver: Callable[..., Path] = get_shared_visual_path,
    ) -> None:
        self.kit = kit
        self._typography = typography
        self._icon_resolver = icon_resolver
        self._visual_resolver = visual_resolver
        self._icons: BoundedCache[tuple[str, int], pygame.Surface | None] = BoundedCache(48)
        self._pictures: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(MAX_PICTURE_CACHE)
        # Preview-sized scenes (~0.8 MB each) get their own tiny bound.
        self._large: BoundedCache[tuple, pygame.Surface | None] = BoundedCache(MAX_PREVIEW_CACHE)
        self.decode_count = 0

    def _cache_for(self, size: Size) -> BoundedCache:
        return self._large if size[0] * size[1] > LARGE_PIXELS else self._pictures

    def clear(self) -> None:
        self._icons.clear()
        self._pictures.clear()
        self._large.clear()

    # -- core icons ----------------------------------------------------------

    def icon(self, icon_id: str, size: int) -> pygame.Surface | None:
        size = max(8, int(size))
        key = (icon_id, size)
        if key in self._icons:
            return self._icons[key]
        surface: pygame.Surface | None
        try:
            source = pygame.image.load(str(self._icon_resolver(icon_id, 256 if size > 128 else 128)))
            if pygame.display.get_surface() is not None:
                source = source.convert_alpha()
            surface = source if source.get_size() == (size, size) else pygame.transform.smoothscale(source, (size, size))
        except Exception:
            surface = None
        self._icons[key] = surface
        return surface

    # -- scenes ----------------------------------------------------------------

    def _decode(self, path: Path, size: Size, *, alpha: bool) -> pygame.Surface | None:
        """Decode one image, cover-fit it to ``size`` and drop the source."""

        try:
            source = pygame.image.load(str(path))
        except Exception:
            return None
        self.decode_count += 1
        if pygame.display.get_surface() is not None:
            source = source.convert_alpha() if alpha else source.convert()
        width, height = size
        sw, sh = source.get_size()
        scale = max(width / max(1, sw), height / max(1, sh))
        scaled = pygame.transform.smoothscale(source, (max(1, round(sw * scale)), max(1, round(sh * scale))))
        # Bottom-anchored like the Shell so the ground stays visible.
        x = (scaled.get_width() - width) // 2
        y = scaled.get_height() - height
        return scaled.subsurface(pygame.Rect(x, y, width, height)).copy()

    def scene_layer(self, size: Size) -> pygame.Surface | None:
        """The storybook meadow (transparent sky) at ``size``."""

        key = ("scene", size)
        cache = self._cache_for(size)
        if key in cache:
            return cache[key]
        try:
            path = self._visual_resolver(HOME_SCENE_ID, variant="default")
        except Exception:
            path = None
        surface = self._decode(path, size, alpha=True) if path is not None else None
        cache[key] = surface
        return surface

    def wallpaper(self, choice: str, size: Size, *, custom: Path | None = None) -> pygame.Surface | None:
        """A curated wallpaper (or the earlier imported picture) at ``size``."""

        key = ("wallpaper", choice, size, str(custom) if custom else None)
        cache = self._cache_for(size)
        if key in cache:
            return cache[key]
        path: Path | None = None
        if choice in CURATED_WALLPAPERS:
            try:
                path = self._visual_resolver(choice, variant="default")
            except Exception:
                path = None
        elif custom is not None:
            path = custom
        surface = self._decode(path, size, alpha=False) if path is not None else None
        cache[key] = surface
        return surface

    def home_backdrop(self, choice: str, room: Rgb, size: Size, *, custom: Path | None = None) -> pygame.Surface:
        """Exactly what Home stands on: room colour + meadow, or the wallpaper."""

        surface = pygame.Surface(size)
        surface.fill(room)
        picture = None if choice == MEADOW_CHOICE else self.wallpaper(choice, size, custom=custom)
        if picture is not None:
            surface.blit(picture, (0, 0))
        else:
            scene = self.scene_layer(size)
            if scene is not None:
                surface.blit(scene, (0, 0))
        return surface

    def picture_tile(self, choice: str, room: Rgb, size: Size, *, custom: Path | None = None) -> pygame.Surface:
        """Rounded thumbnail for a Pictures choice (the meadow shows the room colour)."""

        key = ("picture_tile", choice, room if choice == MEADOW_CHOICE else None, size, str(custom) if custom else None)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        backdrop = self.home_backdrop(choice, room, size, custom=custom)
        surface = rounded(backdrop, max(6, size[1] // 6), width=2)
        self._pictures[key] = surface
        return surface

    # -- drawn swatches -------------------------------------------------------------

    def room_swatch(self, room: Rgb, size: Size) -> pygame.Surface:
        """A tiny meadow whose sky is ``room``: "this colour is my room"."""

        key = ("room", room, size)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        backdrop = pygame.Surface(size)
        backdrop.fill(room)
        scene = self.scene_layer(size)
        if scene is not None:
            backdrop.blit(scene, (0, 0))
        surface = rounded(backdrop, max(6, min(size) // 4), width=2)
        self._pictures[key] = surface
        return surface

    def sparkle_star(self, color: Rgb, size: int) -> pygame.Surface:
        """A plump five-point star filled with a sparkle colour."""

        size = max(12, int(size))
        key = ("star", color, size)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        s = 3
        big = size * s
        canvas = pygame.Surface((big, big), pygame.SRCALPHA)
        cx, cy = big / 2, big / 2 + big * 0.04
        outer, inner = big * 0.46, big * 0.23
        points = []
        for index in range(10):
            angle = -math.pi / 2 + index * math.pi / 5
            radius = outer if index % 2 == 0 else inner
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        shadow = [(x, y + big * 0.04) for x, y in points]
        pygame.draw.polygon(canvas, (*mix(color, INK, 0.45), 90), shadow)
        pygame.draw.polygon(canvas, color, points)
        highlight = [(cx + (x - cx) * 0.45 - big * 0.05, cy + (y - cy) * 0.45 - big * 0.06) for x, y in points]
        pygame.draw.polygon(canvas, (*mix(color, WHITE, 0.45), 150), highlight)
        pygame.draw.polygon(canvas, INK, points, width=max(2, round(big * 0.045)))
        surface = pygame.transform.smoothscale(canvas, (size, size))
        self._pictures[key] = surface
        return surface

    def size_sample(self, interface_size: str, height: int, *, text: Rgb = CAPTION_INK) -> pygame.Surface:
        """A Home caption pill with letters at the size this choice gives."""

        key = ("size", interface_size, height, text)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        scale = InterfaceSize(interface_size).scale
        font_px = max(10, round(height * 0.42 * scale ** 2))
        label = self._typography.render(display_text(SAMPLE_TEXT), FontRole.DISPLAY, font_px, text)
        pill_h = max(label.get_height() + 8, round(height * 0.62 * scale))
        pill_w = label.get_width() + pill_h
        surface = caption_pill(label, (pill_w, pill_h), focused=False)
        self._pictures[key] = surface
        return surface

    def check_badge(self, size: int) -> pygame.Surface:
        """Round leaf-green badge with the shared check glyph: "this one is mine"."""

        size = max(16, int(size))
        key = ("check_badge", size)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        s = 3
        big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
        center = (size * s // 2, size * s // 2)
        radius = size * s // 2 - s
        pygame.draw.circle(big, INK, center, radius)
        pygame.draw.circle(big, CHECK_GREEN, center, radius - max(2, round(size * s * 0.07)))
        surface = pygame.transform.smoothscale(big, (size, size))
        glyph = self.kit.glyph("check", round(size * 0.68))
        if glyph is not None:
            surface.blit(glyph, glyph.get_rect(center=(size // 2, size // 2 + 1)))
        self._pictures[key] = surface
        return surface

    # -- tab pictures ------------------------------------------------------------------

    def tab_pictures_icon(self, size: int) -> pygame.Surface:
        key = ("tab_pictures", size)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        frame = pygame.Surface((size, size), pygame.SRCALPHA)
        inner = (size, round(size * 0.74))
        picture = self.picture_tile("bg.wallpaper.rainbow", (247, 235, 203), inner)
        frame.blit(picture, picture.get_rect(center=(size // 2, size // 2)))
        self._pictures[key] = frame
        return frame

    def tab_size_icon(self, size: int) -> pygame.Surface:
        key = ("tab_size", size)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        small = self._typography.render(display_text("A"), FontRole.DISPLAY, max(10, round(size * 0.36)), CAPTION_INK)
        large = self._typography.render(display_text("A"), FontRole.DISPLAY, max(14, round(size * 0.78)), CAPTION_INK)
        total = small.get_width() + large.get_width() + 2
        x = (size - total) // 2
        baseline = round(size * 0.9)
        surface.blit(small, (x, baseline - small.get_height()))
        surface.blit(large, (x + small.get_width() + 2, baseline - large.get_height()))
        self._pictures[key] = surface
        return surface

    def tab_colours_icon(self, size: int, background: Rgb, accent: Rgb) -> pygame.Surface:
        key = ("tab_colours", size, background, accent)
        cached = self._pictures.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        swatch = self.room_swatch(background, (round(size * 0.78), round(size * 0.62)))
        surface.blit(swatch, (0, size - swatch.get_height() - round(size * 0.04)))
        star = self.sparkle_star(accent, round(size * 0.58))
        surface.blit(star, (size - star.get_width(), 0))
        self._pictures[key] = surface
        return surface


def caption_pill(label: pygame.Surface, size: Size, *, focused: bool, fill: Rgb | None = None) -> pygame.Surface:
    """The Shell's caption pill (cream body, ink contour, soft shadow)."""

    width, height = max(4, size[0]), max(4, size[1])
    s = 2
    big = pygame.Surface((width * s, (height + 2) * s), pygame.SRCALPHA)
    radius = height * s // 2
    body = pygame.Rect(0, 0, width * s, height * s)
    pygame.draw.rect(big, CAPTION_SHADOW, body.move(0, 2 * s), border_radius=radius)
    color = fill if fill is not None else ((255, 194, 52) if focused else CAPTION_CREAM)
    pygame.draw.rect(big, color, body, border_radius=radius)
    pygame.draw.rect(big, CAPTION_INK, body, width=2 * s, border_radius=radius)
    surface = pygame.transform.smoothscale(big, (width, height + 2))
    surface.blit(label, label.get_rect(center=(width // 2, height // 2)))
    return surface


__all__ = ["MyGreiaArt", "SAMPLE_TEXT", "caption_pill", "rounded"]
