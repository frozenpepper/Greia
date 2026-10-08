"""Pure hit geometry for the child's touchable clock face.

All positions are canonical 1024×600 canvas coordinates, after Greia's
trusted viewport/protected-chrome input mapping. A click nearer the rim of
the real practice dial chooses the closest quarter-hour minute mark; clicks
near its center and outside its circle are not changes.
"""
from __future__ import annotations

import math

DIAL_CENTER = (286, 338)
DIAL_RADIUS = 180
MIN_INTERACTIVE_RADIUS = 82
MAX_INTERACTIVE_RADIUS = 181
QUARTER_HOURS = (0, 15, 30, 45)


def practice_quarter_at_point(
    point: tuple[int, int], *,
    center: tuple[int, int] = DIAL_CENTER,
    inner_radius: int = MIN_INTERACTIVE_RADIUS,
    outer_radius: int = MAX_INTERACTIVE_RADIUS,
) -> int | None:
    """Return minute at nearest clock quarter; 12=o'clock zero, 3=15."""
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    square = dx * dx + dy * dy
    if square < inner_radius * inner_radius or square > outer_radius * outer_radius:
        return None
    degrees = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0
    sector = int((degrees + 45.0) // 90.0) % len(QUARTER_HOURS)
    return QUARTER_HOURS[sector]


__all__ = ["DIAL_CENTER", "DIAL_RADIUS", "QUARTER_HOURS", "practice_quarter_at_point"]
