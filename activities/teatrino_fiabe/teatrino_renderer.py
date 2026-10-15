"""Stateless rendering helpers for Teatrino.

No state, no caches beyond what teatrino_assets owns. Pure functions
that draw puppets, sparks, layout geometry and stage chrome.
"""

from __future__ import annotations

import math

import pygame

from greia_platform.typography import GreiaTypography

if __package__:
    from .teatrino_assets import get_glow_surface, get_shadow_surface
else:
    from teatrino_assets import get_glow_surface, get_shadow_surface


def get_library_modal_layout(page: int, total_shows: int) -> dict:
    box_rect = pygame.Rect(80, 36, 864, 528)
    close_rect = pygame.Rect(box_rect.right - 56, box_rect.y + 14, 42, 42)
    header_rect = pygame.Rect(box_rect.x, box_rect.y + 14, box_rect.width, 38)

    cards_per_page = 4
    cards = []
    start_idx = page * cards_per_page
    end_idx = min(total_shows, (page + 1) * cards_per_page)

    for local_idx in range(end_idx - start_idx):
        card_y = box_rect.y + 64 + local_idx * 98
        card_rect = pygame.Rect(box_rect.x + 30, card_y, box_rect.width - 60, 86)
        play_btn = pygame.Rect(card_rect.right - 190, card_rect.centery - 24, 115, 48)
        del_btn = pygame.Rect(card_rect.right - 62, card_rect.centery - 24, 50, 48)
        cards.append(
            {
                "card_rect": card_rect,
                "play_btn": play_btn,
                "del_btn": del_btn,
                "show_index": start_idx + local_idx,
            }
        )

    prev_btn = pygame.Rect(box_rect.x + 30, box_rect.bottom - 50, 120, 38)
    next_btn = pygame.Rect(box_rect.right - 150, box_rect.bottom - 50, 120, 38)

    return {
        "box": box_rect,
        "close": close_rect,
        "header": header_rect,
        "cards": cards,
        "prev_btn": prev_btn,
        "next_btn": next_btn,
        "cards_per_page": cards_per_page,
    }


def get_delete_dialog_layout() -> dict:
    """Rectangles for the deliberate "delete this show?" dialog.

    A preview of the show sits on top; two big pictogram buttons sit below,
    with the safe "keep" choice on the left and the destructive one on the right.
    """
    box = pygame.Rect(212, 118, 600, 364)
    preview = pygame.Rect(box.x + 40, box.y + 28, box.width - 80, 104)
    keep = pygame.Rect(box.x + 50, box.bottom - 190, 220, 150)
    delete = pygame.Rect(box.right - 50 - 220, box.bottom - 190, 220, 150)
    return {"box": box, "preview": preview, "keep": keep, "delete": delete}


