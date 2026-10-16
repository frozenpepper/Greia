"""Reference geometry, picture vocabulary and limits for My Greia.

Pure data — no pygame imports. My Greia is the child's own space: a live
miniature of their Greia Home on the left and big picture choices on the
right. Every value here is either a canonical platform identifier (avatar
IDs, ``bg.wallpaper.*`` visual IDs, theme swatch kinds) or reference-canvas
geometry, so the experience never discovers product content from the
filesystem.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600


class Tab(StrEnum):
    """The four picture tabs of My Greia (one core experience: make it mine)."""

    ME = "me"
    COLOURS = "colours"
    PICTURES = "pictures"
    SIZE = "size"


TABS: Final[tuple[Tab, ...]] = (Tab.ME, Tab.COLOURS, Tab.PICTURES, Tab.SIZE)

# Canonical cast faces first (the friend greets the child on Home), then the
# other avatars in the platform policy order. Unknown policy IDs are appended.
AVATAR_PRIORITY: Final[tuple[str, ...]] = ("unicorn", "robot", "owl", "green_monster")

# Mirrors greia_launcher.profile_chrome_presentation._AVATAR_CAST_CHARACTER so
# the preview greets with the same friend Home will show (parity is tested).
AVATAR_CAST_CHARACTER: Final[dict[str, str]] = {
    "unicorn": "lilli",
    "robot": "dani",
    "owl": "leo",
    "green_monster": "momo",
}
DEFAULT_GREETER: Final = "leo"

# The default storybook Home (no wallpaper): the child's room colour shows
# through the transparent sky of this scene.
HOME_SCENE_ID: Final = "bg.meadow_day.home"
MEADOW_CHOICE: Final = "meadow"
CUSTOM_CHOICE: Final = "custom"
CURATED_WALLPAPERS: Final[tuple[str, ...]] = (
    "bg.wallpaper.meadow",
    "bg.wallpaper.forest",
    "bg.wallpaper.ocean",
    "bg.wallpaper.castle",
    "bg.wallpaper.rainbow",
    "bg.wallpaper.candy",
    "bg.wallpaper.snow",
    "bg.wallpaper.space",
)

# Real Collection Home geometry at 1024x600 (greia_launcher.home_layout with
# six portals), used to draw an honest miniature of the child's Home.
HOME_PORTALS: Final[tuple[tuple[str, str, str, tuple[int, int, int, int]], ...]] = (
    ("create", "coral", "palette", (220, 71, 168, 177)),
    ("my_creations", "sunshine", "backpack", (428, 71, 168, 177)),
    ("play", "ocean", "puzzle_pieces", (636, 71, 168, 177)),
    ("learn", "orange", "book", (220, 302, 168, 177)),
    ("explore", "leaf", "magnifier", (428, 302, 168, 177)),
    ("my_greia", "grape", "unicorn", (636, 302, 168, 177)),
)
HOME_LABEL_SLOTS: Final[tuple[tuple[int, int, int, int], ...]] = (
    (205, 252, 198, 34),
    (413, 252, 198, 34),
    (621, 252, 198, 34),
    (205, 483, 198, 34),
    (413, 483, 198, 34),
    (621, 483, 198, 34),
)
HOME_LABEL_FONT_PX: Final = 22
HOME_BADGE: Final = (14, 10, 85, 85)
HOME_STAR: Final = (935, 10, 79, 79)
HOME_GREETER: Final = (8, 407, 189, 189)
# Cream window centre inside the 288x304 portal art; icon = half its width.
PORTAL_WINDOW_CENTER: Final = (144 / 288, 144 / 304)
PORTAL_ICON_FRACTION: Final = 0.5
# Home returns with the My Greia portal focused (the child just came from it).
HOME_FOCUSED_PORTAL: Final = "my_greia"

# Caption tokens shared with the Shell caption pill.
CAPTION_INK: Final = (75, 55, 47)
CAPTION_CREAM: Final = (255, 251, 235)
CAPTION_SHADOW: Final = (205, 186, 150)

# Interaction pacing.
SPEECH_GAP_SECONDS: Final = 5.0
SPARKLE_SECONDS: Final = 0.9
UNDO_LIMIT: Final = 12

# Bounded caches (Acer floor).
MAX_PREVIEW_CACHE: Final = 3
MAX_PICTURE_CACHE: Final = 48

__all__ = [
    "AVATAR_CAST_CHARACTER",
    "AVATAR_PRIORITY",
    "CAPTION_CREAM",
    "CAPTION_INK",
    "CAPTION_SHADOW",
    "CURATED_WALLPAPERS",
    "CUSTOM_CHOICE",
    "DEFAULT_GREETER",
    "HOME_BADGE",
    "HOME_FOCUSED_PORTAL",
    "HOME_GREETER",
    "HOME_LABEL_FONT_PX",
    "HOME_LABEL_SLOTS",
    "HOME_PORTALS",
    "HOME_SCENE_ID",
    "HOME_STAR",
    "MAX_PICTURE_CACHE",
    "MAX_PREVIEW_CACHE",
    "MEADOW_CHOICE",
    "PORTAL_ICON_FRACTION",
    "PORTAL_WINDOW_CENTER",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SPARKLE_SECONDS",
    "SPEECH_GAP_SECONDS",
    "TABS",
    "Tab",
    "UNDO_LIMIT",
]
