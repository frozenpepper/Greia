"""Content of The Big Seasons Tree: seasons, scene slots, items, missions, ladder.

The child dresses one season's scene, slot by slot (the tree, the weather,
the meadow, a woodland friend, Tito's clothes). Every slot offers picture
cards; exactly one card belongs to the season and the others clearly do not.

Facts live in one table, ``ITEMS``. Each item says where it ``belongs`` and
where it is ``wrong``; a season missing from both sets is *neutral* (true
some years, in some places) and the item is never offered for that season.
That keeps every question unambiguous for a 3-5 year old: autumn apples are
never marked wrong, summer rain is never asked about, and only convention
that early-years seasons teaching relies on (snow = winter, blossom = spring,
orange leaves = autumn, sunhat = summer) decides a wrong answer.

Art is addressed by stable ids: shared library visuals (``ArtRef.shared``)
or this package's own prop renditions (``ArtRef.private``, drawn from
``assets/source/*.svg``). Names are locale keys ``item.<id>``; weather items
also carry the Activity's approved spoken clip, and some items an approved
shared vocabulary noun.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "quattro_stagioni.progress.v1"


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

    @property
    def name_key(self) -> str:
        return f"season.{self.value}"


SEASONS: Final[tuple[Season, ...]] = tuple(Season)


class Slot(StrEnum):
    """A part of the scene the child dresses (one mission each)."""

    TREE = "tree"
    SKY = "sky"
    GROUND = "ground"
    ANIMAL = "animal"
    CLOTHES = "clothes"

    @property
    def prompt_key(self) -> str:
        return f"prompt.{self.value}"


# Scene order: the tree first (it sets the scene), then weather and meadow;
# friend and clothes are the extra missions of the higher rungs.
CORE_SLOTS: Final[tuple[Slot, ...]] = (Slot.TREE, Slot.SKY, Slot.GROUND)
EXTRA_SLOTS: Final[tuple[Slot, ...]] = (Slot.ANIMAL, Slot.CLOTHES)


class Weather(StrEnum):
    SUN = "sun"
    RAIN = "rain"
    WIND = "wind"
    SNOW = "snow"


@dataclass(frozen=True, slots=True)
class ArtRef:
    """One picture: a shared library visual or a private package rendition."""

    asset_id: str | None = None
    variant: str = "default"
    file: str | None = None

    @classmethod
    def shared(cls, asset_id: str, variant: str = "default") -> "ArtRef":
        return cls(asset_id=asset_id, variant=variant)

    @classmethod
    def private(cls, file: str) -> "ArtRef":
        return cls(file=file)

    @property
    def key(self) -> str:
        return self.file if self.file is not None else f"{self.asset_id}#{self.variant}"


@dataclass(frozen=True, slots=True)
class CardLayer:
    """A picture placed in a card icon by fractions of the icon box (x, y, w, h)."""

    art: ArtRef
    box: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)


@dataclass(frozen=True, slots=True)
class Item:
    """One picture card and the scene piece it becomes."""

    item_id: str
    slot: Slot
    belongs: frozenset[Season]
    wrong_for: frozenset[Season]
    card: tuple[CardLayer, ...]
    scene: ArtRef | None = None  # what is drawn in the scene (None: slot-specific)
    crop: bool = False  # crop the card art to its visible bounds (worn clothes)
    weather: Weather | None = None
    speech: str | None = None  # approved Activity clip stem
    vocab: str | None = None  # approved shared vocabulary noun id

    def __post_init__(self) -> None:
        if self.belongs & self.wrong_for:
            raise ValueError(f"{self.item_id}: a season cannot be both right and wrong")

    @property
    def name_key(self) -> str:
        return f"item.{self.item_id}"

    def fits(self, season: Season) -> bool:
        return season in self.belongs

    def clashes(self, season: Season) -> bool:
        return season in self.wrong_for


def _s(*seasons: Season) -> frozenset[Season]:
    return frozenset(seasons)


SP, SU, AU, WI = Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER
ALL = _s(SP, SU, AU, WI)
TRUNK: Final = ArtRef.private("tree_trunk.png")
TREE_CARD_BOX: Final = (-0.08, -0.06, 1.16, 1.16)


def _tree(item_id: str, season: Season, wrong: frozenset[Season]) -> Item:
    canopy = ArtRef.private(f"tree_canopy_{season.value}.png")
    return Item(
        item_id,
        Slot.TREE,
        _s(season),
        wrong,
        # The tree art has generous margins: enlarge it in the card.
        (CardLayer(TRUNK, TREE_CARD_BOX), CardLayer(canopy, TREE_CARD_BOX)),
        scene=canopy,
    )


def _shared(item_id: str, slot: Slot, belongs, wrong, asset_id: str, variant: str = "default", **extra) -> Item:
    art = ArtRef.shared(asset_id, variant)
    return Item(item_id, slot, belongs, wrong, (CardLayer(art),), scene=art, **extra)


def _private(item_id: str, slot: Slot, belongs, wrong, file: str, **extra) -> Item:
    art = ArtRef.private(file)
    return Item(item_id, slot, belongs, wrong, (CardLayer(art),), scene=art, **extra)


CLOUD: Final = ArtRef.shared("prop.nature.cloud")
RAINDROP: Final = ArtRef.shared("prop.nature.raindrop")

ITEMS: Final[dict[str, Item]] = {
    item.item_id: item
    for item in (
        # The tree: one trunk, four canopies. Summer apples are only "wrong"
        # where no apples grow (spring blossom time, winter); autumn harvest
        # keeps them neutral there.
        _tree("tree_blossom", SP, _s(SU, AU, WI)),
        _tree("tree_apples", SU, _s(SP, WI)),
        _tree("tree_orange", AU, _s(SP, SU, WI)),
        _tree("tree_snowy", WI, _s(SP, SU, AU)),
        # The weather.
        Item(
            "sun", Slot.SKY, _s(SP, SU), frozenset(),
            (CardLayer(ArtRef.shared("prop.nature.sun")),),
            weather=Weather.SUN, speech="sun", vocab="sun",
        ),
        Item(
            "rain", Slot.SKY, _s(SP, AU), frozenset(),
            (
                CardLayer(CLOUD, (0.0, 0.0, 1.0, 0.7)),
                CardLayer(RAINDROP, (0.12, 0.55, 0.26, 0.4)),
                CardLayer(RAINDROP, (0.40, 0.62, 0.26, 0.38)),
                CardLayer(RAINDROP, (0.66, 0.55, 0.26, 0.4)),
            ),
            weather=Weather.RAIN, speech="rain",
        ),
        Item(
            "wind", Slot.SKY, _s(AU), _s(SP, SU, WI),
            (
                CardLayer(ArtRef.shared("fx.leaf_drift")),
                CardLayer(ArtRef.shared("prop.nature.leaf_autumn"), (0.24, 0.2, 0.56, 0.56)),
            ),
            weather=Weather.WIND, speech="wind",
        ),
        Item(
            "snow", Slot.SKY, _s(WI), _s(SP, SU, AU),
            (CardLayer(ArtRef.shared("prop.nature.snowflake")),),
            weather=Weather.SNOW, speech="snow",
        ),
        # The meadow.
        _shared("flowers", Slot.GROUND, _s(SP, SU), _s(WI), "prop.nature.flower", vocab="flower"),
        _shared("strawberries", Slot.GROUND, _s(SU), _s(WI), "prop.food.strawberry", vocab="strawberries"),
        _shared("watermelon", Slot.GROUND, _s(SU), _s(SP, AU, WI), "prop.vocab.watermelon", vocab="watermelon"),
        _shared("pumpkin", Slot.GROUND, _s(AU), _s(SP, SU), "prop.vocab.pumpkin", vocab="pumpkin"),
        _shared("mushrooms", Slot.GROUND, _s(AU), _s(WI), "prop.nature.mushroom", vocab="mushrooms"),
        _private("snowman", Slot.GROUND, _s(WI), _s(SP, SU, AU), "snowman.png", vocab="snowman"),
        # A woodland friend: awake in the warm seasons, asleep all winter.
        _shared("butterfly", Slot.ANIMAL, _s(SP, SU), _s(WI), "creature.woodland.butterfly", vocab="butterfly"),
        _shared("frog", Slot.ANIMAL, _s(SP, SU), _s(WI), "creature.woodland.frog", vocab="frog"),
        _shared("hedgehog_asleep", Slot.ANIMAL, _s(WI), _s(SP, SU), "creature.woodland.hedgehog", "asleep", vocab="hedgehog"),
        _shared("bear_asleep", Slot.ANIMAL, _s(WI), _s(SP, SU), "creature.woodland.bear", "asleep", vocab="bear"),
        # Tito's clothes (worn as separate layers on the canonical character).
        Item(
            "winter_hat", Slot.CLOTHES, _s(WI), _s(SU),
            (CardLayer(ArtRef.private("tito_wear_winter_hat.png")),),
            scene=ArtRef.private("tito_wear_winter_hat.png"), crop=True, vocab="winter_hat",
        ),
        Item(
            "scarf", Slot.CLOTHES, _s(WI), _s(SU),
            (CardLayer(ArtRef.private("tito_wear_scarf.png")),),
            scene=ArtRef.private("tito_wear_scarf.png"), crop=True, vocab="scarf",
        ),
        Item(
            "sunhat", Slot.CLOTHES, _s(SU), _s(WI),
            (CardLayer(ArtRef.private("tito_wear_sunhat.png")),),
            scene=ArtRef.private("tito_wear_sunhat.png"), crop=True, vocab="sunhat",
        ),
    )
}
ITEM_IDS: Final[tuple[str, ...]] = tuple(ITEMS)


def right_items(season: Season, slot: Slot) -> tuple[Item, ...]:
    return tuple(item for item in ITEMS.values() if item.slot is slot and item.fits(season))


def wrong_items(season: Season, slot: Slot) -> tuple[Item, ...]:
    return tuple(item for item in ITEMS.values() if item.slot is slot and item.clashes(season))


def slot_available(season: Season, slot: Slot) -> bool:
    """A slot can be asked only when it has a right and a clearly wrong card."""

    return bool(right_items(season, slot)) and bool(wrong_items(season, slot))


@dataclass(frozen=True, slots=True)
class Level:
    """One rung of the ladder: how many missions and how many cards."""

    missions: int
    options: int


LEVELS: Final[tuple[Level, ...]] = (
    Level(3, 2),  # tree, weather, meadow; two cards
    Level(4, 3),  # + a friend or Tito's clothes; three cards
    Level(5, 3),  # every mission the season offers
    Level(5, 4),  # four cards where four fit
)
MAX_LEVEL: Final = len(LEVELS) - 1


@dataclass(frozen=True, slots=True)
class Mission:
    """Dress one slot: ``options`` are item ids, ``answer`` is the one that belongs."""

    slot: Slot
    options: tuple[str, ...]
    answer: str

    def __post_init__(self) -> None:
        if self.answer not in self.options:
            raise ValueError("the answer must be one of the options")


def plan_missions(season: Season, level: int, rng: random.Random) -> tuple[Mission, ...]:
    """Pick this round's missions and cards (fresh every round)."""

    ladder = LEVELS[max(0, min(MAX_LEVEL, int(level)))]
    core = [slot for slot in CORE_SLOTS if slot_available(season, slot)]
    extra = [slot for slot in EXTRA_SLOTS if slot_available(season, slot)]
    rng.shuffle(extra)
    missions: list[Mission] = []
    for slot in (core + extra)[: ladder.missions]:
        answer = rng.choice(right_items(season, slot))
        wrong = list(wrong_items(season, slot))
        rng.shuffle(wrong)
        options = [answer.item_id, *(item.item_id for item in wrong[: max(1, ladder.options - 1)])]
        rng.shuffle(options)
        missions.append(Mission(slot, tuple(options), answer.item_id))
    return tuple(missions)


