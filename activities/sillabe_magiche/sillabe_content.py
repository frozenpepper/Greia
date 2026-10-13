from __future__ import annotations

from dataclasses import dataclass

"""Pure syllable-magic content tables and visual constants (no pygame).

Content owns all reference sizes, storage key, palette and linguistic tables
so model/renderer/app can share one source of truth without creating a
pygame dependency in pure domain code.
"""

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "sillabe_magiche.progress.v1"

# Magical Meadow & Workshop Palette
BG_SKY_TOP = (235, 245, 255)
BG_SKY_BOTTOM = (215, 235, 250)
BG_GRASS_BACK = (160, 220, 170)
BG_GRASS_FRONT = (120, 200, 140)
CARD_BG = (255, 254, 250)
CARD_BORDER = (55, 45, 70)
DARK_TEXT = (45, 35, 55)
LIGHT_TEXT = (255, 255, 255)
GOLD = (255, 200, 40)
GOLD_BORDER = (210, 150, 15)
GOLD_LIGHT = (255, 235, 150)
CORAL = (255, 105, 125)
SKY_BLUE = (65, 175, 255)
MINT_GREEN = (75, 210, 135)
LAVENDER = (170, 130, 245)
PEACH = (255, 155, 95)
ROSE_PINK = (255, 135, 175)
AMBER = (255, 175, 60)
SHADOW_COLOR = (35, 25, 55, 45)

SYLLABLE_COLORS: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((255, 120, 140), (255, 180, 195)),  # Coral / Rose
    ((65, 175, 255), (155, 220, 255)),   # Sky Blue
    ((75, 210, 140), (165, 245, 200)),   # Mint Green
    ((255, 170, 70), (255, 215, 145)),   # Sunny Amber
    ((170, 125, 245), (215, 185, 255)),  # Lavender
    ((255, 135, 190), (255, 195, 225)),  # Magenta / Pink
]

CONSONANTS_IT: list[str] = ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "Z"]
VOWELS_IT: list[str] = ["A", "E", "I", "O", "U"]

WORDS_DATA_IT: list[tuple[str, tuple[str, str], str, str]] = [
    ("CASA", ("CA", "SA"), "🏠", "casa"),
    ("SOLE", ("SO", "LE"), "☀️", "sole"),
    ("LUNA", ("LU", "NA"), "🌙", "luna"),
    ("MELA", ("ME", "LA"), "🍎", "mela"),
    ("RANA", ("RA", "NA"), "🐸", "rana"),
    ("TOPO", ("TO", "PO"), "🐭", "topo"),
    ("MANO", ("MA", "NO"), "🖐️", "mano"),
    ("PANE", ("PA", "NE"), "🥖", "pane"),
    ("NAVE", ("NA", "VE"), "🚢", "nave"),
    ("VASO", ("VA", "SO"), "🏺", "vaso"),
    ("PERA", ("PE", "RA"), "🍐", "pera"),
    ("MURO", ("MU", "RO"), "🧱", "muro"),
    ("LUPO", ("LU", "PO"), "🐺", "lupo"),
    ("FILO", ("FI", "LO"), "🧵", "filo"),
    ("ROSA", ("RO", "SA"), "🌹", "rosa"),
    ("FARO", ("FA", "RO"), "🗼", "faro"),
    ("GUFO", ("GU", "FO"), "🦉", "gufo"),
    ("MOTO", ("MO", "TO"), "🏍️", "moto"),
    ("LAMA", ("LA", "MA"), "🦙", "lama"),
    ("PINO", ("PI", "NO"), "🌲", "pino"),
    ("RETE", ("RE", "TE"), "🥅", "rete"),
    ("SUCO", ("SU", "CO"), "🧃", "suco"),
    ("VELA", ("VE", "LA"), "⛵", "vela"),
    ("DADO", ("DA", "DO"), "🎲", "dado"),
    ("FATA", ("FA", "TA"), "🧚", "fata"),
    ("CANE", ("CA", "NE"), "🐶", "cane"),
    ("PIZZA", ("PI", "ZZA"), "🍕", "pizza"),
]

