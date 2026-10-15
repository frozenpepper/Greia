"""La Bottega delle Misure — scene geometry shared by model, art, renderer and controls.

The reference canvas is 1024x600 logical pixels. One unit block is ``UNIT``
pixels long, so a parcel of N units is exactly N blocks long on screen: what
the child measures with the blocks is what the picture shows. Nothing here
imports pygame, so the pure model and its tests run without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600
# Kept from the first release so existing child saves load (schema migrates).
STORAGE_KEY: Final[str] = "bottega_delle_misure.progress.v1"

UNIT: Final[int] = 56  # one wooden unit block, in reference pixels
BOARD_UNITS: Final[int] = 9  # blocks that fit in one measuring board's groove
MAX_UNITS: Final[int] = 8  # longest parcel (one block can still overhang)

# -- measuring boards (wall shelves with a start stop and a block groove) -----

BOARD_SIZE: Final[tuple[int, int]] = (656, 96)
BOARD_GROOVE_X: Final[int] = 138  # board-local x where the groove (and the stop's face) is
STOP_SIZE: Final[tuple[int, int]] = (24, 184)
STOP_RISE: Final[int] = 92  # how far the stop stands above the board top
BLOCK_TOP: Final[int] = 14  # board-local y of a laid block's top edge
CRATE_SIZE: Final[tuple[int, int]] = (112, 96)
CRATE_TARGET: Final[tuple[int, int]] = (128, 104)

# Parcel "depth" classes for lying parcels: how tall a long parcel looks.
LYING_HEIGHTS: Final[tuple[int, ...]] = (50, 62, 74)
STANDING_WIDTH: Final[int] = 104
# Weighing parcels: (width, height) per size class; weight is invisible.
WEIGH_SIZES: Final[tuple[tuple[int, int], ...]] = ((92, 62), (124, 84), (152, 104))

# -- workbench, sign, cast, buttons -------------------------------------------

BENCH_TOP: Final[int] = 452  # y of the workbench top (parcels stand on it)
BENCH_SIZE: Final[tuple[int, int]] = (1024, 160)
SIGN_POS: Final[tuple[int, int]] = (821, 76)  # pinned over the wall's tool board
SIGN_SIZE: Final[tuple[int, int]] = (196, 224)
SIGN_FACE: Final[tuple[int, int, int, int]] = (16, 24, 164, 184)  # sign-local cream face
GOAL_PICTURE: Final[int] = 162  # job-card pictogram size
# The on-screen guide is Leo: this package's approved clips are in Leo's voice.
GUIDE: Final[str] = "leo"
GUIDE_MIDBOTTOM: Final[tuple[int, int]] = (86, 598)
GUIDE_HEIGHT: Final[int] = 164
CHECK_CENTER: Final[tuple[int, int]] = (934, 522)
CHECK_SIZE: Final[int] = 108
COUNT_CENTERS_X: Final[tuple[int, ...]] = (380, 512, 644)
COUNT_CENTER_Y: Final[int] = 158
COUNT_SIZE: Final[tuple[int, int]] = (112, 112)

# -- toy balance --------------------------------------------------------------

PIVOT: Final[tuple[int, int]] = (545, 244)
BEAM_HALF: Final[int] = 170
BEAM_SIZE: Final[tuple[int, int]] = (376, 44)
STAND_SIZE: Final[tuple[int, int]] = (140, 230)
STAND_PIVOT: Final[tuple[int, int]] = (70, 16)
PAN_SIZE: Final[tuple[int, int]] = (180, 136)
PAN_HANG: Final[tuple[int, int]] = (90, 6)  # pan-local hanging point
PAN_RIM: Final[int] = 104  # pan-local y a parcel rests on
TILT_DEGREES: Final[float] = 11.0
WEIGH_HOME_X: Final[tuple[int, int]] = (232, 858)  # parcels wait on the bench here


@dataclass(frozen=True, slots=True)
class RowGeometry:
    """One measuring board: where the start line is and where the board sits."""

    stop_x: int  # x of the start line (the stop's right face)
    top: int  # y of the board top (parcels rest here)
    crate: bool  # a crate of unit blocks sits on the board's left end

    @property
    def board_rect(self) -> tuple[int, int, int, int]:
        return (self.stop_x - BOARD_GROOVE_X, self.top, BOARD_SIZE[0], BOARD_SIZE[1])

    @property
    def stop_rect(self) -> tuple[int, int, int, int]:
        return (self.stop_x - STOP_SIZE[0] + 2, self.top - STOP_RISE, STOP_SIZE[0], STOP_SIZE[1])

    @property
    def crate_rect(self) -> tuple[int, int, int, int]:
        left = self.stop_x - BOARD_GROOVE_X + 10
        return (left, self.top - CRATE_SIZE[1] + 4, CRATE_SIZE[0], CRATE_SIZE[1])

    @property
    def crate_target(self) -> tuple[int, int, int, int]:
        """Generous touch target that grows sideways/down, never up into chrome."""

        x, y, w, h = self.crate_rect
        tw, th = CRATE_TARGET
        return (x + w // 2 - tw // 2, y, tw, th)

    def block_rect(self, index: int) -> tuple[int, int, int, int]:
        return (self.stop_x + index * UNIT, self.top + BLOCK_TOP, UNIT, UNIT)

    def blocks_rect(self, count: int) -> tuple[int, int, int, int]:
        """The laid blocks as one target (at least one block wide)."""

        return (self.stop_x, self.top + BLOCK_TOP, max(1, count) * UNIT, UNIT)

    def parcel_rect(self, length: int, height: int) -> tuple[int, int, int, int]:
        return (self.stop_x, self.top - height, length * UNIT, height)


# Layouts per task kind (see ``measure_model.TaskKind``). Two-row layouts start
# the boards at different places so the ends of the parcels cannot simply be
# compared by eye: the blocks are the fair way to compare.
MEASURE_ROW: Final[RowGeometry] = RowGeometry(266, 318, True)
COMPARE_ROWS: Final[tuple[RowGeometry, RowGeometry]] = (RowGeometry(300, 222, False), RowGeometry(300, 352, False))
_TWIN_STOPS: Final[tuple[int, int]] = (214, 300)
TWIN_TOPS: Final[tuple[int, int]] = (186, 354)


def twin_rows(stagger: int) -> tuple[RowGeometry, RowGeometry]:
    """The two boards of a measure-and-compare job (``stagger`` swaps the starts)."""

    first, second = _TWIN_STOPS if stagger % 2 == 0 else _TWIN_STOPS[::-1]
    return (RowGeometry(first, TWIN_TOPS[0], True), RowGeometry(second, TWIN_TOPS[1], True))


STANDING_CENTERS_X: Final[tuple[int, int]] = (420, 650)


def standing_rect(index: int, units: int) -> tuple[int, int, int, int]:
    """An upright parcel on the bench (height comparison)."""

    height = units * UNIT
    cx = STANDING_CENTERS_X[index]
    return (cx - STANDING_WIDTH // 2, BENCH_TOP - height, STANDING_WIDTH, height)


def sign_face_rect() -> tuple[int, int, int, int]:
    x, y, w, h = SIGN_FACE
    return (SIGN_POS[0] + x, SIGN_POS[1] + y, w, h)


__all__ = [
    "BEAM_HALF",
    "BEAM_SIZE",
    "BENCH_SIZE",
    "BENCH_TOP",
    "BLOCK_TOP",
    "BOARD_GROOVE_X",
    "BOARD_SIZE",
    "BOARD_UNITS",
    "CHECK_CENTER",
    "CHECK_SIZE",
    "COMPARE_ROWS",
    "COUNT_CENTERS_X",
    "COUNT_CENTER_Y",
    "COUNT_SIZE",
    "CRATE_SIZE",
    "GUIDE",
    "GUIDE_HEIGHT",
    "GUIDE_MIDBOTTOM",
    "GOAL_PICTURE",
    "LYING_HEIGHTS",
    "MAX_UNITS",
    "MEASURE_ROW",
    "PAN_HANG",
    "PAN_RIM",
    "PAN_SIZE",
    "PIVOT",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "RowGeometry",
    "SIGN_FACE",
    "SIGN_POS",
    "SIGN_SIZE",
    "STAND_PIVOT",
    "STAND_SIZE",
    "STANDING_WIDTH",
    "STOP_RISE",
    "STOP_SIZE",
    "STORAGE_KEY",
    "TILT_DEGREES",
    "TWIN_TOPS",
    "UNIT",
    "WEIGH_HOME_X",
    "WEIGH_SIZES",
    "sign_face_rect",
    "standing_rect",
    "twin_rows",
]
