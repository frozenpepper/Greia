"""Il Viaggio del Delfino — shared control-kit wiring (ADR 0037).

* **Journey picker:** three big picture cards (``IconButton`` tiles, one per
  course: bay, reef, lagoon). A course opens when the one before it has been
  finished once; closed cards are disabled (the kit fades them and skips them
  in focus traversal). Arrows / D-pad / stick move focus, Space / Enter /
  south choose, pointer and touch tap.
* **Swim HUD:** ``ProgressDots`` (one dot per stretch of the course) and a
  ``HudChip`` pearl counter in the top bar beside the protected Home/Back
  region; a second ``HudChip`` shows the count-up at the finish; a
  display-only ``KeyboardHint`` (↑ ↓ + Space) sits on the sand bottom-right.

The app owns what each control does; every control stays outside the
protected Home/Back region and is display-only while swimming, so the
arrows keep steering the dolphin.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    HudChip,
    IconButton,
    ProgressDots,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.pygame_blit import PreparedSurfaces

try:
    from delfino_art import DelfinoArt
    from delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, JourneySpec
except ImportError:  # repository/package import context
    from .delfino_art import DelfinoArt
    from .delfino_content import JOURNEYS, REFERENCE_HEIGHT, REFERENCE_WIDTH, JourneySpec

CONTROL_ACCENT = "ocean"

#: Picker geometry (logical px). Name label and stars sit under each card.
CARD_SIZE = (276, 206)
THUMB_SIZE = (250, 164)
CARD_GAP = 46
CARD_TOP = 112
NAME_SIZE = 26
STAR_SIZE = 40


class PickerControls:
    """The three journey cards and their focus layer."""

    def __init__(
        self,
        kit: ControlKit,
        art: DelfinoArt,
        text: Callable[[str], str],
        on_pick: Callable[[str], object],
    ) -> None:
        self._kit = kit
        self.cards: dict[str, IconButton] = {}
        self.names: dict[str, str] = {}
        for spec in JOURNEYS:
            journey_id = spec.journey_id
            self.names[journey_id] = text(spec.name_key)
            self.cards[journey_id] = kit.icon_button(
                f"journey.{journey_id}",
                pygame.Rect(0, 0, *CARD_SIZE),
                icon=art.thumbnail(spec, THUMB_SIZE),
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=journey_id: on_pick(chosen)),
            )
        self.layer: ControlLayer = kit.layer(
            tuple(self.cards.values()),
            layer_id="delfino.picker",
            initial_focus=f"journey.{JOURNEYS[0].journey_id}",
        )
        self.relayout()

    def relayout(self) -> None:
        total = CARD_SIZE[0] * len(self.cards) + CARD_GAP * (len(self.cards) - 1)
        x = REFERENCE_WIDTH // 2 - total // 2
        for card in self.cards.values():
            card.rect = pygame.Rect(x, CARD_TOP, *CARD_SIZE)
            x += CARD_SIZE[0] + CARD_GAP
        self.layer.invalidation.invalidate()

    def sync(self, unlocked: tuple[str, ...], suggested: str) -> None:
        for journey_id, card in self.cards.items():
            card.enabled = journey_id in unlocked
        self.layer.focus(f"journey.{suggested}")
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def card_at(self, point: tuple[int, int]) -> str | None:
        """Journey whose card contains ``point`` (closed cards included)."""

        for journey_id, card in self.cards.items():
            if card.rect.collidepoint(point):
                return journey_id
        return None

    def rect(self, journey_id: str) -> pygame.Rect:
        return self.cards[journey_id].rect


# ↑ ↓ steer the dolphin, Space leaps (delfino_input); ← → do nothing (dimmed).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.SPACE})
KEY_HINT_KEY = 32  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 26  # never drawn smaller than this on screen
KEY_HINT_BOTTOM_MARGIN = 6  # on the sand, below the deepest pearl row


class SwimHud:
    """Display-only swim HUD: stretch dots, pearl counter, count-up chip, keyboard hint.

    The ``KeyboardHint`` (↑ ↓ + Space keycaps, ← → dimmed) sits on the sand in
    the bottom-right corner, below every pearl row and away from the dolphin;
    it teaches the keys and lights the drawn key while the real key is held
    (ADR 0037 §4b). It is not a layer target.
    """

    def __init__(
        self,
        kit: ControlKit,
        art: DelfinoArt,
        layout: ControlLayout,
        spec: JourneySpec,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self._art = art
        self.keys: KeyboardHint = kit.keyboard_hint("keys", pygame.Rect(0, 0, 10, 10), active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 260 * 100)
        self.pearls: HudChip = kit.hud_chip("swim.pearls", pygame.Rect(0, 0, 120, 52), icon=art.pearl(36), value=0)
        self.count: HudChip = kit.hud_chip("count.pearls", pygame.Rect(0, 0, 150, 64), icon=art.pearl(46), value=0)
        self.count.visible = False
        self.dots: ProgressDots = kit.progress_dots("swim.dots", pygame.Rect(0, 0, 120, 36), total=spec.stretches)
        self.layer: ControlLayer = kit.layer((self.dots, self.pearls, self.count), layer_id="delfino.swim")
        self._layout = layout
        self.relayout(layout)

    def set_journey(self, spec: JourneySpec) -> None:
        self.dots = self._kit.progress_dots("swim.dots", pygame.Rect(0, 0, 120, 36), total=spec.stretches)
        self.pearls.value = 0
        self.count.value = 0
        self.count.visible = False
        self.layer.set_targets((self.dots, self.pearls, self.count))
        self.relayout(self._layout)

    def relayout(self, layout: ControlLayout) -> None:
        self._layout = layout
        height = layout.control_height(50, maximum=64)
        top = layout.top_bar(height)
        self.pearls.rect = pygame.Rect(0, 0, 10, height)
        width = self.pearls.preferred_width(digits=2)
        self.pearls.rect = pygame.Rect(top.right - width, top.top, width, height)
        dots_h = max(26, round(height * 0.62))
        dots_w = ProgressDots.preferred_width(self.dots.total, dots_h)
        self.dots.rect = pygame.Rect(top.left, top.centery - dots_h // 2, dots_w, dots_h)
        count_h = layout.control_height(64, maximum=80)
        self.count.rect = pygame.Rect(0, 0, 10, count_h)
        count_w = self.count.preferred_width(digits=2)
        self.count.rect = pygame.Rect(REFERENCE_WIDTH // 2 - count_w // 2, 146, count_w, count_h)
        key = max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, layout.scale)))
        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
        self.keys.rect = pygame.Rect(
            REFERENCE_WIDTH - layout.margin - width, REFERENCE_HEIGHT - KEY_HINT_BOTTOM_MARGIN - height, width, height
        )
        self._fast.clear()
        self.layer.invalidation.invalidate()

    def draw_keys(self, surface: pygame.Surface) -> None:
        """The keyboard hint, one RLE blit per look (no per-frame alpha work)."""

        if self.keys.visible:
            surface.blit(self._fast(self.keys.render()), self.keys.rect.topleft)

    @property
    def top_bar_bottom(self) -> int:
        return max(self.pearls.rect.bottom, self.dots.rect.bottom)

    def set_progress(self, passed: int) -> None:
        if passed != self.dots.current:
            self.dots.set_progress(passed)
            self.layer.invalidation.invalidate()

    def set_pearls(self, value: int) -> None:
        if value != self.pearls.value:
            self.pearls.value = value
            self.layer.invalidation.invalidate()

    def show_count(self, value: int | None) -> None:
        visible = value is not None
        if visible != self.count.visible or (visible and value != self.count.value):
            self.count.visible = visible
            if value is not None:
                self.count.value = value
            self.layer.invalidation.invalidate()


__all__ = [
    "CARD_SIZE",
    "CONTROL_ACCENT",
    "NAME_SIZE",
    "PickerControls",
    "STAR_SIZE",
    "SwimHud",
    "THUMB_SIZE",
]
