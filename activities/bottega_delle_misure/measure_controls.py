"""Shared control-kit wiring for La Bottega delle Misure (ADR 0037).

Parcels, block crates and laid block rows are Activity-drawn
``ExternalTarget``s (the kit adds pointer activation, keyboard/D-pad/stick
focus and the focus ring); "the blocks fit" is a kit round ``IconButton`` with
the shared ``check`` glyph, the three count numerals are kit tiles, replaying
the spoken goal is a round ``listen`` button and delivery progress is
``ProgressDots``. Rules stay in ``Task``; this class only maps controls to the
app callbacks and mirrors task state into enablement.
"""

from __future__ import annotations

from collections.abc import Callable

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
    from .measure_art import BOW_HEIGHT, MeasureArt
    from .measure_content import (
        CHECK_CENTER,
        CHECK_SIZE,
        COUNT_CENTER_Y,
        COUNT_CENTERS_X,
        COUNT_SIZE,
        TILT_DEGREES,
        sign_face_rect,
    )
    from .measure_model import Phase, Task, TaskKind
    from .measure_renderer import parcel_rect, rows_for
else:
    from measure_art import BOW_HEIGHT, MeasureArt
    from measure_content import (
        CHECK_CENTER,
        CHECK_SIZE,
        COUNT_CENTER_Y,
        COUNT_CENTERS_X,
        COUNT_SIZE,
        TILT_DEGREES,
        sign_face_rect,
    )
    from measure_model import Phase, Task, TaskKind
    from measure_renderer import parcel_rect, rows_for

CHECK_GLYPH = 62
LISTEN_GLYPH = 40


def parcel_id(index: int) -> str:
    return f"parcel.{index}"


def crate_id(row: int) -> str:
    return f"crate.{row}"


def row_id(row: int) -> str:
    return f"row.{row}"


def count_id(index: int) -> str:
    return f"count.{index}"


class _MovableTarget(ExternalTarget):
    """An ``ExternalTarget`` whose rectangle follows the gameplay (laid blocks)."""

    def move_to(self, rect: pygame.Rect | tuple[int, int, int, int]) -> None:
        self._rect = pygame.Rect(rect)


def _parcel_target(task: Task, parcel) -> pygame.Rect:
    """Generous hit/focus box around a parcel and its bow (balance at rest)."""

    rect = parcel_rect(task, parcel, degrees=task.tilt() * TILT_DEGREES if task.kind is TaskKind.WEIGH else 0.0)
    # The bow is included, but the box never reaches up into the chrome band.
    return rect.inflate(16, 12).union(rect.move(0, -(BOW_HEIGHT - 6)))


