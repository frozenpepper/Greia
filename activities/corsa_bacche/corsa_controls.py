"""Shared control-kit wiring for La Corsa delle Bacche (ADR 0037).

The HUD is pictorial and sits in one top bar beside -- never inside -- the
protected Home/Back region:

* a basket ``HudChip`` whose icon is the shared basket glyph followed by one
  berry slot per berry in this garden (faded -> the real fruit as Momo picks
  it), so a pre-reader can see how many are still to find -- no numbers;
* ``ProgressDots`` for the gardens of this visit;
* a round ``hint`` button: Momo points and a trail of dots shows the way to
  the nearest berry.

Arrow keys / D-pad / stick steer Momo (gameplay, not focus moves); pointer
input the layer ignores is gameplay too (tap or drag in the garden). A
display-only ``KeyboardHint`` (arrows + Space keycaps) sits in the bottom-right
corner beside the garden: it teaches that the arrows walk Momo and Space
waits, and the drawn key lights while the real key is held (ADR 0037 §4b).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import math
import time

import pygame

from greia_platform.activity_controls import (
    Align,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    HudChip,
    IconButton,
    ProgressDots,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .corsa_layout import garden_area
else:
    from corsa_layout import garden_area

HINT_GLYPH_SHARE = 0.62
FADED_ALPHA = 70
MAX_SLOT_SHARE = 0.62
# Arrows walk Momo, Space waits (corsa_app).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 34  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 28  # never drawn smaller than this on screen
KEY_HINT_SMALLEST = 28  # logical keycap height a wide garden may shrink the hint to
KEY_HINT_CLEARANCE = 14  # free space kept between the hint and the garden


def key_hint_key(scale: float) -> int:
    return max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, scale)))


class CorsaControls:
    """Own the kit controls and the ``ControlLayer`` for the garden screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        gardens: int,
        *,
        berry_icon: Callable[[str, int], pygame.Surface | None],
        on_hint: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        # Display-only (not a layer target): drawn by ``draw_keys``.
        self.keys: KeyboardHint = kit.keyboard_hint("keys", pygame.Rect(0, 0, 10, 10), active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 260 * 100)
        self._berry_icon = berry_icon
        self.basket: HudChip = kit.hud_chip("hud.basket", pygame.Rect(0, 0, 10, 10), icon=None, value="")
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=gardens)
        self.hint: IconButton = kit.icon_button(
            "hint", pygame.Rect(0, 0, 10, 10), icon=None, role=ButtonRole.PRIMARY, on_activate=on_hint
        )
        self.layer: ControlLayer = kit.layer((self.basket, self.progress, self.hint), layer_id="corsa.controls")
        self._state: tuple = ()
        self._faded: dict[tuple[str, int], pygame.Surface | None] = {}
        self.bar = pygame.Rect(0, 0, 0, 0)
        self.area = pygame.Rect(0, 0, 0, 0)
        self._chip_h = 30
        self._chip_room = 200
        self.relayout(layout)

    # -- geometry ----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        height = layout.control_height(58, maximum=86)
        bar = layout.top_bar(height)
        self.bar = bar
        dots_h = max(30, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        dots, hint = layout.row(bar, [dots_w, height], align=Align.END, height=height)
        self.progress.rect = pygame.Rect(dots.x, dots.centery - dots_h // 2, dots_w, dots_h)
        self.hint.rect = hint
        self.hint.icon = self._kit.glyph("hint", int(height * HINT_GLYPH_SHARE))
        self._chip_h = max(30, int(height * 0.8))
        self._chip_room = max(self._chip_h * 3, dots.left - layout.gap * 2 - bar.left)
        self._state = ()
        self._faded.clear()
        top = max(bar.bottom, layout.protected.bottom) + 6
        self.area = garden_area(top)
        self.key_size = key_hint_key(layout.scale)
        self.place_keys(self.key_size)
        self.layer.invalidation.invalidate()

    def place_keys(self, key: int) -> None:
        """Put the keyboard hint, ``key`` px keycaps, in the bottom-right corner."""

        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
        rect = pygame.Rect(self.area.right - width, self.area.bottom - height, width, height)
        if rect != self.keys.rect:
            self.keys.rect = rect
            self._fast.clear()

    def garden_room(self) -> pygame.Rect:
        """The garden area with the keyboard hint's corner column taken off.

        Used only when a wide garden would otherwise run under the hint.
        """

        room = self.area.copy()
        room.width = self.keys.rect.left - KEY_HINT_CLEARANCE - room.left
        return room

    def keys_clear_of(self, panel: pygame.Rect) -> bool:
        return not self.keys.rect.inflate(2 * KEY_HINT_CLEARANCE, 2 * KEY_HINT_CLEARANCE).colliderect(panel)

    def draw_keys(self, surface: pygame.Surface) -> None:
        """The keyboard hint, one RLE blit per look (no per-frame alpha work)."""

        if self.keys.visible:
            surface.blit(self._fast(self.keys.render()), self.keys.rect.topleft)

    # -- state mirroring -----------------------------------------------------

    def sync(self, picked: Sequence[str], total: int, done: int, *, busy: bool = False) -> None:
        """Mirror the basket and the visit into the HUD (rebuilds only on change)."""

        state = (tuple(picked), total)
        if state != self._state:
            self._state = state
            self.basket.icon = self._basket_icon(picked, total)
            width = (self.basket.icon.get_width() if self.basket.icon is not None else self._chip_h) + self._chip_h // 2
            h = self._chip_h
            self.basket.rect = pygame.Rect(self.bar.left, self.bar.centery - h // 2, width, h)
        self.progress.set_progress(done)
        self.hint.enabled = not busy
        self.layer.invalidation.invalidate()

    def _basket_icon(self, picked: Sequence[str], total: int) -> pygame.Surface:
        h = self._chip_h
        basket = self._kit.glyph("basket", int(h * 0.86))
        basket_w = basket.get_width() if basket is not None else 0
        room = max(h, self._chip_room - basket_w - h // 2)
        spacing_share = 0.86
        slot = int(min(h * MAX_SLOT_SHARE, room / max(1, (total - 1) * spacing_share + 1)))
        slot = max(10, slot)
        spacing = max(6, int(slot * spacing_share))
        slots_w = spacing * max(0, total - 1) + slot if total else 0
        gap = max(4, h // 8)
        strip = pygame.Surface((basket_w + gap + slots_w, h), pygame.SRCALPHA)
        if basket is not None:
            strip.blit(basket, basket.get_rect(midleft=(0, h // 2)))
        x = basket_w + gap
        for index in range(total):
            if index < len(picked):
                icon = self._berry_icon(picked[index], slot)
            else:
                icon = self._faded_icon("blueberry", slot)
            if icon is not None:
                strip.blit(icon, icon.get_rect(midleft=(x, h // 2)))
            x += spacing
        return strip

    def _faded_icon(self, fruit: str, size: int) -> pygame.Surface | None:
        key = (fruit, size)
        if key not in self._faded:
            image = self._berry_icon(fruit, size)
            faded = None
            if image is not None:
                faded = image.copy()
                faded.fill((255, 255, 255, FADED_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
            self._faded[key] = faded
        return self._faded[key]


__all__ = ["CorsaControls"]