WORDS_DATA_EN: list[tuple[str, tuple[str, str], str, str]] = [
    ("BABY", ("BA", "BY"), "👶", "baby"),
    ("TIGER", ("TI", "GER"), "🐯", "tiger"),
    ("ROBOT", ("RO", "BOT"), "🤖", "robot"),
    ("LEMON", ("LE", "MON"), "🍋", "lemon"),
    ("PAPER", ("PA", "PER"), "📄", "paper"),
    ("WATER", ("WA", "TER"), "💧", "water"),
    ("MUSIC", ("MU", "SIC"), "🎵", "music"),
    ("RABBIT", ("RAB", "BIT"), "🐰", "rabbit"),
    ("PIZZA", ("PIZ", "ZA"), "🍕", "pizza"),
    ("ZEBRA", ("ZE", "BRA"), "🦓", "zebra"),
    ("PANDA", ("PAN", "DA"), "🐼", "panda"),
    ("ROCKET", ("ROCK", "ET"), "🚀", "rocket"),
    ("SUNNY", ("SUN", "NY"), "☀️", "sunny"),
]


# Candidate native-language builder lessons. Orthographic and spoken-syllable
# accuracy must be approved by native-speaking educators before release.
# ES/FR are NOT enabled in the Activity manifest and have no accepted speech.
WORDS_DATA_ES: list[tuple[str, tuple[str, str], str, str]] = [
    ("CASA", ("CA", "SA"), "🏠", "casa"),
    ("LUNA", ("LU", "NA"), "🌙", "luna"),
    ("MESA", ("ME", "SA"), "🍽️", "mesa"),
    ("PATO", ("PA", "TO"), "🦆", "pato"),
    ("GATO", ("GA", "TO"), "🐱", "gato"),
    ("RANA", ("RA", "NA"), "🐸", "rana"),
    ("NUBE", ("NU", "BE"), "☁️", "nube"),
    ("BOCA", ("BO", "CA"), "👄", "boca"),
    ("CAMA", ("CA", "MA"), "🛏️", "cama"),
    ("PINO", ("PI", "NO"), "🌲", "pino"),
    ("DADO", ("DA", "DO"), "🎲", "dado"),
    ("MOTO", ("MO", "TO"), "🏍️", "moto"),
    ("ROSA", ("RO", "SA"), "🌹", "rosa"),
    ("PERA", ("PE", "RA"), "🍐", "pera"),
    ("TAZA", ("TA", "ZA"), "☕", "taza"),
    ("VASO", ("VA", "SO"), "🏺", "vaso"),
]

WORDS_DATA_FR: list[tuple[str, tuple[str, str], str, str]] = [
    ("BATEAU", ("BA", "TEAU"), "⛵", "bateau"),
    ("LAPIN", ("LA", "PIN"), "🐰", "lapin"),
    ("ROBOT", ("RO", "BOT"), "🤖", "robot"),
    ("MAISON", ("MAI", "SON"), "🏠", "maison"),
    ("VÉLO", ("VÉ", "LO"), "🚲", "velo"),
    ("MOTO", ("MO", "TO"), "🏍️", "moto"),
    ("BÉBÉ", ("BÉ", "BÉ"), "👶", "bebe"),
    ("PAPI", ("PA", "PI"), "👴", "papi"),
    ("RADIS", ("RA", "DIS"), "🌱", "radis"),
    ("TÉLÉ", ("TÉ", "LÉ"), "📺", "tele"),
    ("CHAPEAU", ("CHA", "PEAU"), "🎩", "chapeau"),
    ("GÂTEAU", ("GÂ", "TEAU"), "🎂", "gateau"),
    ("SAPIN", ("SA", "PIN"), "🌲", "sapin"),
    ("CANARD", ("CA", "NARD"), "🦆", "canard"),
    ("MOUTON", ("MOU", "TON"), "🐑", "mouton"),
    ("TAPIS", ("TA", "PIS"), "🧶", "tapis"),
]



