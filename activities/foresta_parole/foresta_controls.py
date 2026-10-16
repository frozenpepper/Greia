"""Shared control-kit wiring and screen geometry for The Word Forest (ADR 0037).

* "hear it again" is a round kit ``IconButton`` with ``icon.hud.listen``;
* round progress is kit ``ProgressDots``;
* the hanging picture sign is an Activity-drawn ``ExternalTarget`` (a tap on
  it also replays the word), so it joins the kit's hit testing.

The basket is gameplay, not a control: arrows / D-pad / left stick move it and
Space / the south face button replay the word (``directional`` profile), while
pointer and touch pull it along the forest floor. A display-only
``KeyboardHint`` (← → + Space keycaps, ↑ ↓ dimmed) hangs above the picture
sign, outside the letter rain and the basket's path: it teaches that the
arrows move the basket and Space says the word again (like the sign), and the
drawn key lights while the real key is held (ADR 0037 §4b). Nothing is placed in the
protected Home/Back region: the top row starts after ``ControlLayout.protected``
and the sign hangs below it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import time

import pygame

from greia_platform.activity_controls import (
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .foresta_model import FieldGeometry
else:
    from foresta_model import FieldGeometry  # type: ignore[no-redef]

SIGN_RECT = pygame.Rect(24, 198, 208, 210)
LEO_HEIGHT = 178
LEO_MIDBOTTOM = (124, 596)
BASKET_SIZE = (220, 138)
FRUIT_SIZE = 104
# Basket mouth (top of the rim) measured on the 256×160 master.
BASKET_MOUTH = 34 / 160
# ← → move the basket, Space says the word again (foresta_app).
KEY_HINT_KEYS = frozenset({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 34  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 28  # never drawn smaller than this on screen (when it fits)


def _key_hint_rect(layout: ControlLayout, top: int, sign: pygame.Rect) -> pygame.Rect:
    """The hint's slot: centred over the sign, between the top bar and the sign."""

    key = max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, layout.scale)))
    room_h = sign.top - 8 - top
    room_w = sign.width + 16
    width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
    while key > 16 and (width > room_w or height > room_h):
        key -= 1
        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
    rect = pygame.Rect(0, 0, width, height)
    rect.midbottom = (sign.centerx, sign.top - 8)
    rect.left = max(layout.margin, rect.left)
    return rect


@dataclass(frozen=True, slots=True)
class ForestLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    dots_bar: pygame.Rect
    sign: pygame.Rect
    stage: pygame.Rect      # sign interior: the big picture while choosing
    picture: pygame.Rect    # smaller picture above the revealed word
    word: pygame.Rect
    field: FieldGeometry
    basket_bottom: int
    keys: pygame.Rect       # keyboard hint, above the sign

    @classmethod
    def build(cls, layout: ControlLayout) -> "ForestLayout":
        size = layout.control_height(72, maximum=96)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        dots_bar = pygame.Rect(listen.right + 24, bar.top, max(0, bar.right - listen.right - 24), size)
        sign = layout.clear_of_chrome(SIGN_RECT.copy())
        sign.top = max(sign.top, bar.bottom + 12, SIGN_RECT.top)
        inner = sign.inflate(-28, -24)
        side = min(inner.width - 10, inner.height - 54)
        picture = pygame.Rect(0, 0, side, side)
        picture.midtop = (inner.centerx, inner.top + 2)
        word = pygame.Rect(inner.left, picture.bottom + 4, inner.width, inner.bottom - picture.bottom - 4)
        basket_bottom = 594
        mouth = basket_bottom - BASKET_SIZE[1] + int(BASKET_SIZE[1] * BASKET_MOUTH)
        field = FieldGeometry(
            mouth_y=float(mouth + 6),
            basket_half=BASKET_SIZE[0] // 2 - 8,
            basket_min_x=sign.right + BASKET_SIZE[0] // 2 - 30,
            basket_max_x=layout.width - BASKET_SIZE[0] // 2 - 4,
        )
        keys_top = max(bar.bottom, layout.protected.bottom) + 8
        keys = _key_hint_rect(layout, keys_top, sign)
        return cls(listen, dots_bar, sign, inner, picture, word, field, basket_bottom, keys)


class ForestControls:
    """Own the kit controls and the ``ControlLayer`` for the forest screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        task_total: int,
        on_listen: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self._on_listen = on_listen
        self.geometry = ForestLayout.build(layout)
        # Display-only (not a layer target): drawn by ``draw_keys``.
        self.keys: KeyboardHint = kit.keyboard_hint("keys", self.geometry.keys, active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 260 * 100)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.dots: ProgressDots = kit.progress_dots("progress", self._dots_rect(task_total), total=task_total)
        self.sign = ExternalTarget("sign", self.geometry.sign, on_listen, focus_radius=28)
        self.layer: ControlLayer = kit.layer((self.listen, self.dots, self.sign), layer_id="foresta.controls")

    def _dots_rect(self, total: int) -> pygame.Rect:
        bar = self.geometry.dots_bar
        height = max(28, min(46, int(bar.height * 0.62)))
        width = min(bar.width, ProgressDots.preferred_width(total, height))
        rect = pygame.Rect(0, 0, width, height)
        rect.midright = (bar.right, bar.centery)
        return rect

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = ForestLayout.build(layout)
        self.keys.rect = self.geometry.keys
        self._fast.clear()
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.dots.rect = self._dots_rect(self.dots.total)
        self.sign = ExternalTarget("sign", self.geometry.sign, self._on_listen, focus_radius=28)
        self.layer.set_targets((self.listen, self.dots, self.sign))
        self.layer.invalidation.invalidate()

    def reset_round(self, task_total: int) -> None:
        self.dots.total = int(task_total)
        self.dots.rect = self._dots_rect(task_total)
        self.dots.set_progress(0)
        self.layer.invalidation.invalidate()

    def set_progress(self, done: int) -> None:
        self.dots.set_progress(done)
        self.layer.invalidation.invalidate()

    @property
    def keys_look(self) -> tuple:
        """What the keyboard hint shows (part of the static-frame signature)."""

        return (self.keys.visible, self.keys.lit if self.keys.visible else frozenset())

    def draw_keys(self, surface: pygame.Surface) -> None:
        """The keyboard hint, one RLE blit per look (no per-frame alpha work)."""

        if self.keys.visible:
            surface.blit(self._fast(self.keys.render()), self.keys.rect.topleft)


__all__ = [
    "BASKET_SIZE",
    "FRUIT_SIZE",
    "ForestControls",
    "ForestLayout",
    "LEO_HEIGHT",
    "LEO_MIDBOTTOM",
]
