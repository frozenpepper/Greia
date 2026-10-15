"""The Word Forest — content data (recorded lessons, pictures, stage ladder).

Pure data: no pygame, no side effects. The Word Forest is the *action
practice* rung of the literacy ladder (ages 5–7): a picture word is shown and
spoken with its letter name ("B as Boat" / "B come Barca"), letters drop from
the forest canopy and the child moves a basket to catch the letter that starts
the word. It practises letter NAMES learnt in Leo's Letter Garden; it never
teaches letter sounds (Dani's Sound Machine owns phonemes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
# Original key kept so earlier saves (score/stars/words) load and carry forward.
STORAGE_KEY: Final = "foresta_parole.progress.v2"

# Picture placeholder for recorded words the shared library cannot show yet.
PICTURE_PENDING: Final = "pending"

# RECORDING AUTHORITY (parsed literally by tools/audit_greia_language_coverage):
# Each tuple is (display_letter, letter_audio_stem, prompt_audio_stem,
#                example_word, picture_id, example_word_audio_stem).
# ``prompt`` clips say the letter name with the word ("B as Boat"), ``letter``
# clips say the letter name, ``word`` clips the word. All EN/IT/ES/FR clips are
# owner-approved recordings; never synthesise, copy or rename them.
# ``picture_id`` is a shared visual ID (``prop.*``/``creature.*``) or
# PICTURE_PENDING when the library has no clear picture for the word yet; a
# pending word stays recorded but is not played (the picture IS the prompt).
PHONICS_DATA: Final = {
    "it": [
        ("A", "a", "find_a", "Ape", "prop.vocab.bee", "ape"),
        ("B", "b", "find_b", "Barca", "prop.vocab.boat", "barca"),
        ("C", "c", "find_c", "Cane", "prop.vocab.dog", "cane"),
        ("D", "d", "find_d", "Delfino", "creature.marine.dolphin", "delfino"),
        ("E", "e", "find_e", "Elefante", "prop.vocab.elephant", "elefante"),
        ("F", "f", "find_f", "Fiore", "prop.nature.flower", "fiore"),
        ("G", "g", "find_g", "Gatto", "prop.vocab.cat", "gatto"),
        ("I", "i", "find_i", "Isola", "pending", "isola"),
        ("L", "l", "find_l", "Luna", "prop.vocab.moon", "luna"),
        ("M", "m", "find_m", "Mela", "prop.food.apple", "mela"),
        ("N", "n", "find_n", "Nave", "pending", "nave"),
        ("O", "o", "find_o", "Orso", "prop.vocab.bear", "orso"),
        ("P", "p", "find_p", "Pesce", "prop.food.fish", "pesce"),
        ("Q", "q", "find_q", "Quercia", "pending", "quercia"),
        ("R", "r", "find_r", "Rana", "prop.vocab.frog", "rana"),
        ("S", "s", "find_s", "Sole", "prop.nature.sun", "sole"),
        ("T", "t", "find_t", "Tigre", "pending", "tigre"),
        ("U", "u", "find_u", "Uva", "prop.vocab.grapes", "uva"),
        ("V", "v", "find_v", "Vento", "pending", "vento"),
        ("Z", "z", "find_z", "Zebra", "pending", "zebra"),
    ],
    "en": [
        ("A", "a", "find_a", "Apple", "prop.food.apple", "apple"),
        ("B", "b", "find_b", "Boat", "prop.vocab.boat", "boat"),
        ("C", "c", "find_c", "Cat", "prop.vocab.cat", "cat"),
        ("D", "d", "find_d", "Dolphin", "creature.marine.dolphin", "dolphin"),
        ("E", "e", "find_e", "Elephant", "prop.vocab.elephant", "elephant"),
        ("F", "f", "find_f", "Flower", "prop.nature.flower", "flower"),
        ("G", "g", "find_g", "Giraffe", "pending", "giraffe"),
        ("H", "h", "find_h", "House", "prop.vocab.house", "house"),
        ("I", "i", "find_i", "Island", "pending", "island"),
        ("L", "l", "find_l", "Lion", "prop.vocab.lion", "lion"),
        ("M", "m", "find_m", "Moon", "prop.vocab.moon", "moon"),
        ("N", "n", "find_n", "Nest", "prop.vocab.nest", "nest"),
        ("O", "o", "find_o", "Owl", "pending", "owl"),
        ("P", "p", "find_p", "Penguin", "prop.vocab.penguin", "penguin"),
        ("Q", "q", "find_q", "Queen", "pending", "queen"),
        ("R", "r", "find_r", "Rabbit", "pending", "rabbit"),
        ("S", "s", "find_s", "Sun", "prop.nature.sun", "sun"),
        ("T", "t", "find_t", "Tiger", "pending", "tiger"),
        ("U", "u", "find_u", "Umbrella", "prop.vocab.umbrella", "umbrella"),
        ("V", "v", "find_v", "Volcano", "pending", "volcano"),
        ("W", "w", "find_w", "Whale", "prop.vocab.whale", "whale"),
        ("Z", "z", "find_z", "Zebra", "pending", "zebra"),
    ],
    # Staged candidates (bundles in key parity; not advertised by activity.toml).
    "es": [
        ("A", "a", "find_a", "Abeja", "prop.vocab.bee", "abeja"),
        ("B", "b", "find_b", "Barco", "prop.vocab.boat", "barco"),
        ("C", "c", "find_c", "Casa", "prop.vocab.house", "casa"),
        ("D", "d", "find_d", "Dado", "pending", "dado"),
        ("E", "e", "find_e", "Elefante", "prop.vocab.elephant", "elefante"),
        ("F", "f", "find_f", "Flor", "prop.nature.flower", "flor"),
        ("G", "g", "find_g", "Gato", "prop.vocab.cat", "gato"),
        ("I", "i", "find_i", "Isla", "pending", "isla"),
        ("J", "j", "find_j", "Jirafa", "pending", "jirafa"),
        ("L", "l", "find_l", "Luna", "prop.vocab.moon", "luna"),
        ("M", "m", "find_m", "Manzana", "prop.food.apple", "manzana"),
        ("N", "n", "find_n", "Nube", "prop.nature.cloud", "nube"),
        ("O", "o", "find_o", "Oso", "prop.vocab.bear", "oso"),
        ("P", "p", "find_p", "Perro", "prop.vocab.dog", "perro"),
        ("Q", "q", "find_q", "Queso", "pending", "queso"),
        ("R", "r", "find_r", "Rana", "prop.vocab.frog", "rana"),
        ("S", "s", "find_s", "Sol", "prop.nature.sun", "sol"),
        ("T", "t", "find_t", "Tigre", "pending", "tigre"),
        ("U", "u", "find_u", "Uva", "prop.vocab.grapes", "uva"),
        ("V", "v", "find_v", "Vaca", "pending", "vaca"),
        ("Z", "z", "find_z", "Zapato", "pending", "zapato"),
    ],
    "fr": [
        ("A", "a", "find_a", "Abeille", "prop.vocab.bee", "abeille"),
        ("B", "b", "find_b", "Bateau", "prop.vocab.boat", "bateau"),
        ("C", "c", "find_c", "Chat", "prop.vocab.cat", "chat"),
        ("D", "d", "find_d", "Dauphin", "creature.marine.dolphin", "dauphin"),
        ("E", "e", "find_e", "Escargot", "prop.vocab.snail", "escargot"),
        ("F", "f", "find_f", "Fleur", "prop.nature.flower", "fleur"),
        ("G", "g", "find_g", "Girafe", "pending", "girafe"),
        ("I", "i", "find_i", "Igloo", "pending", "igloo"),
        ("J", "j", "find_j", "Jardin", "pending", "jardin"),
        ("L", "l", "find_l", "Lune", "prop.vocab.moon", "lune"),
        ("M", "m", "find_m", "Maison", "prop.vocab.house", "maison"),
        ("N", "n", "find_n", "Nuage", "prop.nature.cloud", "nuage"),
        ("O", "o", "find_o", "Ours", "prop.vocab.bear", "ours"),
        ("P", "p", "find_p", "Poisson", "prop.food.fish", "poisson"),
        ("Q", "q", "find_q", "Quiche", "pending", "quiche"),
        ("R", "r", "find_r", "Renard", "pending", "renard"),
        ("S", "s", "find_s", "Soleil", "prop.nature.sun", "soleil"),
        ("T", "t", "find_t", "Tortue", "prop.vocab.turtle", "tortue"),
        ("U", "u", "find_u", "Usine", "pending", "usine"),
        ("V", "v", "find_v", "Vélo", "prop.vocab.bicycle", "velo"),
        ("Z", "z", "find_z", "Zèbre", "pending", "zebre"),
    ],
}

# Recorded examples that mislead a first-letter task even when a picture
# exists; they stay recorded but are never played. Replacements are listed as
# voice requests in the rework report.
AVOIDED_EXAMPLES: Final[dict[tuple[str, str], str]] = {
    ("en", "O"): "Owl starts with /aʊ/, neither the letter name nor a usual O sound",
    ("en", "G"): "Giraffe: soft G; prefer a hard-G word for a first-letter game",
    ("en", "I"): "Island: silent S and an unusual spelling for a first reader",
    ("en", "Q"): "Queen: the picture (a crown) is named 'crown' by children",
    ("fr", "C"): "Chat starts with the digraph CH (/ʃ/), not a C sound",
}

# Capital letters children confuse; used as harder decoys from stage 3.
LOOKALIKE_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("E", "F"),
    ("P", "R"),
    ("B", "D"),
    ("B", "P"),
    ("M", "N"),
    ("M", "W"),
    ("U", "V"),
    ("V", "W"),
    ("C", "G"),
    ("O", "C"),
    ("H", "N"),
    ("L", "T"),
)

# Accent tokens (runtime/theme-defaults) used for the falling letters' ink.
LETTER_TOKENS: Final[tuple[str, ...]] = ("coral", "ocean", "grape", "raspberry", "orange", "turquoise", "leaf")


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One rung of the same catch loop: speed, decoys and how busy the sky is."""

    number: int
    fall_speed: float        # logical px/s
    decoy_kinds: int         # distinct decoy letters per target
    max_falling: int         # letters in the air at once
    spawn_interval: float    # seconds between drops
    lookalikes: bool         # include a look-alike decoy when one exists


STAGES: Final[tuple[StageSpec, ...]] = (
    StageSpec(1, 58.0, 1, 2, 2.3, False),
    StageSpec(2, 70.0, 2, 3, 2.0, False),
    StageSpec(3, 84.0, 3, 3, 1.8, True),
    StageSpec(4, 98.0, 3, 4, 1.6, True),
)

TARGETS_PER_ROUND: Final = 6

__all__ = [
    "AVOIDED_EXAMPLES",
    "LETTER_TOKENS",
    "LOOKALIKE_PAIRS",
    "PHONICS_DATA",
    "PICTURE_PENDING",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STAGES",
    "STORAGE_KEY",
    "StageSpec",
    "TARGETS_PER_ROUND",
]
