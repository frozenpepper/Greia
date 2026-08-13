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
    """Outcome of delivering one input/event object to a UI surface or control."""

    IGNORED = auto()
    HANDLED = auto()
    REQUEST_CLOSE = auto()


class UiSurface(ABC):
    """Polymorphic logical Greia UI surface.

    A surface owns behavior and rendering for one logical UI layer. Concrete
    renderers may use Pygame, Web technologies, or a future backend; callers
    interact with the surface through this lifecycle/event/draw contract.
    """

    @property
    @abstractmethod
    def surface_id(self) -> str:
        """Return a stable semantic identity for diagnostics/navigation."""

    def on_enter(self) -> None:
        """Called when this surface becomes active."""

    def on_exit(self) -> None:
        """Called when this surface ceases to be active."""

    @abstractmethod
    def handle_event(self, event: object) -> UiEventResult:
        """Handle one renderer/runtime event without assuming its concrete type."""

    @abstractmethod
    def draw(self, target: object) -> None:
        """Render this surface onto the renderer-specific target."""


class Screen(UiSurface):
    """One full logical Greia screen.

    Screens replace the desktop/window metaphor. Normal navigation swaps the
    current Screen rather than opening arbitrary draggable windows.
    """


class Overlay(UiSurface):
    """A bounded transient layer above a Screen, normally modal."""

    @property
    def modal(self) -> bool:
        return True


class Control(ABC):
    """Small polymorphic interactive element owned by a Screen or Overlay."""

    @property
    @abstractmethod
    def control_id(self) -> str:
        """Stable semantic control identity for tests and event routing."""

    @abstractmethod
    def handle_event(self, event: object) -> UiEventResult:
        """Handle an event directed at this control."""

    @abstractmethod
    def draw(self, target: object) -> None:
        """Render the control without owning an independent display surface."""


@dataclass(frozen=True, slots=True)
class Collection(Generic[T]):
    """Ordered child-facing grouping that is explicitly not a filesystem path."""

    collection_id: str
    items: tuple[T, ...]
    title: str | None = None
    icon_id: str | None = None

    def __post_init__(self) -> None:
        identifier = self.collection_id.strip()
        if not identifier:
            raise ValueError("collection_id must not be empty")
        if any(character in identifier for character in ("/", "\\", "\x00")):
            raise ValueError("collection_id must be semantic, not a filesystem path")
        object.__setattr__(self, "collection_id", identifier)

    def with_items(self, items: tuple[T, ...]) -> "Collection[T]":
        return Collection(
            collection_id=self.collection_id,
            items=tuple(items),
            title=self.title,
            icon_id=self.icon_id,
        )


@dataclass(frozen=True, slots=True)
class GridPage:
    """Immutable visible page selection for a bounded grid."""

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
    """Cheap deterministic paging shared by child-facing collection grids."""

    columns: int
    max_rows: int

    def __post_init__(self) -> None:
        if self.columns < 1:
            raise ValueError("columns must be positive")
        if self.max_rows < 1:
            raise ValueError("max_rows must be positive")

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
        visible = stop - start
        rows = (visible + self.columns - 1) // self.columns
        return GridPage(
            start=start,
            stop=stop,
            columns=self.columns,
            rows=rows,
            page_size=self.page_size,
            page_index=page_index,
            page_count=page_count,
        )

    def previous_index(self, page: GridPage) -> int:
        return max(0, page.start - page.page_size)

    def next_index(self, page: GridPage, total: int) -> int:
        if total <= 0:
            return 0
        return min(total - 1, page.stop)


class BoundedCache(Generic[K, V]):
    """Small LRU cache with an explicit hard entry bound.

    UI caches must never grow without limit on the low-resource reference
    hardware. Values are evicted least-recently-used and an optional callback
    can release renderer-specific resources explicitly.
    """

    def __init__(
        self,
        max_entries: int,
        *,
        on_evict: Callable[[K, V], None] | None = None,
    ) -> None:
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
        existing = self._items.pop(key, None)
        if existing is not None and self._on_evict is not None and existing is not value:
            self._on_evict(key, existing)
        self._items[key] = value
        self._trim()

    def clear(self) -> None:
        if self._on_evict is not None:
            for key, value in self._items.items():
                self._on_evict(key, value)
        self._items.clear()

    def _trim(self) -> None:
        while len(self._items) > self.max_entries:
            key, value = self._items.popitem(last=False)
            if self._on_evict is not None:
                self._on_evict(key, value)


class InvalidationTracker:
    """Tracks whether a static UI needs another draw.

    The tracker intentionally knows nothing about frame clocks. A renderer can
    draw while `should_draw` is true, call `mark_drawn()`, and otherwise block
    or sleep until input/state invalidates the surface. `animating` keeps draws
    enabled only for an explicitly active bounded animation.
    """

    def __init__(self) -> None:
        self._dirty = True
        self._animating = False

    @property
    def should_draw(self) -> bool:
        return self._dirty or self._animating

    @property
    def animating(self) -> bool:
        return self._animating

    def invalidate(self) -> None:
        self._dirty = True

    def set_animating(self, value: bool) -> None:
        self._animating = bool(value)
        if self._animating:
            self._dirty = True

    def mark_drawn(self) -> None:
        self._dirty = False


class SurfaceNavigator:
    """Owns exactly one Screen plus a bounded stack of Overlays.

    Event dispatch is polymorphic: the top Overlay receives events when one is
    present; otherwise the active Screen receives them. Drawing paints the
    Screen followed by overlays in insertion order.
    """

    def __init__(self, screen: Screen, *, max_overlays: int = 4) -> None:
        if max_overlays < 1:
            raise ValueError("max_overlays must be positive")
        self._screen = screen
        self._overlays: list[Overlay] = []
        self.max_overlays = int(max_overlays)
        self._screen.on_enter()

    @property
    def screen(self) -> Screen:
        return self._screen

    @property
    def overlays(self) -> tuple[Overlay, ...]:
        return tuple(self._overlays)

    @property
    def event_target(self) -> UiSurface:
        return self._overlays[-1] if self._overlays else self._screen

    def replace(self, screen: Screen) -> None:
        while self._overlays:
            self.pop_overlay()
        self._screen.on_exit()
        self._screen = screen
        self._screen.on_enter()

    def push_overlay(self, overlay: Overlay) -> None:
        if len(self._overlays) >= self.max_overlays:
            raise RuntimeError("overlay stack limit reached")
        self._overlays.append(overlay)
        overlay.on_enter()

    def pop_overlay(self) -> Overlay | None:
        if not self._overlays:
            return None
        overlay = self._overlays.pop()
        overlay.on_exit()
        return overlay

    def dispatch(self, event: object) -> UiEventResult:
        return self.event_target.handle_event(event)

    def draw(self, target: object) -> None:
        self._screen.draw(target)
        for overlay in self._overlays:
            overlay.draw(target)

    def close(self) -> None:
        while self._overlays:
            self.pop_overlay()
        self._screen.on_exit()
