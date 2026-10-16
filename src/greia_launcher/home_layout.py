"""Responsive geometry for the child Shell's Collection Home and profile picker.

One authored semantic layout (ADR 0026 / RESPONSIVE_UI_AND_DISPLAY_LAYOUT):
the same rules reflow the Home portals, their labels and the greeting cast
character from 480x320 up to 1280x800 and wider. There are no per-device
coordinate tables; every measure derives from the viewport and is clamped to a
useful range. The module is renderer-neutral (``UiRect`` only) so the geometry
is unit-testable without Pygame.

Reserved rectangles (the active-profile switcher and the achievement star in
the top corners) are inputs: the portal grid and the greeter are moved or
shrunk so that nothing is ever drawn over those protected Shell controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from greia_platform.responsive_layout import UiRect

# Collection portal art canvas (assets/visual/ui/v0.2/collection_portal*.svg).
PORTAL_ART_WIDTH = 288
PORTAL_ART_HEIGHT = 304
# Cream window centre inside the art (where the flat core icon sits).
_PORTAL_WINDOW_CX = 144 / PORTAL_ART_WIDTH
_PORTAL_WINDOW_CY = 144 / PORTAL_ART_HEIGHT
# Flat core icons keep their subject inside a 16 px inset of a 256 canvas, so
# an icon canvas of half the art width fills ~75 % of the window diameter.
PORTAL_ICON_FRACTION = 0.5
# Visible tile body width as a fraction of the art width (232 / 288).
PORTAL_BODY_FRACTION = 232 / PORTAL_ART_WIDTH

_REFERENCE_WIDTH = 1024
_REFERENCE_HEIGHT = 600


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def layout_scale(width: int, height: int) -> float:
    """Return the bounded reference scale used for decorative/typographic measures."""

    return _clamp(
        min(width / _REFERENCE_WIDTH, height / _REFERENCE_HEIGHT), 0.6, 1.3
    )


# Top-right Shell corner: the achievement star sits in the corner and the
# Home time-left pill sits to its left on the same row (never underneath it).
CORNER_MARGIN = 14
CORNER_TOP = 10
_CORNER_GAP = 10


def achievement_button_rect(width: int, height: int) -> UiRect:
    """The badge-library star button, anchored to the top-right corner."""

    size = max(58, min(76, height // 8))
    return UiRect(width - size - CORNER_MARGIN, CORNER_TOP, size, size)


def usage_pill_rect(
    width: int,
    height: int,
    content_width: int,
    pill_height: int,
    *,
    left_limit: int,
) -> UiRect:
    """Time-left pill: right-aligned against the star, vertically centred on it.

    ``content_width`` is the pill's preferred width; it shrinks (never below the
    clock plus a few characters) so it stays right of ``left_limit`` (the
    profile badge edge). The caller scales the label to the returned width.
    """

    star = achievement_button_rect(width, height)
    right = star.x - _CORNER_GAP
    available = max(80, right - left_limit - _CORNER_GAP)
    pill_width = max(80, min(content_width, available))
    top = star.y + max(0, (star.height - pill_height) // 2)
    return UiRect(right - pill_width, top, pill_width, pill_height)


def usage_pill_band(width: int, height: int, *, left_limit: int) -> UiRect:
    """The largest area the time-left pill can occupy (for layout avoidance)."""

    clock = max(24, min(32, height // 18))
    font = max(15, min(21, height // 30))
    pill_height = max(clock + 10, int(font * 1.45) + 14)
    return usage_pill_rect(width, height, 10_000, pill_height, left_limit=left_limit)


def overlaps(a: UiRect, b: UiRect) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


def portal_icon_rect(portal: UiRect) -> UiRect:
    """Return the icon square centred in the portal art's cream window."""

    size = max(16, int(round(portal.width * PORTAL_ICON_FRACTION)))
    cx = portal.x + int(round(portal.width * _PORTAL_WINDOW_CX))
    cy = portal.y + int(round(portal.height * _PORTAL_WINDOW_CY))
    return UiRect(cx - size // 2, cy - size // 2, size, size)


def greeter_rect(
    width: int,
    height: int,
    *,
    free_right_edge: int,
    reserved: Sequence[UiRect] = (),
    minimum_px: int = 56,
) -> UiRect | None:
    """Place the greeting cast character in the free left margin, standing on the ground.

    ``free_right_edge`` is the left edge of the interactive content; the
    character never crosses it. Returns ``None`` when the margin is too narrow
    for a recognisable character (targets always win over decoration).
    """

    scale = layout_scale(width, height)
    side_pad = max(4, int(round(8 * scale)))
    size = min(
        free_right_edge - 2 * side_pad,
        int(round(height * 0.42)),
        int(round(230 * scale)),
    )
    bottom = height - max(2, int(round(4 * scale)))
    for blocker in reserved:
        if blocker.x < free_right_edge:
            # Never stand on top of the profile switcher above the margin.
            size = min(size, bottom - (blocker.bottom + side_pad))
    if size < minimum_px:
        return None
    x = max(side_pad, (free_right_edge - size) // 2)
    return UiRect(x, bottom - size, size, size)


@dataclass(frozen=True, slots=True)
class CollectionHomeLayout:
    """Resolved geometry for one Collection Home frame.

    ``portals`` are the drawn portal-art rectangles (tile + slab + shadow),
    ``labels`` the caption pill slots directly below each portal, and
    ``hits`` the full child target (portal plus caption). ``greeter`` is the
    optional cast-character square in the free left margin.
    """

    width: int
    height: int
    columns: int
    rows: int
    portals: tuple[UiRect, ...]
    labels: tuple[UiRect, ...]
    hits: tuple[UiRect, ...]
    label_font_px: int
    greeter: UiRect | None

    @property
    def portal_width(self) -> int:
        return self.portals[0].width if self.portals else 0

    @property
    def grid_bounds(self) -> UiRect:
        if not self.hits:
            return UiRect(0, 0, 0, 0)
        left = min(rect.x for rect in self.hits)
        top = min(rect.y for rect in self.hits)
        right = max(rect.right for rect in self.hits)
        bottom = max(rect.bottom for rect in self.hits)
        return UiRect(left, top, right - left, bottom - top)

    @classmethod
    def compute(
        cls,
        width: int,
        height: int,
        item_count: int,
        columns: int,
        *,
        reserved: Sequence[UiRect] = (),
        minimum_portal_px: int = 48,
    ) -> "CollectionHomeLayout":
        """Lay out ``item_count`` portals in ``columns`` and fit the greeter beside them."""

        if width < 1 or height < 1:
            raise ValueError("viewport dimensions must be positive")
        item_count = max(0, int(item_count))
        columns = max(1, min(int(columns), max(1, item_count)))
        rows = max(1, (item_count + columns - 1) // columns)
        scale = layout_scale(width, height)

        margin = max(6, int(round(12 * scale)))
        gap_x = int(_clamp(round(40 * scale**1.5), 12, 56))
        gap_y = int(_clamp(round(16 * scale), 6, 24))
        label_font = int(_clamp(round(22 * scale), 14, 28))
        label_h = label_font + max(8, int(round(12 * scale)))
        label_gap = max(2, int(round(4 * scale)))
        # Caption pills may be wider than the portal (long words such as
        # "LE MIE CREAZIONI"), but adjacent pills always keep a quarter gap.
        overhang = gap_x * 3 // 4
        aspect = PORTAL_ART_HEIGHT / PORTAL_ART_WIDTH
        # Leave a calm margin on each side for the greeter/scene; on narrow
        # screens it shrinks before the targets do.
        side_reserve = int(round(width * 0.14))
        portal_cap = int(round(168 * scale))
        blockers = [
            UiRect(r.x - margin, r.y - margin, r.width + 2 * margin, r.height + 2 * margin)
            for r in reserved
        ]

        def fit(top: int, span: int) -> int:
            by_width = (span - (columns - 1) * gap_x - overhang) // columns
            row_h = (height - top - margin - (rows - 1) * gap_y) / rows
            by_height = int((row_h - label_gap - label_h) / aspect)
            return max(minimum_portal_px, min(portal_cap, by_width, by_height))

        def place(top: int, portal_w: int) -> tuple[list[UiRect], list[UiRect], list[UiRect]]:
            portal_h = int(round(portal_w * aspect))
            item_h = portal_h + label_gap + label_h
            total_h = rows * item_h + (rows - 1) * gap_y
            origin_y = top + max(0, (height - top - margin - total_h) // 2)
            # Optical centring: a touch above centre leaves room for the meadow.
            origin_y = max(top, origin_y - int(round(6 * scale)))
            label_w = portal_w + overhang
            portals: list[UiRect] = []
            labels: list[UiRect] = []
            hits: list[UiRect] = []
            for index in range(item_count):
                row = index // columns
                column = index % columns
                row_count = min(columns, item_count - row * columns)
                row_w = row_count * portal_w + (row_count - 1) * gap_x
                x = (width - row_w) // 2 + column * (portal_w + gap_x)
                y = origin_y + row * (item_h + gap_y)
                portal = UiRect(x, y, portal_w, portal_h)
                label = UiRect(
                    x - overhang // 2,
                    y + portal_h + label_gap,
                    label_w,
                    label_h,
                )
                portals.append(portal)
                labels.append(label)
                hits.append(UiRect(x, y, portal_w, portal_h + label_gap + label_h))
            return portals, labels, hits

        def clear(candidate: list[UiRect]) -> bool:
            return not any(r.intersects(b) for r in candidate for b in blockers)

        # Strategy 1: full height, calm side margins.
        top = margin
        portal_w = fit(top, width - 2 * side_reserve)
        portals, labels, hits = place(top, portal_w)
        if blockers and not clear(hits + labels):
            options = []
            # Strategy 2: keep full height, narrow the grid to pass between
            # the corner controls (best on short landscape screens).
            left = max([b.right for b in blockers if b.x < width // 2], default=0)
            right = min([b.x for b in blockers if b.x >= width // 2], default=width)
            centred_span = 2 * min(width // 2 - left, right - width // 2)
            if centred_span > 0:
                w2 = min(portal_w, fit(top, centred_span))
                options.append((w2, top))
            # Strategy 3: start below the corner controls.
            below = max(b.bottom for b in blockers)
            options.append((fit(below, width - 2 * side_reserve), below))
            for w_option, top_option in sorted(options, reverse=True):
                candidate = place(top_option, w_option)
                if clear(candidate[2] + candidate[1]):
                    portal_w, top = w_option, top_option
                    portals, labels, hits = candidate
                    break
            else:
                w_option, top_option = options[-1]
                portal_w, top = w_option, top_option
                portals, labels, hits = place(top_option, w_option)

        grid_left = min((r.x for r in labels + hits), default=width // 2)
        greeter = greeter_rect(
            width,
            height,
            free_right_edge=grid_left,
            reserved=reserved,
        )
        return cls(
            width=width,
            height=height,
            columns=columns,
            rows=rows,
            portals=tuple(portals),
            labels=tuple(labels),
            hits=tuple(hits),
            label_font_px=label_font,
            greeter=greeter,
        )