def draw_puppet(surface: pygame.Surface, puppet, sprite_img: pygame.Surface, typography: GreiaTypography) -> None:
    """Draw one puppet with rod, shadow, glow, tilt and jump/talk offsets."""
    # Puppet is expected to expose update() + attributes; we call update here
    # to preserve original behavior where draw() advanced timers.
    try:
        puppet.update()
    except Exception:
        pass

    shadow_rect = pygame.Rect(0, 0, puppet.shadow_size, 20)
    shadow_rect.center = (int(puppet.x), 430)
    surface.blit(get_shadow_surface(puppet.shadow_size), shadow_rect.topleft)

    rod_top_y = int(puppet.y + 20)
    pygame.draw.line(surface, (160, 100, 45), (int(puppet.x), rod_top_y), (int(puppet.x), 430), 6)
    pygame.draw.line(surface, (210, 150, 80), (int(puppet.x - 1), rod_top_y), (int(puppet.x - 1), 430), 2)

    jump_offset = math.sin(puppet.jump_timer * math.pi) * 36.0 if puppet.jump_timer > 0.0 else 0.0
    talk_offset = math.sin(puppet.talk_timer * 18.0) * 8.0 if puppet.talk_timer > 0.0 else 0.0
    render_y = puppet.y - jump_offset + talk_offset

    img = sprite_img
    if getattr(puppet, "flip_x", False):
        img = pygame.transform.flip(img, True, False)
    if abs(getattr(puppet, "tilt_angle", 0.0)) > 1.5:
        img = pygame.transform.rotate(img, puppet.tilt_angle)

    img_rect = img.get_rect(center=(int(puppet.x), int(render_y)))
    surface.blit(img, img_rect.topleft)

    if puppet.is_held or puppet.talk_timer > 0.0:
        glow = get_glow_surface(puppet.size)
        surface.blit(glow, (int(puppet.x - glow.get_width() // 2), int(render_y - glow.get_height() // 2)))


def draw_ambient_spark(surface: pygame.Surface, spark) -> None:
    if spark.alpha <= 0.0:
        return
    col = (254, 240, 138) if spark.bg_id in ("forest", "sky") else (200, 240, 255)
    spark_surf = pygame.Surface((int(spark.size * 2), int(spark.size * 2)), pygame.SRCALPHA)
    pygame.draw.circle(
        spark_surf,
        (*col, int(spark.alpha * 180)),
        (int(spark.size), int(spark.size)),
        int(spark.size),
    )
    surface.blit(spark_surf, (int(spark.x - spark.size), int(spark.y - spark.size)))


def draw_stage_curtains_and_valance(surface: pygame.Surface) -> None:
    """Draw side curtains and top valance. Extracted from monolithic draw."""
    # Import colors lazily to avoid circular deps at import time.
    try:
        if __package__:
            from .teatrino_content import STAGE_CURTAIN, STAGE_CURTAIN_DARK, STAGE_CURTAIN_LIGHT, STAGE_GOLD
        else:
            from teatrino_content import STAGE_CURTAIN, STAGE_CURTAIN_DARK, STAGE_CURTAIN_LIGHT, STAGE_GOLD
    except Exception:
        STAGE_CURTAIN = (153, 27, 27)
        STAGE_CURTAIN_DARK = (127, 29, 29)
        STAGE_CURTAIN_LIGHT = (220, 38, 38)
        STAGE_GOLD = (245, 158, 11)

    # Need reference width without importing content again? Use constant 1024.
    REFERENCE_WIDTH = 1024
    pygame.draw.polygon(surface, STAGE_CURTAIN_DARK, [(0, 0), (130, 0), (70, 440), (0, 440)])
    pygame.draw.polygon(surface, STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
    pygame.draw.polygon(surface, STAGE_CURTAIN_LIGHT, [(0, 0), (70, 0), (35, 420), (0, 420)])
    pygame.draw.polygon(
        surface,
        STAGE_CURTAIN_DARK,
        [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 130, 0), (REFERENCE_WIDTH - 70, 440), (REFERENCE_WIDTH, 440)],
    )
    pygame.draw.polygon(
        surface,
        STAGE_CURTAIN,
        [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 110, 0), (REFERENCE_WIDTH - 55, 430), (REFERENCE_WIDTH, 430)],
    )
    pygame.draw.polygon(
        surface,
        STAGE_CURTAIN_LIGHT,
        [(REFERENCE_WIDTH, 0), (REFERENCE_WIDTH - 70, 0), (REFERENCE_WIDTH - 35, 420), (REFERENCE_WIDTH, 420)],
    )
    for vx in range(120, 890, 110):
        pygame.draw.circle(surface, STAGE_CURTAIN_DARK, (vx + 55, 24), 68)
        pygame.draw.circle(surface, STAGE_CURTAIN, (vx + 55, 24), 62)
        pygame.draw.circle(surface, STAGE_GOLD, (vx + 55, 24), 62, width=2)
        pygame.draw.circle(surface, STAGE_GOLD, (vx + 55, 86), 4)
    pygame.draw.rect(surface, (60, 40, 15), (0, 0, REFERENCE_WIDTH, 14))
    pygame.draw.rect(surface, STAGE_GOLD, (0, 10, REFERENCE_WIDTH, 4))


__all__ = ["get_library_modal_layout", "get_delete_dialog_layout", "draw_puppet", "draw_ambient_spark", "draw_stage_curtains_and_valance"]