class MeasureControls:
    """Own the kit controls and the ``ControlLayer`` for the workshop screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: MeasureArt,
        layout: ControlLayout,
        jobs: int,
        *,
        on_parcel: Callable[[int], object],
        on_crate: Callable[[int], object],
        on_row: Callable[[int], object],
        on_check: Callable[[], object],
        on_count: Callable[[int], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._art = art
        self._on_parcel = on_parcel
        self._on_crate = on_crate
        self._on_row = on_row
        self.parcels: list[_MovableTarget] = []
        self.crates: list[ExternalTarget] = []
        self.rows: list[_MovableTarget] = []
        check_rect = pygame.Rect(0, 0, CHECK_SIZE, CHECK_SIZE)
        check_rect.center = CHECK_CENTER
        self.check: IconButton = kit.icon_button(
            "check",
            check_rect,
            icon=kit.glyph("check", CHECK_GLYPH),
            role=ButtonRole.PRIMARY,
            on_activate=on_check,
            enabled=False,
        )
        self.counts: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                count_id(index),
                pygame.Rect(x - COUNT_SIZE[0] // 2, COUNT_CENTER_Y - COUNT_SIZE[1] // 2, *COUNT_SIZE),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_count(i)),
                enabled=False,
            )
            for index, x in enumerate(COUNT_CENTERS_X)
        )
        self.sign = ExternalTarget("sign", pygame.Rect(sign_face_rect()).inflate(16, 16), on_listen, focusable=False)
        self.listen: IconButton = kit.icon_button(
            "listen", pygame.Rect(0, 0, 64, 64), icon=kit.glyph("listen", LISTEN_GLYPH), on_activate=on_listen
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=jobs)
        self.layer: ControlLayer = kit.layer((), layer_id="bottega.controls")
        self._choices: tuple[int, ...] = ()
        self.relayout(layout)

    # -- geometry -----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside (never inside) protected chrome: listen, then progress."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(self.progress.total, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- job binding --------------------------------------------------------------

    def bind_task(self, task: Task) -> None:
        """Create the focus targets for a new job's parcels, crates and rows."""

        rows = rows_for(task)
        self.parcels = [
            _MovableTarget(
                parcel_id(parcel.parcel_id),
                _parcel_target(task, parcel),
                (lambda i=parcel.parcel_id: self._on_parcel(i)),
                focus_radius=14,
            )
            for parcel in task.parcels
        ]
        laying = task.kind.lays_blocks
        self.crates = [
            ExternalTarget(
                crate_id(index), pygame.Rect(row.crate_target), (lambda r=index: self._on_crate(r)), focus_radius=16
            )
            for index, row in enumerate(rows)
            if laying and row.crate
        ]
        self.rows = [
            _MovableTarget(
                row_id(index), pygame.Rect(row.blocks_rect(1)), (lambda r=index: self._on_row(r)), focus_radius=10
            )
            for index, row in enumerate(rows)
            if laying
        ]
        self._choices = ()
        self.layer.set_targets(
            (*self.crates, *self.rows, *self.parcels, *self.counts, self.check, self.sign, self.listen, self.progress)
        )
        self.sync(task, refocus=True)

    def choice_value(self, index: int) -> int | None:
        return self._choices[index] if 0 <= index < len(self._choices) else None

    def sync(self, task: Task, *, refocus: bool = False, busy: bool = False) -> None:
        """Mirror job state into control enablement/visibility (cheap).

        ``busy`` disables gameplay targets while a scripted moment plays
        (arrival, demonstration, celebration) so input never races the model.
        """

        phase = task.phase
        live = not busy
        rows = rows_for(task)
        laying = live and phase is Phase.LAYING
        for target in self.crates:
            target.enabled = laying
        for index, target in enumerate(self.rows):
            target.move_to(rows[index].blocks_rect(task.rows[index]))
            target.enabled = laying and task.rows[index] > 0
        for target, parcel in zip(self.parcels, task.parcels):
            loading = phase is Phase.LOADING and not task.on_pan[parcel.parcel_id]
            target.enabled = live and (phase is Phase.PICKING or loading)
            # Weighing parcels move onto the pans; their targets follow.
            target.move_to(_parcel_target(task, parcel))
        resume = task.resume_phase
        self.check.visible = task.kind.lays_blocks and resume is Phase.LAYING
        self.check.enabled = laying and task.can_check
        counting = resume is Phase.COUNTING
        if counting and self._choices != task.choices:
            self._choices = task.choices
            for button, value in zip(self.counts, task.choices):
                button.icon = self._art.numeral(value)
        for index, button in enumerate(self.counts):
            value = self.choice_value(index)
            button.visible = counting and value is not None
            button.enabled = live and phase is Phase.COUNTING and value is not None and value not in task.rejected
        if refocus or not self._focused_is_live():
            self.focus_default(task)
        self.layer.invalidation.invalidate()

    def focus_default(self, task: Task) -> None:
        phase = task.phase
        if phase is Phase.LAYING:
            for index, target in enumerate(self.crates):
                if task.rows[index] == 0:
                    self.layer.focus(target.control_id)
                    return
            if self.check.enabled:
                self.layer.focus("check")
                return
        if phase is Phase.COUNTING:
            for button in self.counts:
                if button.enabled:
                    self.layer.focus(button.control_id)
                    return
        if phase in {Phase.PICKING, Phase.LOADING}:
            for target in self.parcels:
                if target.enabled:
                    self.layer.focus(target.control_id)
                    return
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["MeasureControls", "count_id", "crate_id", "parcel_id", "row_id"]
