"""Shared control-kit wiring for Momo's Happy Faces (ADR 0037).

Every interactive element goes through ``greia_platform.activity_controls``:
the answer tiles (friend faces, Momo faces or help items, with the feeling
word as a caption where the word is the taught vocabulary) and the six mirror
faces are kit ``IconButton`` tiles; Momo himself is an ``ExternalTarget`` in
the warm-up (a cuddle for sad Momo); "let's play" is a primary round button
with the shared ``go`` glyph; the replay voice is a round button with the
shared ``listen`` glyph; progress is ``ProgressDots``. Keyboard, D-pad, stick
and south button reach every control through the kit's focus navigation.
Rules stay in ``MomoVisit``; this class mirrors state into the controls.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .momo_content import TASKS_PER_VISIT
    from .momo_layout import GO_RECT, MOMO_WARMUP, MOMO_WARMUP_HEIGHT, mirror_rects, momo_body_rect, tile_rects
else:
    from momo_content import TASKS_PER_VISIT
    from momo_layout import GO_RECT, MOMO_WARMUP, MOMO_WARMUP_HEIGHT, mirror_rects, momo_body_rect, tile_rects

SLOTS = 6


def choice_id(index: int) -> str:
    return f"choice.{index}"


class MomoControls:
    """Own the kit controls and the ``ControlLayer`` of the play screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        *,
        on_choice: Callable[[int], object],
        on_momo: Callable[[], object],
        on_go: Callable[[], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self.choices: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                choice_id(index),
                pygame.Rect(0, 0, 10, 10),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
                enabled=False,
            )
            for index in range(SLOTS)
        )
        for button in self.choices:
            button.visible = False
        self.momo = ExternalTarget(
            "momo",
            momo_body_rect(MOMO_WARMUP, MOMO_WARMUP_HEIGHT),
            on_momo,
            enabled=False,
            focus_radius=60,
        )
        self.go: IconButton = kit.icon_button(
            "go",
            GO_RECT,
            icon=kit.glyph("go", 62),
            role=ButtonRole.PRIMARY,
            on_activate=on_go,
            enabled=False,
        )
        self.go.visible = False
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, 64, 64),
            icon=kit.glyph("listen", 40),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 10, 10), total=TASKS_PER_VISIT
        )
        self.layer: ControlLayer = kit.layer(
            (*self.choices, self.momo, self.go, self.listen, self.progress),
            layer_id="faccine_momo.controls",
        )
        self._count = 0
        self.relayout(layout)

    # -- geometry --------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: replay voice, then progress dots."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(TASKS_PER_VISIT, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- modes -------------------------------------------------------------------

    def show_warmup(self, faces: Sequence[tuple[pygame.Surface | None, str]]) -> None:
        """Six mirror faces at Momo's sides; Momo is cuddly; progress hidden."""

        for button, rect, (icon, caption) in zip(self.choices, mirror_rects(), faces):
            button.rect = rect
            button.icon = icon
            button.caption = caption
            button.visible = True
            button.enabled = True
            button.selected = False
        self._count = len(faces)
        self.momo.enabled = True
        self.momo.focusable = True
        self.progress.visible = False
        self.layer.focus(choice_id(0))
        self.layer.invalidation.invalidate()

    def set_ready(self, ready: bool) -> None:
        if self.go.visible != ready:
            self.go.visible = ready
            self.go.enabled = ready
            self.layer.invalidation.invalidate()

    def select_mirror(self, index: int) -> None:
        for slot, button in enumerate(self.choices[: self._count]):
            button.selected = slot == index
        self.layer.invalidation.invalidate()

    def show_task(self, tiles: Sequence[tuple[pygame.Surface | None, str]], *, completed: int) -> None:
        """Answer tiles on the floor for one task; Momo is not a target."""

        rects = tile_rects(len(tiles))
        for index, button in enumerate(self.choices):
            if index < len(tiles):
                icon, caption = tiles[index]
                button.rect = rects[index]
                button.icon = icon
                button.caption = caption
                button.visible = True
                button.selected = False
            else:
                button.visible = False
                button.enabled = False
        self._count = len(tiles)
        self.momo.enabled = False
        self.momo.focusable = False
        self.go.visible = False
        self.go.enabled = False
        self.progress.visible = True
        self.progress.set_progress(completed)
        self.layer.invalidation.invalidate()

    def sync(self, *, busy: bool, rejected: set[int], solved_index: int | None = None, refocus: bool = False) -> None:
        """Mirror task state: rejected picks are set aside, busy locks input."""

        # Tiles keep their look while a scripted moment plays (the app ignores
        # picks while busy); only set-aside picks dim, and the solved one lights.
        for index, button in enumerate(self.choices[: self._count]):
            button.enabled = index not in rejected and (solved_index is None or index == solved_index)
            button.selected = index == solved_index
        self.listen.enabled = not busy
        if refocus or not self._focused_is_live():
            self.focus_default()
        self.layer.invalidation.invalidate()

    def focus_default(self) -> None:
        """Focus by position (first live tile), never by correctness."""

        for button in self.choices[: self._count]:
            if button.visible and button.enabled:
                self.layer.focus(button.control_id)
                return
        self.layer.ensure_focus()

    def set_progress(self, completed: int) -> None:
        self.progress.set_progress(completed)
        self.layer.invalidation.invalidate()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def tile(self, index: int) -> IconButton:
        return self.choices[index]

    @property
    def count(self) -> int:
        return self._count


__all__ = ["MomoControls", "SLOTS", "choice_id"]
