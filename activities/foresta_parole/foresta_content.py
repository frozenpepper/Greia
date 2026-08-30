"""Foresta Parole — content constants (geometry, palette, phonics catalogue).

Pure data. No pygame imports, no side effects. Anything that changes only
when the catalogue is reauthored lives here so the runtime modules can be
reasoned about independently.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
STORAGE_KEY: Final = "foresta_parole.progress.v2"

# Enchanted Forest Color Palette
FOREST_SKY_TOP: Final = (18, 24, 48)
FOREST_SKY_BOTTOM: Final = (38, 64, 82)
CANOPY_DARK: Final = (16, 32, 38)
CANOPY_LIGHT: Final = (28, 58, 64)
BRANCH_BROWN: Final = (72, 48, 34)
LEAF_GREEN: Final = (52, 128, 80)
LEAF_LIGHT: Final = (84, 182, 112)
CARD_BG: Final = (255, 250, 240)
CARD_BORDER: Final = (61, 44, 31)
GOLD: Final = (255, 205, 50)
WHITE: Final = (255, 255, 255)
DARK_TEXT: Final = (50, 38, 28)

# CRITICAL AUDIO / TTS SYNTHESIS INSTRUCTIONS:
# ============================================
# When generating audio with TTS (e.g. macOS `say`), ALWAYS pass lowercase strings (.lower()).
# Capital letters (like 'C' or 'C come Cane') cause macOS TTS to say "C maiuscola" or "capital C".
# Target speech rate: ~180 wpm for Italian, ~185 wpm for English (gentle, toddler-friendly pace).
# See `tools/generate_foresta_audio.py` to regenerate all audio assets.

PHONICS_DATA: Final = {
    "it": [
        ("A", "a", "find_a", "Ape", "🐝", "ape"),
        ("B", "b", "find_b", "Barca", "⛵", "barca"),
        ("C", "c", "find_c", "Cane", "🐶", "cane"),
        ("D", "d", "find_d", "Delfino", "🐬", "delfino"),
        ("E", "e", "find_e", "Elefante", "🐘", "elefante"),
        ("F", "f", "find_f", "Fiore", "🌸", "fiore"),
        ("G", "g", "find_g", "Gatto", "🐱", "gatto"),
        ("I", "i", "find_i", "Isola", "🏝️", "isola"),
        ("L", "l", "find_l", "Luna", "🌙", "luna"),
        ("M", "m", "find_m", "Mela", "🍎", "mela"),
        ("N", "n", "find_n", "Nave", "🚢", "nave"),
        ("O", "o", "find_o", "Orso", "🐻", "orso"),
        ("P", "p", "find_p", "Pesce", "🐟", "pesce"),
        ("Q", "q", "find_q", "Quercia", "🌳", "quercia"),
        ("R", "r", "find_r", "Rana", "🐸", "rana"),
        ("S", "s", "find_s", "Sole", "☀️", "sole"),
        ("T", "t", "find_t", "Tigre", "🐯", "tigre"),
        ("U", "u", "find_u", "Uva", "🍇", "uva"),
        ("V", "v", "find_v", "Vento", "💨", "vento"),
        ("Z", "z", "find_z", "Zebra", "🦓", "zebra"),
    ],
    "en": [
        ("A", "a", "find_a", "Apple", "🍎", "apple"),
        ("B", "b", "find_b", "Boat", "⛵", "boat"),
        ("C", "c", "find_c", "Cat", "🐱", "cat"),
        ("D", "d", "find_d", "Dolphin", "🐬", "dolphin"),
        ("E", "e", "find_e", "Elephant", "🐘", "elephant"),
        ("F", "f", "find_f", "Flower", "🌸", "flower"),
        ("G", "g", "find_g", "Giraffe", "🦒", "giraffe"),
        ("H", "h", "find_h", "House", "🏡", "house"),
        ("I", "i", "find_i", "Island", "🏝️", "island"),
        ("L", "l", "find_l", "Lion", "🦁", "lion"),
        ("M", "m", "find_m", "Moon", "🌙", "moon"),
        ("N", "n", "find_n", "Nest", "🪺", "nest"),
        ("O", "o", "find_o", "Owl", "🦉", "owl"),
        ("P", "p", "find_p", "Penguin", "🐧", "penguin"),
        ("Q", "q", "find_q", "Queen", "👑", "queen"),
        ("R", "r", "find_r", "Rabbit", "🐰", "rabbit"),
        ("S", "s", "find_s", "Sun", "☀️", "sun"),
        ("T", "t", "find_t", "Tiger", "🐯", "tiger"),
        ("U", "u", "find_u", "Umbrella", "☂️", "umbrella"),
        ("V", "v", "find_v", "Volcano", "🌋", "volcano"),
        ("W", "w", "find_w", "Whale", "🐋", "whale"),
        ("Z", "z", "find_z", "Zebra", "🦓", "zebra"),
    ],
}

ORB_COLORS: Final = [
    ((255, 140, 60), (255, 200, 120)),
    ((60, 180, 255), (150, 220, 255)),
    ((255, 90, 140), (255, 170, 200)),
    ((140, 90, 255), (200, 160, 255)),
    ((70, 210, 120), (160, 245, 190)),
    ((255, 210, 50), (255, 240, 140)),
]

# Gameplay tuning: how many correct catches before a word is celebrated.
MATCHES_NEEDED: Final = 3

__all__ = [
    "BRANCH_BROWN",
    "CANOPY_DARK",
    "CANOPY_LIGHT",
    "CARD_BG",
    "CARD_BORDER",
    "DARK_TEXT",
    "FOREST_SKY_BOTTOM",
    "FOREST_SKY_TOP",
    "GOLD",
    "LEAF_GREEN",
    "LEAF_LIGHT",
    "MATCHES_NEEDED",
    "ORB_COLORS",
    "PHONICS_DATA",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "WHITE",
]
