from __future__ import annotations

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
]
