"""Pure domain state for My Greia (no pygame, no platform IO).

``Look`` is everything the child chose, expressed only as canonical platform
identifiers. ``MyGreiaModel`` owns the current tab, the current look and a
bounded undo history of whole looks, and encodes the one cross-choice rule:
the "room colour" is the sky of the storybook meadow, so choosing a room
colour while a picture wallpaper is shown returns Home to the meadow (undo
brings the picture back). Persistence happens in ``workshop_services``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from enum import StrEnum

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import CUSTOM_CHOICE, MEADOW_CHOICE, TABS, UNDO_LIMIT, Tab
except ImportError:
    from workshop_content import CUSTOM_CHOICE, MEADOW_CHOICE, TABS, UNDO_LIMIT, Tab  # type: ignore[no-redef]


class ChoiceKind(StrEnum):
    """One child-adjustable property of their Greia."""

    AVATAR = "avatar"
    BACKGROUND = "background"
    ACCENT = "accent"
    WALLPAPER = "wallpaper"
    SIZE = "size"


@dataclass(frozen=True, slots=True)
class Look:
    """The child's chosen Greia look, as canonical identifiers only."""

    avatar: str
    background: str
    accent: str
    wallpaper: str = MEADOW_CHOICE
    size: str = "normal"

    def value(self, kind: ChoiceKind) -> str:
        return str(getattr(self, kind.value))

    def with_value(self, kind: ChoiceKind, value: str) -> "Look":
        return replace(self, **{kind.value: str(value)})

    def changed_kinds(self, other: "Look") -> tuple[ChoiceKind, ...]:
        """Kinds whose value differs from ``other`` (stable order)."""

        return tuple(kind for kind in ChoiceKind if self.value(kind) != other.value(kind))


@dataclass(frozen=True, slots=True)
class Transition:
    """One applied change: what the child picked and the before/after looks."""

    kind: ChoiceKind
    before: Look
    after: Look

    @property
    def changed(self) -> tuple[ChoiceKind, ...]:
        return self.after.changed_kinds(self.before)


class MyGreiaModel:
    """Own the tab, the current look and a bounded undo history."""

    def __init__(self, look: Look, *, tab: Tab = Tab.ME, custom_available: bool = False) -> None:
        if tab not in TABS:
            raise ValueError(f"unknown tab: {tab!r}")
        self.tab: Tab = tab
        self.look = look
        # A wallpaper imported earlier (outside My Greia) cannot be recreated
        # once replaced, so it is offered only while it still exists.
        self.custom_available = bool(custom_available or look.wallpaper == CUSTOM_CHOICE)
        self._history: deque[Look] = deque(maxlen=UNDO_LIMIT)
        self.changes = 0

    # -- tabs ---------------------------------------------------------------

    def set_tab(self, tab: Tab | str) -> bool:
        tab = Tab(tab)
        if tab is self.tab:
            return False
        self.tab = tab
        return True

    def next_tab(self, step: int = 1) -> Tab:
        index = TABS.index(self.tab)
        self.tab = TABS[(index + step) % len(TABS)]
        return self.tab

    # -- choices ------------------------------------------------------------

    def propose(self, kind: ChoiceKind, value: str) -> Transition | None:
        """Return the transition for picking ``value`` (None when nothing changes)."""

        after = self.look.with_value(kind, value)
        if kind is ChoiceKind.BACKGROUND and after.wallpaper != MEADOW_CHOICE:
            # The room colour is the meadow sky: show it.
            after = after.with_value(ChoiceKind.WALLPAPER, MEADOW_CHOICE)
        if after == self.look:
            return None
        return Transition(kind, self.look, after)

    def commit(self, transition: Transition, applied: Look | None = None) -> None:
        """Record a transition once the platform accepted it.

        ``applied`` is the look the platform actually holds (a partial failure
        may leave some properties unchanged); it defaults to ``after``.
        """

        result = applied if applied is not None else transition.after
        if result == self.look:
            return
        self._history.append(self.look)
        if self.look.wallpaper == CUSTOM_CHOICE and result.wallpaper != CUSTOM_CHOICE:
            self.custom_available = False
        self.look = result
        self.changes += 1

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def propose_undo(self) -> Transition | None:
        """Return the transition back to the previous look (None when empty)."""

        while self._history:
            previous = self._history[-1]
            if previous.wallpaper == CUSTOM_CHOICE and not self.custom_available:
                previous = previous.with_value(ChoiceKind.WALLPAPER, self.look.wallpaper)
            if previous != self.look:
                changed = previous.changed_kinds(self.look)
                return Transition(changed[0], self.look, previous)
            self._history.pop()
        return None

    def commit_undo(self, applied: Look) -> None:
        if self._history:
            self._history.pop()
        self.look = applied
        self.changes += 1


__all__ = ["ChoiceKind", "Look", "MyGreiaModel", "Transition"]
