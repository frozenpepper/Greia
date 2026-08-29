"""Orchestra Animali — content constants (palette, notes, instruments)."""

from __future__ import annotations


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "orchestra_animali.state.v3"


# Grand Theater Palette
STAGE_WALL_TOP = (22, 18, 42)
STAGE_WALL_BOTTOM = (45, 30, 65)
STAGE_CURTAIN = (175, 30, 45)
STAGE_CURTAIN_DARK = (120, 18, 30)
STAGE_CURTAIN_GOLD = (245, 195, 60)
STAGE_WOOD_TOP = (180, 115, 60)
STAGE_WOOD_BOTTOM = (110, 65, 30)
STAGE_GOLD = (255, 215, 60)
WHITE = (255, 255, 255)
DARK_TEXT = (30, 41, 59)


RAINBOW_COLORS: list[tuple[int, int, int]] = [
    (245, 75, 75),    # 1: C (Do) - Red
    (250, 140, 45),   # 2: D (Re) - Orange
    (255, 215, 45),   # 3: E (Mi) - Yellow
    (85, 205, 105),   # 4: F (Fa) - Green
    (65, 180, 245),   # 5: G (Sol) - Cyan
    (115, 110, 235),  # 6: A (La) - Indigo
    (200, 85, 215),   # 7: B (Si) - Violet
    (255, 95, 160),   # 8: C5 (Do alto) - Pink
]


NOTE_NAMES_IT = ["DO", "RE", "MI", "FA", "SOL", "LA", "SI", "DO"]
NOTE_NAMES_EN = ["C", "D", "E", "F", "G", "A", "B", "C"]
NOTE_FREQS: list[float] = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
KEYBOARD_SHORTCUTS = ["1", "2", "3", "4", "5", "6", "7", "8"]
