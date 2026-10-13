"""Language-relative rhyme and alliteration curricula for Festa delle Rime.

IT/EN voice review: docs/reviews/2026-08-24_FESTA_DELLE_RIME_AUDIO_REVIEW.md.
ES/FR: staged educational candidates, NOT voice-approved or manifest-enabled.
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



# Spanish/French curriculum candidates. Native phonology and picture semantics
# need human educational review; voice assets are NOT yet recorded/approved.
RHYME_PAIRS_ES: Final[tuple[tuple[RhymeItem, RhymeItem], ...]] = (
    (RhymeItem("gato", "🐱"), RhymeItem("pato", "🦆")),
    (RhymeItem("mesa", "🍽️"), RhymeItem("fresa", "🍓")),
    (RhymeItem("flor", "🌸"), RhymeItem("color", "🎨")),
    (RhymeItem("camino", "🛤️"), RhymeItem("pepino", "🥒")),
    (RhymeItem("sombrero", "🎩"), RhymeItem("cartero", "📬")),
    (RhymeItem("estrella", "⭐"), RhymeItem("botella", "🍼")),
    (RhymeItem("fruta", "🍎"), RhymeItem("ruta", "🛣️")),
    (RhymeItem("luna", "🌙"), RhymeItem("cuna", "🛏️")),
)

ALLITERATION_FAMILIES_ES: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("mano", "🖐️"), RhymeItem("mesa", "🍽️"), RhymeItem("mono", "🐒")),
    (RhymeItem("pato", "🦆"), RhymeItem("pera", "🍐"), RhymeItem("pelota", "⚽")),
    (RhymeItem("luna", "🌙"), RhymeItem("libro", "📖"), RhymeItem("limon", "🍋")),
    (RhymeItem("flor", "🌸"), RhymeItem("foca", "🦭"), RhymeItem("fuego", "🔥")),
    (RhymeItem("toro", "🐂"), RhymeItem("tomate", "🍅"), RhymeItem("tren", "🚂")),
    (RhymeItem("sol", "☀️"), RhymeItem("sapo", "🐸"), RhymeItem("silla", "🪑")),
)

RHYME_PAIRS_FR: Final[tuple[tuple[RhymeItem, RhymeItem], ...]] = (
    (RhymeItem("chat", "🐱"), RhymeItem("rat", "🐭")),
    (RhymeItem("bateau", "⛵"), RhymeItem("chapeau", "🎩")),
    (RhymeItem("lapin", "🐰"), RhymeItem("sapin", "🌲")),
    (RhymeItem("maison", "🏠"), RhymeItem("poisson", "🐟")),
    (RhymeItem("fleur", "🌸"), RhymeItem("peur", "😨")),
    (RhymeItem("poule", "🐔"), RhymeItem("boule", "⚽")),
    (RhymeItem("robe", "👗"), RhymeItem("globe", "🌍")),
    (RhymeItem("soleil", "☀️"), RhymeItem("oreille", "👂")),
)

ALLITERATION_FAMILIES_FR: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("maman", "👩"), RhymeItem("maison", "🏠"), RhymeItem("mouton", "🐑")),
    (RhymeItem("pomme", "🍎"), RhymeItem("poule", "🐔"), RhymeItem("poisson", "🐟")),
    (RhymeItem("lune", "🌙"), RhymeItem("lapin", "🐰"), RhymeItem("livre", "📖")),
    (RhymeItem("fleur", "🌸"), RhymeItem("foret", "🌲"), RhymeItem("fourmi", "🐜")),
    (RhymeItem("tasse", "☕"), RhymeItem("tortue", "🐢"), RhymeItem("tomate", "🍅")),
    (RhymeItem("soleil", "☀️"), RhymeItem("souris", "🐭"), RhymeItem("savon", "🧼")),
)


_CORPORA: Final = {
    "it": (RHYME_PAIRS_IT, ALLITERATION_FAMILIES_IT),
    "en": (RHYME_PAIRS_EN, ALLITERATION_FAMILIES_EN),
    "es": (RHYME_PAIRS_ES, ALLITERATION_FAMILIES_ES),
    "fr": (RHYME_PAIRS_FR, ALLITERATION_FAMILIES_FR),
}


def get_corpus(locale: str) -> tuple[tuple[tuple[RhymeItem, RhymeItem], ...], tuple[tuple[RhymeItem, ...], ...]]:
    """Return only the requested lesson language; never teach Italian by accident.

    Locale packs are staged independently of the Activity manifest and speech.
    A caller requesting an unknown curriculum must fail rather than silently
    use an incorrect first-language rhyme or phoneme.
    """
    language = locale.replace("_", "-").split("-", 1)[0].lower()
    try:
        return _CORPORA[language]
    except KeyError as exc:
        raise ValueError(f"unsupported rhyme curriculum language: {locale}") from exc
