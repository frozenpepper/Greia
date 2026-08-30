"""Pure content constants for Teatrino delle Fiabe.

No pygame imports. Defines reference geometry, storage keys,
stage palette, background roster and character rosters as pure data.
"""

from __future__ import annotations

from typing import Final

REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_RECORDING_SECONDS: Final = 45.0
MAX_SAVED_SHOWS: Final = 16
SHOWS_INDEX_KEY: Final = "teatrino.shows.index.v1"
# STORAGE_KEY alias for app wiring; canonical key is SHOWS_INDEX_KEY.
STORAGE_KEY: Final = SHOWS_INDEX_KEY

# Stage Theme Palette
STAGE_RED: Final = (185, 28, 28)
STAGE_CURTAIN: Final = (153, 27, 27)
STAGE_CURTAIN_DARK: Final = (127, 29, 29)
STAGE_CURTAIN_LIGHT: Final = (220, 38, 38)
STAGE_GOLD: Final = (245, 158, 11)
STAGE_GOLD_LIGHT: Final = (254, 240, 138)
STAGE_WOOD_TOP: Final = (180, 110, 50)
STAGE_WOOD_BASE: Final = (120, 65, 20)
DARK_TEXT: Final = (45, 25, 15)
WHITE: Final = (255, 255, 255)
REC_RED: Final = (239, 68, 68)
MIC_GREEN: Final = (34, 197, 94)

BG_CONFIGS: Final = [
    ("cottage", "🏡", "Casetta"),
    ("castle", "🏰", "Castello"),
    ("ocean", "🌊", "Mare"),
    ("forest", "🌲", "Bosco"),
    ("sky", "☁️", "Cielo"),
]

PUPPET_ROSTER: Final = [
    # Page 1: Canonical Greia Cast
    ("lilli", "Lilli"),
    ("leo", "Leo"),
    ("flash", "Flash"),
    ("dani", "Dani"),
    ("tito", "Tito"),
    ("momo", "Momo"),
    # Page 2: Classic Fairytale Troupe
    ("principessa", "Principessa"),
    ("draghetto", "Draghetto"),
    ("cavaliere", "Cavaliere"),
    ("bebe", "Bebè"),
    ("re", "Re"),
    ("lupetto", "Lupetto"),
    # Page 3: Magical Characters
    ("orsetto", "Orsetto"),
    ("sirenetta", "Sirenetta"),
    ("mago", "Mago"),
    ("fatina", "Fatina"),
]

FX_BUTTONS: Final = [
    ("trumpet", "🎺"),
    ("magic", "✨"),
    ("applause", "👏"),
    ("giggle", "😄"),
    ("mystery", "🔮"),
    ("boing", "💥"),
]

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "MAX_RECORDING_SECONDS",
    "MAX_SAVED_SHOWS",
    "SHOWS_INDEX_KEY",
    "STORAGE_KEY",
    "STAGE_RED",
    "STAGE_CURTAIN",
    "STAGE_CURTAIN_DARK",
    "STAGE_CURTAIN_LIGHT",
    "STAGE_GOLD",
    "STAGE_GOLD_LIGHT",
    "STAGE_WOOD_TOP",
    "STAGE_WOOD_BASE",
    "DARK_TEXT",
    "WHITE",
    "REC_RED",
    "MIC_GREEN",
    "BG_CONFIGS",
    "PUPPET_ROSTER",
    "FX_BUTTONS",
]
