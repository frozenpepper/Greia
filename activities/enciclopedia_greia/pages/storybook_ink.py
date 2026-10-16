"""Inked live-puppet primitives for authored Encyclopedia entry scenes.

E4 entry scenes bake every static object into one flattened authored PNG.
Parts that genuinely move or change state (an elephant trunk, a swimming
penguin, a tree crown changing season) stay live, and these helpers draw them
in the same storybook recipe as the SVG masters: one warm ink contour around a
flat fill, with anti-aliased edges where pygame offers them cheaply. They
allocate nothing per frame.
"""

from __future__ import annotations

from collections.abc import Sequence

import pygame
import pygame.gfxdraw

# Canonical artwork ink (``docs/design/GREIA_SVG_AUTHORING_RULES.md`` §2).
INK = (75, 55, 47)
OUTLINE = 3

Point = tuple[float, float]


def _ipt(point: Point) -> tuple[int, int]:
    return int(round(point[0])), int(round(point[1]))


def inked_circle(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    center: Point,
    radius: int,
    *,
    ink: tuple[int, int, int] = INK,
    outline: int = OUTLINE,
) -> None:
    """Filled disc with an anti-aliased ink rim."""

    x, y = _ipt(center)
    if radius <= 0:
        return
    outer = radius + outline
    pygame.gfxdraw.filled_circle(surface, x, y, outer, ink)
    pygame.gfxdraw.aacircle(surface, x, y, outer, ink)
    pygame.gfxdraw.filled_circle(surface, x, y, radius, color)
    pygame.gfxdraw.aacircle(surface, x, y, radius, color)


def inked_ellipse(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    rect: pygame.Rect | tuple[int, int, int, int],
    *,
    ink: tuple[int, int, int] = INK,
    outline: int = OUTLINE,
) -> None:
    """Filled ellipse with an anti-aliased ink rim."""

    box = pygame.Rect(rect)
    if box.width < 2 or box.height < 2:
        return
    cx, cy = box.center
    rx, ry = box.width // 2, box.height // 2
    pygame.gfxdraw.filled_ellipse(surface, cx, cy, rx + outline, ry + outline, ink)
    pygame.gfxdraw.aaellipse(surface, cx, cy, rx + outline, ry + outline, ink)
    pygame.gfxdraw.filled_ellipse(surface, cx, cy, rx, ry, color)
    pygame.gfxdraw.aaellipse(surface, cx, cy, rx, ry, color)


def inked_polygon(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[Point],
    *,
    ink: tuple[int, int, int] = INK,
    outline: int = OUTLINE,
) -> None:
    """Filled polygon with a rounded ink contour."""

    pts = [_ipt(point) for point in points]
    if len(pts) < 3:
        return
    pygame.draw.polygon(surface, ink, pts, 0)
    pygame.draw.lines(surface, ink, True, pts, outline * 2)
    for point in pts:
        pygame.draw.circle(surface, ink, point, outline)
    pygame.draw.polygon(surface, color, pts, 0)
    pygame.gfxdraw.aapolygon(surface, pts, color)


def inked_limb(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[Point],
    widths: Sequence[int],
    *,
    ink: tuple[int, int, int] = INK,
    outline: int = OUTLINE,
) -> None:
    """A soft tapered tube (trunk, arm, flipper) with one continuous contour.

    The ink pass is drawn for the whole limb before the fill pass so the joints
    between segments never show an internal outline.
    """

    pts = [_ipt(point) for point in points]
    if len(pts) < 2:
        return
    count = len(pts) - 1
    for fill_pass in (False, True):
        paint = color if fill_pass else ink
        grow = 0 if fill_pass else outline * 2
        for index in range(count):
            width = widths[min(index, len(widths) - 1)] + grow
            pygame.draw.line(surface, paint, pts[index], pts[index + 1], width)
            pygame.draw.circle(surface, paint, pts[index], width // 2)
            pygame.draw.circle(surface, paint, pts[index + 1], width // 2)
