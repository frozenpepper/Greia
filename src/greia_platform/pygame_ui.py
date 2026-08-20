"""Platform-wide name for the current shared Pygame UI helpers.

The legacy drawing implementation remains in `activity_ui` until the
compatibility direction can be flipped in one tested migration. New platform
and Activity consumers should import this module: it combines lightweight draw
helpers with Greia's renderer-neutral responsive/canvas contracts through thin
Pygame adapters, including the platform-owned mixed text/color-emoji renderer
and curated child emoji-palette model.
"""

from .activity_ui import (
    ChildUiMetrics,
    clear_icon_cache,
    draw_activity_pointer,
    draw_back_symbol,
    draw_eraser_symbol,
    draw_grid_symbol,
    draw_home_symbol,
    draw_icon_button,
    draw_plus_symbol,
    draw_system_chrome_overlay,
    draw_undo_symbol,
    is_home_clicked,
    load_icon,
    mix,
)
from .emoji_palette import DEFAULT_EMOJI_CATEGORIES, EmojiCategory, EmojiPalette
from .pygame_canvas import (
    PygameCanvasMapper,
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from .typography import (
    FontRole,
    GraphemeSpan,
    GreiaTypography,
    TypographyMetrics,
    grapheme_boundaries,
    grapheme_spans,
    is_emoji_cluster,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
    truncate_grapheme_safe,
)

__all__ = [
    "ChildUiMetrics",
    "DEFAULT_EMOJI_CATEGORIES",
    "EmojiCategory",
    "EmojiPalette",
    "FontRole",
    "GraphemeSpan",
    "GreiaTypography",
    "PygameCanvasMapper",
    "PygameReferenceCanvas",
    "TypographyMetrics",
    "activity_viewport_for_surface",
    "clear_icon_cache",
    "draw_activity_pointer",
    "draw_back_symbol",
    "draw_eraser_symbol",
    "draw_grid_symbol",
    "draw_home_symbol",
    "draw_icon_button",
    "draw_plus_symbol",
    "draw_system_chrome_overlay",
    "draw_undo_symbol",
    "grapheme_boundaries",
    "grapheme_spans",
    "is_emoji_cluster",
    "is_home_clicked",
    "load_icon",
    "mix",
    "next_grapheme_boundary",
    "previous_grapheme_boundary",
    "snap_grapheme_boundary",
    "truncate_grapheme_safe",
]
