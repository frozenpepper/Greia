"""Sottomarino Giramondo — shared control-kit wiring (ADR 0037).

The cockpit keeps its own tactile buttons (they are the submarine fantasy),
but every one of them is a kit focus target. Arrows / D-pad / left stick
pilot the sub directly (the app handles them), so the focus ring is walked
with Tab / Shift+Tab or the controller shoulder buttons, in reading order;
Space / Enter / south then press the focused control, exactly like a tap.
The porthole is a target too (bubbles + names the nearest creature).

Kit-drawn controls:

* top centre: a ``PromptBanner`` for Captain Leo's order, a visitor at the
  glass, or the creature being named, always with a replay-voice button;
* top right: ``ProgressDots`` (three followed orders) and a star ``HudChip``;
* under the pilot cluster (right panel): a display-only ``KeyboardHint``
  (arrow keys + Space) that teaches the arrows fly the sub (↑ surface,
  ↓ dive, ← → steer) and Space sounds the alarm; the drawn key lights while
  the real key is held (ADR 0037 §4b). It is not a focus or touch target.

The app owns what each control does; nothing enters the protected
Home/Back region.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import time
from typing import Optional

import pygame

from greia_platform.activity_controls import (
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    HudChip,
    ProgressDots,
    PromptBanner,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.pygame_blit import PreparedSurfaces

try:
    from sub_art import PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y, PORTHOLE_RADIUS
    from sub_cockpit_view import BUTTON_RECTS, KEY_HINT_BOTTOM, KEY_HINT_TOP, PILOT_LEFT, PILOT_WIDTH
    from sub_model import ORDERS_PER_STAR
except ImportError:
    from .sub_art import PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y, PORTHOLE_RADIUS
    from .sub_cockpit_view import BUTTON_RECTS, KEY_HINT_BOTTOM, KEY_HINT_TOP, PILOT_LEFT, PILOT_WIDTH
    from .sub_model import ORDERS_PER_STAR

PORTHOLE_ID = "porthole"
BANNER_ID = "banner"
BANNER_HEIGHT = 52
BANNER_MAX_WIDTH = 540
BANNER_TOP = 12
_REPLAY_GLYPH = 34
_CHIP_HEIGHT = 42
# Arrows fly the sub, Space sounds the alarm (sub_app._pilot).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 34  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 28  # never drawn smaller than this on screen


def key_hint_rect(scale: float) -> pygame.Rect:
    """The keyboard hint's slot under the pilot cluster, keycaps legible at ``scale``."""

    key = max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, scale)))
    width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
    while key > 20 and (width > PILOT_WIDTH or height > KEY_HINT_BOTTOM - KEY_HINT_TOP):
        key -= 1
        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
    return pygame.Rect(PILOT_LEFT + (PILOT_WIDTH - width) // 2, KEY_HINT_TOP, width, height)


class PortholeTarget:
    """Focus target for the glass; pointer taps are handled by the app.

    Keyboard/controller activation acts at the centre of the porthole.
    """

    def __init__(self, on_activate: Callable[[], object]) -> None:
        self._on_activate = on_activate
        self.enabled = True
        r = int(PORTHOLE_RADIUS * 0.55)
        self._rect = pygame.Rect(PORTHOLE_CENTER_X - r, PORTHOLE_CENTER_Y - r, 2 * r, 2 * r)

    @property
    def control_id(self) -> str:
        return PORTHOLE_ID

    @property
    def rect(self) -> pygame.Rect:
        return self._rect.copy()

    @property
    def focusable(self) -> bool:
        return True

    @property
    def focus_radius(self) -> int:
        return self._rect.width // 2

    def contains(self, point: tuple[int, int]) -> bool:
        return False

    def activate(self) -> bool:
        self._on_activate()
        return True


@dataclass(frozen=True)
class BannerContent:
    """What the prompt banner says (``None`` hides it)."""

    key: tuple
    text: str
    icon: Optional[pygame.Surface]


class SubmarineControls:
    """Own the cockpit's focus targets and kit controls in one ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        on_button: Callable[[str], object],
        on_porthole: Callable[[], object],
        on_replay: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self._layout = layout
        self.keys: KeyboardHint = kit.keyboard_hint("keys", key_hint_rect(layout.scale), active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 240 * 90)
        self.buttons = {
            name: ExternalTarget(name, rect, (lambda n=name: on_button(n)), focus_radius=14)
            for name, rect in BUTTON_RECTS.items()
        }
        self.porthole = PortholeTarget(on_porthole)
        self.banner = kit.prompt_banner(
            BANNER_ID,
            pygame.Rect(PORTHOLE_CENTER_X - 150, BANNER_TOP, 300, BANNER_HEIGHT),
            replay_icon=kit.glyph("replay", _REPLAY_GLYPH),
            on_replay=on_replay,
            text_size=22,
        )
        self.banner.visible = False
        if self.banner.replay is not None:
            self.banner.replay.visible = False
        self._banner_key: Optional[tuple] = None
        self.stars = kit.hud_chip("stars", pygame.Rect(0, 0, 10, _CHIP_HEIGHT), icon=kit.star(30), value=0)
        self.dots = kit.progress_dots("orders", pygame.Rect(0, 0, 10, 34), total=ORDERS_PER_STAR, current=0)
        self._place_hud()
        targets = [
            *self.banner.controls,
            self.dots,
            self.stars,
            self.porthole,
            *self.buttons.values(),
        ]
        self.layer: ControlLayer = kit.layer(targets, initial_focus="action")

    # Reading order for Tab / shoulder focus cycling.
    FOCUS_ORDER = (
        "steer_left", "steer_right", PORTHOLE_ID, "surface", "dive", "ahead", "stop",
        "light", "sonar", "action", "bubbles", "horn",
    )

    def cycle_focus(self, step: int) -> str | None:
        """Show the focus ring, or move it ``step`` places in reading order."""

        layer = self.layer
        order = [cid for cid in self.FOCUS_ORDER if layer.target(cid).focusable]
        replay = self.banner.replay
        if replay is not None and replay.focusable:
            order.append(replay.control_id)
        if not order:
            return None
        current = layer.focused_id
        if not layer.focus_visible and current in order:
            layer.focus(current, visible=True)
            return current
        index = order.index(current) if current in order else -1
        target = order[(index + (1 if step >= 0 else -1)) % len(order)]
        layer.focus(target, visible=True)
        return target

    def relayout(self, layout: ControlLayout) -> None:
        self._layout = layout
        self.keys.rect = key_hint_rect(layout.scale)
        self._fast.clear()
        self._place_hud()

    def _place_hud(self) -> None:
        right = self._layout.width - self._layout.margin
        chip_w = self.stars.preferred_width(digits=2)
        self.stars.rect = pygame.Rect(right - chip_w, BANNER_TOP + 4, chip_w, _CHIP_HEIGHT)
        dots_w = ProgressDots.preferred_width(ORDERS_PER_STAR, 32)
        self.dots.rect = pygame.Rect(self.stars.rect.left - 10 - dots_w, BANNER_TOP + 9, dots_w, 32)

    # -- updates -------------------------------------------------------------------

    def set_progress(self, stars: int, orders_in_set: int) -> None:
        if self.stars.value != stars:
            self.stars.value = stars
            self._place_hud()
            self.layer.invalidation.invalidate()
        if self.dots.current != orders_in_set:
            self.dots.set_progress(orders_in_set)
            self.layer.invalidation.invalidate()

    def show_banner(self, content: Optional[BannerContent]) -> None:
        """Show/replace/hide the prompt banner (rebuilt only when it changes)."""

        key = content.key if content is not None else None
        if key == self._banner_key:
            return
        self._banner_key = key
        replay = self.banner.replay
        if content is None:
            self.banner.visible = False
            if replay is not None:
                replay.visible = False
            self.layer.invalidation.invalidate()
            return
        self.banner.set_text(content.text, icon=content.icon)
        if content.icon is None:
            self.banner.icon = None
        width = min(BANNER_MAX_WIDTH, max(260, self.banner.preferred_width()))
        self.banner.rect = pygame.Rect(PORTHOLE_CENTER_X - width // 2, BANNER_TOP, width, BANNER_HEIGHT)
        self.banner.visible = True
        if replay is not None:
            replay.visible = True
        self.layer.invalidation.invalidate()

    @property
    def banner_key(self) -> Optional[tuple]:
        return self._banner_key

    def blocks_play(self, point: tuple[int, int]) -> bool:
        """True when ``point`` is on a kit display (banner/HUD), not the sea."""

        if self.banner.visible and self.banner.rect.collidepoint(point):
            return True
        return self.stars.rect.collidepoint(point) or self.dots.rect.collidepoint(point)

    def draw(self, surface: pygame.Surface) -> None:
        if self.keys.visible:
            # One RLE blit per look (the kit caches each lit state once).
            surface.blit(self._fast(self.keys.render()), self.keys.rect.topleft)
        self.layer.draw(surface)
