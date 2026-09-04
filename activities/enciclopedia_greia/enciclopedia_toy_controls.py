"""Page-toy action controls for Encyclopedia.

Owns the page-specific big action buttons (erupt, gear turn, heart, breathe,
animal, machine, history, entry). These are distinct from standard navigation
chrome (arrows/discover) which lives in enciclopedia_controls.

All helpers use direct primitives and quantized pulse so they do not allocate
a new SRCALPHA surface every frame. Halo is a stroked rect/circle, not a
cached surface, because the button itself is already a large rect.
"""

from __future__ import annotations

import math

import pygame


def _bucket(time: float) -> int:
    return int((math.sin(time * 2.0) * 0.5 + 0.5) * 3)  # 0..3


VOLCANO_ACTION_SIZE = 76
VOLCANO_ACTION_HIT = 86
GEAR_TURN_SIZE = 76
GEAR_TURN_HIT = 86
HEART_ACTION_SIZE = 76
HEART_ACTION_HIT = 86
BREATHE_ACTION_SIZE = 76
BREATHE_ACTION_HIT = 86
ANIMAL_ACTION_SIZE = 76
ANIMAL_ACTION_HIT = 86
MACHINE_ACTION_SIZE = 76
MACHINE_ACTION_HIT = 86
HISTORY_ACTION_SIZE = 76
HISTORY_ACTION_HIT = 86
ENTRY_ACTION_SIZE = 76
ENTRY_ACTION_HIT = 86


def draw_erupt_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
    erupting: bool = False,
) -> pygame.Rect:
    """Big volcano eruption trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, VOLCANO_ACTION_HIT, VOLCANO_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time) if enabled and not erupting else 0
    size = VOLCANO_ACTION_SIZE + (bucket if enabled and not erupting else 0)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if enabled and not erupting:
        pygame.draw.rect(
            surface,
            (255, 120, 72, 36 + bucket * 9),
            rect.inflate(18, 18),
            width=5,
            border_radius=24,
        )
    # Shadow as direct ellipse
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 242, 200) if not erupting else (255, 210, 140)
    if not enabled:
        fill = (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    mountain_color = (138, 105, 82) if not erupting else (110, 88, 70)
    pts = [(cx - 22, cy + 14), (cx, cy - 16), (cx + 22, cy + 14)]
    pygame.draw.polygon(surface, mountain_color, pts)
    pygame.draw.polygon(surface, edge, pts, 3)
    pygame.draw.ellipse(surface, (78, 68, 61), (cx - 12, cy - 18, 24, 10))
    pygame.draw.ellipse(surface, edge, (cx - 12, cy - 18, 24, 10), 2)
    if erupting:
        pygame.draw.polygon(surface, (239, 89, 39), [(cx - 7, cy - 14), (cx, cy - 30), (cx + 7, cy - 14)])
        pygame.draw.circle(surface, (255, 208, 70), (cx, cy - 26), 4)
        for ax, ay in ((cx - 16, cy - 22), (cx + 16, cy - 18)):
            pygame.draw.circle(surface, (86, 82, 79), (ax, ay), 5)
    else:
        glow_r = 3 + bucket // 2
        pygame.draw.ellipse(surface, (246, 135, 55), (cx - glow_r, cy - 14, glow_r * 2, glow_r), 0)
        sx = cx + int(math.sin(time * 1.2) * 2)
        pygame.draw.circle(surface, (210, 210, 205), (sx, cy - 22), 3)
        pygame.draw.circle(surface, (235, 235, 230), (sx + 2, cy - 26), 2)
    if not enabled:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 255, 88), s.get_rect(), border_radius=22)
        surface.blit(s, rect.topleft)
    return hit


def draw_turn_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    enabled: bool = True,
    spinning: bool = True,
) -> pygame.Rect:
    """Big gear-turn trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, GEAR_TURN_HIT, GEAR_TURN_HIT)
    hit.center = center
    bucket = _bucket(time) if enabled and spinning else 0
    size = GEAR_TURN_SIZE + (bucket if enabled and spinning else 0)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if enabled and spinning:
        pygame.draw.rect(
            surface,
            (120, 180, 210, 32 + bucket * 8),
            rect.inflate(18, 18),
            width=5,
            border_radius=24,
        )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 242, 200) if spinning else (235, 236, 242)
    if not enabled:
        fill = (232, 230, 222)
    edge = (104, 78, 57) if enabled else (148, 146, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    gear_center = (cx, cy - 2)
    pygame.draw.circle(surface, (83, 145, 181), gear_center, 22)
    pygame.draw.circle(surface, edge, gear_center, 22, 3)
    pygame.draw.circle(surface, (255, 248, 232), gear_center, 8)
    for ang in range(0, 360, 45):
        rad = math.radians(ang + time * 48 if spinning else ang)
        x1 = gear_center[0] + int(math.cos(rad) * 22)
        y1 = gear_center[1] + int(math.sin(rad) * 22)
        x2 = gear_center[0] + int(math.cos(rad) * 28)
        y2 = gear_center[1] + int(math.sin(rad) * 28)
        pygame.draw.line(surface, edge, (x1, y1), (x2, y2), 4)
    pygame.draw.circle(surface, (61, 44, 31), gear_center, 6)
    if spinning:
        ax = gear_center[0] + 14
        ay = gear_center[1] + 10
        pygame.draw.polygon(surface, edge, [(ax, ay), (ax - 6, ay - 4), (ax - 6, ay + 4)])
    if not enabled:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 255, 88), s.get_rect(), border_radius=22)
        surface.blit(s, rect.topleft)
    return hit


