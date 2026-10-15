"""Prepared, bounded art for Stories of My Voice.

Every picture is shared library art resolved by semantic ID (scene layers,
canonical cast poses, props, creatures, FX, HUD glyphs). A story card is
composed once per (card, size): scene crop + sprites + optional rain, clipped
to a rounded card with a cream mat and the cocoa ink contour of the house
style. Surfaces live in hard-bounded LRU caches; drawing only blits.
"""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.ui_core import BoundedCache

if __package__:
    from .voice_content import (
        CARD_SPACE,
        HOST,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENE_CROP_WIDTH,
        CardArt,
        StoryTemplate,
    )
else:
    from voice_content import (
        CARD_SPACE,
        HOST,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENE_CROP_WIDTH,
        CardArt,
        StoryTemplate,
    )

INK: Final = (75, 55, 47)
CREAM: Final = (255, 249, 236)
HALO: Final = (255, 214, 102)
REC_RED: Final = (232, 86, 74)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 110, "star_burst": 150, "confetti": 240, "heart_pop": 96, "check_pop": 96}


class StoryArt:
    """Own every prepared surface the renderer blits (built lazily once)."""

    def __init__(self, painter: ControlPainter, *, art: ControlArt | None = None) -> None:
        self._painter = painter
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=96)
        self._cards: BoundedCache[tuple, pygame.Surface] = BoundedCache(24)
        self._scenes: BoundedCache[tuple[str, ...], pygame.Surface] = BoundedCache(3)
        self._backgrounds: BoundedCache[tuple, pygame.Surface] = BoundedCache(3)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(32)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- cards ------------------------------------------------------------------

    def card(self, art: CardArt, size: tuple[int, int], *, key: str) -> pygame.Surface:
        """A framed story card (mat, picture, ink contour) at ``size``."""

        cache_key = ("card", key, size)
        cached = self._cards.get(cache_key)
        if cached is None:
            cached = self._compose_card(art, size)
            self._cards[cache_key] = cached
        return cached

    def card_picture(self, art: CardArt, size: tuple[int, int]) -> pygame.Surface:
        """The unframed picture (scene crop + sprites), scaled once."""

        width, height = size
        scale = width / CARD_SPACE[0]
        scene = self._scene(art.layers)
        crop_h = int(SCENE_CROP_WIDTH * CARD_SPACE[1] / CARD_SPACE[0])
        crop = pygame.Rect(art.crop_x, REFERENCE_HEIGHT - crop_h, SCENE_CROP_WIDTH, crop_h)
        crop = crop.clamp(pygame.Rect(0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT))
        picture = pygame.transform.smoothscale(scene.subsurface(crop), (width, height))
        if art.rain:
            veil = pygame.Surface((width, height), pygame.SRCALPHA)
            veil.fill((96, 112, 140, 70))
            picture.blit(veil, (0, 0))
        for sprite in art.sprites:
            image = self._art.fit(sprite.asset_id, max(4, round(sprite.height * scale)), variant=sprite.variant)
            if image is None:
                continue
            if sprite.angle:
                image = pygame.transform.rotozoom(image, sprite.angle, 1.0)
            rect = image.get_rect(midbottom=(round(sprite.x * scale), round(sprite.y * scale)))
            picture.blit(image, rect)
        if art.rain:
            drops = self._art.image("fx.rain", max(20, round(84 * scale)))
            if drops is not None:
                step = int(drops.get_width() * 1.45)
                for row, y in enumerate(range(-step // 3, height, step)):
                    shift = (row % 2) * step // 2
                    for x in range(-step + shift, width, step):
                        picture.blit(drops, (x, y))
        return picture

    def _compose_card(self, art: CardArt, size: tuple[int, int]) -> pygame.Surface:
        width, height = size
        radius = max(8, width // 18)
        mat = max(4, width // 40)
        contour = max(2, width // 140)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surface, CREAM, surface.get_rect(), border_radius=radius)
        inner = pygame.Rect(mat, mat, width - 2 * mat, height - 2 * mat)
        # Clip the picture to the inner rounded rect with an alpha mask.
        clipped = pygame.Surface(inner.size, pygame.SRCALPHA)
        clipped.blit(self.card_picture(art, inner.size), (0, 0))
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=max(4, radius - mat))
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(clipped, inner.topleft)
        pygame.draw.rect(surface, mix(INK, CREAM, 0.55), inner, width=max(1, contour - 1), border_radius=max(4, radius - mat))
        pygame.draw.rect(surface, INK, surface.get_rect(), width=contour, border_radius=radius)
        return surface

    def _scene(self, layers: tuple[str, ...]) -> pygame.Surface:
        cached = self._scenes.get(layers)
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((207, 234, 247))
        loader = ControlArt(max_entries=len(layers) + 1)
        for asset_id in layers:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        self._scenes[layers] = surface
        return surface

    # -- screens -----------------------------------------------------------------

    def background(self, layers: tuple[str, ...], *, veil: int = 0) -> pygame.Surface:
        """Full-screen scene, optionally under a cream veil (built once)."""

        key = (layers, veil)
        cached = self._backgrounds.get(key)
        if cached is not None:
            return cached
        surface = self._scene(layers).copy()
        if veil:
            wash = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            wash.fill((*CREAM, veil))
            surface.blit(wash, (0, 0))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backgrounds[key] = surface
        return surface

    def panel(self, size: tuple[int, int], *, alpha: int = 214) -> pygame.Surface:
        """Soft cream board behind card rows."""

        key = ("panel", size, alpha)
        cached = self._misc.get(key)
        if cached is None:
            body = self._painter.body(BodyShape.PANEL, size, CREAM, lip=6, contour_width=3).copy()
            body.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            cached = body
            self._misc[key] = cached
        return cached

    def slot(self, size: tuple[int, int], number: int, *, active: bool = False) -> pygame.Surface:
        """An empty numbered place where a card goes (dashed well + number pip)."""

        key = ("slot", size, number, active)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        width, height = size
        radius = max(8, width // 18)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        fill = (255, 240, 205, 235) if active else (255, 251, 240, 200)
        pygame.draw.rect(surface, fill, surface.get_rect(), border_radius=radius)
        dash = max(8, width // 16)
        line = max(3, width // 70)
        rect = surface.get_rect().inflate(-line, -line)
        color = mix(INK, CREAM, 0.15 if active else 0.45)
        for x in range(rect.left + radius, rect.right - radius, dash * 2):
            pygame.draw.line(surface, color, (x, rect.top), (min(x + dash, rect.right - radius), rect.top), line)
            pygame.draw.line(surface, color, (x, rect.bottom), (min(x + dash, rect.right - radius), rect.bottom), line)
        for y in range(rect.top + radius, rect.bottom - radius, dash * 2):
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, min(y + dash, rect.bottom - radius)), line)
            pygame.draw.line(surface, color, (rect.right, y), (rect.right, min(y + dash, rect.bottom - radius)), line)
        number_badge = self.number(number, max(30, height // 3))
        surface.blit(number_badge, number_badge.get_rect(center=(width // 2, height // 2)))
        self._misc[key] = surface
        return surface

    def number(self, number: int, size: int, *, accent: tuple[int, int, int] | None = None) -> pygame.Surface:
        """Round position badge: the number plus that many tiny dots."""

        key = ("number", number, size, accent)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        theme = self._painter.theme
        fill = accent if accent is not None else theme.accent
        surface = self._painter.body(BodyShape.ROUND, (size, size), fill, contour_width=max(2, size // 14)).copy()
        label = self._painter.label(str(number), int(size * 0.56), theme.accent_text)
        surface.blit(label, label.get_rect(center=(size // 2, size // 2 - size // 16)))
        self._misc[key] = surface
        return surface

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm glow ring around a card (hints, celebrations)."""

        key = ("halo", size)
        cached = self._misc.get(key)
        if cached is None:
            width, height = size[0] + 28, size[1] + 28
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 70), (5, 130), (10, 210)):
                pygame.draw.rect(
                    cached,
                    (*HALO, alpha),
                    pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset),
                    width=5,
                    border_radius=max(10, 28 - inset),
                )
            self._misc[key] = cached
        return cached

    def shadow(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("shadow", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(cached, (*INK, 60), cached.get_rect(), border_radius=max(8, size[0] // 18))
            self._misc[key] = cached
        return cached

    def ring(self, radius: int, width: int, color: tuple[int, int, int], alpha: int) -> pygame.Surface:
        """Cached translucent ring (recording aura / time ring background)."""

        key = ("ring", radius, width, color, alpha)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(cached, (*color, alpha), (radius + 1, radius + 1), radius, width)
            self._misc[key] = cached
        return cached

    def dim(self, size: tuple[int, int]) -> pygame.Surface:
        """Cached translucent shade behind modal sheets."""

        key = ("dim", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            cached.fill((20, 16, 30, 150))
            self._misc[key] = cached
        return cached

    def disc(self, radius: int, color: tuple[int, int, int], alpha: int) -> pygame.Surface:
        key = ("disc", radius, color, alpha)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(cached, (*color, alpha), (radius + 1, radius + 1), radius)
            self._misc[key] = cached
        return cached

    # -- story covers / shelf ------------------------------------------------------

    def cover(self, story: StoryTemplate, size: tuple[int, int], *, done: bool, star, title: str = "") -> pygame.Surface:
        """Picker tile icon: the first card, one dot per card, a small title (+ star)."""

        key = ("cover", story.story_id, size, done, title)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        width, height = size
        theme = self._painter.theme
        label = self._painter.label(title, 19, theme.text, max_width=width - 26) if title else None
        label_h = label.get_height() if label is not None else 0
        dots_h = max(12, height // 12)
        card_h = height - dots_h - label_h - 12
        card_w = min(width, int(card_h * CARD_SPACE[0] / CARD_SPACE[1]))
        card_h = int(card_w * CARD_SPACE[1] / CARD_SPACE[0])
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        first = story.cards[0]
        surface.blit(self.card(first.art, (card_w, card_h), key=first.card_id), ((width - card_w) // 2, 0))
        count = len(story.cards)
        spacing = int(dots_h * 1.6)
        start = width // 2 - spacing * (count - 1) // 2
        dots_y = card_h + 5 + dots_h // 2
        for index in range(count):
            dot = self._painter.body(BodyShape.ROUND, (dots_h, dots_h), theme.accent, contour_width=max(2, dots_h // 6))
            surface.blit(dot, dot.get_rect(center=(start + index * spacing, dots_y)))
        if label is not None:
            surface.blit(label, label.get_rect(midtop=(width // 2, card_h + dots_h + 9)))
        if done:
            badge = star(max(24, card_h // 3), filled=True)
            surface.blit(badge, badge.get_rect(center=((width + card_w) // 2 - badge.get_width() // 3, badge.get_height() // 3)))
        self._misc[key] = surface
        return surface

    def home(self, size: tuple[int, int]) -> pygame.Surface:
        """Faint place mark where a card waits in the tray."""

        key = ("home", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            radius = max(8, size[0] // 18)
            pygame.draw.rect(cached, (255, 253, 247, 90), cached.get_rect(), border_radius=radius)
            pygame.draw.rect(cached, (*INK, 50), cached.get_rect(), width=2, border_radius=radius)
            self._misc[key] = cached
        return cached

    def shelf_cover(self, size: tuple[int, int], used: int, capacity: int, *, title: str = "") -> pygame.Surface:
        """My-stories picker tile: a book, the 12-dot shelf meter and a title."""

        key = ("shelf_cover", size, used, capacity, title)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        width, height = size
        theme = self._painter.theme
        label = self._painter.label(title, 19, theme.text, max_width=width - 26) if title else None
        label_h = label.get_height() if label is not None else 0
        meter_h = max(24, height // 6)
        book_h = height - meter_h - label_h - 16
        surface = pygame.Surface(size, pygame.SRCALPHA)
        book = self._art.image("prop.everyday.book", book_h)
        if book is not None:
            surface.blit(book, book.get_rect(midtop=(width // 2, 2)))
        self._draw_meter(surface, pygame.Rect(18, book_h + 6, width - 36, meter_h), used, capacity)
        if label is not None:
            surface.blit(label, label.get_rect(midtop=(width // 2, book_h + meter_h + 12)))
        self._misc[key] = surface
        return surface

    def shelf_icon(self, size: int, used: int, capacity: int) -> pygame.Surface:
        """My-stories tile icon: a book + a meter of ``capacity`` little dots."""

        key = ("shelf", size, used, capacity)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        book = self._art.image("prop.everyday.book", int(size * 0.66))
        if book is not None:
            surface.blit(book, book.get_rect(midtop=(size // 2, 0)))
        self._draw_meter(surface, pygame.Rect(0, int(size * 0.72), size, int(size * 0.26)), used, capacity)
        self._misc[key] = surface
        return surface

    def meter(self, size: tuple[int, int], used: int, capacity: int) -> pygame.Surface:
        key = ("meter", size, used, capacity)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            self._draw_meter(cached, cached.get_rect(), used, capacity)
            self._misc[key] = cached
        return cached

    def _draw_meter(self, surface: pygame.Surface, area: pygame.Rect, used: int, capacity: int) -> None:
        """Two rows of little story dots: filled = a saved story (full = all)."""

        theme = self._painter.theme
        columns = (capacity + 1) // 2
        dot = max(6, min(area.height // 2 - 2, area.width // (columns + 1)))
        step_x = area.width / columns
        full = used >= capacity
        for index in range(capacity):
            row, column = divmod(index, columns)
            cx = int(area.left + step_x * (column + 0.5))
            cy = area.top + dot // 2 + 1 + row * (dot + 3)
            if index < used:
                color = REC_RED if full else theme.accent
                pygame.draw.circle(surface, color, (cx, cy), dot // 2)
                pygame.draw.circle(surface, INK, (cx, cy), dot // 2, max(1, dot // 6))
            else:
                pygame.draw.circle(surface, mix(INK, CREAM, 0.6), (cx, cy), dot // 2, max(1, dot // 6))

    # -- cast / glyphs / FX ---------------------------------------------------------

    def cast(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def host(self, variant: str, height: int) -> pygame.Surface | None:
        return self.cast(HOST, variant, height)

    def picture(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self._art.image(asset_id, size)

    def fx_frames(self, name: str) -> tuple[pygame.Surface, ...]:
        cached = self._fx.get(name)
        if cached is not None:
            return cached
        size = FX_SIZES.get(name, 120)
        frames = []
        for variant in ("default", "frame_2", "frame_3"):
            image = self._art.image(f"fx.{name}", size, variant=variant)
            if image is not None:
                frames.append(image)
        self._fx[name] = tuple(frames)
        return self._fx[name]

    def clear(self) -> None:
        self._cards.clear()
        self._scenes.clear()
        self._backgrounds.clear()
        self._misc.clear()
        self._fx.clear()


__all__ = ["HALO", "INK", "REC_RED", "StoryArt"]
