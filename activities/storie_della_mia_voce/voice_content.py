"""Stories of My Voice — Story Cards catalogue (pure data).

The child picks a short picture story, puts its shuffled cards in order,
tells each card with their own voice and watches it back as a slideshow.
Every card is composed at runtime from the shared art library: a ``bg.*``
scene (flattened layers, cropped to a 4:3 card), canonical cast poses
(``character.<id>`` variants) and library props/creatures/FX. Nothing here is
Activity-private art, so the cards look like one family with the Shell.

Card geometry is authored in a 400x300 card space (``CARD_SPACE``): each
sprite is placed by its mid-bottom point and its height; the renderer scales
the whole composition once per requested card size.

``LEGACY_SCENES`` describes the four free scenes (forest/sea/sky/friends) of
the original version so stories saved before the Story Cards rework keep
loading, playing and sharing with real library art instead of colour blocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

# Cards are authored in this space and keep a 4:3 aspect everywhere.
CARD_SPACE: Final[tuple[int, int]] = (400, 300)
CARD_ASPECT: Final = CARD_SPACE[0] / CARD_SPACE[1]
# A card shows an 800x600 window of the 1024x600 scene layers.
SCENE_CROP_WIDTH: Final = 800

# Recording limits (per card; the platform WAV limit is 90 s).
MAX_RECORDING_SECONDS: Final = 30.0
MIN_RECORDING_SECONDS: Final = 0.4
COUNTDOWN_SECONDS: Final = 1.5
# Child work is never evicted: the shelf refuses new stories when full.
MAX_SAVED_STORIES: Final = 12
SHELF_PAGE_SIZE: Final = 6

HOST: Final = "leo"  # Leo (the owl who loves books) hosts the stories.

MEADOW: Final = ("bg.meadow_day.sky", "bg.meadow_day.far", "bg.meadow_day.mid", "bg.meadow_day.ground")
POND: Final = (
    "bg.woodland_pond.sky",
    "bg.woodland_pond.far",
    "bg.woodland_pond.mid",
    "bg.woodland_pond.ground",
    "bg.woodland_pond.foreground",
)
PLAYROOM: Final = ("bg.indoor_room.wall_playroom", "bg.indoor_room.floor_wood")
BATHROOM: Final = ("bg.indoor_room.wall_bathroom", "bg.indoor_room.floor_tile")
BEDROOM: Final = ("bg.indoor_room.wall_bedroom", "bg.indoor_room.floor_carpet")
SEA: Final = ("bg.sea_surface.sky", "bg.sea_surface.far", "bg.sea_surface.sea", "bg.sea_surface.foreground")
SKY: Final = ("bg.sky_clouds.sky", "bg.sky_clouds.far", "bg.sky_clouds.mid", "bg.sky_clouds.foreground")
AUTUMN: Final = (
    "bg.woodland_autumn.sky",
    "bg.woodland_autumn.far",
    "bg.woodland_autumn.mid",
    "bg.woodland_autumn.ground",
    "bg.woodland_autumn.foreground",
)


@dataclass(frozen=True, slots=True)
class Sprite:
    """One library picture on a card: mid-bottom at (x, y), ``height`` tall.

    Coordinates are in ``CARD_SPACE``. ``angle`` (degrees) is applied once
    when the card is composed, never per frame.
    """

    asset_id: str
    x: int
    y: int
    height: int
    variant: str = "default"
    angle: int = 0


@dataclass(frozen=True, slots=True)
class CardArt:
    """A card picture: scene layers, crop offset, sprites and optional weather."""

    layers: tuple[str, ...]
    sprites: tuple[Sprite, ...]
    crop_x: int = 112
    rain: bool = False


@dataclass(frozen=True, slots=True)
class StoryCard:
    card_id: str
    art: CardArt


@dataclass(frozen=True, slots=True)
class StoryTemplate:
    """A short picture story; ``cards`` is the correct telling order."""

    story_id: str
    title_key: str
    character: str
    cards: tuple[StoryCard, ...]
    pickable: bool = True

    @property
    def card_ids(self) -> tuple[str, ...]:
        return tuple(card.card_id for card in self.cards)

    def card(self, card_id: str) -> StoryCard | None:
        return next((card for card in self.cards if card.card_id == card_id), None)


def _cast(character: str, variant: str, x: int, y: int, height: int) -> Sprite:
    return Sprite(f"character.{character}", x, y, height, variant=variant)


# -- the stories -------------------------------------------------------------

MOMO_SEED: Final = StoryTemplate(
    "momo_seed",
    "story.momo_seed",
    "momo",
    (
        StoryCard("momo_seed_1", CardArt(MEADOW, (
            _cast("momo", "pose_point", 140, 274, 150),
            Sprite("prop.food.seed", 272, 268, 58),
        ), crop_x=224)),
        StoryCard("momo_seed_2", CardArt(MEADOW, (
            _cast("momo", "happy", 124, 274, 140),
            Sprite("prop.food.seed", 286, 268, 50),
            Sprite("prop.nature.cloud", 288, 132, 92),
            Sprite("prop.nature.raindrop", 250, 186, 34),
            Sprite("prop.nature.raindrop", 290, 214, 34),
            Sprite("prop.nature.raindrop", 328, 184, 34),
        ), crop_x=224)),
        StoryCard("momo_seed_3", CardArt(MEADOW, (
            _cast("momo", "pose_cheer", 124, 274, 150),
            Sprite("prop.nature.flower", 286, 272, 156),
            Sprite("creature.woodland.butterfly", 352, 118, 52),
        ), crop_x=224)),
    ),
)

TITO_PICNIC: Final = StoryTemplate(
    "tito_picnic",
    "story.tito_picnic",
    "tito",
    (
        StoryCard("tito_picnic_1", CardArt(MEADOW, (
            _cast("tito", "pose_wave", 112, 276, 142),
            Sprite("prop.food.apple", 236, 266, 48),
            Sprite("prop.vocab.cake", 296, 270, 74),
            Sprite("prop.food.strawberry", 354, 266, 42),
        ), crop_x=224)),
        StoryCard("tito_picnic_2", CardArt(MEADOW, (
            _cast("tito", "surprised", 108, 276, 134),
            Sprite("prop.food.apple", 222, 266, 46),
            Sprite("prop.vocab.cake", 280, 270, 72),
            Sprite("prop.vocab.ant", 336, 276, 34),
            Sprite("prop.vocab.ant", 366, 282, 34),
            Sprite("prop.vocab.ant", 394, 274, 34),
        ), crop_x=224)),
        StoryCard("tito_picnic_3", CardArt(MEADOW, (
            _cast("tito", "pose_cheer", 104, 276, 140),
            Sprite("prop.vocab.ant", 216, 280, 32),
            Sprite("prop.vocab.cake", 274, 270, 72),
            Sprite("prop.vocab.ant", 330, 280, 32),
            Sprite("prop.vocab.ant", 360, 274, 32),
            Sprite("fx.heart_pop", 280, 180, 70),
        ), crop_x=224)),
    ),
)

LEO_RAIN: Final = StoryTemplate(
    "leo_rain",
    "story.leo_rain",
    "leo",
    (
        StoryCard("leo_rain_1", CardArt(POND, (
            _cast("leo", "pose_play", 88, 288, 142),
            Sprite("prop.everyday.ball", 362, 292, 46),
        ), crop_x=60)),
        StoryCard("leo_rain_2", CardArt(POND, (
            Sprite("prop.nature.cloud", 120, 78, 70),
            Sprite("prop.nature.cloud", 300, 64, 84),
            _cast("leo", "sad", 88, 288, 134),
            Sprite("prop.everyday.ball", 362, 292, 46),
        ), crop_x=60, rain=True)),
        StoryCard("leo_rain_3", CardArt(POND, (
            Sprite("prop.nature.cloud", 300, 64, 84),
            Sprite("prop.vocab.umbrella", 112, 240, 168),
            _cast("leo", "happy", 104, 290, 124),
        ), crop_x=60, rain=True)),
        StoryCard("leo_rain_4", CardArt(POND, (
            Sprite("prop.nature.rainbow", 236, 150, 112),
            Sprite("prop.nature.sun", 356, 92, 74),
            _cast("leo", "pose_cheer", 88, 288, 142),
            Sprite("creature.woodland.duck", 250, 262, 46),
        ), crop_x=60)),
    ),
)

LILLI_BEDTIME: Final = StoryTemplate(
    "lilli_bedtime",
    "story.lilli_bedtime",
    "lilli",
    (
        StoryCard("lilli_bedtime_1", CardArt(PLAYROOM, (
            _cast("lilli", "pose_play", 150, 284, 150),
            Sprite("prop.everyday.ball", 284, 282, 52),
            Sprite("prop.everyday.block", 346, 284, 44),
        ))),
        StoryCard("lilli_bedtime_2", CardArt(BATHROOM, (
            _cast("lilli", "happy", 140, 284, 146),
            Sprite("prop.vocab.tooth", 270, 176, 70),
            Sprite("fx.sparkle", 316, 140, 54),
            Sprite("prop.vocab.soap", 306, 284, 52),
        ))),
        StoryCard("lilli_bedtime_3", CardArt(BEDROOM, (
            _cast("lilli", "happy", 200, 284, 140),
            Sprite("prop.everyday.book", 300, 262, 74),
            Sprite("prop.vocab.lamp", 366, 284, 96),
        ), crop_x=0)),
        StoryCard("lilli_bedtime_4", CardArt(BEDROOM, (
            Sprite("prop.vocab.moon", 270, 96, 64),
            Sprite("prop.vocab.bed", 240, 292, 196),
            _cast("lilli", "sleepy", 214, 238, 116),
        ), crop_x=0)),
    ),
)

DANI_TOWER: Final = StoryTemplate(
    "dani_tower",
    "story.dani_tower",
    "dani",
    (
        StoryCard("dani_tower_1", CardArt(PLAYROOM, (
            _cast("dani", "pose_point", 116, 284, 142),
            Sprite("prop.blocks.square", 284, 284, 56),
        ))),
        StoryCard("dani_tower_2", CardArt(PLAYROOM, (
            _cast("dani", "pose_play", 112, 284, 142),
            Sprite("prop.blocks.square", 284, 284, 56),
            Sprite("prop.blocks.square", 284, 230, 56),
            Sprite("prop.blocks.triangle", 284, 176, 50),
        ))),
        StoryCard("dani_tower_3", CardArt(PLAYROOM, (
            _cast("dani", "surprised", 108, 284, 136),
            Sprite("prop.blocks.square", 252, 286, 52, angle=18),
            Sprite("prop.blocks.square", 334, 288, 52, angle=-32),
            Sprite("prop.blocks.triangle", 292, 268, 46, angle=74),
            Sprite("fx.dust_puff", 296, 250, 80),
        ))),
        StoryCard("dani_tower_4", CardArt(PLAYROOM, (
            _cast("dani", "pose_cheer", 100, 284, 142),
            Sprite("prop.blocks.arch", 284, 284, 52),
            Sprite("prop.blocks.square", 284, 234, 52),
            Sprite("prop.blocks.square", 284, 184, 52),
            Sprite("prop.blocks.square", 284, 134, 52),
            Sprite("prop.blocks.triangle", 284, 86, 48),
            Sprite("fx.star_burst", 350, 96, 64),
        ))),
    ),
)

# Ordered from the gentlest (three cards) to four-card stories.
STORIES: Final[tuple[StoryTemplate, ...]] = (MOMO_SEED, TITO_PICNIC, LEO_RAIN, LILLI_BEDTIME, DANI_TOWER)

# The four free scenes of the original version (saves before the rework).
LEGACY_STORY_ID: Final = "legacy_scenes"
LEGACY_SCENES: Final = StoryTemplate(
    LEGACY_STORY_ID,
    "story.legacy",
    HOST,
    (
        StoryCard("forest", CardArt(AUTUMN, (Sprite("creature.woodland.squirrel", 270, 276, 90),))),
        StoryCard("sea", CardArt(SEA, (Sprite("prop.vocab.boat", 210, 250, 90),), crop_x=224)),
        StoryCard("sky", CardArt(SKY, (Sprite("prop.vocab.kite", 230, 170, 110),))),
        StoryCard("friends", CardArt(MEADOW, (
            _cast("lilli", "pose_wave", 110, 276, 120),
            _cast("tito", "pose_wave", 210, 280, 116),
            _cast("momo", "pose_wave", 310, 276, 120),
        ))),
    ),
    pickable=False,
)

ALL_TEMPLATES: Final[dict[str, StoryTemplate]] = {
    template.story_id: template for template in (*STORIES, LEGACY_SCENES)
}


def story_by_id(story_id: str) -> StoryTemplate | None:
    return ALL_TEMPLATES.get(story_id)


def is_valid_card_id(card_id: object) -> bool:
    """Card ids double as private file-name parts: short, lower-case, safe."""

    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    return (
        isinstance(card_id, str)
        and 0 < len(card_id) <= 40
        and card_id[0].isalpha()
        and all(character in allowed for character in card_id)
    )


__all__ = [
    "ALL_TEMPLATES",
    "CARD_ASPECT",
    "CARD_SPACE",
    "COUNTDOWN_SECONDS",
    "CardArt",
    "HOST",
    "LEGACY_SCENES",
    "LEGACY_STORY_ID",
    "MAX_RECORDING_SECONDS",
    "MAX_SAVED_STORIES",
    "MIN_RECORDING_SECONDS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SCENE_CROP_WIDTH",
    "SHELF_PAGE_SIZE",
    "STORIES",
    "Sprite",
    "StoryCard",
    "StoryTemplate",
    "is_valid_card_id",
    "story_by_id",
]