def draw_heart_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    beating: bool = False,
) -> pygame.Rect:
    """Big heart beat trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, HEART_ACTION_HIT, HEART_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time * 1.3) if beating else _bucket(time * 0.9)
    size = HEART_ACTION_SIZE + (bucket if beating else 0)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if beating:
        pygame.draw.rect(
            surface,
            (240, 120, 130, 38 + bucket * 9),
            rect.inflate(18, 18),
            width=5,
            border_radius=24,
        )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 210, 210) if beating else (255, 242, 235)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    scale = 1.0 + bucket * 0.03 if beating else 1.0
    hs = int(18 * scale)
    pygame.draw.circle(surface, (197, 63, 78), (cx - hs // 2, cy - 2), hs // 2)
    pygame.draw.circle(surface, (197, 63, 78), (cx + hs // 2, cy - 2), hs // 2)
    pygame.draw.polygon(
        surface,
        (197, 63, 78),
        [(cx - hs, cy + 2), (cx + hs, cy + 2), (cx, cy + hs + 4)],
    )
    if beating and bucket == 3:
        pygame.draw.circle(surface, (255, 250, 215), (cx + 12, cy - 10), 3)
    return hit


def draw_breathe_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    time: float = 0.0,
    inhaling: bool = False,
    exercise: bool = False,
) -> pygame.Rect:
    """Big breathe trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, BREATHE_ACTION_HIT, BREATHE_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time * (1.2 if exercise else 0.8))
    size = BREATHE_ACTION_SIZE + bucket
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if inhaling or exercise:
        pygame.draw.rect(
            surface,
            (150, 180, 220, 36 + bucket * 7),
            rect.inflate(18, 18),
            width=5,
            border_radius=24,
        )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (220, 235, 245) if inhaling else (255, 248, 235)
    if exercise:
        fill = (210, 230, 240)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    lung_color = (221, 151, 161)
    breathe_scale = 1.0 + (0.12 if inhaling else -0.06) + bucket * 0.01
    lw = int(14 * breathe_scale)
    lh = int(22 * breathe_scale)
    pygame.draw.ellipse(surface, lung_color, (cx - lw - 4, cy - lh // 2, lw, lh))
    pygame.draw.ellipse(surface, lung_color, (cx + 4, cy - lh // 2, lw, lh))
    pygame.draw.line(surface, (104, 78, 57), (cx, cy - 14), (cx, cy + 10), 3)
    if inhaling:
        pygame.draw.polygon(surface, (91, 151, 196), [(cx - 8, cy - 16), (cx, cy - 22), (cx + 8, cy - 16)])
    else:
        pygame.draw.polygon(surface, (91, 151, 196), [(cx - 8, cy + 16), (cx, cy + 22), (cx + 8, cy + 16)])
    return hit


def draw_animal_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    animal: str = "lion",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big playful animal reaction trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, ANIMAL_ACTION_HIT, ANIMAL_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time) if active else 0
    size = ANIMAL_ACTION_SIZE + bucket
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    pygame.draw.rect(
        surface,
        (255, 210, 90, 34 + bucket * 8),
        rect.inflate(18, 18),
        width=5,
        border_radius=24,
    )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if animal == "lion":
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy + 2), 18)
        pygame.draw.circle(surface, (225, 161, 74), (cx, cy + 2), 12)
        pygame.draw.circle(surface, (91, 65, 47), (cx - 5, cy - 1), 2)
        pygame.draw.circle(surface, (91, 65, 47), (cx + 5, cy - 1), 2)
        mouth_h = 4 + bucket
        pygame.draw.ellipse(surface, (61, 44, 31), (cx - 6, cy + 6, 12, mouth_h))
        for ang in (-40, 0, 40):
            rad = math.radians(ang + bucket * 3)
            sx = cx + int(math.cos(rad) * 20)
            sy = cy + int(math.sin(rad) * 20) - 4
            pygame.draw.circle(surface, (143, 82, 45), (sx, sy), 4)
    elif animal == "elephant":
        pygame.draw.ellipse(surface, (143, 153, 160), (cx - 12, cy - 4, 26, 22))
        pygame.draw.circle(surface, (143, 153, 160), (cx + 8, cy - 6), 14)
        trunk_color = (120, 130, 138)
        pygame.draw.line(surface, trunk_color, (cx + 8, cy + 6), (cx + 6 + bucket, cy + 18), 7)
        pygame.draw.circle(surface, trunk_color, (cx + 6 + bucket, cy + 18), 5)
        pygame.draw.ellipse(surface, (170, 175, 180), (cx - 10, cy - 8, 14, 18))
    elif animal == "bee":
        pygame.draw.ellipse(surface, (247, 204, 63), (cx - 14, cy - 4, 28, 16))
        for x in (cx - 6, cx + 4):
            pygame.draw.line(surface, (55, 49, 43), (x, cy - 6), (x, cy + 6), 3)
        pygame.draw.ellipse(surface, (218, 239, 247), (cx - 16, cy - 10, 14, 12))
        pygame.draw.ellipse(surface, (218, 239, 247), (cx + 6, cy - 10, 14, 12))
    elif animal == "octopus":
        pygame.draw.ellipse(surface, (200, 120, 130), (cx, cy - 4, 18, 20))
        for ang in (-30, 0, 30):
            rad = math.radians(ang + bucket * 6)
            x = cx + int(math.cos(rad) * 10)
            y = cy + 12 + int(math.sin(rad) * 3)
            pygame.draw.line(surface, (180, 100, 110), (cx, cy + 6), (x, y), 4)
    elif animal == "penguin":
        pygame.draw.ellipse(surface, (50, 55, 62), (cx - 10, cy - 10, 20, 28))
        pygame.draw.ellipse(surface, (255, 250, 235), (cx - 6, cy - 4, 12, 20))
        pygame.draw.circle(surface, (50, 55, 62), (cx, cy - 14), 8)
        pygame.draw.polygon(surface, (240, 180, 60), [(cx, cy - 10), (cx - 4, cy - 6), (cx + 4, cy - 6)])
    elif animal == "frog":
        pygame.draw.ellipse(surface, (110, 180, 110), (cx - 14, cy - 2, 28, 18))
        pygame.draw.circle(surface, (90, 150, 90), (cx - 8, cy - 8), 7)
        pygame.draw.circle(surface, (90, 150, 90), (cx + 8, cy - 8), 7)
        pygame.draw.circle(surface, (20, 20, 20), (cx - 8, cy - 8), 2)
        pygame.draw.circle(surface, (20, 20, 20), (cx + 8, cy - 8), 2)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


def draw_machine_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    machine: str = "gears",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big machine toy trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, MACHINE_ACTION_HIT, MACHINE_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time) if active else 0
    size = MACHINE_ACTION_SIZE + bucket
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    pygame.draw.rect(
        surface,
        (255, 210, 90, 34 + bucket * 8),
        rect.inflate(18, 18),
        width=5,
        border_radius=24,
    )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if machine == "magnet":
        pygame.draw.rect(surface, (213, 81, 82), (cx - 20, cy - 10, 20, 20), border_radius=6)
        pygame.draw.rect(surface, (87, 133, 199), (cx, cy - 10, 20, 20), border_radius=6)
        pygame.draw.rect(surface, edge, (cx - 20, cy - 10, 40, 20), width=2, border_radius=6)
        pygame.draw.circle(surface, (255, 250, 235), (cx - 10, cy + 12), 5)
        pygame.draw.circle(surface, (255, 250, 235), (cx + 10, cy + 12), 5)
    elif machine == "bicycle":
        pygame.draw.circle(surface, (60, 65, 68), (cx - 14, cy + 6), 14, 3)
        pygame.draw.circle(surface, (60, 65, 68), (cx + 14, cy + 6), 14, 3)
        pygame.draw.line(surface, (76, 135, 181), (cx - 14, cy + 6), (cx, cy - 12), 4)
        pygame.draw.line(surface, (76, 135, 181), (cx, cy - 12), (cx + 14, cy + 6), 4)
        pygame.draw.line(surface, (76, 135, 181), (cx, cy - 12), (cx, cy + 6), 3)
    elif machine == "airplane":
        pygame.draw.ellipse(surface, (220, 224, 221), (cx - 20, cy - 4, 40, 12))
        pygame.draw.polygon(surface, (180, 190, 195), [(cx - 8, cy), (cx - 2, cy - 12), (cx + 6, cy)])
        pygame.draw.polygon(surface, (160, 170, 175), [(cx - 4, cy + 2), (cx + 10, cy - 6), (cx + 14, cy + 2)])
    elif machine == "bridge":
        pygame.draw.line(surface, (120, 130, 145), (cx - 22, cy + 8), (cx + 22, cy + 8), 4)
        pygame.draw.line(surface, (120, 130, 145), (cx - 18, cy + 8), (cx - 8, cy - 10), 3)
        pygame.draw.line(surface, (120, 130, 145), (cx + 8, cy - 10), (cx + 18, cy + 8), 3)
        pygame.draw.circle(surface, (240, 180, 60), (cx, cy - 2), 6)
    elif machine == "gears":
        pygame.draw.circle(surface, (83, 145, 181), (cx, cy), 16)
        pygame.draw.circle(surface, edge, (cx, cy), 16, 2)
        pygame.draw.circle(surface, (255, 248, 232), (cx, cy), 6)
        for ang in range(0, 360, 60):
            rad = math.radians(ang + time * 60)
            x1 = cx + int(math.cos(rad) * 16)
            y1 = cy + int(math.sin(rad) * 16)
            x2 = cx + int(math.cos(rad) * 20)
            y2 = cy + int(math.sin(rad) * 20)
            pygame.draw.line(surface, edge, (x1, y1), (x2, y2), 3)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


