"""Responsive geometry for a child Shell Collection page (Activity browsing).

One authored semantic layout (ADR 0026 / RESPONSIVE_UI_AND_DISPLAY_LAYOUT) in
the same family as :mod:`greia_launcher.home_layout`: a header band (local
Back, the Collection's identity and the other Collections), a page of large
Activity cards, two big page-turn arrows beside the cards and a row of
position dots under them. Every measure derives from the viewport and is
clamped; there are no per-device coordinate tables. The module is
renderer-neutral (``UiRect`` only) so it is unit-testable without Pygame.

Spacing is also a correctness contract: the launcher repairs a hovered card by
restoring ``hit.inflate(*CARD_REPAIR_PAD)`` from the cached backdrop, so the
gaps between cards, header, arrows and dots are kept wider than half that pad
plus the hover lift. Nothing else may be drawn inside a card's repair region.
"""

from __future__ import annotations

from dataclasses import dataclass

from greia_platform.responsive_layout import UiRect

from .home_layout import layout_scale

# Activity card art canvas (assets/visual/ui/v0.2/activity_card*.svg): the same
# 288x304 body/slab/shadow grammar as the Collection portal tiles.
CARD_ART_WIDTH = 288
CARD_ART_HEIGHT = 304
# Cream icon face inside the card art (x48-240, y48-240 of the canvas).
_FACE_X = 48 / CARD_ART_WIDTH
_FACE_Y = 48 / CARD_ART_HEIGHT
_FACE_W = 192 / CARD_ART_WIDTH
_FACE_H = 192 / CARD_ART_HEIGHT
CARD_FACE_RADIUS_FRACTION = 40 / 192
# Round control button art canvas (assets/visual/ui/v0.2/round_button_*.svg).
ROUND_BUTTON_WIDTH = 112
ROUND_BUTTON_HEIGHT = 120
# Card repair region (width, height inflation) used by the launcher's hover
# and launch-tick repair; must cover hover scale/lift and the launch bounce.
CARD_REPAIR_PAD = (28, 34)
# Clear space kept around every card hit rectangle (half the pad + lift).
_CARD_CLEARANCE = 20
_MAX_DOTS = 12


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def card_face_rect(card: UiRect) -> UiRect:
    """Return the cream icon face of a card drawn into ``card`` (art rect)."""

    return UiRect(
        card.x + int(round(card.width * _FACE_X)),
        card.y + int(round(card.height * _FACE_Y)),
        max(1, int(round(card.width * _FACE_W))),
        max(1, int(round(card.height * _FACE_H))),
    )


def card_art_height(width: int) -> int:
    return max(1, int(round(width * CARD_ART_HEIGHT / CARD_ART_WIDTH)))


def round_button_rect(x: int, y: int, size: int) -> UiRect:
    """Return a round-button art rect whose *face* is ``size`` wide at (x, y)."""

    return UiRect(x, y, size, int(round(size * ROUND_BUTTON_HEIGHT / ROUND_BUTTON_WIDTH)))


def collection_grid_shape(width: int, height: int) -> tuple[int, int]:
    """Return ``(columns, rows)`` of Activity cards per Collection page.

    Three big cards per row everywhere; short landscape screens (480x320
    class) show a single row so each card stays finger-sized instead of
    shrinking two rows into thumbnails.
    """

    rows = 1 if height < 400 else 2
    columns = 3 if width >= 420 else 2
    return columns, rows


def page_dot_positions(page_count: int, page_index: int) -> tuple[int, int]:
    """Return ``(dot_count, active_dot)`` for a bounded position indicator."""

    if page_count <= 1:
        return 0, 0
    if page_count <= _MAX_DOTS:
        return page_count, max(0, min(page_index, page_count - 1))
    active = int(round(page_index * (_MAX_DOTS - 1) / max(1, page_count - 1)))
    return _MAX_DOTS, active


