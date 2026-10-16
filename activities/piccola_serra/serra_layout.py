"""Reference-canvas geometry for Piccola Serra (1024x600 logical space).

The greenhouse is one fixed scene: the pot stands in the middle of the
potting bench (bench top y 466), Tito stands at the left end below the sunny
pane, the harvest basket waits at the right end. Controls (seed packets,
care tiles, stage cards) live in the kit's bottom bar and the HUD in the top
bar beside -- never inside -- the protected Home/Back region; both come from
``ControlLayout`` so they hold at every supported resolution.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .serra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from serra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH

# Plant-stage art is authored on a 256 frame with the soil-mound base at
# (128, 222) and rendered 1:1 for the scene at PLANT_SIZE.
PLANT_SIZE: Final = 308
PLANT_SCALE: Final = PLANT_SIZE / 256
PLANT_BASE: Final = (512, 344)
PLANT_TOPLEFT: Final = (
    PLANT_BASE[0] - round(128 * PLANT_SCALE),
    PLANT_BASE[1] - round(222 * PLANT_SCALE),
)
POT_POS: Final = (402, 290)          # pot_back/pot_front frames (220x200)
SOIL_CENTER: Final = (512, 340)
SAUCER_CENTER: Final = (512, 456)
BENCH_TOP: Final = 466
TITO_MIDBOTTOM: Final = (206, 470)
TITO_HEIGHT: Final = 176
SUN_CENTER: Final = (160, 150)
PANE_RECT: Final = pygame.Rect(36, 78, 296, 218)   # the sunny pane behind the cloth
CLOTH_POS: Final = (34, 74)                        # shade_cloth.png (300x232)
ROLL_POS: Final = (26, 64)                         # shade_roll.png (316x28)
BASKET_MIDBOTTOM: Final = (812, 474)
FRUIT_SPOT: Final = (512, 190)                     # where the ripe crop is shown
CAN_POUR_POS: Final = (612, 168)                   # watering can (tilted) centre
CLOCK_POS: Final = (640, 210)                      # "wait" clock centre
BOARD_LEFT: Final = 330                             # sequence board starts right of Tito


def board_rect(top: int, bottom: int, right: int) -> pygame.Rect:
    """Panel holding the picture slots during the ordering task."""

    return pygame.Rect(BOARD_LEFT, top, max(200, right - BOARD_LEFT), max(160, bottom - top))


def slot_rects(board: pygame.Rect, count: int) -> list[pygame.Rect]:
    """Equal square-ish picture slots across the board, left to right."""

    gap = 34  # room for the little "then" arrows between slots
    pad = 22
    width = min(170, (board.width - 2 * pad - gap * (count - 1)) // count)
    height = min(board.height - 2 * pad, int(width * 1.12))
    total = width * count + gap * (count - 1)
    x = board.centerx - total // 2
    y = board.centery - height // 2
    return [pygame.Rect(x + index * (width + gap), y, width, height) for index in range(count)]


__all__ = [
    "BASKET_MIDBOTTOM",
    "BENCH_TOP",
    "BOARD_LEFT",
    "CAN_POUR_POS",
    "CLOCK_POS",
    "CLOTH_POS",
    "FRUIT_SPOT",
    "PANE_RECT",
    "PLANT_BASE",
    "PLANT_SCALE",
    "PLANT_SIZE",
    "PLANT_TOPLEFT",
    "POT_POS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ROLL_POS",
    "SAUCER_CENTER",
    "SOIL_CENTER",
    "SUN_CENTER",
    "TITO_HEIGHT",
    "TITO_MIDBOTTOM",
    "board_rect",
    "slot_rects",
]
