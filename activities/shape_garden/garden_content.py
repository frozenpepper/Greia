"""Shape Garden — pure content and layout constants (no pygame).

The garden is a free composition tool for ages 3+: the child drags named
shapes from a tray onto a big garden, then moves, resizes, turns, recolours
and layers them over a chosen backdrop. Optional "ghost pictures" (a house,
a flower, ...) show faint dashed slots that a matching shape snaps into; they
are a gentle invitation, never a right/wrong task.

Everything here is plain data so the model, repository and tests can reason
about it without a display. Geometry has two spaces:

* **garden space** — the 1024x600 composition that is saved and exported
  (``GARDEN_WIDTH`` x ``GARDEN_HEIGHT``), so a published picture fits
  Painting and Teatrino backdrops without cropping;
* **screen space** — the 1024x600 ``PygameReferenceCanvas`` the Activity
  draws on; the garden is shown scaled inside ``GARDEN_VIEW``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

GARDEN_WIDTH: Final = 1024
GARDEN_HEIGHT: Final = 600

# -- storage ---------------------------------------------------------------

# v1 (single project, tap-to-grow) is read once for migration and never
# rewritten or deleted, so an older package can still open it.
LEGACY_STORAGE_KEY: Final = "shape_garden.project.v1"
INDEX_KEY: Final = "shape_garden.gardens.v2"
GARDEN_KEY_PREFIX: Final = "shape_garden.garden."
# Content-addressed imported backdrop pictures (prefix kept from v1 so the
# migrated garden still finds its picture).
BACKGROUND_PREFIX: Final = "garden/backgrounds"
EXPORT_NAME: Final = "garden/shared.png"
MAX_BACKGROUND_BYTES: Final = 8 * 1024 * 1024
STORAGE_KEY: Final = INDEX_KEY

# -- bounds (Acer floor) ---------------------------------------------------

MAX_SHAPES: Final = 120
MAX_GARDENS: Final = 24
MAX_UNDO: Final = 24
MAX_PARTICLES: Final = 30
GALLERY_PAGE_SIZE: Final = 6
AUTOSAVE_IDLE_SECONDS: Final = 1.0
CREATION_PICKER_POLL_SECONDS: Final = 0.12
FEEDBACK_SECONDS: Final = 2.0
LIBRARY_FULL_SECONDS: Final = 4.0
IDLE_HINT_SECONDS: Final = 6.0

# -- shapes ----------------------------------------------------------------

#: Named shapes in tray order; art is the shared ``prop.shape.<kind>`` token.
SHAPE_KINDS: Final[tuple[str, ...]] = (
    "circle",
    "square",
    "triangle",
    "rectangle",
    "star",
    "heart",
    "oval",
    "diamond",
)

#: Box side (garden px) of each size step; the art fills ~88 % of its box.
SIZE_LEVELS: Final[tuple[int, ...]] = (64, 88, 120, 160, 216, 288)
DEFAULT_SIZE: Final = 2
#: Turns are 45-degree clockwise steps.
TURN_STEPS: Final = 8

#: ``natural`` keeps each shape's own library colour; the others are the
#: theme accent tokens (runtime/theme-defaults.toml).
COLOURS: Final[dict[str, tuple[int, int, int]]] = {
    "natural": (255, 251, 235),
    "coral": (244, 111, 97),
    "orange": (243, 154, 56),
    "sunshine": (255, 194, 52),
    "leaf": (89, 184, 106),
    "ocean": (74, 145, 216),
    "grape": (148, 100, 201),
}
COLOUR_IDS: Final[tuple[str, ...]] = tuple(COLOURS)
DEFAULT_COLOUR: Final = "natural"

# Legacy v1 palette index -> colour id; legacy kind index -> shape (the v1
# "triangle" was drawn as a pentagon, so it becomes a star).
LEGACY_COLOURS: Final[tuple[str, ...]] = ("coral", "sunshine", "leaf", "ocean", "grape")
LEGACY_KINDS: Final[tuple[str, ...]] = ("circle", "square", "star")

# -- backdrops ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BackdropSpec:
    """One shared-library scene kit stacked bottom-to-top (or plain paper)."""

    backdrop_id: str
    layers: tuple[str, ...]
    paper: tuple[int, int, int] = (255, 251, 235)


BACKDROPS: Final[tuple[BackdropSpec, ...]] = (
    BackdropSpec("meadow", tuple(f"bg.meadow_day.{n}" for n in ("sky", "far", "mid", "ground", "foreground"))),
    BackdropSpec("pond", tuple(f"bg.woodland_pond.{n}" for n in ("sky", "far", "mid", "ground", "foreground"))),
    BackdropSpec("autumn", tuple(f"bg.woodland_autumn.{n}" for n in ("sky", "far", "mid", "ground", "foreground"))),
    BackdropSpec("snow", tuple(f"bg.woodland_snow.{n}" for n in ("sky", "far", "mid", "ground", "foreground"))),
    BackdropSpec("night", tuple(f"bg.night_sky.{n}" for n in ("sky", "stars", "far", "mid", "ground"))),
    BackdropSpec("beach", tuple(f"bg.sea_surface.{n}" for n in ("sky", "far", "sea", "foreground"))),
    BackdropSpec("sea", tuple(f"bg.underwater.{n}" for n in ("water", "far", "mid", "ground", "foreground"))),
    BackdropSpec("sky", tuple(f"bg.sky_clouds.{n}" for n in ("sky", "far", "mid", "foreground"))),
    BackdropSpec("paper", ()),
)
BACKDROP_IDS: Final[tuple[str, ...]] = tuple(spec.backdrop_id for spec in BACKDROPS)
DEFAULT_BACKDROP: Final = "meadow"
#: Backdrop id used while the garden shows the child's own imported picture.
PICTURE_BACKDROP: Final = "picture"


def backdrop_spec(backdrop_id: str) -> BackdropSpec:
    for spec in BACKDROPS:
        if spec.backdrop_id == backdrop_id:
            return spec
    return BACKDROPS[0]


# -- ghost pictures ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GhostSlot:
    """One faint dashed slot: a shape of ``kind`` belongs here (garden space)."""

    kind: str
    x: int
    y: int
    size: int
    turn: int
    colour: str  # suggested colour, used only for the picker thumbnail


@dataclass(frozen=True, slots=True)
class GhostPicture:
    ghost_id: str
    slots: tuple[GhostSlot, ...]


# Positions are box centres in garden space; every picture stays inside the
# calm interaction band (x 112-912) of the scene kits.
GHOST_PICTURES: Final[tuple[GhostPicture, ...]] = (
    GhostPicture("house", (
        GhostSlot("square", 512, 418, 4, 0, "coral"),
        GhostSlot("triangle", 512, 234, 4, 0, "ocean"),
        GhostSlot("rectangle", 500, 458, 2, 2, "sunshine"),
        GhostSlot("circle", 566, 372, 0, 0, "sunshine"),
    )),
    GhostPicture("flower", (
        GhostSlot("rectangle", 512, 396, 2, 2, "leaf"),
        GhostSlot("heart", 512, 124, 2, 0, "coral"),
        GhostSlot("heart", 512, 296, 2, 4, "coral"),
        GhostSlot("heart", 426, 210, 2, 6, "coral"),
        GhostSlot("heart", 598, 210, 2, 2, "coral"),
        GhostSlot("circle", 512, 210, 1, 0, "sunshine"),
    )),
    GhostPicture("tree", (
        GhostSlot("rectangle", 512, 438, 3, 2, "orange"),
        GhostSlot("circle", 446, 300, 3, 0, "leaf"),
        GhostSlot("circle", 578, 300, 3, 0, "leaf"),
        GhostSlot("circle", 512, 214, 3, 0, "leaf"),
    )),
    GhostPicture("car", (
        GhostSlot("square", 512, 300, 2, 0, "sunshine"),
        GhostSlot("rectangle", 512, 400, 4, 0, "coral"),
        GhostSlot("circle", 446, 470, 1, 0, "grape"),
        GhostSlot("circle", 578, 470, 1, 0, "grape"),
    )),
    GhostPicture("rocket", (
        GhostSlot("triangle", 444, 404, 1, 0, "coral"),
        GhostSlot("triangle", 580, 404, 1, 0, "coral"),
        GhostSlot("rectangle", 512, 330, 4, 2, "ocean"),
        GhostSlot("triangle", 512, 180, 2, 0, "coral"),
        GhostSlot("circle", 512, 296, 0, 0, "sunshine"),
    )),
    GhostPicture("fish", (
        GhostSlot("triangle", 612, 330, 2, 6, "orange"),
        GhostSlot("oval", 480, 330, 4, 0, "orange"),
        GhostSlot("circle", 410, 306, 0, 0, "ocean"),
    )),
)
GHOST_IDS: Final[tuple[str, ...]] = tuple(picture.ghost_id for picture in GHOST_PICTURES)


def ghost_picture(ghost_id: str | None) -> GhostPicture | None:
    for picture in GHOST_PICTURES:
        if picture.ghost_id == ghost_id:
            return picture
    return None


# -- screen layout (reference canvas) ------------------------------------------

#: Garden view: same 1024:600 aspect as the composition.
GARDEN_VIEW: Final = (167, 92, 690, 404)
LEFT_COLUMN_X: Final = 12
RIGHT_COLUMN_X: Final = 869
COLUMN_WIDTH: Final = 143
TRAY_PANEL: Final = (160, 504, 704, 88)
TRAY_TILE: Final = 76
TRAY_GAP: Final = 8
POT_DIAMETER: Final = 52
TOOL_TILE: Final = 72
BIN_TILE: Final = 96
DANI_HEIGHT: Final = 150
DANI_MIDBOTTOM: Final = (84, 596)

__all__ = [
    "AUTOSAVE_IDLE_SECONDS",
    "BACKDROPS",
    "BACKDROP_IDS",
    "BACKGROUND_PREFIX",
    "BIN_TILE",
    "BackdropSpec",
    "COLOURS",
    "COLOUR_IDS",
    "COLUMN_WIDTH",
    "CREATION_PICKER_POLL_SECONDS",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "DEFAULT_BACKDROP",
    "DEFAULT_COLOUR",
    "DEFAULT_SIZE",
    "EXPORT_NAME",
    "FEEDBACK_SECONDS",
    "GALLERY_PAGE_SIZE",
    "GARDEN_HEIGHT",
    "GARDEN_KEY_PREFIX",
    "GARDEN_VIEW",
    "GARDEN_WIDTH",
    "GHOST_IDS",
    "GHOST_PICTURES",
    "GhostPicture",
    "GhostSlot",
    "IDLE_HINT_SECONDS",
    "INDEX_KEY",
    "LEFT_COLUMN_X",
    "LEGACY_COLOURS",
    "LEGACY_KINDS",
    "LEGACY_STORAGE_KEY",
    "LIBRARY_FULL_SECONDS",
    "MAX_BACKGROUND_BYTES",
    "MAX_GARDENS",
    "MAX_PARTICLES",
    "MAX_SHAPES",
    "MAX_UNDO",
    "PICTURE_BACKDROP",
    "POT_DIAMETER",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "RIGHT_COLUMN_X",
    "SHAPE_KINDS",
    "SIZE_LEVELS",
    "STORAGE_KEY",
    "TOOL_TILE",
    "TRAY_GAP",
    "TRAY_PANEL",
    "TRAY_TILE",
    "TURN_STEPS",
    "backdrop_spec",
    "ghost_picture",
]
