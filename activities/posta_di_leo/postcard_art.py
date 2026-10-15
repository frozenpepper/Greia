"""Prepared, bounded art for Leo's Post.

Every picture is shared-library art resolved by semantic ID (wallpapers,
cast poses, props, creatures, FX, HUD glyphs); a child's own front picture
comes from My Creations. A postcard face is composed once per (card, size):
picture + stickers clipped to a rounded card with a cream mat and the cocoa
ink contour of the house style. The back is paper with an airmail edge, ruled
message lines, the friend's stamp and the friend as the address. Surfaces
live in hard-bounded LRU caches; drawing only blits.
"""

from __future__ import annotations

from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter, mix
from greia_platform.ui_core import BoundedCache

if __package__:
    from .postcard_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STICKER_SCALE,
        friend,
        scene,
        stamp,
        sticker,
    )
    from .postcard_model import CardFront, PlacedSticker
else:
    from postcard_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STICKER_SCALE,
        friend,
        scene,
        stamp,
        sticker,
    )
    from postcard_model import CardFront, PlacedSticker

INK: Final = (75, 55, 47)
CREAM: Final = (255, 249, 236)
PAPER: Final = (255, 252, 244)
STUDIO_TOP: Final = (252, 246, 232)
STUDIO_BOTTOM: Final = (246, 234, 210)
AIRMAIL_RED: Final = (232, 96, 84)
AIRMAIL_BLUE: Final = (72, 128, 196)
RULE: Final = (214, 222, 236)
HALO: Final = (255, 214, 102)
FX_SIZES: Final[dict[str, int]] = {"sparkle": 120, "heart_pop": 110, "confetti": 260, "dust_puff": 110, "star_burst": 150}

# Message lane on the back of a card, as fractions of the card size.
LANE_LEFT: Final = 0.055
LANE_RIGHT: Final = 0.59
LANE_TOP: Final = 0.2
LANE_BOTTOM: Final = 0.9
DIVIDER_X: Final = 0.62


def lane_rect(card: pygame.Rect) -> pygame.Rect:
    """Where the message is written on the back of ``card`` (same space)."""

    return pygame.Rect(
        card.left + round(card.width * LANE_LEFT),
        card.top + round(card.height * LANE_TOP),
        round(card.width * (LANE_RIGHT - LANE_LEFT)),
        round(card.height * (LANE_BOTTOM - LANE_TOP)),
    )


