"""Language-relative rhyme curricula for Festa delle Rime.

Each language owns its own words, because rhymes only exist inside one
language: Italian ``gatto/piatto`` and English ``cat/hat`` are separate lessons,
never translations of each other.

* ``RHYME_PAIRS_<LANG>`` — rhyme groups (2 or 3 words that rhyme).
* ``ALLITERATION_FAMILIES_<LANG>`` — words that share their first sound. The
  child is never asked about first sounds here (that skill belongs to Officina
  dei Suoni); the families supply *lures* for the "tricky rhyme" stage, where
  a non-rhyming word that starts like the target tests that the child listens
  to the end of the word.

Every word is spoken from an approved recording named after ``item_id`` and is
shown with a library picture (``picture`` is a shared ``prop.*`` visual ID, an
``activity:<name>`` picture under this package's ``assets/runtime``, or
``PICTURE_PENDING`` for staged words that still lack art).

IT/EN voice review: 2026-08-24_FESTA_DELLE_RIME_AUDIO_REVIEW.md (archived; see git history).
ES/FR: staged educational candidates, NOT voice-approved or manifest-enabled;
their word lists are kept for key/inventory parity and are not re-taught here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


PICTURE_PENDING: Final = "pending"


class RhymeMode(StrEnum):
    RHYME_MATCH = "rhyme_match"
    RHYME_ODD = "rhyme_odd"


@dataclass(frozen=True, slots=True)
class RhymeItem:
    """One spoken word: approved audio stem plus its library picture ID."""

    item_id: str
    picture: str

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if not self.picture:
            raise ValueError("picture must not be empty")

    @property
    def has_picture(self) -> bool:
        return self.picture != PICTURE_PENDING


# Italian rhyme groups
RHYME_PAIRS_IT: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("cane", "prop.vocab.dog"), RhymeItem("pane", "prop.vocab.bread")),
    (RhymeItem("gatto", "prop.vocab.cat"), RhymeItem("piatto", "activity:plate")),
    (RhymeItem("rana", "prop.vocab.frog"), RhymeItem("lana", "prop.vocab.yarn")),
    (RhymeItem("mela", "prop.food.apple"), RhymeItem("vela", "prop.vocab.boat")),
    (RhymeItem("fiore", "prop.nature.flower"), RhymeItem("cuore", "prop.shape.heart")),
    (RhymeItem("palla", "prop.everyday.ball"), RhymeItem("farfalla", "prop.vocab.butterfly")),
    (RhymeItem("torta", "prop.vocab.cake"), RhymeItem("porta", "prop.vocab.door")),
    (RhymeItem("naso", "activity:nose"), RhymeItem("vaso", "prop.vocab.vase")),
)

# Italian same-first-sound families (lures for the tricky-rhyme stage)
ALLITERATION_FAMILIES_IT: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("mela", "prop.food.apple"), RhymeItem("mano", "prop.vocab.hand")),
    (RhymeItem("pane", "prop.vocab.bread"), RhymeItem("pera", "prop.vocab.pear"), RhymeItem("palla", "prop.everyday.ball")),
    (RhymeItem("lana", "prop.vocab.yarn"), RhymeItem("luna", "prop.vocab.moon"), RhymeItem("luce", "prop.vocab.lamp")),
    (RhymeItem("fiore", "prop.nature.flower"), RhymeItem("foglia", "prop.everyday.leaf"), RhymeItem("farfalla", "prop.vocab.butterfly")),
    (RhymeItem("torta", "prop.vocab.cake"), RhymeItem("topo", "prop.vocab.mouse"), RhymeItem("tenda", "prop.vocab.tent")),
    (RhymeItem("sole", "prop.nature.sun"), RhymeItem("sasso", "prop.everyday.stone"), RhymeItem("sedia", "prop.vocab.chair")),
)

# English rhyme groups
RHYME_PAIRS_EN: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("cat", "prop.vocab.cat"), RhymeItem("hat", "prop.vocab.hat")),
    (RhymeItem("moon", "prop.vocab.moon"), RhymeItem("spoon", "prop.everyday.spoon")),
    (RhymeItem("cake", "prop.vocab.cake"), RhymeItem("snake", "prop.vocab.snake")),
    (RhymeItem("log", "prop.vocab.log"), RhymeItem("frog", "prop.vocab.frog")),
    (RhymeItem("bear", "prop.vocab.bear"), RhymeItem("chair", "prop.vocab.chair"), RhymeItem("pear", "prop.vocab.pear")),
    (RhymeItem("boat", "prop.vocab.boat"), RhymeItem("goat", "prop.vocab.goat")),
    (RhymeItem("star", "prop.vocab.star"), RhymeItem("car", "prop.vocab.car")),
    (RhymeItem("mouse", "prop.vocab.mouse"), RhymeItem("house", "prop.vocab.house")),
    (RhymeItem("fan", "activity:fan"), RhymeItem("pan", "prop.vocab.pan")),
)

# English same-first-sound families (lures for the tricky-rhyme stage)
ALLITERATION_FAMILIES_EN: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("moon", "prop.vocab.moon"), RhymeItem("map", "prop.vocab.map"), RhymeItem("mouse", "prop.vocab.mouse")),
    (RhymeItem("pig", "prop.vocab.pig"), RhymeItem("pan", "prop.vocab.pan"), RhymeItem("pear", "prop.vocab.pear")),
    (RhymeItem("log", "prop.vocab.log"), RhymeItem("leaf", "prop.everyday.leaf"), RhymeItem("lamp", "prop.vocab.lamp")),
    (RhymeItem("frog", "prop.vocab.frog"), RhymeItem("fish", "prop.food.fish"), RhymeItem("fan", "activity:fan")),
    (RhymeItem("top", "prop.vocab.top"), RhymeItem("tent", "prop.vocab.tent"), RhymeItem("turtle", "prop.vocab.turtle")),
    (RhymeItem("star", "prop.vocab.star"), RhymeItem("sun", "prop.nature.sun"), RhymeItem("sock", "prop.everyday.sock")),
)


# Spanish/French curriculum candidates (staged). Native phonology and picture
# semantics need human educational review; voice assets are NOT approved.
# Words without library art carry PICTURE_PENDING.
RHYME_PAIRS_ES: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("gato", "prop.vocab.cat"), RhymeItem("pato", "creature.woodland.duck")),
    (RhymeItem("mesa", "pending"), RhymeItem("fresa", "prop.food.strawberry")),
    (RhymeItem("flor", "prop.nature.flower"), RhymeItem("color", "pending")),
    (RhymeItem("camino", "pending"), RhymeItem("pepino", "pending")),
    (RhymeItem("sombrero", "prop.vocab.hat"), RhymeItem("cartero", "pending")),
    (RhymeItem("estrella", "prop.vocab.star"), RhymeItem("botella", "pending")),
    (RhymeItem("fruta", "prop.food.apple"), RhymeItem("ruta", "pending")),
    (RhymeItem("luna", "prop.vocab.moon"), RhymeItem("cuna", "pending")),
)

ALLITERATION_FAMILIES_ES: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("mano", "prop.vocab.hand"), RhymeItem("mesa", "pending"), RhymeItem("mono", "pending")),
    (RhymeItem("pato", "creature.woodland.duck"), RhymeItem("pera", "prop.vocab.pear"), RhymeItem("pelota", "prop.everyday.ball")),
    (RhymeItem("luna", "prop.vocab.moon"), RhymeItem("libro", "prop.everyday.book"), RhymeItem("limon", "pending")),
    (RhymeItem("flor", "prop.nature.flower"), RhymeItem("foca", "pending"), RhymeItem("fuego", "pending")),
    (RhymeItem("toro", "pending"), RhymeItem("tomate", "pending"), RhymeItem("tren", "prop.vocab.train")),
    (RhymeItem("sol", "prop.nature.sun"), RhymeItem("sapo", "prop.vocab.frog"), RhymeItem("silla", "prop.vocab.chair")),
)

RHYME_PAIRS_FR: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("chat", "prop.vocab.cat"), RhymeItem("rat", "pending")),
    (RhymeItem("bateau", "prop.vocab.boat"), RhymeItem("chapeau", "prop.vocab.hat")),
    (RhymeItem("lapin", "pending"), RhymeItem("sapin", "pending")),
    (RhymeItem("maison", "prop.vocab.house"), RhymeItem("poisson", "prop.food.fish")),
    (RhymeItem("fleur", "prop.nature.flower"), RhymeItem("peur", "pending")),
    (RhymeItem("poule", "prop.vocab.hen"), RhymeItem("boule", "prop.everyday.ball")),
    (RhymeItem("robe", "pending"), RhymeItem("globe", "pending")),
    (RhymeItem("soleil", "prop.nature.sun"), RhymeItem("oreille", "pending")),
)

ALLITERATION_FAMILIES_FR: Final[tuple[tuple[RhymeItem, ...], ...]] = (
    (RhymeItem("maman", "pending"), RhymeItem("maison", "prop.vocab.house"), RhymeItem("mouton", "pending")),
    (RhymeItem("pomme", "prop.food.apple"), RhymeItem("poule", "prop.vocab.hen"), RhymeItem("poisson", "prop.food.fish")),
    (RhymeItem("lune", "prop.vocab.moon"), RhymeItem("lapin", "pending"), RhymeItem("livre", "prop.everyday.book")),
    (RhymeItem("fleur", "prop.nature.flower"), RhymeItem("foret", "pending"), RhymeItem("fourmi", "pending")),
    (RhymeItem("tasse", "prop.everyday.cup"), RhymeItem("tortue", "prop.vocab.turtle"), RhymeItem("tomate", "pending")),
    (RhymeItem("soleil", "prop.nature.sun"), RhymeItem("souris", "prop.vocab.mouse"), RhymeItem("savon", "pending")),
)


RhymeGroups = tuple[tuple[RhymeItem, ...], ...]

_CORPORA: Final[dict[str, tuple[RhymeGroups, RhymeGroups]]] = {
    "it": (RHYME_PAIRS_IT, ALLITERATION_FAMILIES_IT),
    "en": (RHYME_PAIRS_EN, ALLITERATION_FAMILIES_EN),
    "es": (RHYME_PAIRS_ES, ALLITERATION_FAMILIES_ES),
    "fr": (RHYME_PAIRS_FR, ALLITERATION_FAMILIES_FR),
}


def get_corpus(locale: str) -> tuple[RhymeGroups, RhymeGroups]:
    """Return ``(rhyme groups, first-sound families)`` for one lesson language.

    Locale packs are staged independently of the Activity manifest and speech.
    A caller requesting an unknown curriculum must fail rather than silently
    use an incorrect first-language rhyme.
    """
    language = locale.replace("_", "-").split("-", 1)[0].lower()
    try:
        return _CORPORA[language]
    except KeyError as exc:
        raise ValueError(f"unsupported rhyme curriculum language: {locale}") from exc
