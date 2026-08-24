"""Bilingual rhyme and alliteration corpus for Festa delle Rime.

Contains only reviewed vocabulary from docs/reviews/2026-08-24_FESTA_DELLE_RIME_AUDIO_REVIEW.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class RhymeMode(StrEnum):
    RHYME_MATCH = "rhyme_match"
    RHYME_ODD = "rhyme_odd"
    ALLITERATION = "alliteration"


@dataclass(frozen=True, slots=True)
class RhymeItem:
    """Semantic word item with picture symbol and audio key."""

    item_id: str
    symbol: str

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if not self.symbol:
            raise ValueError("symbol must not be empty")


# Italian Rhyme Pairs
RHYME_PAIRS_IT: Final[tuple[tuple[RhymeItem, RhymeItem], ...]] = (
    (RhymeItem("cane", "🐶"), RhymeItem("pane", "🥖")),
    (RhymeItem("gatto", "🐱"), RhymeItem("piatto", "🍽️")),
    (RhymeItem("rana", "🐸"), RhymeItem("lana", "🧶")),
    (RhymeItem("mela", "🍎"), RhymeItem("vela", "⛵")),
    (RhymeItem("fiore", "🌸"), RhymeItem("cuore", "❤️")),
    (RhymeItem("palla", "⚽"), RhymeItem("farfalla", "🦋")),
    (RhymeItem("torta", "🎂"), RhymeItem("porta", "🚪")),
    (RhymeItem("naso", "👃"), RhymeItem("vaso", "🏺")),
)

# Italian Alliteration Families
ALLITERATION_FAMILIES_IT: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("mela", "🍎"), RhymeItem("mare", "🌊"), RhymeItem("mano", "🖐️")),
    (RhymeItem("pane", "🥖"), RhymeItem("pera", "🍐"), RhymeItem("palla", "⚽")),
    (RhymeItem("lana", "🧶"), RhymeItem("luna", "🌙"), RhymeItem("luce", "💡")),
    (RhymeItem("fiore", "🌸"), RhymeItem("fata", "🧚"), RhymeItem("foglia", "🍃")),
    (RhymeItem("torta", "🎂"), RhymeItem("topo", "🐭"), RhymeItem("tenda", "⛺")),
    (RhymeItem("sole", "☀️"), RhymeItem("sasso", "🪨"), RhymeItem("sedia", "🪑")),
)

# English Rhyme Pairs
RHYME_PAIRS_EN: Final[tuple[tuple[RhymeItem, RhymeItem], ...]] = (
    (RhymeItem("cat", "🐱"), RhymeItem("hat", "🎩")),
    (RhymeItem("moon", "🌙"), RhymeItem("spoon", "🥄")),
    (RhymeItem("cake", "🎂"), RhymeItem("snake", "🐍")),
    (RhymeItem("log", "🪵"), RhymeItem("frog", "🐸")),
    (RhymeItem("bear", "🐻"), RhymeItem("chair", "🪑")),
    (RhymeItem("boat", "⛵"), RhymeItem("goat", "🐐")),
    (RhymeItem("star", "⭐"), RhymeItem("car", "🚗")),
    (RhymeItem("mouse", "🐭"), RhymeItem("house", "🏠")),
)

# English Alliteration Families
ALLITERATION_FAMILIES_EN: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("moon", "🌙"), RhymeItem("map", "🗺️"), RhymeItem("mouse", "🐭")),
    (RhymeItem("pig", "🐷"), RhymeItem("pan", "🍳"), RhymeItem("pear", "🍐")),
    (RhymeItem("log", "🪵"), RhymeItem("leaf", "🍃"), RhymeItem("lamp", "💡")),
    (RhymeItem("frog", "🐸"), RhymeItem("fish", "🐟"), RhymeItem("fan", "🪭")),
    (RhymeItem("top", "🪀"), RhymeItem("tent", "⛺"), RhymeItem("turtle", "🐢")),
    (RhymeItem("star", "⭐"), RhymeItem("sun", "☀️"), RhymeItem("sock", "🧦")),
)


def get_corpus(locale: str) -> tuple[tuple[tuple[RhymeItem, RhymeItem], ...], tuple[tuple[RhymeItem, ...], ...]]:
    """Return (rhyme_pairs, alliteration_families) for the requested locale."""
    if locale == "en":
        return RHYME_PAIRS_EN, ALLITERATION_FAMILIES_EN
    return RHYME_PAIRS_IT, ALLITERATION_FAMILIES_IT
