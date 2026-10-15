"""Theatre geometry in 1024x600 logical pixels, derived from ``ControlLayout``.

The stage itself is fixed reference art; only the control bands adapt:
``ControlLayout`` maps the platform Home/Back region into logical space and
raises control heights to the physical touch floor, so the same layout holds
at 1024x600, 800x480 and 480x320 without per-device coordinates and nothing
is ever placed inside the protected chrome.

* top bar (right of the protected corner): shows / scene / clear on the
  left, the voice choice and record on the right;
* two sound-sticker columns over the curtains (3 + 3);
* the puppet tray at the bottom is the stage's playboard: puppets come up
  from it on their rods and go back into it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from greia_platform.activity_controls import Align, ControlLayout

if __package__:
    from .teatrino_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, TRAY_PAGE_SIZE
    from .teatrino_model import StageBounds
else:
    from teatrino_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, TRAY_PAGE_SIZE
    from teatrino_model import StageBounds

# Footlights row of ``bg.stage.boards`` ends at y 572: the floor is lifted so
# that row sits right on the tray's top edge.
FOOTLIGHTS_BOTTOM = 572
CURTAIN_INNER_LEFT = 200
CURTAIN_INNER_RIGHT = REFERENCE_WIDTH - 200


@dataclass(frozen=True, slots=True)
class TheatreLayout:
    """Every rect of the stage screen (logical px)."""

    control: int
    shows: pygame.Rect
    scene: pygame.Rect
    clear: pygame.Rect
    mic: pygame.Rect
    rec: pygame.Rect
    fx: tuple[pygame.Rect, ...]
    tray: pygame.Rect
    tray_prev: pygame.Rect
    tray_next: pygame.Rect
    cards: tuple[pygame.Rect, ...]
    floor_dy: int
    bounds: StageBounds
    protected: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "TheatreLayout":
        margin, gap = layout.margin, layout.gap
        control = layout.control_height(60, maximum=88)
        bar = layout.top_bar(control)
        shows, scene, clear = layout.row(bar, [control] * 3, align=Align.START)
        rec_width = int(control * 1.45)
        mic, rec = layout.row(bar, [control, rec_width], align=Align.END)

        sticker = layout.control_height(58, maximum=86)
        top = max(bar.bottom, layout.protected.bottom) + gap + 6
        fx: list[pygame.Rect] = []
        for column_x in (margin, REFERENCE_WIDTH - margin - sticker):
            for index in range(3):
                fx.append(pygame.Rect(column_x, top + index * (sticker + gap + 4), sticker, sticker))

        card_h = layout.control_height(96, maximum=124)
        cards_y = REFERENCE_HEIGHT - margin - card_h
        tray = pygame.Rect(0, cards_y - 12, REFERENCE_WIDTH, REFERENCE_HEIGHT - cards_y + 12)
        arrow_w = max(int(card_h * 0.62), layout.control_height(52))
        tray_prev = pygame.Rect(margin, cards_y, arrow_w, card_h)
        tray_next = pygame.Rect(REFERENCE_WIDTH - margin - arrow_w, cards_y, arrow_w, card_h)
        area_left = tray_prev.right + gap + 4
        area_right = tray_next.left - gap - 4
        card_w = min(int(card_h * 1.32), (area_right - area_left - gap * (TRAY_PAGE_SIZE - 1)) // TRAY_PAGE_SIZE)
        total = card_w * TRAY_PAGE_SIZE + gap * (TRAY_PAGE_SIZE - 1)
        start = area_left + (area_right - area_left - total) // 2
        cards = tuple(
            pygame.Rect(start + index * (card_w + gap), cards_y, card_w, card_h) for index in range(TRAY_PAGE_SIZE)
        )

        stage_left = max(CURTAIN_INNER_LEFT, fx[0].right + 64)
        stage_right = min(CURTAIN_INNER_RIGHT, fx[3].left - 64)
        bounds = StageBounds(
            float(stage_left),
            float(bar.bottom + 70),
            float(stage_right),
            float(tray.top - 92),
            float(tray.top - 34),
        )
        return cls(
            control=control,
            shows=shows,
            scene=scene,
            clear=clear,
            mic=mic,
            rec=rec,
            fx=tuple(fx),
            tray=tray,
            tray_prev=tray_prev,
            tray_next=tray_next,
            cards=cards,
            floor_dy=tray.top - FOOTLIGHTS_BOTTOM,
            bounds=bounds,
            protected=pygame.Rect(layout.protected),
        )

    # -- sheets ----------------------------------------------------------------

    def sheet_panel(self, width: int, height: int) -> pygame.Rect:
        """A centred panel kept below the protected corner."""

        top_limit = self.protected.bottom + 10
        width = min(width, REFERENCE_WIDTH - 32)
        height = min(height, REFERENCE_HEIGHT - top_limit - 12)
        panel = pygame.Rect(0, 0, width, height)
        panel.center = (REFERENCE_WIDTH // 2, (top_limit + REFERENCE_HEIGHT - 12) // 2)
        if panel.top < top_limit:
            panel.top = top_limit
        return panel


@dataclass(frozen=True, slots=True)
class GridLayout:
    """A paged grid of cards inside a sheet panel (library / scenes)."""

    panel: pygame.Rect
    header: pygame.Rect
    close: pygame.Rect
    cards: tuple[pygame.Rect, ...]
    previous: pygame.Rect
    following: pygame.Rect
    action: pygame.Rect

    @classmethod
    def build(cls, theatre: TheatreLayout, *, columns: int, rows: int, aspect: float, width: int = 940) -> "GridLayout":
        control = theatre.control
        panel = theatre.sheet_panel(width, 600)
        pad = 18
        header = pygame.Rect(panel.x + pad, panel.y + pad, panel.width - 2 * pad, control)
        close = pygame.Rect(header.right - control, header.y, control, control)
        footer_y = panel.bottom - pad - control
        previous = pygame.Rect(panel.x + pad, footer_y, int(control * 1.4), control)
        following = pygame.Rect(panel.right - pad - int(control * 1.4), footer_y, int(control * 1.4), control)
        action = pygame.Rect(0, footer_y, control, control)
        action.centerx = panel.centerx
        gap = 16
        area = pygame.Rect(panel.x + pad, header.bottom + gap, panel.width - 2 * pad, footer_y - gap - header.bottom - gap)
        card_w = (area.width - gap * (columns - 1)) // columns
        card_h = (area.height - gap * (rows - 1)) // rows
        # Keep the picture aspect: shrink the larger side.
        if card_w / max(1, card_h) > aspect:
            card_w = int(card_h * aspect)
        else:
            card_h = int(card_w / aspect)
        total_w = card_w * columns + gap * (columns - 1)
        total_h = card_h * rows + gap * (rows - 1)
        left = area.x + (area.width - total_w) // 2
        top = area.y + (area.height - total_h) // 2
        cards = tuple(
            pygame.Rect(left + col * (card_w + gap), top + row * (card_h + gap), card_w, card_h)
            for row in range(rows)
            for col in range(columns)
        )
        return cls(panel, header, close, cards, previous, following, action)


@dataclass(frozen=True, slots=True)
class DialogLayout:
    """A centred dialog: a picture on top and two (or three) big buttons."""

    panel: pygame.Rect
    picture: pygame.Rect
    buttons: tuple[pygame.Rect, ...]
    host_midbottom: tuple[int, int]

    @classmethod
    def build(
        cls,
        theatre: TheatreLayout,
        *,
        buttons: int,
        width: int = 700,
        height: int = 470,
        picture: bool = True,
    ) -> "DialogLayout":
        control = max(theatre.control, 72)
        if not picture:
            control = max(control, 110)
        panel = theatre.sheet_panel(width, height)
        pad = 22
        button_w = int(control * (1.5 if picture else 1.2))
        gap = 22
        total = button_w * buttons + gap * (buttons - 1)
        y = panel.bottom - pad - control if picture else panel.centery - control // 2
        x = panel.centerx - total // 2
        rects = tuple(pygame.Rect(x + index * (button_w + gap), y, button_w, control) for index in range(buttons))
        if not picture:
            return cls(panel, pygame.Rect(panel.centerx, panel.y, 0, 0), rects, (panel.x + 60, panel.bottom))
        picture_h = y - pad - (panel.y + pad)
        picture_w = min(panel.width - 2 * pad - 150, int(picture_h * REFERENCE_WIDTH / REFERENCE_HEIGHT))
        picture_h = int(picture_w * REFERENCE_HEIGHT / REFERENCE_WIDTH)
        picture = pygame.Rect(0, panel.y + pad, picture_w, picture_h)
        picture.centerx = panel.centerx + 60
        host = (panel.x + 92, picture.bottom + 6)
        return cls(panel, picture, rects, host)


__all__ = ["DialogLayout", "FOOTLIGHTS_BOTTOM", "GridLayout", "TheatreLayout"]