def draw_history_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    history: str = "dinosaurs",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Big history toy trigger."""

    cx, cy = center
    hit = pygame.Rect(0, 0, HISTORY_ACTION_HIT, HISTORY_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time) if active else 0
    size = HISTORY_ACTION_SIZE + bucket
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    pygame.draw.rect(
        surface,
        (255, 210, 90, 34 + bucket * 8),
        rect.inflate(18, 18),
        width=5,
        border_radius=24,
    )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if history == "dinosaurs":
        pygame.draw.ellipse(surface, (115, 140, 110), (cx - 12, cy - 4, 26, 14))
        pygame.draw.circle(surface, (115, 140, 110), (cx + 12, cy - 6), 9)
        pygame.draw.line(surface, (115, 140, 110), (cx - 10, cy + 6), (cx - 18, cy + 14), 4)
        pygame.draw.line(surface, (115, 140, 110), (cx + 6, cy + 6), (cx + 14, cy + 14), 4)
        pygame.draw.circle(surface, (60, 65, 60), (cx + 14, cy - 8), 2)
    elif history == "mammoth":
        pygame.draw.ellipse(surface, (150, 130, 115), (cx - 14, cy - 2, 28, 18))
        pygame.draw.circle(surface, (150, 130, 115), (cx + 12, cy - 6), 10)
        pygame.draw.arc(surface, (90, 70, 60), (cx - 4, cy + 4, 18, 14), 0.2, 2.8, 3)
        pygame.draw.circle(surface, (40, 30, 25), (cx + 14, cy - 8), 2)
    elif history == "cave":
        pygame.draw.rect(surface, (190, 150, 110), (cx - 16, cy - 10, 32, 22), border_radius=4)
        pygame.draw.circle(surface, (120, 80, 60), (cx - 6, cy), 4)
        pygame.draw.circle(surface, (180, 120, 90), (cx + 6, cy + 4), 3)
        pygame.draw.circle(surface, (210, 180, 160), (cx, cy - 8), 7)
        for dx, dy in ((-6, 6), (0, 7), (6, 6)):
            pygame.draw.circle(surface, (210, 180, 160), (cx + dx, cy + dy), 2)
    elif history == "fossils":
        pygame.draw.ellipse(surface, (120, 140, 150), (cx - 14, cy - 6, 28, 14))
        pygame.draw.ellipse(surface, (90, 110, 125), (cx - 8, cy - 4, 16, 8))
        pygame.draw.line(surface, (80, 100, 115), (cx - 16, cy + 6), (cx + 16, cy + 6), 2)
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 14)
    return hit


def draw_entry_action_button(
    surface: pygame.Surface,
    center: tuple[int, int],
    *,
    entry: str = "generic",
    time: float = 0.0,
    active: bool = True,
) -> pygame.Rect:
    """Generic big entry toy button for remaining earth/space/history entries."""

    cx, cy = center
    hit = pygame.Rect(0, 0, ENTRY_ACTION_HIT, ENTRY_ACTION_HIT)
    hit.center = center
    bucket = _bucket(time) if active else 0
    size = ENTRY_ACTION_SIZE + bucket
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    pygame.draw.rect(
        surface,
        (255, 210, 90, 34 + bucket * 8),
        rect.inflate(18, 18),
        width=5,
        border_radius=24,
    )
    pygame.draw.ellipse(surface, (40, 28, 20, 42), (rect.x - 4 + 4, rect.y - 2 + 8, size, size - 6))
    fill = (255, 248, 232)
    edge = (104, 78, 57)
    pygame.draw.rect(surface, fill, rect, border_radius=22)
    pygame.draw.rect(surface, edge, rect, width=4, border_radius=22)
    if entry in ("rain", "water"):
        pygame.draw.ellipse(surface, (90, 150, 190), (cx - 12, cy - 8, 24, 16))
        pygame.draw.line(surface, (90, 150, 190), (cx - 8, cy + 6), (cx - 6, cy + 14), 3)
        pygame.draw.line(surface, (90, 150, 190), (cx, cy + 6), (cx + 2, cy + 14), 3)
        pygame.draw.line(surface, (90, 150, 190), (cx + 8, cy + 6), (cx + 10, cy + 14), 3)
    elif entry in ("ocean", "deep"):
        pygame.draw.rect(surface, (90, 150, 190), (cx - 16, cy - 6, 32, 22), border_radius=6)
        pygame.draw.arc(surface, (160, 200, 220), (cx - 12, cy - 2, 24, 8), 0.2, 2.9, 2)
    elif entry in ("tree", "roots"):
        pygame.draw.rect(surface, (120, 100, 80), (cx - 4, cy - 8, 8, 22))
        pygame.draw.circle(surface, (110, 180, 110), (cx, cy - 14), 14)
        pygame.draw.circle(surface, (90, 150, 90), (cx, cy + 12), 6)
    elif entry == "rainbow":
        for i, col in enumerate(((220, 80, 80), (240, 180, 80), (90, 180, 110), (80, 120, 200))):
            pygame.draw.arc(surface, col, (cx - 18 + i * 2, cy - 10 + i * 2, 36 - i * 4, 20 - i * 2), 0, 3.14, 3)
    elif entry == "sun":
        pygame.draw.circle(surface, (250, 210, 90), (cx, cy), 16)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1 = cx + int(math.cos(rad) * 16)
            y1 = cy + int(math.sin(rad) * 16)
            x2 = cx + int(math.cos(rad) * 20)
            y2 = cy + int(math.sin(rad) * 20)
            pygame.draw.line(surface, (240, 180, 60), (x1, y1), (x2, y2), 2)
    elif entry in ("mercury", "moon", "mars"):
        pygame.draw.circle(surface, (180, 180, 170), (cx, cy), 14)
        pygame.draw.circle(surface, (140, 140, 130), (cx + 4, cy - 4), 3)
        pygame.draw.circle(surface, (160, 160, 150), (cx - 3, cy + 5), 2)
    elif entry == "venus":
        pygame.draw.circle(surface, (240, 210, 120), (cx, cy), 14)
        pygame.draw.ellipse(surface, (230, 200, 100), (cx - 10, cy - 2, 20, 8))
    elif entry == "earth":
        pygame.draw.circle(surface, (90, 150, 200), (cx, cy), 14)
        pygame.draw.ellipse(surface, (110, 180, 110), (cx - 6, cy - 4, 10, 8))
    elif entry == "jupiter":
        pygame.draw.circle(surface, (210, 170, 120), (cx, cy), 14)
        pygame.draw.ellipse(surface, (240, 210, 150), (cx - 8, cy - 2, 16, 4))
        pygame.draw.ellipse(surface, (200, 100, 80), (cx + 4, cy + 2, 6, 3))
    elif entry == "saturn":
        pygame.draw.circle(surface, (220, 200, 140), (cx, cy), 12)
        pygame.draw.ellipse(surface, (230, 215, 160), (cx - 16, cy, 32, 6), 2)
    elif entry in ("uranus", "neptune"):
        c = (150, 210, 220) if entry == "uranus" else (80, 120, 200)
        pygame.draw.circle(surface, c, (cx, cy), 14)
        pygame.draw.ellipse(surface, (200, 220, 230), (cx - 6, cy - 2, 12, 4))
    else:
        pygame.draw.circle(surface, (143, 82, 45), (cx, cy), 10)
        pygame.draw.circle(surface, (255, 210, 90), (cx + 8, cy - 8), 4)
    return hit