class PostcardArt:
    """Own every prepared surface the renderer blits (built lazily once)."""

    def __init__(self, painter: ControlPainter, *, art: ControlArt | None = None) -> None:
        self._painter = painter
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=96)
        self._cards: BoundedCache[tuple, pygame.Surface] = BoundedCache(16)
        self._backs: BoundedCache[tuple, pygame.Surface] = BoundedCache(6)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(48)
        self._screens: BoundedCache[str, pygame.Surface] = BoundedCache(2)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    @property
    def painter(self) -> ControlPainter:
        return self._painter

    # -- screens -----------------------------------------------------------------

    def background(self) -> pygame.Surface:
        """Warm studio paper with an airmail edge along the bottom (built once)."""

        cached = self._screens.get("studio")
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        span = REFERENCE_HEIGHT - 1
        for row in range(REFERENCE_HEIGHT):
            pygame.draw.line(surface, mix(STUDIO_TOP, STUDIO_BOTTOM, row / span), (0, row), (REFERENCE_WIDTH, row))
        _airmail_band(surface, pygame.Rect(0, REFERENCE_HEIGHT - 7, REFERENCE_WIDTH, 7), stripe=18)
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._screens["studio"] = surface
        return surface

    def delivered_backdrop(self) -> pygame.Surface:
        """The friends' meadow under a soft cream veil (built once)."""

        cached = self._screens.get("delivered")
        if cached is not None:
            return cached
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill((207, 234, 247))
        meadow = self._art.image(scene("meadow").asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
        if meadow is not None:
            surface.blit(meadow, (0, 0))
        veil = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        veil.fill((*CREAM, 60))
        surface.blit(veil, (0, 0))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._screens["delivered"] = surface
        return surface

    # -- card faces ----------------------------------------------------------------

    def card(
        self,
        key: object,
        front: CardFront | None,
        picture: pygame.Surface | None,
        stickers: Sequence[PlacedSticker],
        size: tuple[int, int],
        *,
        skip: int | None = None,
    ) -> pygame.Surface:
        """A framed postcard face. ``key`` must change whenever content does."""

        cache_key = ("card", key, size, skip)
        cached = self._cards.get(cache_key)
        if cached is None:
            cached = self._compose_card(front, picture, stickers, size, skip)
            self._cards[cache_key] = cached
        return cached

    def card_inner(self, size: tuple[int, int]) -> pygame.Rect:
        width, _height = size
        mat = max(4, width // 34)
        return pygame.Rect(mat, mat, size[0] - 2 * mat, size[1] - 2 * mat)

    def sticker_height(self, inner_height: int) -> int:
        return max(12, round(inner_height * STICKER_SCALE))

    def sticker_image(self, sticker_id: str, height: int) -> pygame.Surface | None:
        return self._art.fit(sticker(sticker_id).asset_id, height)

    def _picture(self, front: CardFront | None, picture: pygame.Surface | None, size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size)
        surface.fill(PAPER)
        if front is None:
            return surface
        if front.is_picture:
            if picture is not None:
                if picture.get_size() != size:
                    picture = pygame.transform.smoothscale(picture, size)
                surface.blit(picture, (0, 0))
            return surface
        image = self._art.image(scene(front.scene_id).asset_id, size)
        if image is not None:
            surface.blit(image, (0, 0))
        return surface

    def _compose_card(
        self,
        front: CardFront | None,
        picture: pygame.Surface | None,
        stickers: Sequence[PlacedSticker],
        size: tuple[int, int],
        skip: int | None,
    ) -> pygame.Surface:
        width, height = size
        radius = max(8, width // 22)
        contour = max(2, width // 150)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surface, PAPER, surface.get_rect(), border_radius=radius)
        inner = self.card_inner(size)
        clipped = pygame.Surface(inner.size, pygame.SRCALPHA)
        clipped.blit(self._picture(front, picture, inner.size), (0, 0))
        if front is None:
            self._draw_empty_front(clipped)
        sticker_h = self.sticker_height(inner.height)
        for index, placed in enumerate(stickers):
            if index == skip:
                continue
            image = self.sticker_image(placed.sticker_id, sticker_h)
            if image is not None:
                clipped.blit(image, image.get_rect(center=(round(placed.x * inner.width), round(placed.y * inner.height))))
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=max(4, radius - inner.left))
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(clipped, inner.topleft)
        pygame.draw.rect(surface, mix(INK, PAPER, 0.55), inner, width=max(1, contour - 1), border_radius=max(4, radius - inner.left))
        pygame.draw.rect(surface, INK, surface.get_rect(), width=contour, border_radius=radius)
        return surface

    def _draw_empty_front(self, surface: pygame.Surface) -> None:
        """No front yet: a dashed frame with a waiting picture pictogram."""

        width, height = surface.get_size()
        surface.fill((250, 240, 222))
        line = max(2, width // 160)
        dash = max(10, width // 30)
        rect = surface.get_rect().inflate(-width // 10, -height // 7)
        color = mix(INK, CREAM, 0.55)
        for x in range(rect.left, rect.right, dash * 2):
            pygame.draw.line(surface, color, (x, rect.top), (min(x + dash, rect.right), rect.top), line)
            pygame.draw.line(surface, color, (x, rect.bottom), (min(x + dash, rect.right), rect.bottom), line)
        for y in range(rect.top, rect.bottom, dash * 2):
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, min(y + dash, rect.bottom)), line)
            pygame.draw.line(surface, color, (rect.right, y), (rect.right, min(y + dash, rect.bottom)), line)
        icon = self._art.image("icon.hud.page", max(24, min(96, height // 3)))
        if icon is not None:
            icon = icon.copy()
            icon.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(icon, icon.get_rect(center=rect.center))

    # -- card backs ----------------------------------------------------------------

    def back(
        self,
        recipient_id: str | None,
        stamp_id: str,
        label: pygame.Surface | None,
        label_key: str,
        size: tuple[int, int],
    ) -> pygame.Surface:
        """Paper back: airmail edge, ruled lane, the friend's stamp and address."""

        key = ("back", recipient_id, stamp_id, label_key, size)
        cached = self._backs.get(key)
        if cached is not None:
            return cached
        width, height = size
        radius = max(8, width // 22)
        contour = max(2, width // 150)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surface, PAPER, surface.get_rect(), border_radius=radius)
        edge = max(5, height // 34)
        band = pygame.Surface(size, pygame.SRCALPHA)
        _airmail_band(band, pygame.Rect(0, 0, width, edge), stripe=max(10, width // 28))
        _airmail_band(band, pygame.Rect(0, height - edge, width, edge), stripe=max(10, width // 28))
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(band, (0, 0))

        card = surface.get_rect()
        lane = lane_rect(card)
        pitch = max(18, lane.height // 5)
        rule = max(1, height // 180)
        for index in range(1, 6):
            y = lane.top + index * pitch - pitch // 6
            if y < lane.bottom + 2:
                pygame.draw.line(surface, RULE, (lane.left, y), (lane.right, y), rule)
        divider = round(width * DIVIDER_X)
        pygame.draw.line(surface, mix(INK, PAPER, 0.7), (divider, round(height * 0.14)), (divider, round(height * 0.86)), max(2, rule + 1))

        # Stamp box (top right) with a postmark nudging its left edge.
        box_h = round(height * 0.3)
        box_w = round(box_h * 0.86)
        box = pygame.Rect(0, 0, box_w, box_h)
        box.topright = (width - round(width * 0.05), round(height * 0.1))
        self._draw_stamp(surface, box, stamp_id)
        mark_r = round(box_h * 0.36)
        mark_c = (box.left - round(mark_r * 0.35), box.centery + round(box_h * 0.1))
        mark = pygame.Surface((mark_r * 2 + 4, mark_r * 2 + 4), pygame.SRCALPHA)
        centre = (mark_r + 2, mark_r + 2)
        ink = (*INK, 110)
        pygame.draw.circle(mark, ink, centre, mark_r, max(2, rule + 1))
        pygame.draw.circle(mark, ink, centre, round(mark_r * 0.7), max(1, rule))
        surface.blit(mark, mark.get_rect(center=mark_c))
        wave = max(2, rule + 1)
        wave_color = mix(INK, PAPER, 0.45)
        for offset in (-0.22, 0.0, 0.22):
            y = mark_c[1] + round(box_h * offset)
            points = [
                (mark_c[0] - mark_r - round(width * 0.06) + step * max(4, width // 90), y + (3 if step % 2 else -3))
                for step in range(7)
            ]
            pygame.draw.lines(surface, wave_color, False, points, wave)

        # Address: the friend (happy) above the name label.
        address = pygame.Rect(divider + round(width * 0.03), box.bottom + round(height * 0.04), width - divider - round(width * 0.06), 0)
        address.height = round(height * 0.88) - address.top
        if recipient_id is not None:
            portrait_h = round(address.height * (0.62 if label is not None else 0.8))
            portrait = self._art.image(friend(recipient_id).asset_id, portrait_h, variant="happy")
            if portrait is not None:
                surface.blit(portrait, portrait.get_rect(midtop=(address.centerx, address.top)))
        if label is not None:
            fitted = label
            if label.get_width() > address.width:
                scale = address.width / label.get_width()
                fitted = pygame.transform.smoothscale(label, (address.width, max(1, round(label.get_height() * scale))))
            surface.blit(fitted, fitted.get_rect(midbottom=(address.centerx, address.bottom)))
        pygame.draw.rect(surface, INK, surface.get_rect(), width=contour, border_radius=radius)
        self._backs[key] = surface
        return surface

    def _draw_stamp(self, surface: pygame.Surface, box: pygame.Rect, stamp_id: str) -> None:
        """Perforated stamp: white scalloped edge, cream face, the stamp prop."""

        tooth = max(3, box.width // 12)
        pygame.draw.rect(surface, (255, 255, 255), box)
        for x in range(box.left, box.right + 1, tooth * 2):
            for y in (box.top, box.bottom):
                pygame.draw.circle(surface, PAPER, (x, y), max(2, tooth // 2 + 1))
        for y in range(box.top, box.bottom + 1, tooth * 2):
            for x in (box.left, box.right):
                pygame.draw.circle(surface, PAPER, (x, y), max(2, tooth // 2 + 1))
        face = box.inflate(-tooth * 2, -tooth * 2)
        pygame.draw.rect(surface, (255, 238, 214), face)
        pygame.draw.rect(surface, mix(INK, PAPER, 0.35), face, max(1, tooth // 3))
        image = self._art.image(stamp(stamp_id).asset_id, int(min(face.width, face.height) * 0.86))
        if image is not None:
            surface.blit(image, image.get_rect(center=face.center))

    # -- tray tiles ----------------------------------------------------------------

    def scene_tile(self, scene_id: str, size: int) -> pygame.Surface:
        """Rounded wallpaper thumbnail used as a tray tile icon."""

        key = ("scene", scene_id, size)
        cached = self._misc.get(key)
        if cached is None:
            cached = self._rounded(self._art.image(scene(scene_id).asset_id, (size, round(size / 1.25))), size)
            self._misc[key] = cached
        return cached

    def picture_tile(self, picture: pygame.Surface, size: int, token: object) -> pygame.Surface:
        key = ("picture", token, size)
        cached = self._misc.get(key)
        if cached is None:
            height = round(size / 1.25)
            scaled = pygame.transform.smoothscale(picture, (size, height))
            cached = self._rounded(scaled, size)
            self._misc[key] = cached
        return cached

    def _rounded(self, image: pygame.Surface | None, width: int) -> pygame.Surface:
        height = round(width / 1.25)
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        if image is not None:
            surface.blit(image, (0, 0))
        else:
            surface.fill(CREAM)
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        radius = max(6, width // 8)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(surface, INK, surface.get_rect(), width=max(2, width // 40), border_radius=radius)
        return surface

    # -- small pieces ----------------------------------------------------------------

    def cast(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", height, variant=variant)

    def picture(self, asset_id: str, size: int) -> pygame.Surface | None:
        return self._art.image(asset_id, size)

    def tick(self, size: int) -> pygame.Surface:
        """Leaf-green done tick on a step tile (2x supersampled)."""

        key = ("tick", size)
        cached = self._misc.get(key)
        if cached is None:
            big = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            c = size
            pygame.draw.circle(big, INK, (c, c), c)
            pygame.draw.circle(big, (89, 184, 106), (c, c), c - max(2, size // 6))
            u = size / 15
            pygame.draw.lines(big, (255, 255, 255), False, [(c - 6 * u, c), (c - 2 * u, c + 4.5 * u), (c + 6.5 * u, c - 5 * u)], max(3, round(3.4 * u)))
            cached = pygame.transform.smoothscale(big, (size, size))
            self._misc[key] = cached
        return cached

    def badge(self, number: int, size: int) -> pygame.Surface:
        """Round count badge (cards in the postbox)."""

        key = ("badge", number, size)
        cached = self._misc.get(key)
        if cached is None:
            theme = self._painter.theme
            cached = self._painter.body(BodyShape.ROUND, (size, size), theme.accent, contour_width=max(2, size // 12)).copy()
            label = self._painter.label(str(number), int(size * 0.5), theme.accent_text)
            cached.blit(label, label.get_rect(center=(size // 2, size // 2 - size // 16)))
            self._misc[key] = cached
        return cached

    def meter(self, size: tuple[int, int], used: int, capacity: int) -> pygame.Surface:
        """Two rows of little card dots: filled = a card in the postbox."""

        key = ("meter", size, used, capacity)
        cached = self._misc.get(key)
        if cached is not None:
            return cached
        cached = pygame.Surface(size, pygame.SRCALPHA)
        theme = self._painter.theme
        columns = (capacity + 1) // 2
        area = cached.get_rect()
        dot = max(6, min(area.height // 2 - 2, area.width // (columns + 1)))
        step_x = area.width / columns
        full = used >= capacity
        for index in range(capacity):
            row, column = divmod(index, columns)
            cx = int(area.left + step_x * (column + 0.5))
            cy = area.top + dot // 2 + 1 + row * (dot + 3)
            if index < used:
                pygame.draw.circle(cached, AIRMAIL_RED if full else theme.accent, (cx, cy), dot // 2)
                pygame.draw.circle(cached, INK, (cx, cy), dot // 2, max(1, dot // 6))
            else:
                pygame.draw.circle(cached, mix(INK, CREAM, 0.6), (cx, cy), dot // 2, max(1, dot // 6))
        self._misc[key] = cached
        return cached

    def panel(self, size: tuple[int, int], *, alpha: int = 230) -> pygame.Surface:
        key = ("panel", size, alpha)
        cached = self._misc.get(key)
        if cached is None:
            body = self._painter.body(BodyShape.PANEL, size, CREAM, lip=6, contour_width=3).copy()
            body.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            cached = body
            self._misc[key] = cached
        return cached

    def shadow(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("shadow", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(cached, (*INK, 60), cached.get_rect(), border_radius=max(8, size[0] // 22))
            self._misc[key] = cached
        return cached

    def halo(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm glow ring around a control or card (hints, celebrations)."""

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

    def dim(self, size: tuple[int, int]) -> pygame.Surface:
        key = ("dim", size)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            cached.fill((20, 16, 30, 150))
            self._misc[key] = cached
        return cached

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
        self._backs.clear()
        self._misc.clear()
        self._screens.clear()
        self._fx.clear()


def _airmail_band(surface: pygame.Surface, rect: pygame.Rect, *, stripe: int) -> None:
    """Diagonal red / cream / blue airmail stripes filling ``rect``."""

    colors = (AIRMAIL_RED, PAPER, AIRMAIL_BLUE, PAPER)
    previous = surface.get_clip()
    surface.set_clip(rect)
    slant = rect.height
    x = rect.left - slant
    index = 0
    while x < rect.right + slant:
        points = [(x, rect.bottom), (x + stripe, rect.bottom), (x + stripe + slant, rect.top), (x + slant, rect.top)]
        pygame.draw.polygon(surface, colors[index % 4], points)
        x += stripe
        index += 1
    surface.set_clip(previous)


__all__ = ["AIRMAIL_BLUE", "AIRMAIL_RED", "HALO", "INK", "PAPER", "PostcardArt", "lane_rect"]
