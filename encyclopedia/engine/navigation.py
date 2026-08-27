"""Explicit page registry and bounded navigation stack."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .page import EncyclopediaPage, PageContext

PageFactory = Callable[[PageContext], EncyclopediaPage]


@dataclass(frozen=True)
class RegisteredPage:
    page_id: str
    factory: PageFactory


class PageRegistry:
    """Deterministic page-id -> factory map.

    Runtime filesystem walking is deliberately avoided. Missing/duplicate page
    IDs fail loudly during authoring and tests instead of becoming mysterious
    child-runtime behavior.
    """

    def __init__(self, pages: Iterable[RegisteredPage] = ()) -> None:
        self._factories: dict[str, PageFactory] = {}
        for page in pages:
            self.register(page.page_id, page.factory)

    def register(self, page_id: str, factory: PageFactory) -> None:
        normalized = page_id.strip()
        if not normalized:
            raise ValueError("page_id cannot be empty")
        if normalized in self._factories:
            raise ValueError(f"duplicate encyclopedia page_id: {normalized}")
        self._factories[normalized] = factory

    def create(self, page_id: str, context: PageContext) -> EncyclopediaPage:
        try:
            factory = self._factories[page_id]
        except KeyError as exc:
            raise KeyError(f"unknown encyclopedia page_id: {page_id}") from exc
        page = factory(context)
        if page.page_id != page_id:
            raise ValueError(
                f"page factory for {page_id!r} created {page.page_id!r}"
            )
        return page

    def contains(self, page_id: str) -> bool:
        return page_id in self._factories

    def page_ids(self) -> tuple[str, ...]:
        return tuple(self._factories)


class PageNavigator:
    """Own one current page plus a bounded internal back stack.

    Greia's trusted Activity Home remains outside this object and outside
    encyclopedia rendering/input authority.
    """

    def __init__(
        self,
        registry: PageRegistry,
        context_factory: Callable[["PageNavigator"], PageContext],
        *,
        max_back_depth: int = 8,
    ) -> None:
        if max_back_depth < 0:
            raise ValueError("max_back_depth must be non-negative")
        self._registry = registry
        self._context_factory = context_factory
        self._max_back_depth = max_back_depth
        self._back_stack: list[str] = []
        self._current: EncyclopediaPage | None = None

    @property
    def current(self) -> EncyclopediaPage | None:
        return self._current

    def open(self, page_id: str, *, remember_current: bool = True) -> None:
        if not self._registry.contains(page_id):
            raise KeyError(f"unknown encyclopedia page_id: {page_id}")

        previous = self._current
        if previous is not None:
            previous.on_exit()
            if remember_current and self._max_back_depth:
                self._back_stack.append(previous.page_id)
                if len(self._back_stack) > self._max_back_depth:
                    del self._back_stack[0]

        context = self._context_factory(self)
        self._current = self._registry.create(page_id, context)
        self._current.on_enter()

    def back(self) -> None:
        if not self._back_stack:
            return
        page_id = self._back_stack.pop()
        if self._current is not None:
            self._current.on_exit()
        context = self._context_factory(self)
        self._current = self._registry.create(page_id, context)
        self._current.on_enter()

    def reset(self, page_id: str = "home") -> None:
        self._back_stack.clear()
        self.open(page_id, remember_current=False)
