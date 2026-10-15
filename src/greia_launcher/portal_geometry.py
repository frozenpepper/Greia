"""Icon placement inside the shared Collection portal frame (``ui.portal.frame``).

Adaptive-discovery sub-Collection portals draw this frame art, so they size and
centre their core icon here instead of guessing a fraction of the outer rect.
(The root Collection Home uses the flat ``ui.portal.collection`` tiles laid out
by :mod:`greia_launcher.home_layout`.)

Geometry source: ``assets/visual/ui/v0.1/portal_frame.svg`` (520 viewBox) has
its cream opening at r=154 centred on (260, 250), i.e. a diameter of ~59 % of
the frame, sitting slightly above the frame centre. Flat core icons keep their
subject inside a 16 px inset of a 256 canvas (subjects span ~0.8 of the
canvas), so an icon canvas of 54 % of the frame width puts the subject at roughly
65-75 % of the opening diameter while square subjects still clear the rim.
"""

from __future__ import annotations

_FRAME_VIEWBOX = 520.0
_OPENING_CENTER_DY = (250.0 - 260.0) / _FRAME_VIEWBOX
PORTAL_ICON_FRACTION = 0.54
_MIN_ICON_SIZE = 24


def portal_icon_size(portal_width: int) -> int:
    """Return the square icon size for a portal of the given *untransformed* width.

    Callers pass the stable layout width rather than the hover-scaled rect so
    the bounded icon cache keeps hitting while hover/selection motion runs.
    """

    return max(_MIN_ICON_SIZE, int(round(portal_width * PORTAL_ICON_FRACTION)))


def portal_icon_center(drawn_center: tuple[int, int], drawn_height: int) -> tuple[int, int]:
    """Return the centre of the frame's opening for a drawn portal rect."""

    x, y = drawn_center
    return (x, y + int(round(drawn_height * _OPENING_CENTER_DY)))
