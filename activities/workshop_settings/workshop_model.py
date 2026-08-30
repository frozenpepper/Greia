"""Pure domain state for workshop_settings.

No pygame, PIL or rendering imports. Owns the parent-only
customization state and its invariants so it can be reasoned
about and tested without a display.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import MODES, SCAN_INTERVAL_SECONDS
except ImportError:
    from workshop_content import MODES, SCAN_INTERVAL_SECONDS  # type: ignore[no-redef]


@dataclass(slots=True)
class WorkshopModel:
    """Profile-scoped customization state for the My Greia surface."""

    mode: str = "colors"
    candidates: tuple[object, ...] = ()
    selected_wallpaper_source: Path | None = None
    wallpaper_page: int = 0
    next_scan: float = 0.0
    feedback_until: float = 0.0
    feedback_error: bool = False
    profile: dict[str, object] = field(default_factory=dict)
    avatar_choices: tuple[str, ...] = ()
    # Platform-resolved presentation objects (kept as opaque objects to stay pure).
    palette: object | None = None
    theme: object | None = None
    ui_preferences: object | None = None

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown workshop mode: {mode}")
        self.mode = str(mode)

    def success(self) -> None:
        self.feedback_error = False
        self.feedback_until = time.monotonic() + 0.8

    def error(self) -> None:
        self.feedback_error = True
        self.feedback_until = time.monotonic() + 1.8

    def change_wallpaper_page(self, delta: int, maximum: int) -> None:
        self.wallpaper_page = min(maximum, max(0, self.wallpaper_page + delta))

    def should_rescan(self, now: float) -> bool:
        return now >= self.next_scan

    def note_scanned(self, now: float) -> None:
        self.next_scan = now + SCAN_INTERVAL_SECONDS

    def clamp_wallpaper_page(self, maximum: int) -> None:
        self.wallpaper_page = min(self.wallpaper_page, max(0, maximum))


__all__ = ["WorkshopModel"]
