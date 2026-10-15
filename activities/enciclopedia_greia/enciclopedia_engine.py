"""Tiny internal page engine for the Greia Encyclopedia.

The engine standardizes only lifecycle, navigation and input vocabulary. Page
content stays executable Python so a Solar System can orbit while a volcano,
heart or gear page can use entirely different lightweight interactions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    import pygame
    from greia_platform.localization import LocalizedResources
    from greia_platform.typography import GreiaTypography
    from .enciclopedia_audio import EncyclopediaAudio
    from .enciclopedia_services import EncyclopediaPalette, VisualLibrary


class PageCommand(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ACTIVATE = "activate"
    BACK = "back"


class PageInputKind(StrEnum):
    POINTER_MOVE = "pointer_move"
    POINTER_PRESS = "pointer_press"
    COMMAND = "command"


@dataclass(frozen=True, slots=True)
class PageInput:
    kind: PageInputKind
    position: tuple[float, float] | None = None
    command: PageCommand | None = None

    @classmethod
    def pointer_move(cls, position: tuple[float, float]) -> "PageInput":
        return cls(PageInputKind.POINTER_MOVE, position=position)

    @classmethod
    def pointer_press(cls, position: tuple[float, float]) -> "PageInput":
        return cls(PageInputKind.POINTER_PRESS, position=position)

    @classmethod
    def command_event(cls, command: PageCommand) -> "PageInput":
        return cls(PageInputKind.COMMAND, command=command)


class PageHost(Protocol):
    def open_page(self, page_id: str) -> None: ...
    def go_back(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class PageContext:
    host: PageHost
    resources: "LocalizedResources"
    typography: "GreiaTypography"
    visuals: "VisualLibrary"
    audio: "EncyclopediaAudio"
    palette: "EncyclopediaPalette"


class EncyclopediaPage:
    """Minimal lifecycle contract shared by every encyclopedia page."""

    page_id: str = ""

    def __init__(self, context: PageContext) -> None:
        if not self.page_id:
            raise ValueError("encyclopedia page must declare a stable page_id")
        self.context = context
        self._localized_cache: dict[str, str] = {}

    def localized(self, key: str) -> str:
        """Resolve one semantic UI string once per page instance.

        ``LocalizedResources.text`` already applies the child letter-case
        policy; draw paths use this so a frame never re-resolves a string.
        """
        cached = self._localized_cache.get(key)
        if cached is None:
            cached = self.context.resources.text(key)
            if len(self._localized_cache) >= 64:
                self._localized_cache.clear()
            self._localized_cache[key] = cached
        return cached

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def handle_input(self, event: PageInput) -> None:
        pass

    def draw(self, surface: "pygame.Surface") -> None:
        raise NotImplementedError


PageFactory = Callable[[PageContext], EncyclopediaPage]


class PageRegistry:
    """Explicit runtime registry; no filesystem scanning or runtime imports."""

    def __init__(self) -> None:
        self._factories: dict[str, PageFactory] = {}

    def register(self, page_id: str, factory: PageFactory) -> None:
        if not page_id or page_id in self._factories:
            raise ValueError(f"invalid or duplicate encyclopedia page id: {page_id!r}")
        self._factories[page_id] = factory

    def create(self, page_id: str, context: PageContext) -> EncyclopediaPage:
        try:
            factory = self._factories[page_id]
        except KeyError as exc:
            raise KeyError(f"unknown encyclopedia page: {page_id}") from exc
        page = factory(context)
        if page.page_id != page_id:
            raise ValueError(
                f"registered page id {page_id!r} does not match page {page.page_id!r}"
            )
        return page

    def page_ids(self) -> tuple[str, ...]:
        return tuple(self._factories)


class PageNavigator:
    """Own one current page and a hard-bounded internal Back history."""

    def __init__(
        self,
        registry: PageRegistry,
        context: PageContext,
        *,
        root_page_id: str = "home",
        maximum_history: int = 8,
    ) -> None:
        if maximum_history < 1 or maximum_history > 32:
            raise ValueError("maximum_history must be between 1 and 32")
        self._registry = registry
        self._context = context
        self._root_page_id = root_page_id
        self._maximum_history = maximum_history
        self._history: list[str] = []
        self._current = registry.create(root_page_id, context)
        self._current.on_enter()

    @property
    def current_page_id(self) -> str:
        return self._current.page_id

    @property
    def history(self) -> tuple[str, ...]:
        return tuple(self._history)

    @property
    def can_go_back(self) -> bool:
        return bool(self._history)

    def open(self, page_id: str) -> None:
        if page_id == self._current.page_id:
            return
        next_page = self._registry.create(page_id, self._context)
        previous_id = self._current.page_id
        self._current.on_exit()
        self._history.append(previous_id)
        if len(self._history) > self._maximum_history:
            del self._history[0]
        self._current = next_page
        self._current.on_enter()

    def back(self) -> bool:
        if not self._history:
            return False
        previous_id = self._history.pop()
        previous_page = self._registry.create(previous_id, self._context)
        self._current.on_exit()
        self._current = previous_page
        self._current.on_enter()
        return True

    def update(self, dt: float) -> None:
        self._current.update(dt)

    def handle_input(self, event: PageInput) -> None:
        self._current.handle_input(event)

    def draw(self, surface: "pygame.Surface") -> None:
        self._current.draw(surface)
