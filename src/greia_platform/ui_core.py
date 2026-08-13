from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class UiEventResult(Enum):
    """Outcome of delivering one event to a UI surface/control."""

    IGNORED = auto()
    HANDLED = auto()
    REQUEST_CLOSE = auto()


class UiSurface(ABC):
    """Renderer-neutral logical UI layer with explicit lifecycle."""

    @property
    @abstractmethod
    def surface_id(self) -> str: ...

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    @abstractmethod
    def handle_event(self, event: object) -> UiEventResult: ...

    @abstractmethod
    def draw(self, target: object) -> None: ...


class Screen(UiSurface):
    """One full Greia UI surface; replaces the desktop-window metaphor."""


class Overlay(UiSurface):
    """Bounded transient surface above a Screen; modal by default."""

    @property
    def modal(self) -> bool:
        return True


class Control(ABC):
    """Small polymorphic interactive element owned by a Screen/Overlay."""

    @property
    @abstractmethod
    def control_id(self) -> str: ...

    @abstractmethod
    def handle_event(self, event: object) -> UiEventResult: ...

    @abstractmethod
    def draw(self, target: object) -> None: ...


@dataclass(frozen=True, slots=True)
class Collection(Generic[T]):
    """Semantic child grouping; deliberately not a filesystem directory."""

    collection_id: str
    items: tuple[T, ...]
    title: str | None = None
    icon_id: str | None = None

    def __post_init__(self) -> None:
        identifier = self.collection_id.strip()
        if not identifier:
            raise ValueError("collection_id must not be empty")
        if any(ch in identifier for ch in ("/", "\\", "\x00")):
            raise ValueError("collection_id must be semantic, not a filesystem path")
        object.__setattr__(self, "collection_id", identifier)

    def with_items(self, items: tuple[T, ...]) -> "Collection[T]":
        return Collection(self.collection_id, tuple(items), self.title, self.icon_id)


@dataclass(frozen=True, slots=True)
class GridPage:
    start: int
    stop: int
    columns: int
    rows: int
    page_size: int
    page_index: int
    page_count: int

    @property
    def empty(self) -> bool:
        return self.stop <= self.start


@dataclass(frozen=True, slots=True)
class PagedGrid:
    """Deterministic visible-page calculation for child collections."""

    columns: int
    max_rows: int

    def __post_init__(self) -> None:
        if self.columns < 1 or self.max_rows < 1:
            raise ValueError("grid dimensions must be positive")

    @property
    def page_size(self) -> int:
        return self.columns * self.max_rows

    def page(self, total: int, selected: int = 0) -> GridPage:
        total = max(0, int(total))
        if total == 0:
            return GridPage(0, 0, self.columns, 0, self.page_size, 0, 1)
        selected = min(max(0, int(selected)), total - 1)
        page_count = (total + self.page_size - 1) // self.page_size
        page_index = selected // self.page_size
        start = page_index * self.page_size
        stop = min(total, start + self.page_size)
        rows = (stop - start + self.columns - 1) // self.columns
        return GridPage(start, stop, self.columns, rows, self.page_size, page_index, page_count)

    def previous_index(self, page: GridPage) -> int:
        return max(0, page.start - page.page_size)

    def next_index(self, page: GridPage, total: int) -> int:
        return 0 if total <= 0 else min(total - 1, page.stop)


class BoundedCache(Generic[K, V]):
    """Hard-bounded LRU cache with optional explicit eviction cleanup."""

    def __init__(self, max_entries: int, *, on_evict: Callable[[K, V], None] | None = None):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = int(max_entries)
        self._items: OrderedDict[K, V] = OrderedDict()
        self._on_evict = on_evict

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def get(self, key: K, default: V | None = None) -> V | None:
        if key not in self._items:
            return default
        value = self._items.pop(key)
        self._items[key] = value
        return value

    def __getitem__(self, key: K) -> V:
        if key not in self._items:
            raise KeyError(key)
        value = self._items.pop(key)
        self._items[key] = value
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if key in self._items:
            previous = self._items.pop(key)
            if self._on_evict is not None and previous is not value:
                self._on_evict(key, previous)
        self._items[key] = value
        while len(self._items) > self.max_entries:
            old_key, old_value = self._items.popitem(last=False)
            if self._on_evict is not None:
                self._on_evict(old_key, old_value)

    def clear(self) -> None:
        if self._on_evict is not None:
            for key, value in self._items.items():
                self._on_evict(key, value)
        self._items.clear()


class InvalidationTracker:
    """Dirty/animation state for event-driven rendering."""

    def __init__(self) -> None:
        self._dirty = True
        self._animating = False

    @property
    def should_draw(self) -> bool:
        return self._dirty or self._animating

    def invalidate(self) -> None:
        self._dirty = True

    def set_animating(self, value: bool) -> None:
        self._animating = bool(value)
        if self._animating:
            self._dirty = True

    def mark_drawn(self) -> None:
        self._dirty = False


class SurfaceNavigator:
    """Own one Screen plus a bounded Overlay stack and route polymorphically."""

    def __init__(self, screen: Screen, *, max_overlays: int = 4) -> None:
        if max_overlays < 1:
            raise ValueError("max_overlays must be positive")
        self._screen = screen
        self._overlays: list[Overlay] = []
        self.max_overlays = int(max_overlays)
        self._closed = False
        self._screen.on_enter()

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("surface navigator is closed")

    @property
    def screen(self) -> Screen:
        self._require_open()
        return self._screen

    @property
    def overlays(self) -> tuple[Overlay, ...]:
        self._require_open()
        return tuple(self._overlays)

    @property
    def event_target(self) -> UiSurface:
        self._require_open()
        return self._overlays[-1] if self._overlays else self._screen

    def replace(self, screen: Screen) -> None:
        self._require_open()
        while self._overlays:
            self.pop_overlay()
        self._screen.on_exit()
        self._screen = screen
        self._screen.on_enter()

    def push_overlay(self, overlay: Overlay) -> None:
        self._require_open()
        if len(self._overlays) >= self.max_overlays:
            raise RuntimeError("overlay stack limit reached")
        self._overlays.append(overlay)
        overlay.on_enter()

    def pop_overlay(self) -> Overlay | None:
        self._require_open()
        if not self._overlays:
            return None
        overlay = self._overlays.pop()
        overlay.on_exit()
        return overlay

    def dispatch(self, event: object) -> UiEventResult:
        self._require_open()
        for overlay in reversed(self._overlays):
            result = overlay.handle_event(event)
            if result is not UiEventResult.IGNORED or overlay.modal:
                return result
        return self._screen.handle_event(event)

    def draw(self, target: object) -> None:
        self._require_open()
        self._screen.draw(target)
        for overlay in self._overlays:
            overlay.draw(target)

    def close(self) -> None:
        if self._closed:
            return
        while self._overlays:
            overlay = self._overlays.pop()
            overlay.on_exit()
        self._screen.on_exit()
        self._closed = True
