"""Pure lesson content for Magic Syllables — Leo's Syllable Train (no pygame).

One core experience: *hear a picture word, clap its beats onto the train's
wagons, then (where the language's reading method supports it) build each
wagon's syllable and let the train read the whole word*.

The reading method is per language, never borrowed from another one:

* **Italian / Spanish** — open consonant+vowel syllables are the classroom
  *metodo sillabico* / *método silábico*: the child claps the beats, then
  builds every wagon's syllable (consonant given + vowel chosen, later whole
  syllable tiles) and the train blends the syllables into the word;
* **French** (staged) — syllables are often not simple C+V, so wagons are
  built from whole, authored syllable tiles only;
* **English** — the Italian syllabary is **not** shipped. The same train loop
  is limited to syllable *beats*: clap a word's beats and choose the picture
  whose word fits a train of N wagons. No English letters or phonics chunks
  are shown or spoken.

Source-level literal tables (``CONSONANTS_IT``, ``VOWELS_IT``, ``WORDS_DATA_*``,
``_FAMILIES_*`` and ``_CURRICULA``) are read *without import* by
``tools/audit_greia_language_coverage.py`` to inventory the playback stems;
keep them statically literal. The third field of a ``WORDS_DATA_*`` row is the
shared-library (or ``activity:``) picture ID — never emoji — or
``PICTURE_PENDING`` for a word whose picture is not authored yet; pending
words are never offered to a child.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "sillabe_magiche.progress.v1"
PICTURE_PENDING: Final = "pending"

CONSONANTS_IT: list[str] = ["B", "C", "D", "F", "G", "L", "M", "N", "P", "R", "S", "T", "V", "Z"]
VOWELS_IT: list[str] = ["A", "E", "I", "O", "U"]

# (written word, written syllables, picture id, approved word-clip stem).
# Words whose picture is "pending" keep their approved audio inventory but are
# not offered until library art exists (e.g. MURO, LUPO, FARO).
WORDS_DATA_IT: list[tuple[str, tuple[str, str], str, str]] = [
    ("CASA", ("CA", "SA"), "prop.vocab.house", "casa"),
    ("SOLE", ("SO", "LE"), "prop.nature.sun", "sole"),
    ("LUNA", ("LU", "NA"), "prop.vocab.moon", "luna"),
    ("MELA", ("ME", "LA"), "prop.food.apple", "mela"),
    ("RANA", ("RA", "NA"), "prop.vocab.frog", "rana"),
    ("TOPO", ("TO", "PO"), "prop.vocab.mouse", "topo"),
    ("MANO", ("MA", "NO"), "prop.vocab.hand", "mano"),
    ("PANE", ("PA", "NE"), "prop.vocab.bread", "pane"),
    ("NAVE", ("NA", "VE"), "pending", "nave"),
    ("VASO", ("VA", "SO"), "prop.vocab.vase", "vaso"),
    ("PERA", ("PE", "RA"), "prop.vocab.pear", "pera"),
    ("MURO", ("MU", "RO"), "pending", "muro"),
    ("LUPO", ("LU", "PO"), "pending", "lupo"),
    ("FILO", ("FI", "LO"), "pending", "filo"),
    ("ROSA", ("RO", "SA"), "pending", "rosa"),
    ("FARO", ("FA", "RO"), "pending", "faro"),
    ("GUFO", ("GU", "FO"), "pending", "gufo"),
    ("MOTO", ("MO", "TO"), "pending", "moto"),
    ("LAMA", ("LA", "MA"), "pending", "lama"),
    ("PINO", ("PI", "NO"), "pending", "pino"),
    ("RETE", ("RE", "TE"), "pending", "rete"),
    ("VELA", ("VE", "LA"), "pending", "vela"),
    ("DADO", ("DA", "DO"), "pending", "dado"),
    ("FATA", ("FA", "TA"), "pending", "fata"),
    ("CANE", ("CA", "NE"), "prop.vocab.dog", "cane"),
]

# English two-beat picture words. The written chunks are kept only as the
# audited recording inventory; the English loop never shows or speaks them.
# A rabbit or robot picture would be named after the cast (Flash, Dani), so
# those words stay pending.
WORDS_DATA_EN: list[tuple[str, tuple[str, str], str, str]] = [
    ("BABY", ("BA", "BY"), "pending", "baby"),
    ("TIGER", ("TI", "GER"), "activity:tiger", "tiger"),
    ("ROBOT", ("RO", "BOT"), "pending", "robot"),
    ("LEMON", ("LE", "MON"), "activity:lemon", "lemon"),
    ("PAPER", ("PA", "PER"), "pending", "paper"),
    ("WATER", ("WA", "TER"), "pending", "water"),
    ("MUSIC", ("MU", "SIC"), "pending", "music"),
    ("RABBIT", ("RAB", "BIT"), "pending", "rabbit"),
    ("PIZZA", ("PIZ", "ZA"), "prop.vocab.pizza", "pizza"),
    ("ZEBRA", ("ZE", "BRA"), "activity:zebra", "zebra"),
    ("PANDA", ("PAN", "DA"), "activity:panda", "panda"),
    ("ROCKET", ("ROCK", "ET"), "prop.vocab.rocket", "rocket"),
    ("SUNNY", ("SUN", "NY"), "pending", "sunny"),
]

# English one-beat picture words. Each is an owner-approved recording of the
# whole word (recorded as a single-syllable clip: "sun", "rock", "pan", "be"
# = /biː/). (written word, approved clip stem, picture id).
ONE_BEAT_WORDS_EN: tuple[tuple[str, str, str], ...] = (
    ("SUN", "syl_sun", "prop.nature.sun"),
    ("ROCK", "syl_rock", "prop.everyday.stone"),
    ("PAN", "syl_pan", "prop.vocab.pan"),
    ("BEE", "syl_be", "prop.vocab.bee"),
)


# Candidate native-language lessons. Orthographic and spoken-syllable
# accuracy must be approved by native-speaking educators before release.
# ES/FR are NOT enabled in the Activity manifest. Spanish "vaso" is a drinking
# glass (the library vase would mislead), so it stays pending.
WORDS_DATA_ES: list[tuple[str, tuple[str, str], str, str]] = [
    ("CASA", ("CA", "SA"), "prop.vocab.house", "casa"),
    ("LUNA", ("LU", "NA"), "prop.vocab.moon", "luna"),
    ("MESA", ("ME", "SA"), "pending", "mesa"),
    ("PATO", ("PA", "TO"), "creature.woodland.duck", "pato"),
    ("GATO", ("GA", "TO"), "prop.vocab.cat", "gato"),
    ("RANA", ("RA", "NA"), "prop.vocab.frog", "rana"),
    ("NUBE", ("NU", "BE"), "prop.nature.cloud", "nube"),
    ("BOCA", ("BO", "CA"), "pending", "boca"),
    ("CAMA", ("CA", "MA"), "pending", "cama"),
    ("PINO", ("PI", "NO"), "pending", "pino"),
    ("DADO", ("DA", "DO"), "pending", "dado"),
    ("MOTO", ("MO", "TO"), "pending", "moto"),
    ("ROSA", ("RO", "SA"), "pending", "rosa"),
    ("PERA", ("PE", "RA"), "prop.vocab.pear", "pera"),
    ("TAZA", ("TA", "ZA"), "prop.everyday.cup", "taza"),
    ("VASO", ("VA", "SO"), "pending", "vaso"),
]

WORDS_DATA_FR: list[tuple[str, tuple[str, str], str, str]] = [
    ("BATEAU", ("BA", "TEAU"), "prop.vocab.boat", "bateau"),
    ("LAPIN", ("LA", "PIN"), "pending", "lapin"),
    ("ROBOT", ("RO", "BOT"), "pending", "robot"),
    ("MAISON", ("MAI", "SON"), "prop.vocab.house", "maison"),
    ("VÉLO", ("VÉ", "LO"), "prop.vocab.bicycle", "velo"),
    ("MOTO", ("MO", "TO"), "pending", "moto"),
    ("BÉBÉ", ("BÉ", "BÉ"), "pending", "bebe"),
    ("PAPI", ("PA", "PI"), "pending", "papi"),
    ("RADIS", ("RA", "DIS"), "pending", "radis"),
    ("TÉLÉ", ("TÉ", "LÉ"), "pending", "tele"),
    ("CHAPEAU", ("CHA", "PEAU"), "prop.vocab.hat", "chapeau"),
    ("GÂTEAU", ("GÂ", "TEAU"), "prop.vocab.cake", "gateau"),
    ("SAPIN", ("SA", "PIN"), "pending", "sapin"),
    ("CANARD", ("CA", "NARD"), "creature.woodland.duck", "canard"),
    ("MOUTON", ("MOU", "TON"), "pending", "mouton"),
    ("TAPIS", ("TA", "PIS"), "pending", "tapis"),
]


# Explicit teaching syllables for the staged ES/FR syllable inventories.
# Restrict built syllables to educator-reviewable ones instead of generating
# every Italian consonant × vowel combination.
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


class ReadingMethod(StrEnum):
    """How a language's train is built (see the module docstring)."""

    CV_SYLLABLES = "cv_syllables"     # IT / ES: consonant + vowel, then whole syllables
    SYLLABLE_TILES = "syllable_tiles"  # FR (staged): authored whole syllables only
    BEATS = "beats"                    # EN: clap / count beats, choose by beats