@dataclass(frozen=True, slots=True)
class SceneKit:
    """The season's landscape: shared backdrop layers (sky built from ``sky``)."""

    sky: str
    layers: tuple[str, ...] = field(default_factory=tuple)


SCENES: Final[dict[Season, SceneKit]] = {
    # Spring and summer share the meadow; the meadow foreground (an apple
    # tree) is left out so it never contradicts the child's own tree.
    Season.SPRING: SceneKit("bg.meadow_day.sky", ("bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground")),
    Season.SUMMER: SceneKit("bg.sky_clouds.sky", ("bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground")),
    Season.AUTUMN: SceneKit(
        "bg.woodland_autumn.sky",
        ("bg.woodland_autumn.far", "bg.woodland_autumn.mid", "bg.woodland_autumn.ground", "bg.woodland_autumn.foreground"),
    ),
    Season.WINTER: SceneKit(
        "bg.woodland_snow.sky",
        ("bg.woodland_snow.far", "bg.woodland_snow.mid", "bg.woodland_snow.ground", "bg.woodland_snow.foreground"),
    ),
}

# The season picker shows one emblem per season (library art).
EMBLEMS: Final[dict[Season, ArtRef]] = {
    Season.SPRING: ArtRef.shared("prop.nature.flower"),
    Season.SUMMER: ArtRef.shared("prop.nature.sun"),
    Season.AUTUMN: ArtRef.shared("prop.nature.leaf_autumn"),
    Season.WINTER: ArtRef.shared("prop.nature.snowflake"),
}

# Banner pictures for each mission: what is being dressed (never an answer).
SLOT_ICONS: Final[dict[Slot, tuple[CardLayer, ...]]] = {
    Slot.TREE: (CardLayer(TRUNK),),
    Slot.SKY: (CardLayer(CLOUD),),
    Slot.GROUND: (CardLayer(ArtRef.shared("icon.hud.basket")),),
    Slot.ANIMAL: (CardLayer(ArtRef.shared("creature.woodland.squirrel", "peek")),),
    Slot.CLOTHES: (CardLayer(ArtRef.shared("character.tito", "happy")),),
}


__all__ = [
    "ALL",
    "ArtRef",
    "CORE_SLOTS",
    "CardLayer",
    "EMBLEMS",
    "EXTRA_SLOTS",
    "ITEMS",
    "ITEM_IDS",
    "Item",
    "LEVELS",
    "Level",
    "MAX_LEVEL",
    "Mission",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SCENES",
    "SEASONS",
    "SLOT_ICONS",
    "STORAGE_KEY",
    "SceneKit",
    "Season",
    "Slot",
    "TRUNK",
    "Weather",
    "plan_missions",
    "right_items",
    "slot_available",
    "wrong_items",
]
