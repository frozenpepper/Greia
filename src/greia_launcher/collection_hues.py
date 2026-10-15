"""Collection hue vocabulary shared by every child Shell surface.

GREIA_SVG_AUTHORING_RULES §7 (accepted 2026-10-15) gives each primary
Collection one hue: create -> coral, play -> ocean, learn -> orange,
explore -> leaf, my_greia -> grape, and turquoise for music. My Creations is
sunshine. Home portals, Collection-page cards, header identity, page dots and
the launch overlay all read the hue from here so a child can recognise "where
am I" by colour on every screen.

Hue names are the variant names of the ``ui.portal.collection`` and
``ui.card.activity_tile`` renditions (``default`` is the turquoise variant).
RGB values are the theme tokens (``runtime/theme-defaults.toml``) and are used
only for primitive fallbacks and small accents such as page dots.
"""

from __future__ import annotations

COLLECTION_HUES: dict[str, str] = {
    "create": "coral",
    "my_creations": "sunshine",
    "play": "ocean",
    "learn": "orange",
    "explore": "leaf",
    "my_greia": "grape",
}

# Sub-Collections inherit their parent's hue except where the recipe gives
# the group its own colour (music is turquoise everywhere).
_GROUP_HUES: dict[str, str] = {"music": "default"}

HUE_RGB: dict[str, tuple[int, int, int]] = {
    "default": (68, 184, 174),
    "coral": (244, 111, 97),
    "sunshine": (255, 194, 52),
    "ocean": (74, 145, 216),
    "orange": (243, 154, 56),
    "leaf": (89, 184, 106),
    "grape": (148, 100, 201),
}


def collection_hue(collection_id: str | None, *, group_id: str | None = None) -> str:
    """Return the rendition hue variant for a Collection (and optional group)."""

    if group_id is not None and group_id in _GROUP_HUES:
        return _GROUP_HUES[group_id]
    return COLLECTION_HUES.get(collection_id or "", "default")


def hue_rgb(hue: str) -> tuple[int, int, int]:
    """Return the theme-token RGB for a hue variant (turquoise if unknown)."""

    return HUE_RGB.get(hue, HUE_RGB["default"])