@dataclass(frozen=True, slots=True)
class SyllableCurriculum:
    """One coherent language's literacy settings and recorded-cue inventory."""

    consonants: tuple[str, ...]
    vowels: tuple[str, ...]
    words: tuple[tuple[str, tuple[str, str], str, str], ...]
    tabs: tuple[str, str, str]
    consonant_heading: str
    praise_cues: tuple[str, ...]
    syllable_families: tuple[tuple[str, tuple[str, ...]], ...] = ()


# ``tabs`` / ``consonant_heading`` / ``praise_cues`` are retained recording
# inventory of the previous design (the audit tool reads them); the train loop
# shows no tabs and praises through Leo's shared character clips.
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

_METHODS: Final[dict[str, ReadingMethod]] = {
    "it": ReadingMethod.CV_SYLLABLES,
    "es": ReadingMethod.CV_SYLLABLES,
    "fr": ReadingMethod.SYLLABLE_TILES,
    "en": ReadingMethod.BEATS,
}

# The narrator's "you made the word" line, recorded per language under these stems.
WORD_DONE_CUES: Final[dict[str, str]] = {
    "it": "parola_composta",
    "es": "parola_composta",
    "fr": "parola_composta",
    "en": "word_complete",
}


@dataclass(frozen=True, slots=True)
class TrainWord:
    """One picture word the train can carry.

    ``syllables`` are the written syllables (one wagon each); ``audio_id`` is
    the approved whole-word clip stem. ``label`` is the written word, shown
    only where reading is the taught object (never in the English beats loop).
    """

    word_id: str
    label: str
    syllables: tuple[str, ...]
    picture: str
    audio_id: str

    def __post_init__(self) -> None:
        if not self.word_id or not self.audio_id:
            raise ValueError("a train word needs an id and an approved clip")
        if not self.syllables or any(not part for part in self.syllables):
            raise ValueError("a train word needs at least one syllable")
        if "".join(self.syllables) != self.label:
            raise ValueError(f"syllables must spell the word: {self.label!r}")

    @property
    def beats(self) -> int:
        return len(self.syllables)

    @property
    def has_picture(self) -> bool:
        return bool(self.picture) and self.picture != PICTURE_PENDING


