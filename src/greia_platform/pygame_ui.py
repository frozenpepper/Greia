"""Platform-wide name for the current shared Pygame UI helpers.

The legacy drawing implementation remains in `activity_ui` until the
compatibility direction can be flipped in one tested migration. New platform
and Activity consumers should import this module: it combines lightweight draw
helpers with Greia's renderer-neutral responsive/canvas contracts through thin
Pygame adapters.
"""

from .activity_ui import (
    ChildUiMetrics,
    clear_icon_cache,
    draw_back_symbol,
    draw_eraser_symbol,
    draw_grid_symbol,
    draw_home_symbol,
    draw_icon_button,
    draw_plus_symbol,
    draw_undo_symbol,
    load_icon,
    mix,
)
from .pygame_canvas import (
    PygameCanvasMapper,
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)

__all__ = [
    "ChildUiMetrics",
    "PygameCanvasMapper",
    "PygameReferenceCanvas",
    "activity_viewport_for_surface",
    "clear_icon_cache",
    "draw_back_symbol",
    "draw_eraser_symbol",
    "draw_grid_symbol",
    "draw_home_symbol",
    "draw_icon_button",
    "draw_plus_symbol",
    "draw_undo_symbol",
    "load_icon",
    "mix",
]
