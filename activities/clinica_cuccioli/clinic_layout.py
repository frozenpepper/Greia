"""Scene geometry for Little Vet Clinic in 1024x600 logical pixels.

The vet corner (shared ``bg.indoor_room.wall_vet_corner`` + ``floor_tile``)
holds the private exam table in the middle, the patient on its cushion,
Momo on the floor at the left and the kit tool tray along the bottom.
Nothing interactive enters the protected Home/Back corner (top-left; at
480x320 it reaches about x 239 / y 87 in this logical space).
"""

from __future__ import annotations

from typing import Final

import pygame

if __package__:
    from .clinic_content import SPRITE_MASTER, BodyPart, Species
else:
    from clinic_content import SPRITE_MASTER, BodyPart, Species

TABLE_SIZE: Final[tuple[int, int]] = (480, 176)
TABLE_ORIGIN: Final[tuple[int, int]] = (320, 302)

PATIENT_SIZE: Final = 320
PATIENT_HOME: Final[tuple[int, int]] = (560, 340)  # sprite midbottom on the cushion
PATIENT_OFFSTAGE_X: Final = 1200

MOMO_MIDBOTTOM: Final[tuple[int, int]] = (128, 596)
MOMO_HEIGHT: Final = 228

TILE_SIZE: Final = 100
TILE_GAP: Final = 14
TRAY_CENTER_X: Final = 606
TILE_TOP: Final = 484
TRAY_PANEL: Final = pygame.Rect(254, 472, 704, 124)

PART_SIZES: Final[dict[BodyPart, tuple[int, int]]] = {
    BodyPart.EAR: (88, 88),
    BodyPart.TUMMY: (84, 64),
    BodyPart.PAW: (80, 60),
}


def tile_rects(count: int) -> tuple[pygame.Rect, ...]:
    """``count`` square tool tiles centred in the tray."""

    total = count * TILE_SIZE + (count - 1) * TILE_GAP
    left = TRAY_CENTER_X - total // 2
    return tuple(pygame.Rect(left + i * (TILE_SIZE + TILE_GAP), TILE_TOP, TILE_SIZE, TILE_SIZE) for i in range(count))


def patient_rect(midbottom: tuple[int, int] = PATIENT_HOME) -> pygame.Rect:
    rect = pygame.Rect(0, 0, PATIENT_SIZE, PATIENT_SIZE)
    rect.midbottom = midbottom
    return rect


def to_screen(anchor: tuple[int, int], midbottom: tuple[int, int] = PATIENT_HOME) -> tuple[int, int]:
    """Map a master-sprite anchor to logical screen space."""

    rect = patient_rect(midbottom)
    scale = PATIENT_SIZE / SPRITE_MASTER
    return (round(rect.left + anchor[0] * scale), round(rect.top + anchor[1] * scale))


def part_rects(species: Species, *, hurt_pose: bool) -> dict[str, tuple[BodyPart, pygame.Rect]]:
    """Hotspots for the "where does it hurt?" step, keyed by target id.

    Registration order matters to the kit (last registered wins on overlap):
    tummy first, then the ears, then the paw.
    """

    def rect(part: BodyPart, anchor: tuple[int, int]) -> pygame.Rect:
        width, height = PART_SIZES[part]
        box = pygame.Rect(0, 0, width, height)
        box.center = to_screen(anchor)
        return box

    paw = rect(BodyPart.PAW, species.paw_hurt if hurt_pose else species.paw)
    return {
        "part.tummy": (BodyPart.TUMMY, _clear_of(rect(BodyPart.TUMMY, species.tummy), paw)),
        "part.ear_left": (BodyPart.EAR, rect(BodyPart.EAR, species.ear_left)),
        "part.ear_right": (BodyPart.EAR, rect(BodyPart.EAR, species.ear_right)),
        "part.paw": (BodyPart.PAW, paw),
    }


def _clear_of(box: pygame.Rect, other: pygame.Rect) -> pygame.Rect:
    """Trim ``box`` so it no longer overlaps ``other`` (paws sit on bellies).

    The cut is made along the axis of the smaller overlap so the tummy keeps
    as much of its area as possible; every tap then has exactly one meaning.
    """

    overlap = box.clip(other)
    if overlap.width == 0 or overlap.height == 0:
        return box
    trimmed = box.copy()
    if overlap.width <= overlap.height:
        if other.centerx >= box.centerx:
            trimmed.width = other.left - box.left
        else:
            trimmed.left = other.right
            trimmed.width = box.right - other.right
    else:
        if other.centery >= box.centery:
            trimmed.height = other.top - box.top
        else:
            trimmed.top = other.bottom
            trimmed.height = box.bottom - other.bottom
    return trimmed


__all__ = [
    "MOMO_HEIGHT",
    "MOMO_MIDBOTTOM",
    "PART_SIZES",
    "PATIENT_HOME",
    "PATIENT_OFFSTAGE_X",
    "PATIENT_SIZE",
    "TABLE_ORIGIN",
    "TABLE_SIZE",
    "TILE_GAP",
    "TILE_SIZE",
    "TILE_TOP",
    "TRAY_PANEL",
    "part_rects",
    "patient_rect",
    "tile_rects",
    "to_screen",
]
