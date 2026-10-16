"""Prepared, bounded art for Magic Bakery.

* The shop is the shared bakery wall + wood floor (``bg.indoor_room``) with
  this package's counter on top, composed once into one opaque surface.
* The cake, the order bubble and the counter are this package's own props
  (``assets/source/*.svg`` -> ``assets/runtime/*.png``, drawn 1:1 in the
  1024x600 reference space, so they are never scaled).
* Toppings are shared ``prop.food.*`` art; customers and the baker are the
  canonical cast (``character.<id>`` variants); bursts are shared ``fx.*``.

Every surface is scaled once per size and kept in a hard-bounded cache;
drawing only blits. Missing art degrades to simple shapes, never a crash.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_controls import BodyShape, ControlArt, ControlPainter
from greia_platform.ui_core import BoundedCache

if __package__:
    from .pasticceria_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ROOM_LAYERS, TOPPINGS_BY_ID
    from .pasticceria_layout import BUBBLE_RECT, CAKE_SIZE, COUNTER_POS
else:
    from pasticceria_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, ROOM_LAYERS, TOPPINGS_BY_ID
    from pasticceria_layout import BUBBLE_RECT, CAKE_SIZE, COUNTER_POS

PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
RUNTIME_DIR: Final[Path] = PACKAGE_ROOT / "assets" / "runtime"
PRIVATE_FILES: Final[tuple[str, ...]] = ("cake.png", "counter.png", "bubble.png")
CUPCAKE_GLYPH: Final = "icon.hud.cupcake"
WALL_FALLBACK: Final = (247, 222, 230)
FLOOR_FALLBACK: Final = (221, 174, 134)
CAKE_FALLBACK: Final = (243, 191, 210)
INK: Final = (75, 55, 47)
HALO: Final = (255, 226, 138)
GHOST_ALPHA: Final = 105
FX_SIZES: Final[dict[str, int]] = {
    "sparkle": 110,
    "star_burst": 170,
    "heart_pop": 150,
    "confetti": 260,
    "check_pop": 130,
}


def bakery_visual_resolver(asset_id: str, variant: str) -> Path:
    """Kit art resolver with one content alias for the completion scene.

    The "my cake" button of the shared completion scene takes its picture
    through the kit glyph lookup (``icon.hud.<id>``); ``icon.hud.cupcake`` is
    this Activity's alias for the shared ``prop.food.cupcake`` picture.
    Everything else resolves through the shared catalogue unchanged.
    """

    from greia_platform.activity_api import get_shared_visual_path

    if asset_id == CUPCAKE_GLYPH:
        return get_shared_visual_path("prop.food.cupcake", variant=variant)
    return get_shared_visual_path(asset_id, variant=variant)


class BakeryArt:
    """Own every prepared surface the renderer and controls blit."""

    def __init__(
        self,
        painter: ControlPainter,
        *,
        art: ControlArt | None = None,
        runtime_dir: Path = RUNTIME_DIR,
    ) -> None:
        # Content art gets its own bounded loader so it never evicts kit glyphs.
        self._art = art if art is not None else ControlArt(max_entries=64)
        self._painter = painter
        self._runtime_dir = runtime_dir
        self._backdrop: pygame.Surface | None = None
        self._private: BoundedCache[str, pygame.Surface | None] = BoundedCache(len(PRIVATE_FILES))
        self._ghosts: BoundedCache[tuple[str, int], pygame.Surface | None] = BoundedCache(8)
        self._misc: BoundedCache[tuple, pygame.Surface] = BoundedCache(24)
        self._fx: dict[str, tuple[pygame.Surface, ...]] = {}

    @property
    def loader(self) -> ControlArt:
        return self._art

    # -- the shop -----------------------------------------------------------------

    def backdrop(self) -> pygame.Surface:
        """Bakery wall + floor + counter, composed once (opaque, 1024x600)."""

        if self._backdrop is not None:
            return self._backdrop
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        surface.fill(WALL_FALLBACK)
        pygame.draw.rect(surface, FLOOR_FALLBACK, (0, 432, REFERENCE_WIDTH, REFERENCE_HEIGHT - 432))
        loader = ControlArt(max_entries=2)
        for asset_id in ROOM_LAYERS:
            image = loader.image(asset_id, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            if image is not None:
                surface.blit(image, (0, 0))
        loader.clear()
        counter = self._private_image("counter.png")
        if counter is not None:
            surface.blit(counter, COUNTER_POS)
        else:
            pygame.draw.rect(surface, (251, 230, 204), (COUNTER_POS[0], COUNTER_POS[1] + 22, REFERENCE_WIDTH, 160))
            pygame.draw.rect(surface, (185, 130, 87), (COUNTER_POS[0], COUNTER_POS[1], REFERENCE_WIDTH, 26))
        if pygame.display.get_surface() is not None:
            surface = surface.convert()
        self._backdrop = surface
        return surface

    def cake(self) -> pygame.Surface:
        image = self._private_image("cake.png")
        if image is not None:
            return image
        key = ("cake_fallback",)
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface(CAKE_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(cached, (248, 200, 145), (20, 110, 380, 150), border_radius=20)
            pygame.draw.ellipse(cached, CAKE_FALLBACK, (20, 40, 380, 140))
            pygame.draw.ellipse(cached, INK, (20, 40, 380, 140), 3)
            self._misc[key] = cached
        return cached

    def bubble(self) -> pygame.Surface:
        image = self._private_image("bubble.png")
        if image is not None:
            return image
        key = ("bubble_fallback",)
        cached = self._misc.get(key)
        if cached is None:
            cached = self._painter.body(BodyShape.PANEL, BUBBLE_RECT.size, (255, 251, 235), lip=4)
            self._misc[key] = cached
        return cached

    # -- toppings, cast, effects ------------------------------------------------------

    def topping(self, topping_id: str, size: int) -> pygame.Surface | None:
        topping = TOPPINGS_BY_ID.get(topping_id)
        if topping is None:
            return None
        image = self._art.image(topping.asset_id, int(size))
        if image is not None:
            return image
        key = ("topping_fallback", topping_id, int(size))
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(cached, CAKE_FALLBACK, (size // 2, size // 2), size // 3)
            pygame.draw.circle(cached, INK, (size // 2, size // 2), size // 3, 2)
            self._misc[key] = cached
        return cached

    def ghost(self, topping_id: str, size: int) -> pygame.Surface | None:
        """A faint copy of a topping: where one still belongs (late hint)."""

        key = (topping_id, int(size))
        if key in self._ghosts:
            return self._ghosts[key]
        base = self.topping(topping_id, size)
        faded = None
        if base is not None:
            faded = base.copy()
            faded.fill((255, 255, 255, GHOST_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
        self._ghosts[key] = faded
        return faded

    def cast(self, character: str, variant: str, height: int) -> pygame.Surface | None:
        return self._art.image(f"character.{character}", int(height), variant=variant)

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

    # -- small code-drawn marks (theme tokens, cached) -------------------------------------

    def socket(self, size: int) -> pygame.Surface:
        """An open place in a pattern row: a soft dotted ring on the frosting."""

        key = ("socket", int(size))
        cached = self._misc.get(key)
        if cached is None:
            width, height = int(size), max(8, int(size * 0.42))
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.ellipse(cached, (255, 251, 235, 200), cached.get_rect().inflate(-4, -4))
            dots = 14
            for index in range(dots):
                angle = 2 * math.pi * index / dots
                x = width / 2 + (width / 2 - 4) * math.cos(angle)
                y = height / 2 + (height / 2 - 3) * math.sin(angle)
                pygame.draw.circle(cached, INK, (int(x), int(y)), 2)
            self._misc[key] = cached
        return cached

    def card_blank(self, size: int) -> pygame.Surface:
        """A "?" place on the order card for a pattern blank."""

        key = ("card_blank", int(size))
        cached = self._misc.get(key)
        if cached is None:
            cached = pygame.Surface((size, size), pygame.SRCALPHA)
            rect = cached.get_rect().inflate(-4, -4)
            pygame.draw.ellipse(cached, (255, 236, 179), rect)
            pygame.draw.ellipse(cached, INK, rect, 2)
            mark = self._painter.label("?", int(size * 0.62), INK)
            cached.blit(mark, mark.get_rect(center=rect.center))
            self._misc[key] = cached
        return cached

    def numeral(self, value: int, size: int) -> pygame.Surface:
        return self._painter.label(str(int(value)), int(size), self._painter.theme.text)

    def badge(self, value: int, size: int) -> pygame.Surface:
        """Counting badge popped above a topping (the numeral is the taught object)."""

        key = ("badge", int(value), int(size))
        cached = self._misc.get(key)
        if cached is None:
            theme = self._painter.theme
            cached = self._painter.body(BodyShape.ROUND, (size, size), theme.accent, contour_width=max(2, size // 12)).copy()
            label = self._painter.label(str(int(value)), int(size * 0.6), theme.accent_text)
            cached.blit(label, label.get_rect(center=(size // 2, size // 2 - 1)))
            self._misc[key] = cached
        return cached

    def glow(self, size: tuple[int, int]) -> pygame.Surface:
        """Warm hint ring drawn around the order bubble or a pantry tile."""

        key = ("glow", int(size[0]), int(size[1]))
        cached = self._misc.get(key)
        if cached is None:
            width, height = int(size[0]), int(size[1])
            cached = pygame.Surface((width, height), pygame.SRCALPHA)
            for inset, alpha in ((0, 70), (7, 120), (14, 190)):
                rect = pygame.Rect(inset, inset, width - 2 * inset, height - 2 * inset)
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.rect(cached, (*HALO, alpha), rect, width=7, border_radius=max(8, min(rect.size) // 4))
            self._misc[key] = cached
        return cached

    # -- loading ------------------------------------------------------------------------

    def _private_image(self, name: str) -> pygame.Surface | None:
        if name in self._private:
            return self._private[name]
        image: pygame.Surface | None
        try:
            image = pygame.image.load(str(self._runtime_dir / name))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (OSError, pygame.error):
            image = None
        self._private[name] = image
        return image

    def clear(self) -> None:
        self._backdrop = None
        self._private.clear()
        self._ghosts.clear()
        self._misc.clear()
        self._fx.clear()


__all__ = ["BakeryArt", "CUPCAKE_GLYPH", "FX_SIZES", "PRIVATE_FILES", "RUNTIME_DIR", "bakery_visual_resolver"]
