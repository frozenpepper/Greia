"""Shared control-kit wiring for Il Volo del Draghetto (ADR 0037).

Two small control sets, both laid out beside (never inside) the protected
Home/Back region:

* ``FlightHud`` - flight: a star ``HudChip``, a gem ``HudChip`` (courses with
  gems) and ``ProgressDots`` for the course's rainbow rings. Nothing here is
  focusable: during flight arrows / D-pad / stick steer the dragon and Space /
  south button flap (gameplay, not focus moves). A display-only
  ``KeyboardHint`` (arrows + Space keycaps) sits in the bottom-right corner,
  below the band the dragon and the pickups fly in: it teaches the keys and
  lights the drawn key while the real key is held (ADR 0037 §4b).
* ``MapControls`` - the pre-flight sky map: one picture ``IconButton`` tile per
  course (its sky, motif, ring and earned stars; locked courses are disabled)
  and one round ``IconButton`` per look (worn prop; locked looks disabled,
  the chosen look ``selected``). Keyboard / D-pad / stick move the kit focus,
  Space / Enter / south button activate, pointer/touch tap directly.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time

import pygame

from greia_platform.activity_controls import (
    Align,
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
    from dragon_art import DragonArt
    from dragon_courses import COURSES, LOOKS
    from dragon_model import FlightRun
    from dragon_services import FlightProgress
except ImportError:  # pragma: no cover - package import path
    from .dragon_art import DragonArt
    from .dragon_courses import COURSES, LOOKS
    from .dragon_model import FlightRun
    from .dragon_services import FlightProgress

#: Map geometry (logical 1024x600): the dragon preview owns the left side.
MAP_PREVIEW_CENTER = (190, 300)
MAP_COLUMN_LEFT = 360
MAP_COLUMN_RIGHT = 1004


def course_id_for(index: int) -> str:
    return f"course.{index}"


def look_control_id(look_id: str) -> str:
    return f"look.{look_id}"


# Arrows steer the dragon, Space flaps (dragon_app).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 34  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 28  # never drawn smaller than this on screen
KEY_HINT_BOTTOM_MARGIN = 8  # the hint sits on the cloud floor, under the flight band


class FlightHud:
    """Kit HUD for one flight: stars, gems, ring progress and the keyboard hint."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        rings: int,
        gems: bool,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        # Display-only (not a layer target): drawn by ``draw_keys`` over the sky.
        self.keys: KeyboardHint = kit.keyboard_hint("keys", pygame.Rect(0, 0, 10, 10), active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 260 * 100)
        self.has_gems = gems
        self.stars: HudChip = kit.hud_chip("hud.stars", pygame.Rect(0, 0, 10, 10), icon=None, value=0)
        self.gems: HudChip = kit.hud_chip("hud.gems", pygame.Rect(0, 0, 10, 10), icon=None, value=0)
        self.gems.visible = gems
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=rings)
        self.layer: ControlLayer = kit.layer((self.stars, self.gems, self.progress), layer_id="volo.flight")
        self._state: tuple[int, int, int] | None = None
        self.bar = pygame.Rect(0, 0, 0, 0)
        self.relayout(layout)

    def relayout(self, layout: ControlLayout) -> None:
        height = layout.control_height(52, maximum=80)
        bar = layout.top_bar(height)
        self.bar = bar
        icon = max(16, int(height * 0.72))
        self.stars.icon = self._kit.star(icon)
        self.gems.icon = self._kit.art.image("prop.shape.diamond", icon)
        self.stars.rect = pygame.Rect(0, 0, 10, height)
        chip_w = max(height * 2, self.stars.preferred_width(digits=3))
        self.gems.rect = pygame.Rect(0, 0, 10, height)
        gem_w = max(height * 2, self.gems.preferred_width(digits=2))
        dots_h = max(28, int(height * 0.7))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        left = [chip_w, gem_w] if self.has_gems else [chip_w]
        rects = layout.row(bar, left, align=Align.START, height=height)
        self.stars.rect = rects[0]
        if self.has_gems:
            self.gems.rect = rects[1]
        (dots,) = layout.row(bar, [dots_w], align=Align.END, height=dots_h)
        self.progress.rect = dots
        key = max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, layout.scale)))
        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
        right = layout.width - layout.margin
        bottom = layout.height - KEY_HINT_BOTTOM_MARGIN
        self.keys.rect = pygame.Rect(right - width, bottom - height, width, height)
        self._fast.clear()
        self._state = None
        self.layer.invalidation.invalidate()

    def draw_keys(self, surface: pygame.Surface) -> None:
        """The keyboard hint, one RLE blit per look (no per-frame alpha work)."""

        if self.keys.visible:
            surface.blit(self._fast(self.keys.render()), self.keys.rect.topleft)

    def sync(self, run: FlightRun) -> bool:
        """Mirror the run into the HUD; returns True when something changed."""

        state = (run.stars, run.gems, run.rings_passed)
        if state == self._state:
            return False
        self._state = state
        self.stars.value = run.stars
        self.gems.value = run.gems
        self.progress.set_progress(run.rings_passed)
        self.layer.invalidation.invalidate()
        return True

    @property
    def bottom(self) -> int:
        return self.bar.bottom


