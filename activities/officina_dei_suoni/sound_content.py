"""Language-relative sound-and-word curricula for Officina dei Suoni.

IT/EN review: docs/reviews/2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md.
ES/FR are staged curricula; their phoneme and word audio is not approved.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class WorkshopMode(StrEnum):
    FIND_SOUND = "find_sound"        # L1: Hear isolated phoneme, pick 1 of 3 pictures
    INITIAL_LETTER = "initial_letter"  # L2: Hear word/picture, place initial letter tile into sound box
    BUILD_WORD = "build_word"        # L3: Place missing initial letter before remaining letters to build word


@dataclass(frozen=True, slots=True)
class WordItem:
    """Semantic word with picture token and grapheme breakdown."""

    word_id: str
    label: str
    symbol: str
    initial_sound_id: str
    remainder: str

    def __post_init__(self) -> None:
        if not self.word_id:
            raise ValueError("word_id must not be empty")
        if not self.symbol:
            raise ValueError("symbol must not be empty")


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


# Italian Units
SOUND_UNITS_IT: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m",
        "M",
        "m",
        "sound_m",
        (
            WordItem("mela", "MELA", "🍎", "sound_m", "ELA"),
            WordItem("mare", "MARE", "🌊", "sound_m", "ARE"),
            WordItem("mano", "MANO", "🖐️", "sound_m", "ANO"),
        ),
    ),
    SoundUnit(
        "sound_p",
        "P",
        "p",
        "sound_p",
        (
            WordItem("pane", "PANE", "🥖", "sound_p", "ANE"),
            WordItem("pera", "PERA", "🍐", "sound_p", "ERA"),
            WordItem("palla", "PALLA", "⚽", "sound_p", "ALLA"),
        ),
    ),
    SoundUnit(
        "sound_l",
        "L",
        "l",
        "sound_l",
        (
            WordItem("lana", "LANA", "🧶", "sound_l", "ANA"),
            WordItem("luna", "LUNA", "🌙", "sound_l", "UNA"),
            WordItem("luce", "LUCE", "💡", "sound_l", "UCE"),
        ),
    ),
    SoundUnit(
        "sound_f",
        "F",
        "f",
        "sound_f",
        (
            WordItem("fiore", "FIORE", "🌸", "sound_f", "IORE"),
            WordItem("fata", "FATA", "🧚", "sound_f", "ATA"),
            WordItem("foglia", "FOGLIA", "🍃", "sound_f", "OGLIA"),
        ),
    ),
    SoundUnit(
        "sound_t",
        "T",
        "t",
        "sound_t",
        (
            WordItem("torta", "TORTA", "🎂", "sound_t", "ORTA"),
            WordItem("topo", "TOPO", "🐭", "sound_t", "OPO"),
            WordItem("tenda", "TENDA", "⛺", "sound_t", "ENDA"),
        ),
    ),
    SoundUnit(
        "sound_s",
        "S",
        "s",
        "sound_s",
        (
            WordItem("sole", "SOLE", "☀️", "sound_s", "OLE"),
            WordItem("sasso", "SASSO", "🪨", "sound_s", "ASSO"),
            WordItem("sedia", "SEDIA", "🪑", "sound_s", "EDIA"),
        ),
    ),
    SoundUnit(
        "sound_r",
        "R",
        "r",
        "sound_r",
        (
            WordItem("rana", "RANA", "🐸", "sound_r", "ANA"),
            WordItem("rosa", "ROSA", "🌹", "sound_r", "OSA"),
            WordItem("ramo", "RAMO", "🌿", "sound_r", "AMO"),
        ),
    ),
    SoundUnit(
        "sound_c",
        "C",
        "c",
        "sound_c",
        (
            WordItem("cane", "CANE", "🐶", "sound_c", "ANE"),
            WordItem("casa", "CASA", "🏠", "sound_c", "ASA"),
            WordItem("cuore", "CUORE", "❤️", "sound_c", "UORE"),
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
            WordItem("moon", "MOON", "🌙", "sound_m", "OON"),
            WordItem("map", "MAP", "🗺️", "sound_m", "AP"),
            WordItem("mouse", "MOUSE", "🐭", "sound_m", "OUSE"),
        ),
    ),
    SoundUnit(
        "sound_p",
        "P",
        "p",
        "sound_p",
        (
            WordItem("pig", "PIG", "🐷", "sound_p", "IG"),
            WordItem("pan", "PAN", "🍳", "sound_p", "AN"),
            WordItem("pear", "PEAR", "🍐", "sound_p", "EAR"),
        ),
    ),
    SoundUnit(
        "sound_l",
        "L",
        "l",
        "sound_l",
        (
            WordItem("leaf", "LEAF", "🍃", "sound_l", "EAF"),
            WordItem("lamp", "LAMP", "💡", "sound_l", "AMP"),
            WordItem("log", "LOG", "🪵", "sound_l", "OG"),
        ),
    ),
    SoundUnit(
        "sound_f",
        "F",
        "f",
        "sound_f",
        (
            WordItem("fish", "FISH", "🐟", "sound_f", "ISH"),
            WordItem("fan", "FAN", "🪭", "sound_f", "AN"),
            WordItem("fox", "FOX", "🦊", "sound_f", "OX"),
        ),
    ),
    SoundUnit(
        "sound_t",
        "T",
        "t",
        "sound_t",
        (
            WordItem("top", "TOP", "🪀", "sound_t", "OP"),
            WordItem("tent", "TENT", "⛺", "sound_t", "ENT"),
            WordItem("turtle", "TURTLE", "🐢", "sound_t", "URTLE"),
        ),
    ),
    SoundUnit(
        "sound_s",
        "S",
        "s",
        "sound_s",
        (
            WordItem("sun", "SUN", "☀️", "sound_s", "UN"),
            WordItem("sock", "SOCK", "🧦", "sound_s", "OCK"),
            WordItem("star", "STAR", "⭐", "sound_s", "TAR"),
        ),
    ),
    SoundUnit(
        "sound_b",
        "B",
        "b",
        "sound_b",
        (
            WordItem("bear", "BEAR", "🐻", "sound_b", "EAR"),
            WordItem("boat", "BOAT", "⛵", "sound_b", "OAT"),
            WordItem("book", "BOOK", "📖", "sound_b", "OOK"),
        ),
    ),
    SoundUnit(
        "sound_c",
        "C",
        "c",
        "sound_c",
        (
            WordItem("cat", "CAT", "🐱", "sound_c", "AT"),
            WordItem("car", "CAR", "🚗", "sound_c", "AR"),
            WordItem("cake", "CAKE", "🎂", "sound_c", "AKE"),
        ),
    ),
)



# Spanish/French phoneme-word candidates, not yet certified by native
# educational reviewers or paired with approved isolated phoneme WAVs.
SOUND_UNITS_ES: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m", "M", "m", "sound_m",
        (
            WordItem("mano", "MANO", "🖐️", "sound_m", "ANO"),
            WordItem("mesa", "MESA", "🍽️", "sound_m", "ESA"),
            WordItem("mono", "MONO", "🐒", "sound_m", "ONO"),
        ),
    ),
    SoundUnit(
        "sound_p", "P", "p", "sound_p",
        (
            WordItem("pato", "PATO", "🦆", "sound_p", "ATO"),
            WordItem("pan", "PAN", "🥖", "sound_p", "AN"),
            WordItem("pera", "PERA", "🍐", "sound_p", "ERA"),
        ),
    ),
    SoundUnit(
        "sound_l", "L", "l", "sound_l",
        (
            WordItem("luna", "LUNA", "🌙", "sound_l", "UNA"),
            WordItem("lobo", "LOBO", "🐺", "sound_l", "OBO"),
            WordItem("lapiz", "LÁPIZ", "✏️", "sound_l", "ÁPIZ"),
        ),
    ),
    SoundUnit(
        "sound_f", "F", "f", "sound_f",
        (
            WordItem("flor", "FLOR", "🌸", "sound_f", "LOR"),
            WordItem("foca", "FOCA", "🦭", "sound_f", "OCA"),
            WordItem("fuego", "FUEGO", "🔥", "sound_f", "UEGO"),
        ),
    ),
    SoundUnit(
        "sound_t", "T", "t", "sound_t",
        (
            WordItem("tren", "TREN", "🚂", "sound_t", "REN"),
            WordItem("toro", "TORO", "🐂", "sound_t", "ORO"),
            WordItem("tomate", "TOMATE", "🍅", "sound_t", "OMATE"),
        ),
    ),
    SoundUnit(
        "sound_s", "S", "s", "sound_s",
        (
            WordItem("sol", "SOL", "☀️", "sound_s", "OL"),
            WordItem("sapo", "SAPO", "🐸", "sound_s", "APO"),
            WordItem("silla", "SILLA", "🪑", "sound_s", "ILLA"),
        ),
    ),
    SoundUnit(
        "sound_b", "B", "b", "sound_b",
        (
            WordItem("barco", "BARCO", "⛵", "sound_b", "ARCO"),
            WordItem("bola", "BOLA", "⚽", "sound_b", "OLA"),
            WordItem("burro", "BURRO", "🫏", "sound_b", "URRO"),
        ),
    ),
    SoundUnit(
        "sound_n", "N", "n", "sound_n",
        (
            WordItem("nube", "NUBE", "☁️", "sound_n", "UBE"),
            WordItem("nariz", "NARIZ", "👃", "sound_n", "ARIZ"),
            WordItem("nido", "NIDO", "🪺", "sound_n", "IDO"),
        ),
    ),
)

SOUND_UNITS_FR: Final[tuple[SoundUnit, ...]] = (
    SoundUnit(
        "sound_m", "M", "m", "sound_m",
        (
            WordItem("maman", "MAMAN", "👩", "sound_m", "AMAN"),
            WordItem("moto", "MOTO", "🏍️", "sound_m", "OTO"),
            WordItem("mouton", "MOUTON", "🐑", "sound_m", "OUTON"),
        ),
    ),
    SoundUnit(
        "sound_p", "P", "p", "sound_p",
        (
            WordItem("pomme", "POMME", "🍎", "sound_p", "OMME"),
            WordItem("poule", "POULE", "🐔", "sound_p", "OULE"),
            WordItem("poisson", "POISSON", "🐟", "sound_p", "OISSON"),
        ),
    ),
    SoundUnit(
        "sound_l", "L", "l", "sound_l",
        (
            WordItem("lune", "LUNE", "🌙", "sound_l", "UNE"),
            WordItem("lion", "LION", "🦁", "sound_l", "ION"),
            WordItem("livre", "LIVRE", "📖", "sound_l", "IVRE"),
        ),
    ),
    SoundUnit(
        "sound_f", "F", "f", "sound_f",
        (
            WordItem("fleur", "FLEUR", "🌸", "sound_f", "LEUR"),
            WordItem("fee", "FÉE", "🧚", "sound_f", "ÉE"),
            WordItem("fourmi", "FOURMI", "🐜", "sound_f", "OURMI"),
        ),
    ),
    SoundUnit(
        "sound_t", "T", "t", "sound_t",
        (
            WordItem("tasse", "TASSE", "☕", "sound_t", "ASSE"),
            WordItem("tortue", "TORTUE", "🐢", "sound_t", "ORTUE"),
            WordItem("tomate", "TOMATE", "🍅", "sound_t", "OMATE"),
        ),
    ),
    SoundUnit(
        "sound_s", "S", "s", "sound_s",
        (
            WordItem("soleil", "SOLEIL", "☀️", "sound_s", "OLEIL"),
            WordItem("sac", "SAC", "🎒", "sound_s", "AC"),
            WordItem("souris", "SOURIS", "🐭", "sound_s", "OURIS"),
        ),
    ),
    SoundUnit(
        "sound_b", "B", "b", "sound_b",
        (
            WordItem("bateau", "BATEAU", "⛵", "sound_b", "ATEAU"),
            WordItem("bebe", "BÉBÉ", "👶", "sound_b", "ÉBÉ"),
            WordItem("banane", "BANANE", "🍌", "sound_b", "ANANE"),
        ),
    ),
    SoundUnit(
        "sound_r", "R", "r", "sound_r",
        (
            WordItem("robot", "ROBOT", "🤖", "sound_r", "OBOT"),
            WordItem("renard", "RENARD", "🦊", "sound_r", "ENARD"),
            WordItem("rose", "ROSE", "🌹", "sound_r", "OSE"),
        ),
    ),
)

_SOUND_UNITS_BY_LANGUAGE: Final = {
    "it": SOUND_UNITS_IT,
    "en": SOUND_UNITS_EN,
    "es": SOUND_UNITS_ES,
    "fr": SOUND_UNITS_FR,
}


def get_sound_units(locale: str) -> tuple[SoundUnit, ...]:
    """Resolve the actual phoneme curriculum, never a wrong-language fallback."""
    language = locale.replace("_", "-").split("-", 1)[0].lower()
    try:
        return _SOUND_UNITS_BY_LANGUAGE[language]
    except KeyError as exc:
        raise ValueError(f"unsupported sound workshop curriculum language: {locale}") from exc
