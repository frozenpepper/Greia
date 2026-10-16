"""Scene geometry for My Cute Pet in 1024x600 logical pixels (pure).

Pet art (``creature.pet.*``, 256 canvas) stands on its contact shadow at
``ART_BASE`` of the canvas, so ``pet_rect`` places a sprite by the floor
point under its feet. Floors own y >= 432 in the shared room kits.
Nothing here enters the protected Home/Back corner (top-left); the top bar
is laid out by the control kit outside it.
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .cucciolo_content import Care
else:
    from cucciolo_content import Care

ART_BASE: Final = 231 / 256  # contact-shadow centre of library pets
PET_SIZE: Final = 300
# The pet's floor point in its home room, above the care tray.
HOME_FLOOR: Final[tuple[int, int]] = (566, 462)

LILLI_HEIGHT: Final = 184
LILLI_MIDBOTTOM: Final[tuple[int, int]] = (100, 598)

TRAY_TILE: Final[tuple[int, int]] = (112, 116)
TRAY_GAP: Final = 18
TRAY_TOP: Final = 472
TRAY_CENTER_X: Final = 566
TRAY_ICON: Final = 88

# Adopt screen: three big pet cards and a confirm button.
ADOPT_CARD: Final[tuple[int, int]] = (220, 240)
ADOPT_TOP: Final = 150
ADOPT_GAP: Final = 36
ADOPT_CENTER_X: Final = 566
ADOPT_ICON: Final = 196
CONFIRM_RECT: Final[pygame.Rect] = pygame.Rect(882, 452, 112, 118)
CONFIRM_ICON: Final = 64

# Name screen: the chosen pet on the left, four picture name tags.
NAME_PET_FLOOR: Final[tuple[int, int]] = (338, 470)
NAME_TILE: Final[tuple[int, int]] = (150, 158)
NAME_ORIGIN: Final[tuple[int, int]] = (524, 124)
NAME_GAP: Final = 20
NAME_ICON: Final = 92


def pet_rect(floor: tuple[int, int], size: int = PET_SIZE) -> pygame.Rect:
    """Sprite rect whose contact shadow sits on ``floor``."""

    rect = pygame.Rect(0, 0, size, size)
    rect.midtop = (floor[0], int(round(floor[1] - ART_BASE * size)))
    return rect


def pet_hit_rect(floor: tuple[int, int], size: int = PET_SIZE) -> pygame.Rect:
    """Touch area of a standing pet (its art without the empty margins)."""

    sprite = pet_rect(floor, size)
    return pygame.Rect(
        sprite.x + int(size * 0.12),
        sprite.y + int(size * 0.12),
        int(size * 0.76),
        int(size * 0.80),
    )


def tray_rects(count: int) -> tuple[pygame.Rect, ...]:
    width, height = TRAY_TILE
    total = count * width + (count - 1) * TRAY_GAP
    left = TRAY_CENTER_X - total // 2
    return tuple(pygame.Rect(left + i * (width + TRAY_GAP), TRAY_TOP, width, height) for i in range(count))


def adopt_rects(count: int) -> tuple[pygame.Rect, ...]:
    width, height = ADOPT_CARD
    total = count * width + (count - 1) * ADOPT_GAP
    left = ADOPT_CENTER_X - total // 2
    return tuple(pygame.Rect(left + i * (width + ADOPT_GAP), ADOPT_TOP, width, height) for i in range(count))


def name_rects(count: int) -> tuple[pygame.Rect, ...]:
    width, height = NAME_TILE
    rects = []
    for index in range(count):
        row, column = divmod(index, 2)
        rects.append(
            pygame.Rect(
                NAME_ORIGIN[0] + column * (width + NAME_GAP),
                NAME_ORIGIN[1] + row * (height + NAME_GAP),
                width,
                height,
            )
        )
    return tuple(rects)


class CareStage:
    """Where the pet and the care prop stand while one care is done."""

    def __init__(self, floor: tuple[int, int], prop: pygame.Rect | None) -> None:
        self.floor = floor
        self.prop = prop

    @property
    def pet(self) -> pygame.Rect:
        return pet_rect(self.floor)

    @property
    def target(self) -> pygame.Rect:
        """Touch area for the care actions: the pet plus its prop."""

        area = pet_hit_rect(self.floor)
        if self.prop is not None:
            area = area.union(self.prop)
        return area.clip(pygame.Rect(180, 130, 820, 470))


def _rect_mid(size: tuple[int, int], midbottom: tuple[int, int]) -> pygame.Rect:
    rect = pygame.Rect(0, 0, *size)
    rect.midbottom = midbottom
    return rect


BOWL_SIZE: Final = 190
BED_SIZE: Final[tuple[int, int]] = (500, 250)
BALL_SIZE: Final = 92
PLASTER_SIZE: Final = 66
SPONGE_SIZE: Final = 104

STAGES: Final[dict[Care, CareStage]] = {
    Care.FOOD: CareStage((452, 470), _rect_mid((BOWL_SIZE, BOWL_SIZE), (668, 488))),
    Care.BATH: CareStage((540, 474), None),
    Care.BALL: CareStage((470, 470), _rect_mid((BALL_SIZE, BALL_SIZE), (760, 482))),
    Care.PLASTER: CareStage((540, 470), None),
    # In bed the pet sits on the cushion; the bed's bolster covers its paws.
    Care.BED: CareStage((540, 484), _rect_mid(BED_SIZE, (540, 548))),
}

# Where an offered care meets the pet in its home room (just under its chin).
OFFER_POINT: Final[tuple[int, int]] = (HOME_FLOOR[0] - 20, HOME_FLOOR[1] - 120)

# Where the ball rests and where it is caught (centres).
BALL_REST: Final[tuple[int, int]] = STAGES[Care.BALL].prop.center if STAGES[Care.BALL].prop else (760, 436)
BALL_CATCH: Final[tuple[int, int]] = (470, 250)
SPONGE_SPOTS: Final[tuple[tuple[int, int], ...]] = ((600, 300), (480, 350), (610, 400))


__all__ = [
    "ADOPT_CARD",
    "ADOPT_ICON",
    "ART_BASE",
    "BALL_CATCH",
    "BALL_REST",
    "BALL_SIZE",
    "BED_SIZE",
    "BOWL_SIZE",
    "CONFIRM_ICON",
    "CONFIRM_RECT",
    "CareStage",
    "HOME_FLOOR",
    "LILLI_HEIGHT",
    "LILLI_MIDBOTTOM",
    "NAME_ICON",
    "NAME_PET_FLOOR",
    "PET_SIZE",
    "OFFER_POINT",
    "PLASTER_SIZE",
    "SPONGE_SIZE",
    "SPONGE_SPOTS",
    "STAGES",
    "TRAY_ICON",
    "TRAY_TILE",
    "adopt_rects",
    "name_rects",
    "pet_hit_rect",
    "pet_rect",
    "tray_rects",
]
