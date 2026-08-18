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
class ScrollModel:
    """Cheap deterministic scrolling with no unbounded retained item state."""

    capacity: int
    step: int = 1

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be positive")
        if self.step < 1:
            raise ValueError("step must be positive")

    def window(self, total: int, selected: int = 0, start: int = 0) -> ScrollWindow:
        total = max(0, int(total))
        if total == 0:
            return ScrollWindow(0, 0, 0, 0, self.capacity)
        selected = min(max(0, int(selected)), total - 1)
        maximum_start = max(0, total - self.capacity)
        start = min(max(0, int(start)), maximum_start)
        if selected < start:
            start = selected
        elif selected >= start + self.capacity:
            start = selected - self.capacity + 1
        start = min(start, maximum_start)
        stop = min(total, start + self.capacity)
        return ScrollWindow(total, start, stop, selected, self.capacity)

    def move_start(self, window: ScrollWindow, direction: int) -> int:
        if window.total <= self.capacity:
            return 0
        delta = self.step * (-1 if direction < 0 else 1 if direction > 0 else 0)
        return min(max(0, window.start + delta), window.total - self.capacity)