class MapControls:
    """Course tiles + look buttons for the pre-flight sky map."""

    def __init__(
        self,
        kit: ControlKit,
        art: DragonArt,
        layout: ControlLayout,
        *,
        on_course: Callable[[int], object],
        on_look: Callable[[str], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.total: HudChip = kit.hud_chip("hud.total", pygame.Rect(0, 0, 10, 10), icon=None, value=0)
        self.courses: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                course_id_for(index),
                pygame.Rect(0, 0, 10, 10),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_course(i)),
            )
            for index in range(len(COURSES))
        )
        self.looks: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                look_control_id(look.look_id),
                pygame.Rect(0, 0, 10, 10),
                icon=None,
                shape=BodyShape.ROUND,
                on_activate=(lambda lid=look.look_id: on_look(lid)),
            )
            for look in LOOKS
        )
        self.layer: ControlLayer = kit.layer((self.total, *self.courses, *self.looks), layer_id="volo.map")
        self._tile_picture = 120
        self._look_icon = 56
        self._state: tuple | None = None
        self.relayout(layout)

    def relayout(self, layout: ControlLayout) -> None:
        chip_h = layout.control_height(52, maximum=80)
        bar = layout.top_bar(chip_h)
        self.total.icon = self._kit.star(max(16, int(chip_h * 0.72)))
        self.total.rect = pygame.Rect(0, 0, 10, chip_h)
        (self.total.rect,) = layout.row(bar, [max(chip_h * 2, self.total.preferred_width(digits=2))], align=Align.END, height=chip_h)
        gap = 18
        span = MAP_COLUMN_RIGHT - MAP_COLUMN_LEFT
        count = len(self.courses)
        tile_w = (span - gap * (count - 1)) // count
        self._tile_picture = tile_w - 26
        tile_h = int(self._tile_picture * 0.86) + 30
        top = max(bar.bottom + 40, 140)
        for index, button in enumerate(self.courses):
            button.rect = pygame.Rect(MAP_COLUMN_LEFT + index * (tile_w + gap), top, tile_w, tile_h)
        look_size = layout.control_height(88, maximum=110)
        looks = len(self.looks)
        look_gap = max(12, (span - looks * look_size) // max(1, looks - 1))
        look_gap = min(look_gap, 40)
        row_w = looks * look_size + (looks - 1) * look_gap
        x0 = MAP_COLUMN_LEFT + (span - row_w) // 2
        y = min(layout.height - layout.margin - look_size - 6, top + tile_h + 100)
        for index, button in enumerate(self.looks):
            button.rect = pygame.Rect(x0 + index * (look_size + look_gap), y, look_size, look_size + 6)
        self._look_icon = int(look_size * 0.62)
        self._state = None
        self.layer.invalidation.invalidate()

    def sync(self, progress: FlightProgress, *, refocus: int | None = None) -> None:
        """Mirror unlocks / earned stars / chosen look into the controls."""

        state = (tuple(sorted(progress.best.items())), progress.look, self._tile_picture, self._look_icon)
        if state != self._state:
            self._state = state
            self.total.value = progress.star_sum
            for index, (button, spec) in enumerate(zip(self.courses, COURSES)):
                unlocked = progress.is_unlocked(index)
                button.enabled = unlocked
                button.icon = self._art.course_picture(
                    spec, self._tile_picture, earned=progress.best.get(spec.course_id, 0), locked=not unlocked
                )
            for button, look in zip(self.looks, LOOKS):
                button.enabled = progress.look_unlocked(look.look_id)
                button.selected = look.look_id == progress.look
                button.icon = self._art.look_icon(look.look_id, self._look_icon)
            self.layer.invalidation.invalidate()
        if refocus is not None:
            self.layer.focus(course_id_for(refocus), visible=False)
        self.layer.ensure_focus()


__all__ = ["FlightHud", "MapControls", "course_id_for", "look_control_id", "MAP_PREVIEW_CENTER"]
