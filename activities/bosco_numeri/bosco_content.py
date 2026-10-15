"""Content constants and educational assets for Il Bosco dei Numeri di Tito."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from greia_platform.system_chrome import ActivitySystemChromeLayout

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "bosco_numeri_progress"

# Number carousel geometry shared by the renderer and the pointer dispatch. The
# whole carousel starts clear of the trusted Home/Back region, which the platform
# reserves in full (both slots) so layout never jumps with navigation context.
CAROUSEL_Y = 52
CAROUSEL_ARROW_RADIUS = 24
CAROUSEL_BUTTON_SIZE = 50
CAROUSEL_SPACING = 60
CAROUSEL_PREV_X = (
    ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    .protected_region.right
    + 8
    + CAROUSEL_ARROW_RADIUS
)
CAROUSEL_START_X = CAROUSEL_PREV_X + CAROUSEL_ARROW_RADIUS + 8 + CAROUSEL_BUTTON_SIZE // 2
CAROUSEL_NEXT_X = (
    CAROUSEL_START_X + 9 * CAROUSEL_SPACING + CAROUSEL_BUTTON_SIZE // 2 + 8 + CAROUSEL_ARROW_RADIUS
)


class ForestItemKind(Enum):
    SUN = "sun"
    APPLE = "apple"
    BUTTERFLY = "butterfly"
    STRAWBERRY = "strawberry"
    DUCKLING = "duckling"
    MUSHROOM = "mushroom"
    ACORN = "acorn"
    LEAF = "leaf"
    SUNFLOWER = "sunflower"
    STAR = "star"

    @property
    def symbol(self) -> str:
        match self:
            case ForestItemKind.SUN:
                return "☀️"
            case ForestItemKind.APPLE:
                return "🍎"
            case ForestItemKind.BUTTERFLY:
                return "🦋"
            case ForestItemKind.STRAWBERRY:
                return "🍓"
            case ForestItemKind.DUCKLING:
                return "🐥"
            case ForestItemKind.MUSHROOM:
                return "🍄"
            case ForestItemKind.ACORN:
                return "🌰"
            case ForestItemKind.LEAF:
                return "🍃"
            case ForestItemKind.SUNFLOWER:
                return "🌻"
            case ForestItemKind.STAR:
                return "⭐"


@dataclass(frozen=True)
class NumberDefinition:
    number: int
    kind: ForestItemKind
    name_it: str
    name_en: str
    item_plural_it: str
    item_plural_en: str


NUMBERS_1_TO_10: list[NumberDefinition] = [
    NumberDefinition(1, ForestItemKind.SUN, "Uno", "One", "sole", "sun"),
    NumberDefinition(2, ForestItemKind.APPLE, "Due", "Two", "mele", "apples"),
    NumberDefinition(3, ForestItemKind.BUTTERFLY, "Tre", "Three", "farfalle", "butterflies"),
    NumberDefinition(4, ForestItemKind.STRAWBERRY, "Quattro", "Four", "fragole", "strawberries"),
    NumberDefinition(5, ForestItemKind.DUCKLING, "Cinque", "Five", "pulcini", "ducklings"),
    NumberDefinition(6, ForestItemKind.MUSHROOM, "Sei", "Six", "funghi", "mushrooms"),
    NumberDefinition(7, ForestItemKind.ACORN, "Sette", "Seven", "ghiande", "acorns"),
    NumberDefinition(8, ForestItemKind.LEAF, "Otto", "Eight", "foglie", "leaves"),
    NumberDefinition(9, ForestItemKind.SUNFLOWER, "Nove", "Nine", "girasoli", "sunflowers"),
    NumberDefinition(10, ForestItemKind.STAR, "Dieci", "Ten", "stelle", "stars"),
]
