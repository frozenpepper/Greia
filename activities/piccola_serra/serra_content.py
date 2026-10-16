"""Piccola Serra (Little Green Thumb) -- authored content, no pygame.

The child grows one plant at a time from seed in a greenhouse. Each growth
stage shows one *need* through the plant's look and its surroundings, and the
child chooses the care that fixes it:

==========  ========================================  ==========
need        what the child sees                       care
==========  ========================================  ==========
thirsty     droopy, dull leaves; dry cracked soil     water
dark        shade cloth down, pale plant leaning      sun
            toward the window
soggy       water standing on the soil (puddle)       wait
ripe        fruit/seeds/root ready on the plant       harvest
==========  ========================================  ==========

Plants follow honest cycles (bean: seed -> sprout -> young -> flower ->
pods; sunflower: ... -> flower -> seeds; strawberry: ... -> flower ->
berries; carrot: seed -> sprout -> leaves -> root, pulled before it
flowers). After the harvest the child puts the plant's stage pictures in
order. This module owns the vocabulary, plants and the difficulty ladder.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
# Historical key kept so existing saves still load (schema 1 had no version).
STORAGE_KEY: Final = "piccola_serra.progress.v1"
PLANTS_PER_VISIT: Final = 3
TITO: Final = "tito"


class Stage(StrEnum):
    SEED = "seed"
    SPROUT = "sprout"
    YOUNG = "young"
    FLOWER = "flower"
    FRUIT = "fruit"


class Need(StrEnum):
    THIRSTY = "thirsty"
    DARK = "dark"
    SOGGY = "soggy"
    RIPE = "ripe"


class Care(StrEnum):
    WATER = "water"
    SUN = "sun"
    WAIT = "wait"
    HARVEST = "harvest"


CURE: Final[dict[Need, Care]] = {
    Need.THIRSTY: Care.WATER,
    Need.DARK: Care.SUN,
    Need.SOGGY: Care.WAIT,
    Need.RIPE: Care.HARVEST,
}

# Stages whose picture has authored ``droopy`` / ``leaning`` variants.
SYMPTOM_STAGES: Final = frozenset({Stage.SPROUT, Stage.YOUNG, Stage.FLOWER})


@dataclass(frozen=True, slots=True)
class PlantSpec:
    """One plant the child can grow.

    ``harvest_asset`` is the shared food prop the harvest becomes (``None``
    when the picture is this package's own ``harvest_file``).
    """

    plant_id: str
    stages: tuple[Stage, ...]
    harvest_asset: str | None
    harvest_file: str | None = None
    packet_stage: Stage = Stage.FRUIT  # the picture on the seed packet

    def __post_init__(self) -> None:
        if not self.stages or self.stages[0] is not Stage.SEED or self.stages[-1] is not Stage.FRUIT:
            raise ValueError("a plant grows from seed to fruit")
        if (self.harvest_asset is None) == (self.harvest_file is None):
            raise ValueError("a plant needs exactly one harvest picture")


_FULL = (Stage.SEED, Stage.SPROUT, Stage.YOUNG, Stage.FLOWER, Stage.FRUIT)
PLANTS: Final[tuple[PlantSpec, ...]] = (
    PlantSpec("bean", _FULL, None, "bean_pod.png"),
    PlantSpec("sunflower", _FULL, "prop.food.seed", packet_stage=Stage.FLOWER),
    PlantSpec("strawberry", _FULL, "prop.food.strawberry"),
    # Carrots are pulled for their root before they ever flower.
    PlantSpec("carrot", (Stage.SEED, Stage.SPROUT, Stage.YOUNG, Stage.FRUIT), "prop.food.carrot"),
)
PLANTS_BY_ID: Final[dict[str, PlantSpec]] = {plant.plant_id: plant for plant in PLANTS}


@dataclass(frozen=True, slots=True)
class Rung:
    """One step of the ladder: which needs appear, which cares are offered,
    and how many stage cards the child orders after the harvest."""

    level: int
    needs: tuple[Need, ...]
    cares: tuple[Care, ...]
    cards: int


RUNGS: Final[tuple[Rung, ...]] = (
    # Water and light only; three very different pictures to order.
    Rung(1, (Need.THIRSTY, Need.DARK), (Care.WATER, Care.SUN, Care.HARVEST), 3),
    # Too much water appears (the right care is to wait); four pictures.
    Rung(2, (Need.THIRSTY, Need.DARK, Need.SOGGY), (Care.WATER, Care.SUN, Care.WAIT, Care.HARVEST), 4),
    # Every stage of the cycle.
    Rung(3, (Need.THIRSTY, Need.DARK, Need.SOGGY), (Care.WATER, Care.SUN, Care.WAIT, Care.HARVEST), 5),
)
MIN_LEVEL: Final = RUNGS[0].level
MAX_LEVEL: Final = RUNGS[-1].level


def rung_for(level: int) -> Rung:
    return RUNGS[max(MIN_LEVEL, min(MAX_LEVEL, int(level))) - 1]


def sequence_stages(plant: PlantSpec, cards: int) -> tuple[Stage, ...]:
    """The stage pictures to order: always seed first and fruit last.

    Three cards keep the most different pictures (seed, young plant, fruit);
    four add the sprout (and the flower replaces the young plant when the
    plant has one); five show the whole cycle.
    """

    stages = plant.stages
    count = max(3, min(int(cards), len(stages)))
    if count >= len(stages):
        return stages
    if count == 3:
        return (Stage.SEED, Stage.YOUNG, Stage.FRUIT)
    middle = Stage.FLOWER if Stage.FLOWER in stages else Stage.YOUNG
    return (Stage.SEED, Stage.SPROUT, middle, Stage.FRUIT)


__all__ = [
    "CURE",
    "Care",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "Need",
    "PLANTS",
    "PLANTS_BY_ID",
    "PLANTS_PER_VISIT",
    "PlantSpec",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "RUNGS",
    "Rung",
    "STORAGE_KEY",
    "SYMPTOM_STAGES",
    "Stage",
    "TITO",
    "rung_for",
    "sequence_stages",
]
