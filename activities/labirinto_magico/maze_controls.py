"""Shared control-kit wiring for Il Labirinto Magico (ADR 0037).

The HUD is pictorial and sits in one top bar beside -- never inside -- the
protected Home/Back region: a ``HudChip`` of star slots (outline -> gold as
Tito gathers this maze's stars), a ``HudChip`` holding the key once Tito has
it, ``ProgressDots`` for the mazes of this visit and a round ``hint`` button
that sends the firefly to show the way. There are no setting chips in the
child flow: maze size, stars and keys follow the adaptive ladder.

Arrow keys / D-pad steer Tito (they are gameplay, not focus moves); pointer
input the layer ignores is gameplay too (tap or drag in the maze). A
display-only ``KeyboardHint`` (arrows + Space keycaps) sits in the bottom-right
corner beside the maze: it teaches that the arrows walk Tito and Space calls
the firefly, and the drawn key lights while the real key is held (ADR 0037 §4b).
"""

from __future__ import annotations

from collections.abc import Callable
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
    from .maze_layout import maze_area
    from .maze_model import Maze
else:
    from maze_layout import maze_area
    from maze_model import Maze

HINT_GLYPH_SHARE = 0.62
# Arrows walk Tito, Space / Enter call the firefly (maze_app).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 34  # logical keycap height (legible for 4-7 year olds)
KEY_HINT_MIN_PHYSICAL = 28  # never drawn smaller than this on screen
KEY_HINT_SMALLEST = 28  # logical keycap height a wide maze may shrink the hint to
KEY_HINT_CLEARANCE = 14  # free space kept between the hint and the maze


def key_hint_key(scale: float) -> int:
    return max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, scale)))


class MazeControls:
    """Own the kit controls and the ``ControlLayer`` for the maze screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        mazes: int,
        *,
        on_hint: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        # Display-only (not a layer target): drawn by ``draw_keys``.
        self.keys: KeyboardHint = kit.keyboard_hint("keys", pygame.Rect(0, 0, 10, 10), active=KEY_HINT_KEYS, clock=clock)
        self._fast = PreparedSurfaces(max_entries=12, max_pixels=12 * 260 * 100)
        self.stars: HudChip = kit.hud_chip("hud.stars", pygame.Rect(0, 0, 10, 10), icon=None, value="")
        self.key: HudChip = kit.hud_chip("hud.key", pygame.Rect(0, 0, 10, 10), icon=None, value="")
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=mazes)
        self.hint: IconButton = kit.icon_button(
            "hint", pygame.Rect(0, 0, 10, 10), icon=None, role=ButtonRole.PRIMARY, on_activate=on_hint
        )
        self.layer: ControlLayer = kit.layer(
            (self.stars, self.key, self.progress, self.hint), layer_id="labirinto.controls"
        )
        self._icons: dict[tuple, pygame.Surface | None] = {}
        self._star_state: tuple[int, int] = (-1, -1)
        self._key_state: tuple[bool, bool] = (False, False)
        self.bar = pygame.Rect(0, 0, 0, 0)
        self.area = pygame.Rect(0, 0, 0, 0)
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
        self._chip_h = max(30, int(height * 0.78))
        self._icons.clear()
        self._star_state = (-1, -1)
        self._key_state = (False, False)
        top = max(bar.bottom, layout.protected.bottom) + 6
        self.area = maze_area(top)
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

    def maze_room(self) -> pygame.Rect:
        """The maze area with the keyboard hint's corner column taken off."""

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

    def sync(self, maze: Maze, done: int, *, busy: bool = False) -> None:
        """Mirror maze/visit state into the HUD (rebuilds only on change)."""

        layout = maze.layout
        total = len(layout.stars)
        got = len(maze.collected)
        h = self._chip_h
        x = self.bar.left
        width = h
        if total:
            if (got, total) != self._star_state:
                self._star_state = (got, total)
                self.stars.icon = self._star_slots(got, total, h)
            width = self.stars.icon.get_width() + h // 2 if self.stars.icon is not None else h
        self.stars.rect = pygame.Rect(x, self.bar.centery - h // 2, width, h)
        if total:
            x += width + 10
        self.stars.visible = bool(total)
        has_key_level = layout.key is not None
        state = (has_key_level, maze.has_key or maze.door_open)
        if state != self._key_state:
            self._key_state = state
            self.key.icon = self._key_icon(state[1], h)
        self.key.rect = pygame.Rect(x, self.bar.centery - h // 2, int(h * 1.35), h)
        self.key.visible = has_key_level
        self.progress.set_progress(done)
        self.hint.enabled = not busy and not maze.solved
        self.layer.invalidation.invalidate()

    def _star_slots(self, got: int, total: int, height: int) -> pygame.Surface:
        size = int(height * 0.74)
        spacing = int(size * 0.92)
        strip = pygame.Surface((spacing * (total - 1) + size, size), pygame.SRCALPHA)
        for index in range(total):
            strip.blit(self._kit.star(size, filled=index < got), (index * spacing, 0))
        return strip

    def _key_icon(self, owned: bool, height: int) -> pygame.Surface | None:
        image = self._kit.art.image("prop.everyday.key", int(height * 0.9))
        if image is None:
            return None
        if owned:
            return image
        faded = image.copy()
        faded.fill((255, 255, 255, 80), special_flags=pygame.BLEND_RGBA_MULT)
        return faded


__all__ = ["MazeControls"]
