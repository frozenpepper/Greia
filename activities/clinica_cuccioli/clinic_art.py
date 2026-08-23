from __future__ import annotations

import math

import pygame


def draw_tool_icon(
    surface: pygame.Surface,
    tool_id: str,
    cx: int,
    cy: int,
    size: int,
) -> None:
    """Draw one language-neutral clinic tool icon using cheap primitives."""

    r = size // 2
    if tool_id == "stethoscope":
        pygame.draw.arc(
            surface,
            (37, 99, 235),
            pygame.Rect(cx - r * 3 // 4, cy - r, r * 3 // 2, r * 3 // 2),
            0.8,
            2.34,
            5,
        )
        pygame.draw.line(surface, (37, 99, 235), (cx, cy), (cx, cy + r // 2), 5)
        pygame.draw.circle(surface, (203, 213, 225), (cx, cy + r // 2), r // 3 + 2)
        pygame.draw.circle(surface, (59, 130, 246), (cx, cy + r // 2), r // 5)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 2, cy + r // 2 - 2), 2)
    elif tool_id == "bath":
        pygame.draw.rect(
            surface,
            (14, 165, 233),
            pygame.Rect(cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r * 3 // 4),
            border_radius=10,
        )
        pygame.draw.rect(
            surface,
            (56, 189, 248),
            pygame.Rect(cx - r * 3 // 4 + 4, cy - r // 4 + 3, r * 3 // 2 - 8, r * 3 // 4 - 6),
            border_radius=6,
        )
        pygame.draw.circle(surface, (255, 255, 255), (cx - r // 3, cy - r // 2), r // 3)
        pygame.draw.circle(surface, (224, 242, 254), (cx - r // 3, cy - r // 2), r // 3, 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 4, cy - r * 2 // 3), r // 4)
        pygame.draw.circle(surface, (224, 242, 254), (cx + r // 4, cy - r * 2 // 3), r // 4, 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 2, cy - r // 3), r // 5)
    elif tool_id == "bandaid":
        pygame.draw.rect(
            surface,
            (244, 114, 182),
            pygame.Rect(cx - r, cy - r // 3, size, r * 2 // 3),
            border_radius=8,
        )
        pygame.draw.rect(
            surface,
            (251, 207, 232),
            pygame.Rect(cx - r + 3, cy - r // 3 + 2, size - 6, r * 2 // 3 - 4),
            border_radius=6,
        )
        pygame.draw.rect(
            surface,
            (255, 255, 255),
            pygame.Rect(cx - r // 3, cy - r // 3, r * 2 // 3, r * 2 // 3),
            border_radius=4,
        )
        pygame.draw.rect(surface, (236, 72, 153), pygame.Rect(cx - 3, cy - 8, 6, 16), border_radius=2)
        pygame.draw.rect(surface, (236, 72, 153), pygame.Rect(cx - 8, cy - 3, 16, 6), border_radius=2)
    elif tool_id == "food":
        pygame.draw.ellipse(surface, (234, 179, 8), pygame.Rect(cx - r, cy - r // 4, size, r * 3 // 4))
        pygame.draw.ellipse(surface, (202, 138, 4), pygame.Rect(cx - r * 4 // 5, cy - r // 6, r * 8 // 5, r // 2))
        pygame.draw.circle(surface, (180, 83, 9), (cx - r // 3, cy - r // 8), 6)
        pygame.draw.circle(surface, (180, 83, 9), (cx, cy - r // 6), 7)
        pygame.draw.circle(surface, (180, 83, 9), (cx + r // 3, cy - r // 8), 6)
        pygame.draw.circle(surface, (251, 146, 60), (cx - r // 6, cy + 2), 5)
        pygame.draw.circle(surface, (251, 146, 60), (cx + r // 6, cy + 2), 5)
    else:
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 3, cy - r // 4), r // 2)
        pygame.draw.circle(surface, (239, 68, 68), (cx + r // 3, cy - r // 4), r // 2)
        pygame.draw.polygon(
            surface,
            (239, 68, 68),
            [
                (cx - r * 4 // 5, cy - r // 8),
                (cx + r * 4 // 5, cy - r // 8),
                (cx, cy + r * 4 // 5),
            ],
        )
        pygame.draw.circle(surface, (254, 202, 202), (cx - r // 3, cy - r // 3), 4)
        pygame.draw.circle(surface, (255, 255, 255), (cx + r // 4, cy - r // 3), 3)


def draw_thought_bubble(
    surface: pygame.Surface,
    cx: int,
    cy: int,
    next_needed: str | None,
    now: float,
) -> None:
    dark = (30, 41, 59)
    white = (255, 255, 255)
    for ox, oy, radius in [(-45, 50, 7), (-30, 34, 11), (-14, 18, 15)]:
        pygame.draw.circle(surface, white, (cx + ox, cy + oy), radius)
        pygame.draw.circle(surface, dark, (cx + ox, cy + oy), radius, 2)

    bob = int(math.sin(now * 4.0) * 3.0)
    bubble_y = cy + bob
    for ox, oy, radius in [
        (-24, 0, 26),
        (24, 0, 26),
        (0, -16, 28),
        (0, 12, 24),
        (-14, -14, 22),
        (14, -14, 22),
    ]:
        pygame.draw.circle(surface, white, (cx + ox, bubble_y + oy), radius)
        pygame.draw.circle(surface, dark, (cx + ox, bubble_y + oy), radius, 2)
    for ox, oy, radius in [(-24, 0, 24), (24, 0, 24), (0, -16, 26), (0, 12, 22)]:
        pygame.draw.circle(surface, white, (cx + ox, bubble_y + oy), radius)

    draw_tool_icon(surface, next_needed or "cuddle", cx, bubble_y, 52 if next_needed else 48)


def draw_patient(
    surface: pygame.Surface,
    patient_id: str,
    cx: int,
    cy: int,
    size: int,
    *,
    has_mud: bool,
    has_scratch: bool,
    completed_steps: list[str] | tuple[str, ...],
    is_happy: bool,
) -> None:
    """Draw the current patient and treatment-state decorations."""

    bed_w = size * 7 // 4
    bed_h = size
    pygame.draw.ellipse(surface, (241, 245, 249), pygame.Rect(cx - bed_w // 2, cy - bed_h // 3, bed_w, bed_h))
    pygame.draw.ellipse(surface, (203, 213, 225), pygame.Rect(cx - bed_w // 2, cy - bed_h // 3, bed_w, bed_h), 4)

    body_y = cy + 20
    body_w = size * 5 // 4
    body_h = size * 3 // 4
    head_y = cy - 40
    head_r = size * 2 // 5

    if patient_id == "dog":
        body_col = (217, 119, 6)
        ear_col = (180, 83, 9)
        muzzle_col = (254, 243, 199)
        pygame.draw.arc(surface, body_col, pygame.Rect(cx + body_w // 3, body_y - 30, 60, 50), 0.5, 3.0, 10)
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx - body_w // 2, body_y - body_h // 2, body_w, body_h))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - body_w // 3, body_y - body_h // 3, body_w * 2 // 3, body_h * 2 // 3))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - 50, body_y + 30, 36, 24))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx + 14, body_y + 30, 36, 24))
        pygame.draw.circle(surface, body_col, (cx, head_y), head_r)
        pygame.draw.ellipse(surface, ear_col, pygame.Rect(cx - head_r - 20, head_y - 20, 32, 70))
        pygame.draw.ellipse(surface, ear_col, pygame.Rect(cx + head_r - 12, head_y - 20, 32, 70))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - 30, head_y, 60, 44))
        pygame.draw.circle(surface, (20, 20, 30), (cx, head_y + 10), 9)
        _draw_round_eyes(surface, cx, head_y, radius=10, highlight=4)
        pygame.draw.circle(surface, (251, 146, 60), (cx - 36, head_y + 12), 8)
        pygame.draw.circle(surface, (251, 146, 60), (cx + 36, head_y + 12), 8)
        if is_happy:
            pygame.draw.circle(surface, (244, 114, 182), (cx, head_y + 24), 8)
    elif patient_id == "cat":
        body_col = (251, 146, 60)
        ear_col = (244, 114, 182)
        muzzle_col = (255, 255, 255)
        pygame.draw.arc(surface, body_col, pygame.Rect(cx + body_w // 3, body_y - 30, 50, 60), 0.2, 2.5, 9)
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx - body_w // 2, body_y - body_h // 2, body_w, body_h))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - body_w // 3, body_y - body_h // 3, body_w * 2 // 3, body_h * 2 // 3))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - 50, body_y + 30, 34, 22))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx + 16, body_y + 30, 34, 22))
        pygame.draw.circle(surface, body_col, (cx, head_y), head_r)
        pygame.draw.polygon(surface, body_col, [(cx - head_r + 4, head_y - 10), (cx - head_r - 10, head_y - 65), (cx - 10, head_y - 35)])
        pygame.draw.polygon(surface, ear_col, [(cx - head_r + 8, head_y - 12), (cx - head_r - 6, head_y - 55), (cx - 16, head_y - 32)])
        pygame.draw.polygon(surface, body_col, [(cx + head_r - 4, head_y - 10), (cx + head_r + 10, head_y - 65), (cx + 10, head_y - 35)])
        pygame.draw.polygon(surface, ear_col, [(cx + head_r - 8, head_y - 12), (cx + head_r + 6, head_y - 55), (cx + 16, head_y - 32)])
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - 26, head_y + 2, 52, 36))
        pygame.draw.polygon(surface, ear_col, [(cx - 7, head_y + 10), (cx + 7, head_y + 10), (cx, head_y + 16)])
        for offset_y, end_y in [(14, 10), (18, 22)]:
            pygame.draw.line(surface, (20, 20, 30), (cx - 30, head_y + offset_y), (cx - 60, head_y + end_y), 2)
            pygame.draw.line(surface, (20, 20, 30), (cx + 30, head_y + offset_y), (cx + 60, head_y + end_y), 2)
        for eye_x in (cx - 24, cx + 24):
            pygame.draw.circle(surface, (16, 185, 129), (eye_x, head_y - 8), 10)
            pygame.draw.circle(surface, (20, 20, 30), (eye_x, head_y - 8), 6)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 27, head_y - 12), 4)
        pygame.draw.circle(surface, (255, 255, 255), (cx + 21, head_y - 12), 4)
    elif patient_id == "bunny":
        body_col = (248, 250, 252)
        ear_col = (244, 114, 182)
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx - body_w // 2, body_y - body_h // 2, body_w, body_h))
        pygame.draw.circle(surface, (255, 255, 255), (cx + body_w // 2, body_y), 18)
        pygame.draw.ellipse(surface, (255, 255, 255), pygame.Rect(cx - 50, body_y + 30, 34, 22))
        pygame.draw.ellipse(surface, (255, 255, 255), pygame.Rect(cx + 16, body_y + 30, 34, 22))
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx - 38, head_y - 95, 28, 75))
        pygame.draw.ellipse(surface, ear_col, pygame.Rect(cx - 32, head_y - 88, 16, 60))
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx + 10, head_y - 95, 28, 75))
        pygame.draw.ellipse(surface, ear_col, pygame.Rect(cx + 16, head_y - 88, 16, 60))
        pygame.draw.circle(surface, body_col, (cx, head_y), head_r)
        _draw_round_eyes(surface, cx, head_y, radius=9, highlight=4, eye_y=-6)
        pygame.draw.circle(surface, ear_col, (cx, head_y + 8), 6)
        pygame.draw.circle(surface, (251, 113, 133), (cx - 32, head_y + 8), 8)
        pygame.draw.circle(surface, (251, 113, 133), (cx + 32, head_y + 8), 8)
    else:
        body_col = (146, 64, 14)
        ear_col = (120, 53, 15)
        muzzle_col = (254, 215, 170)
        pygame.draw.ellipse(surface, body_col, pygame.Rect(cx - body_w // 2, body_y - body_h // 2, body_w, body_h))
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - body_w // 3, body_y - body_h // 3, body_w * 2 // 3, body_h * 2 // 3))
        for ear_x in (cx - 36, cx + 36):
            pygame.draw.circle(surface, ear_col, (ear_x, head_y - 36), 20)
            pygame.draw.circle(surface, muzzle_col, (ear_x, head_y - 36), 12)
        pygame.draw.circle(surface, body_col, (cx, head_y), head_r)
        pygame.draw.ellipse(surface, muzzle_col, pygame.Rect(cx - 30, head_y, 60, 44))
        pygame.draw.circle(surface, (20, 20, 30), (cx, head_y + 10), 8)
        _draw_round_eyes(surface, cx, head_y, radius=9, highlight=3)

    steps = set(completed_steps)
    if has_mud and "bath" not in steps:
        for mud_x, mud_y, radius in [
            (cx - 40, body_y - 10, 16),
            (cx + 35, body_y + 10, 20),
            (cx - 10, body_y + 20, 14),
            (cx + 45, head_y + 15, 12),
        ]:
            pygame.draw.circle(surface, (120, 53, 15), (mud_x, mud_y), radius)
            pygame.draw.circle(surface, (90, 40, 10), (mud_x - 2, mud_y - 2), radius * 2 // 3)
    elif "bath" in steps:
        for bubble_x, bubble_y, radius in [
            (cx - 30, head_y - 15, 12),
            (cx + 30, body_y - 15, 14),
            (cx - 15, body_y - 25, 10),
        ]:
            pygame.draw.circle(surface, (255, 255, 255), (bubble_x, bubble_y), radius)
            pygame.draw.circle(surface, (186, 230, 253), (bubble_x, bubble_y), radius, 2)

    if has_scratch:
        if "bandaid" in steps:
            draw_tool_icon(surface, "bandaid", cx + 38, body_y - 12, 38)
        else:
            pygame.draw.rect(surface, (254, 202, 202), pygame.Rect(cx + 18, body_y - 25, 42, 26), border_radius=6)
            pygame.draw.rect(surface, (244, 114, 182), pygame.Rect(cx + 18, body_y - 25, 42, 26), width=2, border_radius=6)
            pygame.draw.line(surface, (239, 68, 68), (cx + 25, body_y - 20), (cx + 53, body_y - 8), 4)
            pygame.draw.line(surface, (239, 68, 68), (cx + 28, body_y - 8), (cx + 50, body_y - 20), 4)

    if "food" in steps:
        draw_tool_icon(surface, "food", cx - 75, body_y + 30, 42)
    if "stethoscope" in steps:
        draw_tool_icon(surface, "stethoscope", cx - 35, body_y, 40)


def _draw_round_eyes(
    surface: pygame.Surface,
    cx: int,
    head_y: int,
    *,
    radius: int,
    highlight: int,
    eye_y: int = -8,
) -> None:
    pygame.draw.circle(surface, (20, 20, 30), (cx - 24, head_y + eye_y), radius)
    pygame.draw.circle(surface, (20, 20, 30), (cx + 24, head_y + eye_y), radius)
    pygame.draw.circle(surface, (255, 255, 255), (cx - 27, head_y + eye_y - 4), highlight)
    pygame.draw.circle(surface, (255, 255, 255), (cx + 21, head_y + eye_y - 4), highlight)