def syllable_cue(syllable: str) -> str:
    """Approved clip stem for one spoken syllable (``syl_lu``, ``syl_mé``)."""

    return f"syl_{syllable.lower()}"


def vowel_cue(vowel: str) -> str:
    return f"vowel_{vowel.lower()}"


def _language(locale: str) -> str:
    return locale.replace("_", "-").split("-", 1)[0].lower()


def get_syllable_curriculum(locale: str) -> SyllableCurriculum:
    """Resolve native lesson data; never silently substitute English/Italian."""
    try:
        return _CURRICULA[_language(locale)]
    except KeyError as exc:
        raise ValueError(f"unsupported syllable curriculum language: {locale}") from exc


def get_reading_method(locale: str) -> ReadingMethod:
    try:
        return _METHODS[_language(locale)]
    except KeyError as exc:
        raise ValueError(f"unsupported syllable curriculum language: {locale}") from exc


def train_words(locale: str, *, pictured_only: bool = True) -> tuple[TrainWord, ...]:
    """Every picture word of one language (pending pictures excluded by default)."""

    language = _language(locale)
    curriculum = get_syllable_curriculum(language)
    words = [
        TrainWord(stem, label, tuple(parts), picture, f"word_{stem}")
        for label, parts, picture, stem in curriculum.words
    ]
    if language == "en":
        words.extend(
            TrainWord(label.lower(), label, (label,), picture, cue)
            for label, cue, picture in ONE_BEAT_WORDS_EN
        )
    if pictured_only:
        words = [word for word in words if word.has_picture]
    return tuple(words)


def approved_syllables(locale: str) -> tuple[str, ...]:
    """Syllables with an authored, recorded clip in this language's curriculum.

    Italian: every consonant × vowel of the syllabary plus the word parts.
    Spanish/French: only the explicit families plus the authored word parts —
    never a generated, unreviewed combination.
    """

    language = _language(locale)
    curriculum = get_syllable_curriculum(language)
    if curriculum.syllable_families:
        base = [syl for _, family in curriculum.syllable_families for syl in family]
    elif language == "it":
        base = [f"{c}{v}" for c in curriculum.consonants for v in curriculum.vowels]
    else:
        base = []
    parts = [part for _, segments, _, _ in curriculum.words for part in segments]
    return tuple(dict.fromkeys((*base, *parts)))


__all__ = [
    "CONSONANTS_IT",
    "ONE_BEAT_WORDS_EN",
    "PICTURE_PENDING",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ReadingMethod",
    "STORAGE_KEY",
    "SyllableCurriculum",
    "TrainWord",
    "VOWELS_IT",
    "WORDS_DATA_EN",
    "WORDS_DATA_ES",
    "WORDS_DATA_FR",
    "WORDS_DATA_IT",
    "WORD_DONE_CUES",
    "approved_syllables",
    "get_reading_method",
    "get_syllable_curriculum",
    "syllable_cue",
    "train_words",
    "vowel_cue",
]
