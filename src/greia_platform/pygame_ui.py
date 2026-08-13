"""Platform-wide name for the current shared Pygame UI helpers.

The implementation remains in `activity_ui` until the compatibility direction
can be flipped in one tested migration. New platform consumers should import
this module; existing Activities may keep importing `activity_ui`.
"""

from .activity_ui import (
    ChildUiMetrics,
    clear_icon_cache,
    draw_eraser_symbol,
    draw_grid_symbol,
    draw_icon_button,
    draw_plus_symbol,
    draw_undo_symbol,
    load_icon,
    mix,
)

__all__ = [
    "ChildUiMetrics",
    "clear_icon_cache",
    "draw_eraser_symbol",
    "draw_grid_symbol",
    "draw_icon_button",
    "draw_plus_symbol",
    "draw_undo_symbol",
    "load_icon",
    "mix",
]
