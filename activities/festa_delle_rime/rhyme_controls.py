"""Shared control-kit wiring and festival layout for Festa delle Rime (ADR 0037).

The picture choices are kit ``IconButton`` tiles (focus, hover, pressed and
disabled states for free), the listen button is a round kit ``IconButton`` with
the shared ``icon.hud.listen`` glyph, and the big target lantern is an
``ExternalTarget`` drawn by the Activity. Keyboard, D-pad/stick and the south
face button move between them through the kit's spatial focus; pointer/touch
taps activate them directly. Nothing is placed in the protected Home/Back
region: the top row starts after ``ControlLayout.protected``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
)

if __package__:
    from .rhyme_art import RhymeArt
    from .rhyme_model import CHALLENGE_COUNT, REFERENCE_WIDTH, RhymeSession
else:
    from rhyme_art import RhymeArt
    from rhyme_model import CHALLENGE_COUNT, REFERENCE_WIDTH, RhymeSession

MAX_CHOICES = 3
STAGE_CENTER_X = 612
CHOICE_SIZE = 176
CHOICE_GAP = 26
CHOICE_CENTER_Y = 470
PICTURE_SIZE = 138
TARGET_SIZE = 236
TARGET_TOP = 92
TARGET_PICTURE = 122
LEO_HEIGHT = 250
LEO_MIDBOTTOM = (148, 590)
GARLAND_SAG = 16


def choice_id(index: int) -> str:
    return f"choice.{index}"


@dataclass(frozen=True, slots=True)
class FestivalLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    target: pygame.Rect
    garland_left: int
    garland_right: int
    garland_top: int
    slots: tuple[pygame.Rect, ...]

    @classmethod
    def build(cls, layout: ControlLayout) -> "FestivalLayout":
        size = layout.control_height(72, maximum=112)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        left = listen.right + 26
        right = REFERENCE_WIDTH - 14
        top = 18
        spacing = (right - left) / CHALLENGE_COUNT
        lantern = int(min(72, spacing * 0.86))
        slots = []
        for index in range(CHALLENGE_COUNT):
            cx = int(left + spacing * (index + 0.5))
            cy = cls._string_y(cx, left, right, top)
            slots.append(pygame.Rect(cx - lantern // 2, cy - 2, lantern, lantern))
        target = pygame.Rect(STAGE_CENTER_X - TARGET_SIZE // 2, TARGET_TOP, TARGET_SIZE, TARGET_SIZE)
        return cls(listen, target, left, right, top, tuple(slots))

    @staticmethod
    def _string_y(x: float, left: float, right: float, top: float) -> int:
        t = (x - left) / max(1.0, right - left)
        return int(top + GARLAND_SAG * 4 * t * (1 - t))

    def string_y(self, x: float) -> int:
        return self._string_y(x, self.garland_left, self.garland_right, self.garland_top)

    @staticmethod
    def choice_rect(count: int, index: int) -> pygame.Rect:
        span = count * CHOICE_SIZE + (count - 1) * CHOICE_GAP
        left = STAGE_CENTER_X - span // 2 + index * (CHOICE_SIZE + CHOICE_GAP)
        return pygame.Rect(left, CHOICE_CENTER_Y - CHOICE_SIZE // 2, CHOICE_SIZE, CHOICE_SIZE)


class RhymeControls:
    """Own the kit controls and the ``ControlLayer`` for the festival screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: RhymeArt,
        layout: ControlLayout,
        *,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
        on_target: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.geometry = FestivalLayout.build(layout)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.target = ExternalTarget("target", self.geometry.target, on_target, focus_radius=40)
        self.choices = tuple(
            kit.icon_button(
                choice_id(index),
                FestivalLayout.choice_rect(MAX_CHOICES, index),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
            )
            for index in range(MAX_CHOICES)
        )
        self.layer: ControlLayer = kit.layer(
            (self.listen, self.target, *self.choices),
            layer_id="festa.controls",
        )
        self._challenge_id: str | None = None

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = FestivalLayout.build(layout)
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.layer.invalidation.invalidate()

    def sync(self, session: RhymeSession) -> None:
        """Mirror the current challenge into tiles (pictures are pre-scaled here)."""

        challenge = session.current_challenge
        if challenge is None:
            for button in self.choices:
                button.visible = False
            self.layer.invalidation.invalidate()
            return
        count = len(challenge.choices)
        eliminated = session.eliminated
        for index, button in enumerate(self.choices):
            if index < count:
                button.rect = FestivalLayout.choice_rect(count, index)
                button.icon = self._art.picture(challenge.choices[index], PICTURE_SIZE)
                button.visible = True
                button.enabled = index not in eliminated
            else:
                button.visible = False
                button.enabled = False
        self.target.enabled = True
        if challenge.challenge_id != self._challenge_id:
            self._challenge_id = challenge.challenge_id
            self.layer.focus(choice_id(0))
        elif self.layer.focused_id is not None and not self.layer.target(self.layer.focused_id).focusable:
            first = next((choice_id(i) for i in range(count) if i not in eliminated), "listen")
            self.layer.focus(first)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def choice_center(self, index: int) -> tuple[int, int]:
        return self.choices[index].rect.center


__all__ = ["FestivalLayout", "RhymeControls", "choice_id", "MAX_CHOICES"]
