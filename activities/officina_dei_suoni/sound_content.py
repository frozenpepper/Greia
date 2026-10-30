"""Language-relative sound-and-word curricula for Officina dei Suoni.

Officina is the *phonemic* rung of the literacy ladder: children hear a word's
first **sound** (never a letter name — Leo's Letter Garden owns names), match
that sound to its letter, and finally build short words from their sounds.

* ``SOUND_UNITS_<LANG>`` — one isolated phoneme clip (``audio_id``, e.g.
  ``sound_m`` = /m/), its capital letter and three words that start with it.
  Every word is spoken from an approved recording named after ``word_id`` and
  is shown with a library picture: a shared ``prop.*`` visual ID, an
  ``activity:<name>`` picture under this package's ``assets/runtime``, or
  ``PICTURE_PENDING`` where no unambiguous picture exists yet (those words are
  never used as a target in a language that has enough pictured words).
* ``BUILD_SLOTS_<LANG>`` — curated build-a-word lessons: the letter positions
  whose sound the child supplies (the first sound plus one later consonant
  whose isolated phoneme clip exists). Spelling-to-sound is not 1:1 (Italian
  ``luce`` has /tʃ/, French final consonants are silent), so positions are
  reviewed per word, never derived from spelling.
* ``CONFUSABLE_PICTURES`` — picture pairs a child could name with the other
  word's first sound (a rose is also "a flower"); they never share a task.

IT/EN review: 2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md (archived; see git history).
ES/FR are staged curricula; their phoneme and word audio is not approved and
they have no build lessons (the build stage falls back to the first sound).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Mapping


PICTURE_PENDING: Final = "pending"


class WorkshopMode(StrEnum):
    """The three stages of the one Sound Machine loop."""

    FIND_SOUND = "find_sound"          # stage 1: hear a sound, feed the picture that starts with it
    INITIAL_LETTER = "initial_letter"  # stage 2: hear a word, feed the letter of its first sound
    BUILD_WORD = "build_word"          # stage 3: hear a word, fill its first (and a later) sound slot


@dataclass(frozen=True, slots=True)
class WordItem:
    """One spoken word: approved audio stem, capital spelling and library picture."""

    word_id: str
    label: str
    picture: str
    initial_sound_id: str
    remainder: str

    def __post_init__(self) -> None:
        if not self.word_id:
            raise ValueError("word_id must not be empty")
        if not self.picture:
            raise ValueError("picture must not be empty")
        if not self.label or self.label[1:] != self.remainder:
            raise ValueError("label must be the initial letter followed by the remainder")

    @property
    def has_picture(self) -> bool:
        return self.picture != PICTURE_PENDING


@dataclass(frozen=True, slots=True)
class SoundUnit:
    """Phoneme unit with uppercase/lowercase graphemes and associated words."""

    phoneme_id: str
    grapheme_upper: str
    grapheme_lower: str
    audio_id: str
    words: tuple[WordItem, ...]

    def __post_init__(self) -> None:
        if not self.phoneme_id:
            raise ValueError("phoneme_id must not be empty")
        if not self.words:
            raise ValueError("words must not be empty")

    @property
    def pictured_words(self) -> tuple[WordItem, ...]:
        return tuple(word for word in self.words if word.has_picture)


# Italian Units
SOUND_UNITS_IT: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m",
        "M",
        "m",
        "sound_m",
        (
            WordItem("mela", "MELA", "prop.food.apple", "sound_m", "ELA"),
            WordItem("mare", "MARE", "activity:sea", "sound_m", "ARE"),
            WordItem("mano", "MANO", "prop.vocab.hand", "sound_m", "ANO"),
        ),
    ),
    SoundUnit(
        "sound_p",
        "P",
        "p",
        "sound_p",
        (
            WordItem("pane", "PANE", "prop.vocab.bread", "sound_p", "ANE"),
            WordItem("pera", "PERA", "prop.vocab.pear", "sound_p", "ERA"),
            WordItem("palla", "PALLA", "prop.everyday.ball", "sound_p", "ALLA"),
        ),
    ),
    SoundUnit(
        "sound_l",
        "L",
        "l",
        "sound_l",
        (
            WordItem("lana", "LANA", "prop.vocab.yarn", "sound_l", "ANA"),
            WordItem("luna", "LUNA", "prop.vocab.moon", "sound_l", "UNA"),
            WordItem("luce", "LUCE", "prop.vocab.lamp", "sound_l", "UCE"),
        ),
    ),
    SoundUnit(
        "sound_f",
        "F",
        "f",
        "sound_f",
        (
            WordItem("fiore", "FIORE", "prop.nature.flower", "sound_f", "IORE"),
            WordItem("fata", "FATA", "pending", "sound_f", "ATA"),
            WordItem("foglia", "FOGLIA", "prop.everyday.leaf", "sound_f", "OGLIA"),
        ),
    ),
    SoundUnit(
        "sound_t",
        "T",
        "t",
        "sound_t",
        (
            WordItem("torta", "TORTA", "prop.vocab.cake", "sound_t", "ORTA"),
            WordItem("topo", "TOPO", "prop.vocab.mouse", "sound_t", "OPO"),
            WordItem("tenda", "TENDA", "prop.vocab.tent", "sound_t", "ENDA"),
        ),
    ),
    SoundUnit(
        "sound_s",
        "S",
        "s",
        "sound_s",
        (
            WordItem("sole", "SOLE", "prop.nature.sun", "sound_s", "OLE"),
            WordItem("sasso", "SASSO", "prop.everyday.stone", "sound_s", "ASSO"),
            WordItem("sedia", "SEDIA", "prop.vocab.chair", "sound_s", "EDIA"),
        ),
    ),
    SoundUnit(
        "sound_r",
        "R",
        "r",
        "sound_r",
        (
            WordItem("rana", "RANA", "prop.vocab.frog", "sound_r", "ANA"),
            WordItem("rosa", "ROSA", "activity:rose", "sound_r", "OSA"),
            WordItem("ramo", "RAMO", "activity:branch", "sound_r", "AMO"),
        ),
    ),
    SoundUnit(
        "sound_c",
        "C",
        "c",
        "sound_c",
        (
            WordItem("cane", "CANE", "prop.vocab.dog", "sound_c", "ANE"),
            WordItem("casa", "CASA", "prop.vocab.house", "sound_c", "ASA"),
            WordItem("cuore", "CUORE", "prop.shape.heart", "sound_c", "UORE"),
        ),
    ),
)

# English Units
SOUND_UNITS_EN: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m",
        "M",
        "m",
        "sound_m",
        (
            WordItem("moon", "MOON", "prop.vocab.moon", "sound_m", "OON"),
            WordItem("map", "MAP", "prop.vocab.map", "sound_m", "AP"),
            WordItem("mouse", "MOUSE", "prop.vocab.mouse", "sound_m", "OUSE"),
        ),
    ),
    SoundUnit(
        "sound_p",
        "P",
        "p",
        "sound_p",
        (
            WordItem("pig", "PIG", "prop.vocab.pig", "sound_p", "IG"),
            WordItem("pan", "PAN", "prop.vocab.pan", "sound_p", "AN"),
            WordItem("pear", "PEAR", "prop.vocab.pear", "sound_p", "EAR"),
        ),
    ),
    SoundUnit(
        "sound_l",
        "L",
        "l",
        "sound_l",
        (
            WordItem("leaf", "LEAF", "prop.everyday.leaf", "sound_l", "EAF"),
            WordItem("lamp", "LAMP", "prop.vocab.lamp", "sound_l", "AMP"),
            WordItem("log", "LOG", "prop.vocab.log", "sound_l", "OG"),
        ),
    ),
    SoundUnit(
        "sound_f",
        "F",
        "f",
        "sound_f",
        (
            WordItem("fish", "FISH", "prop.food.fish", "sound_f", "ISH"),
            WordItem("fan", "FAN", "activity:fan", "sound_f", "AN"),
            WordItem("fox", "FOX", "activity:fox", "sound_f", "OX"),
        ),
    ),
    SoundUnit(
        "sound_t",
        "T",
        "t",
        "sound_t",
        (
            WordItem("top", "TOP", "prop.vocab.top", "sound_t", "OP"),
            WordItem("tent", "TENT", "prop.vocab.tent", "sound_t", "ENT"),
            WordItem("turtle", "TURTLE", "prop.vocab.turtle", "sound_t", "URTLE"),
        ),
    ),
    SoundUnit(
        "sound_s",
        "S",
        "s",
        "sound_s",
        (
            WordItem("sun", "SUN", "prop.nature.sun", "sound_s", "UN"),
            WordItem("sock", "SOCK", "prop.everyday.sock", "sound_s", "OCK"),
            WordItem("star", "STAR", "prop.vocab.star", "sound_s", "TAR"),
        ),
    ),
    SoundUnit(
        "sound_b",
        "B",
        "b",
        "sound_b",
        (
            WordItem("bear", "BEAR", "prop.vocab.bear", "sound_b", "EAR"),
            WordItem("boat", "BOAT", "prop.vocab.boat", "sound_b", "OAT"),
            WordItem("book", "BOOK", "prop.everyday.book", "sound_b", "OOK"),
        ),
    ),
    SoundUnit(
        "sound_c",
        "C",
        "c",
        "sound_c",
        (
            WordItem("cat", "CAT", "prop.vocab.cat", "sound_c", "AT"),
            WordItem("car", "CAR", "prop.vocab.car", "sound_c", "AR"),
            WordItem("cake", "CAKE", "prop.vocab.cake", "sound_c", "AKE"),
        ),
    ),
)



# Spanish/French phoneme-word candidates, not yet certified by native
# educational reviewers or paired with approved isolated phoneme WAVs.
SOUND_UNITS_ES: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m", "M", "m", "sound_m",
        (
            WordItem("mano", "MANO", "prop.vocab.hand", "sound_m", "ANO"),
            WordItem("mesa", "MESA", "pending", "sound_m", "ESA"),
            WordItem("mono", "MONO", "pending", "sound_m", "ONO"),
        ),
    ),
    SoundUnit(
        "sound_p", "P", "p", "sound_p",
        (
            WordItem("pato", "PATO", "prop.everyday.duck", "sound_p", "ATO"),
            WordItem("pan", "PAN", "prop.vocab.bread", "sound_p", "AN"),
            WordItem("pera", "PERA", "prop.vocab.pear", "sound_p", "ERA"),
        ),
    ),
    SoundUnit(
        "sound_l", "L", "l", "sound_l",
        (
            WordItem("luna", "LUNA", "prop.vocab.moon", "sound_l", "UNA"),
            WordItem("lobo", "LOBO", "pending", "sound_l", "OBO"),
            WordItem("lapiz", "LÁPIZ", "prop.everyday.pencil", "sound_l", "ÁPIZ"),
        ),
    ),
    SoundUnit(
        "sound_f", "F", "f", "sound_f",
        (
            WordItem("flor", "FLOR", "prop.nature.flower", "sound_f", "LOR"),
            WordItem("foca", "FOCA", "pending", "sound_f", "OCA"),
            WordItem("fuego", "FUEGO", "pending", "sound_f", "UEGO"),
        ),
    ),
    SoundUnit(
        "sound_t", "T", "t", "sound_t",
        (
            WordItem("tren", "TREN", "prop.vocab.train", "sound_t", "REN"),
            WordItem("toro", "TORO", "pending", "sound_t", "ORO"),
            WordItem("tomate", "TOMATE", "pending", "sound_t", "OMATE"),
        ),
    ),
    SoundUnit(
        "sound_s", "S", "s", "sound_s",
        (
            WordItem("sol", "SOL", "prop.nature.sun", "sound_s", "OL"),
            WordItem("sapo", "SAPO", "prop.vocab.frog", "sound_s", "APO"),
            WordItem("silla", "SILLA", "prop.vocab.chair", "sound_s", "ILLA"),
        ),
    ),
    SoundUnit(
        "sound_b", "B", "b", "sound_b",
        (
            WordItem("barco", "BARCO", "prop.vocab.boat", "sound_b", "ARCO"),
            WordItem("bola", "BOLA", "prop.everyday.ball", "sound_b", "OLA"),
            WordItem("burro", "BURRO", "pending", "sound_b", "URRO"),
        ),
    ),
    SoundUnit(
        "sound_n", "N", "n", "sound_n",
        (
            WordItem("nube", "NUBE", "prop.nature.cloud", "sound_n", "UBE"),
            WordItem("nariz", "NARIZ", "pending", "sound_n", "ARIZ"),
            WordItem("nido", "NIDO", "prop.vocab.nest", "sound_n", "IDO"),
        ),
    ),
)

SOUND_UNITS_FR: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m", "M", "m", "sound_m",
        (
            WordItem("maman", "MAMAN", "pending", "sound_m", "AMAN"),
            WordItem("moto", "MOTO", "pending", "sound_m", "OTO"),
            WordItem("mouton", "MOUTON", "pending", "sound_m", "OUTON"),
        ),
    ),
    SoundUnit(
        "sound_p", "P", "p", "sound_p",
        (
            WordItem("pomme", "POMME", "prop.food.apple", "sound_p", "OMME"),
            WordItem("poule", "POULE", "prop.vocab.hen", "sound_p", "OULE"),
            WordItem("poisson", "POISSON", "prop.food.fish", "sound_p", "OISSON"),
        ),
    ),
    SoundUnit(
        "sound_l", "L", "l", "sound_l",
        (
            WordItem("lune", "LUNE", "prop.vocab.moon", "sound_l", "UNE"),
            WordItem("lion", "LION", "prop.vocab.lion", "sound_l", "ION"),
            WordItem("livre", "LIVRE", "prop.everyday.book", "sound_l", "IVRE"),
        ),
    ),
    SoundUnit(
        "sound_f", "F", "f", "sound_f",
        (
            WordItem("fleur", "FLEUR", "prop.nature.flower", "sound_f", "LEUR"),
            WordItem("fee", "FÉE", "pending", "sound_f", "ÉE"),
            WordItem("fourmi", "FOURMI", "pending", "sound_f", "OURMI"),
        ),
    ),
    SoundUnit(
        "sound_t", "T", "t", "sound_t",
        (
            WordItem("tasse", "TASSE", "prop.everyday.cup", "sound_t", "ASSE"),
            WordItem("tortue", "TORTUE", "prop.vocab.turtle", "sound_t", "ORTUE"),
            WordItem("tomate", "TOMATE", "pending", "sound_t", "OMATE"),
        ),
    ),
    SoundUnit(
        "sound_s", "S", "s", "sound_s",
        (
            WordItem("soleil", "SOLEIL", "prop.nature.sun", "sound_s", "OLEIL"),
            WordItem("sac", "SAC", "pending", "sound_s", "AC"),
            WordItem("souris", "SOURIS", "prop.vocab.mouse", "sound_s", "OURIS"),
        ),
    ),
    SoundUnit(
        "sound_b", "B", "b", "sound_b",
        (
            WordItem("bateau", "BATEAU", "prop.vocab.boat", "sound_b", "ATEAU"),
            WordItem("bebe", "BÉBÉ", "pending", "sound_b", "ÉBÉ"),
            WordItem("banane", "BANANE", "prop.food.banana", "sound_b", "ANANE"),
        ),
    ),
    SoundUnit(
        "sound_r", "R", "r", "sound_r",
        (
            WordItem("robot", "ROBOT", "pending", "sound_r", "OBOT"),
            WordItem("renard", "RENARD", "activity:fox", "sound_r", "ENARD"),
            WordItem("rose", "ROSE", "activity:rose", "sound_r", "OSE"),
        ),
    ),
)

# Build-a-word lessons: word_id -> letter positions the child fills, in order.
# Each position's letter is a unit grapheme whose isolated phoneme is the
# sound actually heard there (reviewed by hand; see module docstring).
BUILD_SLOTS_EN: Final[Mapping[str, tuple[int, ...]]] = {
    "map": (0, 2),
    "top": (0, 2),
    "cat": (0, 2),
    "leaf": (0, 3),
    "lamp": (0, 3),
    "tent": (0, 3),
    "boat": (0, 3),
}

BUILD_SLOTS_IT: Final[Mapping[str, tuple[int, ...]]] = {
    "mela": (0, 2),
    "mare": (0, 2),
    "pera": (0, 2),
    "topo": (0, 2),
    "sole": (0, 2),
    "ramo": (0, 2),
    "fiore": (0, 3),
    "cuore": (0, 3),
    "fata": (0, 2),
}

# Staged languages have no reviewed build lessons yet.
BUILD_SLOTS_ES: Final[Mapping[str, tuple[int, ...]]] = {}
BUILD_SLOTS_FR: Final[Mapping[str, tuple[int, ...]]] = {}

# Picture pairs that must never appear in the same task.
CONFUSABLE_PICTURES: Final[frozenset[frozenset[str]]] = frozenset(
    {
        frozenset({"activity:rose", "prop.nature.flower"}),
        frozenset({"activity:branch", "prop.everyday.leaf"}),
        frozenset({"activity:branch", "prop.vocab.log"}),
    }
)

_SOUND_UNITS_BY_LANGUAGE: Final = {
    "it": SOUND_UNITS_IT,
    "en": SOUND_UNITS_EN,
    "es": SOUND_UNITS_ES,
    "fr": SOUND_UNITS_FR,
}

_BUILD_SLOTS_BY_LANGUAGE: Final = {
    "it": BUILD_SLOTS_IT,
    "en": BUILD_SLOTS_EN,
    "es": BUILD_SLOTS_ES,
    "fr": BUILD_SLOTS_FR,
}


def _language(locale: str) -> str:
    return locale.replace("_", "-").split("-", 1)[0].lower()


def get_sound_units(locale: str) -> tuple[SoundUnit, ...]:
    """Resolve the actual phoneme curriculum, never a wrong-language fallback."""
    try:
        return _SOUND_UNITS_BY_LANGUAGE[_language(locale)]
    except KeyError as exc:
        raise ValueError(f"unsupported sound workshop curriculum language: {locale}") from exc


def get_build_slots(locale: str) -> Mapping[str, tuple[int, ...]]:
    """Reviewed build-a-word slot positions for one curriculum language."""
    try:
        return _BUILD_SLOTS_BY_LANGUAGE[_language(locale)]
    except KeyError as exc:
        raise ValueError(f"unsupported sound workshop curriculum language: {locale}") from exc


def pictures_conflict(first: str, second: str) -> bool:
    """True when two pictures could be named alike (same picture or a listed pair)."""
    return first == second or frozenset({first, second}) in CONFUSABLE_PICTURES
