"""Narrative sequence seeds and card content for Tre Carte Una Storia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class StoryCard:
    card_id: str
    symbol: str
    accent_color: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class StorySeed:
    seed_id: str
    title_key: str
    cards: tuple[StoryCard, StoryCard, StoryCard]
    caption_keys: tuple[str, str, str]


STORY_SEEDS: Final[tuple[StorySeed, ...]] = (
    StorySeed(
        seed_id="drawing",
        title_key="story.drawing.title",
        cards=(
            StoryCard("drawing_1", "🖍️", (254, 205, 211)),
            StoryCard("drawing_2", "🖼️", (254, 240, 138)),
            StoryCard("drawing_3", "🎁", (187, 247, 208)),
        ),
        caption_keys=("story.drawing.c1", "story.drawing.c2", "story.drawing.c3"),
    ),
    StorySeed(
        seed_id="rain",
        title_key="story.rain.title",
        cards=(
            StoryCard("rain_1", "🌧️", (219, 234, 254)),
            StoryCard("rain_2", "🌂", (254, 205, 211)),
            StoryCard("rain_3", "🥾", (254, 240, 138)),
        ),
        caption_keys=("story.rain.c1", "story.rain.c2", "story.rain.c3"),
    ),
    StorySeed(
        seed_id="kite",
        title_key="story.kite.title",
        cards=(
            StoryCard("kite_1", "🧵", (254, 249, 195)),
            StoryCard("kite_2", "🪢", (233, 213, 255)),
            StoryCard("kite_3", "🪁", (187, 247, 208)),
        ),
        caption_keys=("story.kite.c1", "story.kite.c2", "story.kite.c3"),
    ),
    StorySeed(
        seed_id="picnic",
        title_key="story.picnic.title",
        cards=(
            StoryCard("picnic_1", "🧺", (254, 240, 138)),
            StoryCard("picnic_2", "🌼", (187, 247, 208)),
            StoryCard("picnic_3", "🥪", (254, 205, 211)),
        ),
        caption_keys=("story.picnic.c1", "story.picnic.c2", "story.picnic.c3"),
    ),
    StorySeed(
        seed_id="postcard",
        title_key="story.postcard.title",
        cards=(
            StoryCard("postcard_1", "✍️", (254, 249, 195)),
            StoryCard("postcard_2", "✉️", (219, 234, 254)),
            StoryCard("postcard_3", "💌", (254, 205, 211)),
        ),
        caption_keys=("story.postcard.c1", "story.postcard.c2", "story.postcard.c3"),
    ),
    StorySeed(
        seed_id="tower",
        title_key="story.tower.title",
        cards=(
            StoryCard("tower_1", "🧱", (254, 205, 211)),
            StoryCard("tower_2", "🏰", (254, 240, 138)),
            StoryCard("tower_3", "🚩", (187, 247, 208)),
        ),
        caption_keys=("story.tower.c1", "story.tower.c2", "story.tower.c3"),
    ),
    StorySeed(
        seed_id="cloud",
        title_key="story.cloud.title",
        cards=(
            StoryCard("cloud_1", "☁️", (219, 234, 254)),
            StoryCard("cloud_2", "🧣", (254, 205, 211)),
            StoryCard("cloud_3", "☀️", (254, 240, 138)),
        ),
        caption_keys=("story.cloud.c1", "story.cloud.c2", "story.cloud.c3"),
    ),
    StorySeed(
        seed_id="spill",
        title_key="story.spill.title",
        cards=(
            StoryCard("spill_1", "💧", (219, 234, 254)),
            StoryCard("spill_2", "🧽", (254, 240, 138)),
            StoryCard("spill_3", "✨", (254, 249, 195)),
        ),
        caption_keys=("story.spill.c1", "story.spill.c2", "story.spill.c3"),
    ),
)

STORY_SEEDS_BY_ID: Final[dict[str, StorySeed]] = {s.seed_id: s for s in STORY_SEEDS}
VALID_SEED_IDS: Final[frozenset[str]] = frozenset(STORY_SEEDS_BY_ID.keys())