@dataclass(frozen=True, slots=True)
class CollectionPageLayout:
    """Resolved geometry for one Collection page frame.

    ``back`` is the local Back control (round button art rect),
    ``identity`` the slot where the current Collection's mini portal and name
    are drawn, ``header_right`` the right limit for the other-Collection
    chips. ``cards`` are drawn card-art rects, ``labels`` the title pill
    slots below them and ``hits`` the full child target (card + title).
    ``previous``/``next`` are the page-turn arrow buttons and ``dots`` the
    band for the page-position dots.
    """

    width: int
    height: int
    columns: int
    rows: int
    header_height: int
    back: UiRect
    identity: UiRect
    header_right: int
    header_bottom: int
    cards: tuple[UiRect, ...]
    labels: tuple[UiRect, ...]
    hits: tuple[UiRect, ...]
    previous: UiRect
    next: UiRect
    dots: UiRect
    dot_radius: int
    label_font_px: int
    label_gap: int

    @property
    def capacity(self) -> int:
        return self.columns * self.rows

    @property
    def card_width(self) -> int:
        return self.cards[0].width if self.cards else 0

    @property
    def grid_bounds(self) -> UiRect:
        if not self.hits:
            return UiRect(0, 0, 0, 0)
        left = min(r.x for r in self.hits)
        top = min(r.y for r in self.hits)
        right = max(r.right for r in self.hits)
        bottom = max(r.bottom for r in self.hits)
        return UiRect(left, top, right - left, bottom - top)

    @property
    def header_band(self) -> UiRect:
        """Region the header owns (Back to the last chip), for repairs."""

        left = self.back.x - 6
        return UiRect(left, 0, max(0, self.header_right + 6 - left), self.header_bottom + 2)

    @classmethod
    def compute(
        cls,
        width: int,
        height: int,
        *,
        profile_badge: UiRect | None = None,
        right_reserve: int = 0,
        minimum_target_px: int = 44,
    ) -> "CollectionPageLayout":
        """Lay out one page of cards, header, arrows and dots for a viewport."""

        if width < 1 or height < 1:
            raise ValueError("viewport dimensions must be positive")
        columns, rows = collection_grid_shape(width, height)
        scale = layout_scale(width, height)
        margin = max(8, int(round(12 * scale)))

        # Header: Back + identity on the same line as the profile badge.
        header_h = max(minimum_target_px, int(_clamp(round(58 * scale), 44, 74)))
        top = max(8, int(round(10 * scale)))
        left = (profile_badge.right + max(8, int(round(12 * scale)))) if profile_badge else margin
        back = round_button_rect(left, top, header_h)
        header_bottom = back.bottom
        identity = UiRect(back.right + max(8, int(round(12 * scale))), top, 0, header_h)
        header_right = max(identity.x, width - max(margin, right_reserve))
        identity = UiRect(identity.x, top, max(0, header_right - identity.x), header_h)

        # Page-turn arrows own the side gutters.
        arrow = max(minimum_target_px, int(_clamp(round(68 * scale), 48, 92)))
        arrow_rect_h = int(round(arrow * ROUND_BUTTON_HEIGHT / ROUND_BUTTON_WIDTH))
        side = margin + arrow + _CARD_CLEARANCE

        dot_r = int(_clamp(round(7 * scale), 6, 10))
        dots_h = 2 * dot_r + 8
        label_font = int(_clamp(round(17 * scale), 13, 23))
        # Two caption lines at the Shell font's ~1.4 line height plus padding.
        label_h = 2 * int(round(label_font * 1.42)) + 6
        label_gap = max(2, int(round(3 * scale)))
        # Gaps exceed half the repair pad plus the hover lift (see module doc).
        gap_x = int(_clamp(round(34 * scale), 20, 50))
        gap_y = int(_clamp(round(22 * scale), 20, 40))
        # Title pills may be a little wider than their card on roomy screens.
        overhang = max(0, min(gap_x // 3, gap_x - 20))
        aspect = CARD_ART_HEIGHT / CARD_ART_WIDTH
        card_cap = int(round(236 * scale))

        def fit(content_top: int) -> int:
            avail_w = width - 2 * side
            avail_h = height - content_top - margin - dots_h - _CARD_CLEARANCE
            by_width = (avail_w - (columns - 1) * gap_x) // columns
            row_h = (avail_h - (rows - 1) * gap_y) / rows
            by_height = int((row_h - label_gap - label_h) / aspect)
            return max(40, min(card_cap, by_width, by_height))

        def place(content_top: int, card_w: int):
            card_h = card_art_height(card_w)
            item_h = card_h + label_gap + label_h
            total_w = columns * card_w + (columns - 1) * gap_x
            total_h = rows * item_h + (rows - 1) * gap_y
            avail_h = height - content_top - margin - dots_h - _CARD_CLEARANCE
            origin_x = (width - total_w) // 2
            origin_y = content_top + max(0, (avail_h - total_h) // 2)
            cards, labels, hits = [], [], []
            for index in range(columns * rows):
                row, column = divmod(index, columns)
                x = origin_x + column * (card_w + gap_x)
                y = origin_y + row * (item_h + gap_y)
                cards.append(UiRect(x, y, card_w, card_h))
                labels.append(
                    UiRect(x - overhang // 2, y + card_h + label_gap, card_w + overhang, label_h)
                )
                hits.append(UiRect(x, y, card_w, item_h))
            return cards, labels, hits

        content_top = header_bottom + _CARD_CLEARANCE
        card_w = fit(content_top)
        cards, labels, hits = place(content_top, card_w)
        if profile_badge is not None:
            guard = UiRect(
                profile_badge.x - _CARD_CLEARANCE,
                profile_badge.y,
                profile_badge.width + 2 * _CARD_CLEARANCE,
                profile_badge.height + _CARD_CLEARANCE,
            )
            if any(hit.intersects(guard) for hit in hits):
                # Narrow screens: start the cards below the profile badge.
                content_top = profile_badge.bottom + _CARD_CLEARANCE
                card_w = fit(content_top)
                cards, labels, hits = place(content_top, card_w)

        grid_top = min(r.y for r in hits)
        grid_bottom = max(r.bottom for r in hits)
        # Arrows sit beside the card faces, centred on the card rows.
        arrow_cy = (grid_top + (grid_bottom - label_h)) // 2
        previous = UiRect(margin, arrow_cy - arrow_rect_h // 2, arrow, arrow_rect_h)
        next_rect = UiRect(width - margin - arrow, arrow_cy - arrow_rect_h // 2, arrow, arrow_rect_h)
        dots_top = grid_bottom + _CARD_CLEARANCE
        dots = UiRect(margin + arrow, dots_top, max(0, width - 2 * (margin + arrow)), dots_h)
        return cls(
            width=width,
            height=height,
            columns=columns,
            rows=rows,
            header_height=header_h,
            back=back,
            identity=identity,
            header_right=header_right,
            header_bottom=header_bottom,
            cards=tuple(cards),
            labels=tuple(labels),
            hits=tuple(hits),
            previous=previous,
            next=next_rect,
            dots=dots,
            dot_radius=dot_r,
            label_font_px=label_font,
            label_gap=label_gap,
        )