# Explicit teaching syllables for ES/FR staged explorer/catcher modes.
# Restrict the interactive cards to educator-reviewable syllables instead
# of generating every Italian consonant × vowel combination; audio and
# native pronunciation approval are still mandatory before promotion.
_FAMILIES_ES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("M", ("MA", "ME", "MI", "MO", "MU")),
    ("P", ("PA", "PE", "PI", "PO", "PU")),
    ("L", ("LA", "LE", "LI", "LO", "LU")),
    ("S", ("SA", "SE", "SI", "SO", "SU")),
    ("T", ("TA", "TE", "TI", "TO", "TU")),
    ("N", ("NA", "NE", "NI", "NO", "NU")),
    ("D", ("DA", "DE", "DI", "DO", "DU")),
    ("F", ("FA", "FE", "FI", "FO", "FU")),
)

_FAMILIES_FR: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("M", ("MA", "MÉ", "MI", "MO", "MU")),
    ("P", ("PA", "PÉ", "PI", "PO", "PU")),
    ("L", ("LA", "LÉ", "LI", "LO", "LU")),
    ("T", ("TA", "TÉ", "TI", "TO", "TU")),
    ("S", ("SA", "SÉ", "SI", "SO", "SU")),
)

@dataclass(frozen=True, slots=True)
class SyllableCurriculum:
    """One coherent language's child-facing literacy and speech-cue settings."""

    consonants: tuple[str, ...]
    vowels: tuple[str, ...]
    words: tuple[tuple[str, tuple[str, str], str, str], ...]
    tabs: tuple[str, str, str]
    consonant_heading: str
    praise_cues: tuple[str, ...]
    syllable_families: tuple[tuple[str, tuple[str, ...]], ...] = ()


_CURRICULA: dict[str, SyllableCurriculum] = {
    "it": SyllableCurriculum(
        tuple(CONSONANTS_IT), tuple(VOWELS_IT), tuple(WORDS_DATA_IT),
        ("Sillabario", "Acchiappa", "Crea Parole"), "Consonanti",
        ("esatto", "fantastico", "super", "magnifico", "ottimo", "ben_fatto"),
        (),
    ),
    "en": SyllableCurriculum(
        tuple(CONSONANTS_IT), tuple(VOWELS_IT), tuple(WORDS_DATA_EN),
        ("Syllabary", "Catch", "Words"), "Consonants",
        ("great_job", "wonderful", "you_did_it", "fantastic", "super", "well_done"),
        (),
    ),
    "es": SyllableCurriculum(
        tuple(label for label, _ in _FAMILIES_ES), tuple(VOWELS_IT), tuple(WORDS_DATA_ES),
        ("Sílabas", "Atrapa", "Palabras"), "Consonantes",
        ("muy_bien", "genial", "lo_lograste"),
        _FAMILIES_ES,
    ),
    "fr": SyllableCurriculum(
        tuple(label for label, _ in _FAMILIES_FR), tuple(VOWELS_IT), tuple(WORDS_DATA_FR),
        ("Syllabes", "Attrape", "Mots"), "Consonnes",
        ("bravo", "tres_bien", "tu_as_reussi"),
        _FAMILIES_FR,
    ),
}


def get_syllable_curriculum(locale: str) -> SyllableCurriculum:
    """Resolve native lesson data; never silently substitute English/Italian."""
    language = locale.replace("_", "-").split("-", 1)[0].lower()
    try:
        return _CURRICULA[language]
    except KeyError as exc:
        raise ValueError(f"unsupported syllable curriculum language: {locale}") from exc


__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "BG_SKY_TOP",
    "BG_SKY_BOTTOM",
    "BG_GRASS_BACK",
    "BG_GRASS_FRONT",
    "CARD_BG",
    "CARD_BORDER",
    "DARK_TEXT",
    "LIGHT_TEXT",
    "GOLD",
    "GOLD_BORDER",
    "GOLD_LIGHT",
    "CORAL",
    "SKY_BLUE",
    "MINT_GREEN",
    "LAVENDER",
    "PEACH",
    "ROSE_PINK",
    "AMBER",
    "SHADOW_COLOR",
    "SYLLABLE_COLORS",
    "CONSONANTS_IT",
    "VOWELS_IT",
    "WORDS_DATA_IT",
    "WORDS_DATA_EN",
    "WORDS_DATA_ES",
    "WORDS_DATA_FR",
    "SyllableCurriculum",
    "get_syllable_curriculum",
]
