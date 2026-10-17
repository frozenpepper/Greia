"""Swallow a stray Home/Back tap that reaches the Shell after an Activity ends.

Why this exists. Greia's protected Activity Home sits in the top-left corner
(ADR 0019), exactly where the Shell draws the active-profile switcher on Home
and on every Collection page. Home ends the Activity in about 0.2-1.2 s; a
child who taps Home twice (or taps again because nothing seemed to happen)
lands the second tap on the Shell once the Activity window is gone, and that
tap switched the profile: on the Acer reference (2026-10-17) Home, then Home
again 0.94 s later, went Activity -> Collection page -> profile picker. Home
means "back to Greia" (docs/product/ACTIVITY_SYSTEM_NAVIGATION.md); leaving
the child's profile is a separate deliberate choice.

The guard is armed when the Shell regains the foreground after any launch
(normal return, Home before READY, crash or failed start) and, for a short
bounded interval, makes the Shell ignore primary releases inside the
protected Home/Back region. Taps anywhere else work at once, and the corner
works again after the interval. Pure geometry and time: no display system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greia_platform.system_chrome import ActivitySystemChromeLayout, UiRect

#: Long enough to cover a child's repeated tap after the Activity has gone
#: (Home -> Shell took 0.75-1.2 s on the Acer; the second tap followed within
#: about a second), short enough that a deliberate profile switch only waits
#: a moment.
RETURN_TAP_GUARD_SECONDS = 1.5


@dataclass(frozen=True, slots=True)
class ReturnTapGuard:
    """Bounded time window in which Shell taps on the protected corner are ignored."""

    region: UiRect | None = None
    until: float = 0.0

    @classmethod
    def after_activity(
        cls,
        width: int,
        height: int,
        now: float,
        *,
        home_box: Any = None,
        seconds: float = RETURN_TAP_GUARD_SECONDS,
    ) -> "ReturnTapGuard":
        """Arm for the Shell surface ``width`` x ``height`` at ``now``.

        The region is the complete protected Home+Back footprint (reserved
        even when Back was hidden). ``home_box`` (the launch-screen Home hit
        box, which may be larger on high-density metrics) widens it.
        """

        try:
            region = ActivitySystemChromeLayout.for_surface(
                width, height, back_available=True
            ).protected_region
        except ValueError:  # surface too small for chrome: nothing to guard
            return cls()
        if home_box is not None:
            right = max(region.right, int(home_box.x) + int(home_box.width))
            bottom = max(region.bottom, int(home_box.y) + int(home_box.height))
            region = UiRect(0, 0, right, bottom)
        return cls(region, now + max(0.0, float(seconds)))

    def swallows(self, position: tuple[int, int], now: float) -> bool:
        """Whether a primary release at ``position`` must not reach Shell controls."""

        if self.region is None or now >= self.until:
            return False
        x, y = position
        return self.region.contains(int(x), int(y))


__all__ = ["RETURN_TAP_GUARD_SECONDS", "ReturnTapGuard"]
