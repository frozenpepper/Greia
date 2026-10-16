"""Orchestra Animali — stage geometry in the 1024×600 reference canvas.

The canvas is scaled by ``PygameReferenceCanvas`` (ADR 0026), so these
logical positions hold at 800×480 and 480×320 too. The top bar is laid out
at runtime beside the protected Home/Back region by ``ControlLayout``.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .orchestra_content import BAND, REFERENCE_WIDTH, XYLOPHONE_COLORS
else:  # pragma: no cover - runtime/script fallback
    from orchestra_content import BAND, REFERENCE_WIDTH, XYLOPHONE_COLORS

# Musicians stand on the stage boards.
STAGE_FLOOR: Final = 468
CAST_HEIGHT: Final = 194
MUSICIAN_X: Final[tuple[int, ...]] = tuple(round(196 + index * 126.4) for index in range(len(BAND)))
MUSICIAN_HIT: Final[tuple[pygame.Rect, ...]] = tuple(
    pygame.Rect(x - 60, STAGE_FLOOR - CAST_HEIGHT - 8, 120, CAST_HEIGHT + 20) for x in MUSICIAN_X
)
# Each instrument rests in front of its musician (bottom-centre anchor).
INSTRUMENT_SIZE: Final = 90
INSTRUMENT_OFFSET: Final = (0, 18)

# Rainbow xylophone at the front of the stage: long (low) to short (high).
BAR_WIDTH: Final = 64
BAR_GAP: Final = 12
BAR_CENTER_Y: Final = 536
_BAR_LEFT: Final = (REFERENCE_WIDTH - (len(XYLOPHONE_COLORS) * BAR_WIDTH + (len(XYLOPHONE_COLORS) - 1) * BAR_GAP)) // 2
BAR_RECTS: Final[tuple[pygame.Rect, ...]] = tuple(
    pygame.Rect(
        _BAR_LEFT + index * (BAR_WIDTH + BAR_GAP),
        BAR_CENTER_Y - (104 - index * 4) // 2,
        BAR_WIDTH,
        104 - index * 4,
    )
    for index in range(len(XYLOPHONE_COLORS))
)
XYLOPHONE_FRAME: Final = pygame.Rect(_BAR_LEFT - 22, BAR_CENTER_Y - 34, 2 * 22 + BAR_RECTS[-1].right - _BAR_LEFT, 68)

# Speech bubble of the inviting musician (above their head).
BUBBLE_TOP: Final = 120
BUBBLE_HEIGHT: Final = 104
BUBBLE_MIN_X: Final = 150
BUBBLE_MAX_X: Final = REFERENCE_WIDTH - 150
BUBBLE_TOKEN: Final = 54
BUBBLE_ICON: Final = 58


def musician_anchor(index: int) -> tuple[int, int]:
    """Midbottom of a musician's pose."""

    return (MUSICIAN_X[index], STAGE_FLOOR)


def instrument_anchor(index: int) -> tuple[int, int]:
    """Midbottom of a musician's instrument prop."""

    return (MUSICIAN_X[index] + INSTRUMENT_OFFSET[0], STAGE_FLOOR + INSTRUMENT_OFFSET[1])


def musician_head(index: int) -> tuple[int, int]:
    return (MUSICIAN_X[index], STAGE_FLOOR - CAST_HEIGHT + 30)


__all__ = [
    "BAR_RECTS",
    "BUBBLE_HEIGHT",
    "BUBBLE_ICON",
    "BUBBLE_MAX_X",
    "BUBBLE_MIN_X",
    "BUBBLE_TOKEN",
    "BUBBLE_TOP",
    "CAST_HEIGHT",
    "INSTRUMENT_SIZE",
    "MUSICIAN_HIT",
    "MUSICIAN_X",
    "STAGE_FLOOR",
    "XYLOPHONE_FRAME",
    "instrument_anchor",
    "musician_anchor",
    "musician_head",
]
