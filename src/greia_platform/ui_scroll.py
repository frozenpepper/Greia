from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScrollWindow:
    """Visible slice for a bounded child-facing collection.

    This is selection-aware scrolling rather than desktop freeform scrolling:
    only a bounded item range is rendered, keyboard/controller selection is
    kept visible, and pointer-wheel movement advances by semantic item rows.
    """

    total: int
    start: int
    stop: int
    selected: int
    capacity: int

    @property
    def empty(self) -> bool:
        return self.total == 0

    @property
    def can_scroll_backward(self) -> bool:
        return self.start > 0

    @property
    def can_scroll_forward(self) -> bool:
        return self.stop < self.total


@dataclass(frozen=True, slots=True)
class PaginationModel:
    """Strict, selection-aware pagination for discrete child-facing pages.

    A page is not a sliding window. In particular, a short final page must
    begin on its real page boundary instead of being shifted backward merely
    to fill the viewport. Keeping this separate from :class:`ScrollModel`
    prevents page counters, dots/arrows and the visible item slice from
    disagreeing when the final page is incomplete.
    """

    capacity: int

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be positive")

    def page_count(self, total: int) -> int:
        total = max(0, int(total))
        if total == 0:
            return 0
        return (total + self.capacity - 1) // self.capacity

    def window(self, total: int, selected: int = 0) -> ScrollWindow:
        total = max(0, int(total))
        if total == 0:
            return ScrollWindow(0, 0, 0, 0, self.capacity)
        selected = min(max(0, int(selected)), total - 1)
        start = (selected // self.capacity) * self.capacity
        stop = min(total, start + self.capacity)
        return ScrollWindow(total, start, stop, selected, self.capacity)

    def move_start(self, window: ScrollWindow, direction: int) -> int:
        if window.total <= self.capacity or direction == 0:
            return window.start if window.total else 0
        last_start = ((window.total - 1) // self.capacity) * self.capacity
        delta = self.capacity * (-1 if direction < 0 else 1)
        return min(max(0, window.start + delta), last_start)


@dataclass(frozen=True, slots=True)
class ScrollModel:
    """Cheap deterministic sliding scroll with no unbounded retained state.

    ``step == capacity`` was historically used by the launcher to mean
    discrete page navigation. Preserve that call-site compatibility by
    delegating to :class:`PaginationModel`; all other step sizes retain true
    sliding-window semantics. New discrete-page code should use
    ``PaginationModel`` directly.
    """

    capacity: int
    step: int = 1

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be positive")
        if self.step < 1:
            raise ValueError("step must be positive")

    @property
    def _is_discrete_paging(self) -> bool:
        return self.step == self.capacity

    def window(self, total: int, selected: int = 0, start: int = 0) -> ScrollWindow:
        if self._is_discrete_paging:
            return PaginationModel(self.capacity).window(total, selected)

        total = max(0, int(total))
        if total == 0:
            return ScrollWindow(0, 0, 0, 0, self.capacity)
        selected = min(max(0, int(selected)), total - 1)
        maximum_start = max(0, total - self.capacity)
        if selected < start:
            if self.step > 1:
                start = (selected // self.step) * self.step
            else:
                start = selected
        elif selected >= start + self.capacity:
            if self.step > 1:
                raw_start = selected - self.capacity + 1
                start = ((raw_start + self.step - 1) // self.step) * self.step
            else:
                start = selected - self.capacity + 1
        start = min(max(0, start), maximum_start)
        stop = min(total, start + self.capacity)
        return ScrollWindow(total, start, stop, selected, self.capacity)

    def move_start(self, window: ScrollWindow, direction: int) -> int:
        if self._is_discrete_paging:
            return PaginationModel(self.capacity).move_start(window, direction)
        if window.total <= self.capacity:
            return 0
        delta = self.step * (-1 if direction < 0 else 1 if direction > 0 else 0)
        return min(max(0, window.start + delta), window.total - self.capacity)
