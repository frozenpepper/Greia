"""La Memoria delle Meraviglie — stateless card illustration drawing.

Each supported ``item_id`` is a small inline drawing routine. These
helpers do not own state; the renderer decides when to call them and
which surface to blit into.
"""

from __future__ import annotations

import math

import pygame


def draw_card_illustration(
    surface: pygame.Surface,
    item_id: str,
    cx: int,
    cy: int,
    size: int,
) -> None:
    r = size // 2
    dark = (30, 41, 59)
    white = (255, 255, 255)

    if item_id == "lion":
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r)
        pygame.draw.circle(surface, (251, 191, 36), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, (217, 119, 6), (cx - r * 3 // 5, cy - r * 3 // 5), r // 4)
        pygame.draw.circle(surface, (217, 119, 6), (cx + r * 3 // 5, cy - r * 3 // 5), r // 4)
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.polygon(surface, (180, 83, 9), [(cx - r // 6, cy + r // 8), (cx + r // 6, cy + r // 8), (cx, cy + r // 4)])
        pygame.draw.circle(surface, dark, (cx, cy), r, 2)

    elif item_id == "panda":
        pygame.draw.circle(surface, dark, (cx - r * 3 // 5, cy - r * 3 // 5), r // 3)
        pygame.draw.circle(surface, dark, (cx + r * 3 // 5, cy - r * 3 // 5), r // 3)
        pygame.draw.circle(surface, white, (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r // 2, cy - r // 3, r // 3, r // 2))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx + r // 6, cy - r // 3, r // 3, r // 2))
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 6), max(2, r // 10))
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 6), max(2, r // 10))
        pygame.draw.circle(surface, dark, (cx, cy + r // 5), max(2, r // 8))

    elif item_id == "cat":
        pygame.draw.polygon(surface, (249, 115, 22), [(cx - r * 3 // 4, cy - r // 4), (cx - r * 3 // 4, cy - r * 4 // 5), (cx - r // 4, cy - r // 2)])
        pygame.draw.polygon(surface, (249, 115, 22), [(cx + r * 3 // 4, cy - r // 4), (cx + r * 3 // 4, cy - r * 4 // 5), (cx + r // 4, cy - r // 2)])
        pygame.draw.circle(surface, (253, 186, 116), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.circle(surface, (16, 185, 129), (cx - r // 4, cy - r // 8), max(2, r // 7))
        pygame.draw.circle(surface, (16, 185, 129), (cx + r // 4, cy - r // 8), max(2, r // 7))
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(1, r // 12))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(1, r // 12))
        pygame.draw.polygon(surface, (244, 114, 182), [(cx - r // 8, cy + r // 8), (cx + r // 8, cy + r // 8), (cx, cy + r // 4)])

    elif item_id == "dog":
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx - r * 9 // 10, cy - r // 2, r // 2, r * 9 // 10))
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx + r * 2 // 5, cy - r // 2, r // 2, r * 9 // 10))
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.ellipse(surface, (254, 243, 199), pygame.Rect(cx - r // 3, cy, r * 2 // 3, r // 2))
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), max(2, r // 7))

    elif item_id == "bunny":
        pygame.draw.ellipse(surface, white, pygame.Rect(cx - r // 2, cy - r * 9 // 10, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx - r * 2 // 5, cy - r * 4 // 5, r // 6, r * 3 // 5))
        pygame.draw.ellipse(surface, white, pygame.Rect(cx + r // 6, cy - r * 9 // 10, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx + r // 4, cy - r * 4 // 5, r // 6, r * 3 // 5))
        pygame.draw.circle(surface, white, (cx, cy + r // 6), r * 3 // 5)
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), r * 3 // 5, 2)
        pygame.draw.circle(surface, dark, (cx - r // 5, cy + r // 12), max(2, r // 9))
        pygame.draw.circle(surface, dark, (cx + r // 5, cy + r // 12), max(2, r // 9))
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy + r // 4), max(2, r // 8))

    elif item_id == "frog":
        pygame.draw.circle(surface, (74, 222, 128), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (74, 222, 128), (cx + r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, white, (cx - r // 2, cy - r // 3), r // 5)
        pygame.draw.circle(surface, white, (cx + r // 2, cy - r // 3), r // 5)
        pygame.draw.circle(surface, dark, (cx - r // 2, cy - r // 3), r // 9)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy - r // 3), r // 9)
        pygame.draw.ellipse(surface, (74, 222, 128), pygame.Rect(cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r * 4 // 5))
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), r * 3 // 4, 2)
        pygame.draw.arc(surface, dark, pygame.Rect(cx - r // 3, cy, r * 2 // 3, r // 3), 3.4, 6.0, 3)

    elif item_id == "cupcake":
        pygame.draw.polygon(surface, (251, 146, 60), [(cx - r // 2, cy), (cx + r // 2, cy), (cx + r // 3, cy + r * 3 // 4), (cx - r // 3, cy + r * 3 // 4)])
        pygame.draw.polygon(surface, dark, [(cx - r // 2, cy), (cx + r // 2, cy), (cx + r // 3, cy + r * 3 // 4), (cx - r // 3, cy + r * 3 // 4)], 2)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy - r // 5), r // 2)
        pygame.draw.circle(surface, (244, 114, 182), (cx - r // 3, cy), r // 3)
        pygame.draw.circle(surface, (244, 114, 182), (cx + r // 3, cy), r // 3)
        pygame.draw.circle(surface, (239, 68, 68), (cx, cy - r // 2), max(3, r // 5))
        pygame.draw.circle(surface, dark, (cx, cy - r // 2), max(3, r // 5), 2)

    elif item_id == "icecream":
        pygame.draw.polygon(surface, (217, 119, 6), [(cx - r // 3, cy), (cx + r // 3, cy), (cx, cy + r * 4 // 5)])
        pygame.draw.polygon(surface, dark, [(cx - r // 3, cy), (cx + r // 3, cy), (cx, cy + r * 4 // 5)], 2)
        pygame.draw.circle(surface, (251, 146, 60), (cx, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy - r // 2), r // 3)
        pygame.draw.circle(surface, dark, (cx, cy - r // 8), r * 2 // 5, 2)
        pygame.draw.circle(surface, dark, (cx, cy - r // 2), r // 3, 2)

    elif item_id == "donut":
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx, cy), r // 3)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        pygame.draw.circle(surface, dark, (cx, cy), r // 3, 2)
        for dx, dy, col in [(-r // 3, -r // 3, (234, 179, 8)), (r // 3, -r // 3, (56, 189, 248)), (0, r // 2, (34, 197, 94))]:
            pygame.draw.circle(surface, col, (cx + dx, cy + dy), max(2, r // 8))

    elif item_id == "strawberry":
        pygame.draw.polygon(surface, (239, 68, 68), [(cx - r * 3 // 5, cy - r // 3), (cx + r * 3 // 5, cy - r // 3), (cx, cy + r * 4 // 5)])
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 4, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (239, 68, 68), (cx + r // 4, cy - r // 3), r // 3)
        pygame.draw.polygon(surface, dark, [(cx - r * 3 // 5, cy - r // 3), (cx + r * 3 // 5, cy - r // 3), (cx, cy + r * 4 // 5)], 2)
        pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(cx - r // 2, cy - r * 3 // 4, r, r // 3))
        for dx, dy in [(-r // 5, 0), (r // 5, 0), (0, r // 3)]:
            pygame.draw.circle(surface, (254, 240, 138), (cx + dx, cy + dy), max(1, r // 10))

    elif item_id == "cookie":
        pygame.draw.circle(surface, (180, 83, 9), (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        for dx, dy in [(-r // 3, -r // 4), (r // 4, -r // 3), (0, 0), (-r // 4, r // 3), (r // 3, r // 4)]:
            pygame.draw.circle(surface, (69, 26, 3), (cx + dx, cy + dy), max(2, r // 7))

    elif item_id == "rocket":
        pygame.draw.polygon(surface, (239, 68, 68), [(cx, cy - r * 4 // 5), (cx + r // 3, cy + r // 3), (cx - r // 3, cy + r // 3)])
        pygame.draw.polygon(surface, (59, 130, 246), [(cx - r // 3, cy), (cx - r * 3 // 4, cy + r // 2), (cx - r // 3, cy + r // 2)])
        pygame.draw.polygon(surface, (59, 130, 246), [(cx + r // 3, cy), (cx + r * 3 // 4, cy + r // 2), (cx + r // 3, cy + r // 2)])
        pygame.draw.circle(surface, (56, 189, 248), (cx, cy - r // 6), r // 4)
        pygame.draw.circle(surface, dark, (cx, cy - r // 6), r // 4, 2)
        pygame.draw.polygon(surface, (245, 158, 11), [(cx - r // 4, cy + r // 3), (cx + r // 4, cy + r // 3), (cx, cy + r * 4 // 5)])

    elif item_id == "car":
        pygame.draw.rect(surface, (220, 38, 38), pygame.Rect(cx - r * 3 // 4, cy - r // 8, r * 3 // 2, r // 2), border_radius=6)
        pygame.draw.ellipse(surface, (56, 189, 248), pygame.Rect(cx - r // 2, cy - r // 2, r, r // 2))
        pygame.draw.circle(surface, dark, (cx - r // 2, cy + r * 3 // 8), r // 4)
        pygame.draw.circle(surface, (148, 163, 184), (cx - r // 2, cy + r * 3 // 8), r // 8)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy + r * 3 // 8), r // 4)
        pygame.draw.circle(surface, (148, 163, 184), (cx + r // 2, cy + r * 3 // 8), r // 8)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r * 3 // 4, cy - r // 8, r * 3 // 2, r // 2), width=2, border_radius=6)

    elif item_id == "train":
        pygame.draw.rect(surface, (59, 130, 246), pygame.Rect(cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r // 2), border_radius=4)
        pygame.draw.rect(surface, (239, 68, 68), pygame.Rect(cx + r // 6, cy - r * 3 // 5, r * 2 // 5, r * 4 // 5), border_radius=4)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r // 2, cy - r // 2, r // 4, r // 3))
        pygame.draw.circle(surface, dark, (cx - r // 2, cy + r // 3), r // 4)
        pygame.draw.circle(surface, dark, (cx, cy + r // 3), r // 4)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy + r // 3), r // 4)

    elif item_id == "boat":
        pygame.draw.polygon(surface, (180, 83, 9), [(cx - r * 3 // 4, cy + r // 8), (cx + r * 3 // 4, cy + r // 8), (cx + r // 2, cy + r // 2), (cx - r // 2, cy + r // 2)])
        pygame.draw.polygon(surface, dark, [(cx - r * 3 // 4, cy + r // 8), (cx + r * 3 // 4, cy + r // 8), (cx + r // 2, cy + r // 2), (cx - r // 2, cy + r // 2)], 2)
        pygame.draw.polygon(surface, white, [(cx, cy - r * 3 // 4), (cx + r // 2, cy), (cx, cy)])
        pygame.draw.polygon(surface, (239, 68, 68), [(cx - r // 2, cy), (cx, cy - r // 2), (cx, cy)])

    elif item_id == "sunflower":
        for i in range(8):
            ang = i * math.pi / 4
            px = cx + int(math.cos(ang) * r * 3 // 5)
            py = cy + int(math.sin(ang) * r * 3 // 5)
            pygame.draw.circle(surface, (234, 179, 8), (px, py), r // 3)
        pygame.draw.circle(surface, (120, 53, 15), (cx, cy), r // 2)
        pygame.draw.circle(surface, dark, (cx, cy), r // 2, 2)

    elif item_id == "mushroom":
        pygame.draw.rect(surface, white, pygame.Rect(cx - r // 4, cy, r // 2, r * 3 // 5), border_radius=6)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r // 4, cy, r // 2, r * 3 // 5), width=2, border_radius=6)
        pygame.draw.ellipse(surface, (239, 68, 68), pygame.Rect(cx - r * 4 // 5, cy - r * 3 // 5, r * 8 // 5, r * 4 // 5))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r * 4 // 5, cy - r * 3 // 5, r * 8 // 5, r * 4 // 5), 2)
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 5), max(2, r // 6))
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 5), max(2, r // 6))
        pygame.draw.circle(surface, white, (cx, cy - r // 3), max(2, r // 5))

    elif item_id == "rainbow":
        colors = [(239, 68, 68), (245, 158, 11), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
        for idx, col in enumerate(colors):
            rad = r - idx * max(2, r // 8)
            if rad > 2:
                pygame.draw.arc(surface, col, pygame.Rect(cx - rad, cy - rad + r // 3, rad * 2, rad * 2), 0.0, math.pi, max(2, r // 8))
        pygame.draw.circle(surface, white, (cx - r * 2 // 3, cy + r // 3), r // 4)
        pygame.draw.circle(surface, white, (cx + r * 2 // 3, cy + r // 3), r // 4)

    elif item_id == "star":
        pts = []
        for i in range(10):
            ang = i * math.pi / 5 - math.pi / 2
            rad = r * 4 // 5 if i % 2 == 0 else r * 2 // 5
            pts.append((cx + int(math.cos(ang) * rad), cy + int(math.sin(ang) * rad)))
        pygame.draw.polygon(surface, (254, 202, 87), pts)
        pygame.draw.polygon(surface, (180, 83, 9), pts, 2)
        pygame.draw.circle(surface, white, (cx - r // 5, cy - r // 5), max(2, r // 8))

    elif item_id == "sun":
        for i in range(8):
            ang = i * math.pi / 4
            p1 = (cx + int(math.cos(ang) * r * 3 // 5), cy + int(math.sin(ang) * r * 3 // 5))
            p2 = (cx + int(math.cos(ang) * r * 9 // 10), cy + int(math.sin(ang) * r * 9 // 10))
            pygame.draw.line(surface, (245, 158, 11), p1, p2, max(2, r // 7))
        pygame.draw.circle(surface, (234, 179, 8), (cx, cy), r // 2)
        pygame.draw.circle(surface, (180, 83, 9), (cx, cy), r // 2, 2)
        pygame.draw.circle(surface, dark, (cx - r // 6, cy - r // 10), max(1, r // 12))
        pygame.draw.circle(surface, dark, (cx + r // 6, cy - r // 10), max(1, r // 12))
        pygame.draw.arc(surface, dark, pygame.Rect(cx - r // 5, cy - r // 10, r * 2 // 5, r // 3), 3.4, 6.0, 2)

    elif item_id == "moon":
        pygame.draw.circle(surface, (253, 224, 71), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 4), r * 3 // 5)
        pygame.draw.circle(surface, (202, 138, 4), (cx, cy), r * 3 // 4, 2)

    elif item_id == "tree":
        pygame.draw.rect(surface, (120, 53, 15), pygame.Rect(cx - r // 6, cy, r // 3, r * 3 // 4))
        pygame.draw.circle(surface, (34, 197, 94), (cx, cy - r // 3), r // 2)
        pygame.draw.circle(surface, (22, 163, 74), (cx - r // 3, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (22, 163, 74), (cx + r // 3, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (20, 83, 45), (cx, cy - r // 4), r * 3 // 5, 2)

    elif item_id == "butterfly":
        pygame.draw.circle(surface, (236, 72, 153), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (236, 72, 153), (cx + r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (168, 85, 247), (cx - r // 3, cy + r // 4), r // 4)
        pygame.draw.circle(surface, (168, 85, 247), (cx + r // 3, cy + r // 4), r // 4)
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r // 8, cy - r // 2, r // 4, r))

    elif item_id == "fish":
        pygame.draw.ellipse(surface, (249, 115, 22), pygame.Rect(cx - r * 3 // 5, cy - r // 3, r * 6 // 5, r * 2 // 3))
        pygame.draw.polygon(surface, (249, 115, 22), [(cx + r // 3, cy), (cx + r * 4 // 5, cy - r // 3), (cx + r * 4 // 5, cy + r // 3)])
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 10), max(2, r // 7))
        pygame.draw.circle(surface, dark, (cx - r // 3, cy - r // 10), max(1, r // 12))

    else:
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx, cy), r // 2)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.circle(surface, (254, 240, 138), (cx, cy), r // 4)


def compute_grid_layout(
    grid_cfg: dict,
    card_count: int,
    *,
    reference_width: int = 1024,
    reference_height: int = 600,
) -> tuple[int, int, list[pygame.Rect]]:
    """Cell size and rect list for the card grid.

    Layout sits inside a generous top/bottom margin so the bottom toolbar
    buttons (new/theme/grid) and the top star pill never overlap the
    play area. Returns (card_w, card_h, [pygame.Rect, ...]).
    """
    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]
    top_y = 80
    bottom_y = reference_height - 65
    avail_w = reference_width - 120
    avail_h = bottom_y - top_y

    gap_x = 12 if cols >= 5 else 16
    gap_y = 10 if rows >= 4 else 14

    card_w = min(170, (avail_w - (cols - 1) * gap_x) // cols)
    card_h = min(210, (avail_h - (rows - 1) * gap_y) // rows)
    grid_w = cols * card_w + (cols - 1) * gap_x
    grid_h = rows * card_h + (rows - 1) * gap_y
    grid_ox = (reference_width - grid_w) // 2
    grid_oy = top_y + (avail_h - grid_h) // 2

    rects: list[pygame.Rect] = []
    for i in range(card_count):
        c = i % cols
        r = i // cols
        rx = grid_ox + c * (card_w + gap_x)
        ry = grid_oy + r * (card_h + gap_y)
        rects.append(pygame.Rect(rx, ry, card_w, card_h))
    return card_w, card_h, rects
