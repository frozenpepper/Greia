"""Minimal page contracts for the Greia Encyclopedia.

The encyclopedia deliberately standardizes lifecycle and navigation, not page
composition. A page may be a calm illustrated scene, an animated diagram or a
small interactive simulation.

These contracts remain runtime-light and Greia-agnostic until Phase E1 supplies
adapters for the current Activity API, localization, audio and viewport owners.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol


class PageAudioPort(Protocol):
    """Play prerecorded semantic cues without exposing file-path policy."""

    def play(self, cue_id: str) -> None:
        """Play the localized prerecorded cue identified by ``cue_id``."""

    def stop_presenter(self) -> None:
        """Stop current presenter speech when navigation makes it irrelevant."""


class PageNavigationPort(Protocol):
    """Narrow navigation surface exposed to page implementations."""

    def open(self, page_id: str) -> None:
        """Request navigation to another encyclopedia page."""

    def back(self) -> None:
        """Request a return to the previous encyclopedia page."""


@dataclass(frozen=True)
class PageContext:
    """Collaborators a page may use.

    Phase E1 will replace the intentionally loose ``Any`` collaborators with
    exact adapters/types after inspecting the then-current Greia source owners.
    Keeping them here prevents page code from reaching directly into OS
    internals.
    """

    audio: PageAudioPort
    navigation: PageNavigationPort
    localization: Any = None
    assets: Any = None
    progress: Any = None
    viewport: Any = None


@dataclass(frozen=True)
class PageRequest:
    """Optional explicit page transition returned by an interaction."""

    page_id: str


class EncyclopediaPage(ABC):
    """Base lifecycle for every section and final encyclopedia entry."""

    page_id: str

    def __init__(self, context: PageContext) -> None:
        if not getattr(self, "page_id", ""):
            raise ValueError("EncyclopediaPage subclasses require a stable page_id")
        self.context = context

    def on_enter(self) -> None:
        """Called once when this page becomes current."""

    def on_exit(self) -> None:
        """Called before this page is replaced."""

    def handle_event(self, event: Any) -> PageRequest | None:
        """Handle one semantic/runtime event.

        The Phase E1 Pygame adapter will decide the exact event shape. Pages
        should react to Greia/Activity-level meaning rather than physical device
        identifiers whenever possible.
        """

        return None

    def update(self, dt: float) -> None:
        """Advance page-local state by bounded elapsed seconds."""

        if dt < 0:
            raise ValueError("dt must be non-negative")

    @abstractmethod
    def draw(self, surface: Any) -> None:
        """Render the current page state."""
