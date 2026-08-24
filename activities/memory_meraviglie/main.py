from __future__ import annotations

import collections
import io
import math
from pathlib import Path
import random
import struct
import time
from typing import Any
import wave

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics, is_home_clicked
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import CompletionContent, PygameCompletionScreen
from greia_platform.typography import FontRole, GreiaTypography

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "memory_meraviglie.progress.v1"

THEMES = [
    {
        "id": "animals",
        "name_it": "🐾 Animali",
        "name_en": "🐾 Animals",
        "bg": (240, 249, 255),
        "card_back": (59, 130, 246),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "lion", "color": (251, 191, 36), "label_it": "Leone", "label_en": "Lion"},
            {"id": "panda", "color": (226, 232, 240), "label_it": "Panda", "label_en": "Panda"},
            {"id": "fox", "color": (249, 115, 22), "label_it": "Volpe", "label_en": "Fox"},
            {"id": "cat", "color": (253, 186, 116), "label_it": "Gatto", "label_en": "Cat"},
            {"id": "dog", "color": (217, 119, 6), "label_it": "Cane", "label_en": "Dog"},
            {"id": "bunny", "color": (251, 207, 232), "label_it": "Coniglio", "label_en": "Bunny"},
            {"id": "frog", "color": (74, 222, 128), "label_it": "Rana", "label_en": "Frog"},
            {"id": "bear", "color": (180, 83, 9), "label_it": "Orso", "label_en": "Bear"},
            {"id": "pig", "color": (244, 114, 182), "label_it": "Maialino", "label_en": "Pig"},
            {"id": "monkey", "color": (161, 98, 7), "label_it": "Scimmia", "label_en": "Monkey"},
            {"id": "owl", "color": (147, 51, 234), "label_it": "Gufo", "label_en": "Owl"},
            {"id": "penguin", "color": (51, 65, 85), "label_it": "Pinguino", "label_en": "Penguin"},
            {"id": "elephant", "color": (148, 163, 184), "label_it": "Elefante", "label_en": "Elephant"},
            {"id": "unicorn", "color": (236, 72, 153), "label_it": "Unicorno", "label_en": "Unicorn"},
            {"id": "butterfly", "color": (168, 85, 247), "label_it": "Farfalla", "label_en": "Butterfly"},
            {"id": "fish", "color": (14, 165, 233), "label_it": "Pesciolino", "label_en": "Fish"},
        ],
    },
    {
        "id": "sweets",
        "name_it": "🍭 Dolcetti",
        "name_en": "🍭 Sweets",
        "bg": (253, 242, 248),
        "card_back": (236, 72, 153),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "cupcake", "color": (244, 114, 182), "label_it": "Cupcake", "label_en": "Cupcake"},
            {"id": "icecream", "color": (251, 146, 60), "label_it": "Gelato", "label_en": "Ice Cream"},
            {"id": "donut", "color": (217, 119, 6), "label_it": "Ciambella", "label_en": "Donut"},
            {"id": "strawberry", "color": (239, 68, 68), "label_it": "Fragola", "label_en": "Strawberry"},
            {"id": "cookie", "color": (180, 83, 9), "label_it": "Biscotto", "label_en": "Cookie"},
            {"id": "candy", "color": (168, 85, 247), "label_it": "Caramella", "label_en": "Candy"},
            {"id": "lollipop", "color": (234, 179, 8), "label_it": "Lecca-lecca", "label_en": "Lollipop"},
            {"id": "cake", "color": (244, 63, 94), "label_it": "Torta", "label_en": "Cake"},
            {"id": "watermelon", "color": (34, 197, 94), "label_it": "Anguria", "label_en": "Watermelon"},
            {"id": "apple", "color": (220, 38, 38), "label_it": "Mela", "label_en": "Apple"},
            {"id": "banana", "color": (234, 179, 8), "label_it": "Banana", "label_en": "Banana"},
            {"id": "chocolate", "color": (120, 53, 15), "label_it": "Cioccolato", "label_en": "Chocolate"},
            {"id": "cherry", "color": (225, 29, 72), "label_it": "Ciliegia", "label_en": "Cherry"},
            {"id": "popsicle", "color": (14, 165, 233), "label_it": "Ghiacciolo", "label_en": "Popsicle"},
            {"id": "muffin", "color": (202, 138, 4), "label_it": "Muffin", "label_en": "Muffin"},
            {"id": "honey", "color": (245, 158, 11), "label_it": "Miele", "label_en": "Honey"},
        ],
    },
    {
        "id": "vehicles",
        "name_it": "🚀 Veicoli",
        "name_en": "🚀 Vehicles",
        "bg": (238, 242, 255),
        "card_back": (99, 102, 241),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "rocket", "color": (239, 68, 68), "label_it": "Razzo", "label_en": "Rocket"},
            {"id": "train", "color": (59, 130, 246), "label_it": "Treno", "label_en": "Train"},
            {"id": "boat", "color": (14, 165, 233), "label_it": "Barca", "label_en": "Boat"},
            {"id": "car", "color": (220, 38, 38), "label_it": "Auto", "label_en": "Car"},
            {"id": "helicopter", "color": (245, 158, 11), "label_it": "Elicottero", "label_en": "Helicopter"},
            {"id": "plane", "color": (16, 185, 129), "label_it": "Aereo", "label_en": "Plane"},
            {"id": "tractor", "color": (34, 197, 94), "label_it": "Trattore", "label_en": "Tractor"},
            {"id": "submarine", "color": (234, 179, 8), "label_it": "Sottomarino", "label_en": "Submarine"},
            {"id": "fire_truck", "color": (220, 38, 38), "label_it": "Pompieri", "label_en": "Fire Truck"},
            {"id": "police_car", "color": (37, 99, 235), "label_it": "Polizia", "label_en": "Police"},
            {"id": "bus", "color": (245, 158, 11), "label_it": "Bus", "label_en": "Bus"},
            {"id": "bicycle", "color": (168, 85, 247), "label_it": "Bici", "label_en": "Bicycle"},
            {"id": "balloon", "color": (236, 72, 153), "label_it": "Mongolfiera", "label_en": "Balloon"},
            {"id": "scooter", "color": (13, 148, 136), "label_it": "Scooter", "label_en": "Scooter"},
            {"id": "ufo", "color": (99, 102, 241), "label_it": "UFO", "label_en": "UFO"},
            {"id": "truck", "color": (234, 88, 12), "label_it": "Camion", "label_en": "Truck"},
        ],
    },
    {
        "id": "nature",
        "name_it": "🌸 Natura",
        "name_en": "🌸 Nature",
        "bg": (240, 253, 244),
        "card_back": (34, 197, 94),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "sunflower", "color": (234, 179, 8), "label_it": "Girasole", "label_en": "Sunflower"},
            {"id": "mushroom", "color": (239, 68, 68), "label_it": "Fungo", "label_en": "Mushroom"},
            {"id": "rainbow", "color": (168, 85, 247), "label_it": "Arcobaleno", "label_en": "Rainbow"},
            {"id": "star", "color": (254, 202, 87), "label_it": "Stella", "label_en": "Star"},
            {"id": "sun", "color": (245, 158, 11), "label_it": "Sole", "label_en": "Sun"},
            {"id": "moon", "color": (253, 224, 71), "label_it": "Luna", "label_en": "Moon"},
            {"id": "flower", "color": (244, 114, 182), "label_it": "Fiore", "label_en": "Flower"},
            {"id": "clover", "color": (16, 185, 129), "label_it": "Quadrifoglio", "label_en": "Clover"},
            {"id": "tree", "color": (22, 163, 74), "label_it": "Albero", "label_en": "Tree"},
            {"id": "cloud", "color": (56, 189, 248), "label_it": "Nuvola", "label_en": "Cloud"},
            {"id": "leaf", "color": (249, 115, 22), "label_it": "Foglia", "label_en": "Leaf"},
            {"id": "mountain", "color": (100, 116, 139), "label_it": "Montagna", "label_en": "Mountain"},
            {"id": "snowflake", "color": (14, 165, 233), "label_it": "Neve", "label_en": "Snowflake"},
            {"id": "planet", "color": (99, 102, 241), "label_it": "Pianeta", "label_en": "Planet"},
            {"id": "shell", "color": (251, 146, 60), "label_it": "Conchiglia", "label_en": "Shell"},
            {"id": "acorn", "color": (180, 83, 9), "label_it": "Ghianda", "label_en": "Acorn"},
        ],
    },
]

GRID_CONFIGS = [
    {"id": "small", "label_key": "grid.small", "label": "2x2", "cols": 2, "rows": 2, "pairs": 2},
    {"id": "medium", "label_key": "grid.medium", "label": "3x2", "cols": 3, "rows": 2, "pairs": 3},
    {"id": "large", "label_key": "grid.large", "label": "4x3", "cols": 4, "rows": 3, "pairs": 6},
    {"id": "xlarge", "label_key": "grid.xlarge", "label": "4x4", "cols": 4, "rows": 4, "pairs": 8},
    {"id": "giant", "label_key": "grid.giant", "label": "6x3", "cols": 6, "rows": 3, "pairs": 9},
]


def _synth_wav(samples: list[int], rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        raw = bytearray()
        for s in samples:
            clamped = max(-32768, min(32767, int(s)))
            raw.extend(struct.pack("<h", clamped))
        w.writeframes(raw)
    return buf.getvalue()


class MemoryAudio:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._init_sounds()
        except Exception:
            pass

    def _init_sounds(self) -> None:
        rate = 22050
        flip_samples = []
        for i in range(int(rate * 0.05)):
            t = i / rate
            env = math.exp(-20.0 * t)
            val = math.sin(2.0 * math.pi * 450.0 * t)
            flip_samples.append(int(32767.0 * 0.25 * env * val))
        self._sounds["flip"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(flip_samples)))

        match_samples = []
        for i in range(int(rate * 0.25)):
            t = i / rate
            env = math.exp(-4.0 * t)
            val = 0.6 * math.sin(2.0 * math.pi * 523.25 * t) + 0.4 * math.sin(2.0 * math.pi * 659.25 * t)
            match_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["match"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(match_samples)))

        mismatch_samples = []
        for i in range(int(rate * 0.08)):
            t = i / rate
            env = math.exp(-12.0 * t)
            val = math.sin(2.0 * math.pi * 180.0 * t)
            mismatch_samples.append(int(32767.0 * 0.20 * env * val))
        self._sounds["mismatch"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(mismatch_samples)))

        win_samples = []
        for i in range(int(rate * 0.45)):
            t = i / rate
            env = math.exp(-2.0 * t)
            freq = 523.25 if t < 0.12 else (659.25 if t < 0.24 else (783.99 if t < 0.36 else 1046.50))
            val = math.sin(2.0 * math.pi * freq * t)
            win_samples.append(int(32767.0 * 0.30 * env * val))
        self._sounds["win"] = pygame.mixer.Sound(io.BytesIO(_synth_wav(win_samples)))

    def play(self, name: str) -> None:
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


def _draw_card_illustration(surface: pygame.Surface, item_id: str, cx: int, cy: int, size: int) -> None:
    r = size // 2
    dark = (30, 41, 59)
    white = (255, 255, 255)

    if item_id == "lion":
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r)
        pygame.draw.circle(surface, (251, 191, 36), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, (217, 119, 6), (cx - r * 3 // 5, cy - r * 3 // 5), r // 4)
        pygame.draw.circle(surface, (217, 119, 6), (cx + r * 3 // 5, cy - r * 3 // 5), r // 4)
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.polygon(surface, (180, 83, 9), [(cx - r // 6, cy + r // 8), (cx + r // 6, cy + r // 8), (cx, cy + r // 4)])
        pygame.draw.circle(surface, dark, (cx, cy), r, 2)

    elif item_id == "panda":
        pygame.draw.circle(surface, dark, (cx - r * 3 // 5, cy - r * 3 // 5), r // 3)
        pygame.draw.circle(surface, dark, (cx + r * 3 // 5, cy - r * 3 // 5), r // 3)
        pygame.draw.circle(surface, white, (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r // 2, cy - r // 3, r // 3, r // 2))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx + r // 6, cy - r // 3, r // 3, r // 2))
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 6), max(2, r // 10))
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 6), max(2, r // 10))
        pygame.draw.circle(surface, dark, (cx, cy + r // 5), max(2, r // 8))

    elif item_id == "cat":
        pygame.draw.polygon(surface, (249, 115, 22), [(cx - r * 3 // 4, cy - r // 4), (cx - r * 3 // 4, cy - r * 4 // 5), (cx - r // 4, cy - r // 2)])
        pygame.draw.polygon(surface, (249, 115, 22), [(cx + r * 3 // 4, cy - r // 4), (cx + r * 3 // 4, cy - r * 4 // 5), (cx + r // 4, cy - r // 2)])
        pygame.draw.circle(surface, (253, 186, 116), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.circle(surface, (16, 185, 129), (cx - r // 4, cy - r // 8), max(2, r // 7))
        pygame.draw.circle(surface, (16, 185, 129), (cx + r // 4, cy - r // 8), max(2, r // 7))
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(1, r // 12))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(1, r // 12))
        pygame.draw.polygon(surface, (244, 114, 182), [(cx - r // 8, cy + r // 8), (cx + r // 8, cy + r // 8), (cx, cy + r // 4)])

    elif item_id == "dog":
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx - r * 9 // 10, cy - r // 2, r // 2, r * 9 // 10))
        pygame.draw.ellipse(surface, (180, 83, 9), pygame.Rect(cx + r * 2 // 5, cy - r // 2, r // 2, r * 9 // 10))
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.ellipse(surface, (254, 243, 199), pygame.Rect(cx - r // 3, cy, r * 2 // 3, r // 2))
        pygame.draw.circle(surface, dark, (cx - r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx + r // 4, cy - r // 8), max(2, r // 8))
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), max(2, r // 7))

    elif item_id == "bunny":
        pygame.draw.ellipse(surface, white, pygame.Rect(cx - r // 2, cy - r * 9 // 10, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx - r * 2 // 5, cy - r * 4 // 5, r // 6, r * 3 // 5))
        pygame.draw.ellipse(surface, white, pygame.Rect(cx + r // 6, cy - r * 9 // 10, r // 3, r * 4 // 5))
        pygame.draw.ellipse(surface, (244, 114, 182), pygame.Rect(cx + r // 4, cy - r * 4 // 5, r // 6, r * 3 // 5))
        pygame.draw.circle(surface, white, (cx, cy + r // 6), r * 3 // 5)
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), r * 3 // 5, 2)
        pygame.draw.circle(surface, dark, (cx - r // 5, cy + r // 12), max(2, r // 9))
        pygame.draw.circle(surface, dark, (cx + r // 5, cy + r // 12), max(2, r // 9))
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy + r // 4), max(2, r // 8))

    elif item_id == "frog":
        pygame.draw.circle(surface, (74, 222, 128), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (74, 222, 128), (cx + r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, white, (cx - r // 2, cy - r // 3), r // 5)
        pygame.draw.circle(surface, white, (cx + r // 2, cy - r // 3), r // 5)
        pygame.draw.circle(surface, dark, (cx - r // 2, cy - r // 3), r // 9)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy - r // 3), r // 9)
        pygame.draw.ellipse(surface, (74, 222, 128), pygame.Rect(cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r * 4 // 5))
        pygame.draw.circle(surface, dark, (cx, cy + r // 6), r * 3 // 4, 2)
        pygame.draw.arc(surface, dark, pygame.Rect(cx - r // 3, cy, r * 2 // 3, r // 3), 3.4, 6.0, 3)

    elif item_id == "cupcake":
        pygame.draw.polygon(surface, (251, 146, 60), [(cx - r // 2, cy), (cx + r // 2, cy), (cx + r // 3, cy + r * 3 // 4), (cx - r // 3, cy + r * 3 // 4)])
        pygame.draw.polygon(surface, dark, [(cx - r // 2, cy), (cx + r // 2, cy), (cx + r // 3, cy + r * 3 // 4), (cx - r // 3, cy + r * 3 // 4)], 2)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy - r // 5), r // 2)
        pygame.draw.circle(surface, (244, 114, 182), (cx - r // 3, cy), r // 3)
        pygame.draw.circle(surface, (244, 114, 182), (cx + r // 3, cy), r // 3)
        pygame.draw.circle(surface, (239, 68, 68), (cx, cy - r // 2), max(3, r // 5))
        pygame.draw.circle(surface, dark, (cx, cy - r // 2), max(3, r // 5), 2)

    elif item_id == "icecream":
        pygame.draw.polygon(surface, (217, 119, 6), [(cx - r // 3, cy), (cx + r // 3, cy), (cx, cy + r * 4 // 5)])
        pygame.draw.polygon(surface, dark, [(cx - r // 3, cy), (cx + r // 3, cy), (cx, cy + r * 4 // 5)], 2)
        pygame.draw.circle(surface, (251, 146, 60), (cx, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy - r // 2), r // 3)
        pygame.draw.circle(surface, dark, (cx, cy - r // 8), r * 2 // 5, 2)
        pygame.draw.circle(surface, dark, (cx, cy - r // 2), r // 3, 2)

    elif item_id == "donut":
        pygame.draw.circle(surface, (217, 119, 6), (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx, cy), r // 3)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        pygame.draw.circle(surface, dark, (cx, cy), r // 3, 2)
        for dx, dy, col in [(-r // 3, -r // 3, (234, 179, 8)), (r // 3, -r // 3, (56, 189, 248)), (0, r // 2, (34, 197, 94))]:
            pygame.draw.circle(surface, col, (cx + dx, cy + dy), max(2, r // 8))

    elif item_id == "strawberry":
        pygame.draw.polygon(surface, (239, 68, 68), [(cx - r * 3 // 5, cy - r // 3), (cx + r * 3 // 5, cy - r // 3), (cx, cy + r * 4 // 5)])
        pygame.draw.circle(surface, (239, 68, 68), (cx - r // 4, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (239, 68, 68), (cx + r // 4, cy - r // 3), r // 3)
        pygame.draw.polygon(surface, dark, [(cx - r * 3 // 5, cy - r // 3), (cx + r * 3 // 5, cy - r // 3), (cx, cy + r * 4 // 5)], 2)
        pygame.draw.ellipse(surface, (34, 197, 94), pygame.Rect(cx - r // 2, cy - r * 3 // 4, r, r // 3))
        for dx, dy in [(-r // 5, 0), (r // 5, 0), (0, r // 3)]:
            pygame.draw.circle(surface, (254, 240, 138), (cx + dx, cy + dy), max(1, r // 10))

    elif item_id == "cookie":
        pygame.draw.circle(surface, (180, 83, 9), (cx, cy), r * 4 // 5)
        pygame.draw.circle(surface, dark, (cx, cy), r * 4 // 5, 2)
        for dx, dy in [(-r // 3, -r // 4), (r // 4, -r // 3), (0, 0), (-r // 4, r // 3), (r // 3, r // 4)]:
            pygame.draw.circle(surface, (69, 26, 3), (cx + dx, cy + dy), max(2, r // 7))

    elif item_id == "rocket":
        pygame.draw.polygon(surface, (239, 68, 68), [(cx, cy - r * 4 // 5), (cx + r // 3, cy + r // 3), (cx - r // 3, cy + r // 3)])
        pygame.draw.polygon(surface, (59, 130, 246), [(cx - r // 3, cy), (cx - r * 3 // 4, cy + r // 2), (cx - r // 3, cy + r // 2)])
        pygame.draw.polygon(surface, (59, 130, 246), [(cx + r // 3, cy), (cx + r * 3 // 4, cy + r // 2), (cx + r // 3, cy + r // 2)])
        pygame.draw.circle(surface, (56, 189, 248), (cx, cy - r // 6), r // 4)
        pygame.draw.circle(surface, dark, (cx, cy - r // 6), r // 4, 2)
        pygame.draw.polygon(surface, (245, 158, 11), [(cx - r // 4, cy + r // 3), (cx + r // 4, cy + r // 3), (cx, cy + r * 4 // 5)])

    elif item_id == "car":
        pygame.draw.rect(surface, (220, 38, 38), pygame.Rect(cx - r * 3 // 4, cy - r // 8, r * 3 // 2, r // 2), border_radius=6)
        pygame.draw.ellipse(surface, (56, 189, 248), pygame.Rect(cx - r // 2, cy - r // 2, r, r // 2))
        pygame.draw.circle(surface, dark, (cx - r // 2, cy + r * 3 // 8), r // 4)
        pygame.draw.circle(surface, (148, 163, 184), (cx - r // 2, cy + r * 3 // 8), r // 8)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy + r * 3 // 8), r // 4)
        pygame.draw.circle(surface, (148, 163, 184), (cx + r // 2, cy + r * 3 // 8), r // 8)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r * 3 // 4, cy - r // 8, r * 3 // 2, r // 2), width=2, border_radius=6)

    elif item_id == "train":
        pygame.draw.rect(surface, (59, 130, 246), pygame.Rect(cx - r * 3 // 4, cy - r // 4, r * 3 // 2, r // 2), border_radius=4)
        pygame.draw.rect(surface, (239, 68, 68), pygame.Rect(cx + r // 6, cy - r * 3 // 5, r * 2 // 5, r * 4 // 5), border_radius=4)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r // 2, cy - r // 2, r // 4, r // 3))
        pygame.draw.circle(surface, dark, (cx - r // 2, cy + r // 3), r // 4)
        pygame.draw.circle(surface, dark, (cx, cy + r // 3), r // 4)
        pygame.draw.circle(surface, dark, (cx + r // 2, cy + r // 3), r // 4)

    elif item_id == "boat":
        pygame.draw.polygon(surface, (180, 83, 9), [(cx - r * 3 // 4, cy + r // 8), (cx + r * 3 // 4, cy + r // 8), (cx + r // 2, cy + r // 2), (cx - r // 2, cy + r // 2)])
        pygame.draw.polygon(surface, dark, [(cx - r * 3 // 4, cy + r // 8), (cx + r * 3 // 4, cy + r // 8), (cx + r // 2, cy + r // 2), (cx - r // 2, cy + r // 2)], 2)
        pygame.draw.polygon(surface, white, [(cx, cy - r * 3 // 4), (cx + r // 2, cy), (cx, cy)])
        pygame.draw.polygon(surface, (239, 68, 68), [(cx - r // 2, cy), (cx, cy - r // 2), (cx, cy)])

    elif item_id == "sunflower":
        for i in range(8):
            ang = i * math.pi / 4
            px = cx + int(math.cos(ang) * r * 3 // 5)
            py = cy + int(math.sin(ang) * r * 3 // 5)
            pygame.draw.circle(surface, (234, 179, 8), (px, py), r // 3)
        pygame.draw.circle(surface, (120, 53, 15), (cx, cy), r // 2)
        pygame.draw.circle(surface, dark, (cx, cy), r // 2, 2)

    elif item_id == "mushroom":
        pygame.draw.rect(surface, white, pygame.Rect(cx - r // 4, cy, r // 2, r * 3 // 5), border_radius=6)
        pygame.draw.rect(surface, dark, pygame.Rect(cx - r // 4, cy, r // 2, r * 3 // 5), width=2, border_radius=6)
        pygame.draw.ellipse(surface, (239, 68, 68), pygame.Rect(cx - r * 4 // 5, cy - r * 3 // 5, r * 8 // 5, r * 4 // 5))
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r * 4 // 5, cy - r * 3 // 5, r * 8 // 5, r * 4 // 5), 2)
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 5), max(2, r // 6))
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 5), max(2, r // 6))
        pygame.draw.circle(surface, white, (cx, cy - r // 3), max(2, r // 5))

    elif item_id == "rainbow":
        colors = [(239, 68, 68), (245, 158, 11), (234, 179, 8), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
        for idx, col in enumerate(colors):
            rad = r - idx * max(2, r // 8)
            if rad > 2:
                pygame.draw.arc(surface, col, pygame.Rect(cx - rad, cy - rad + r // 3, rad * 2, rad * 2), 0.0, math.pi, max(2, r // 8))
        pygame.draw.circle(surface, white, (cx - r * 2 // 3, cy + r // 3), r // 4)
        pygame.draw.circle(surface, white, (cx + r * 2 // 3, cy + r // 3), r // 4)

    elif item_id == "star":
        pts = []
        for i in range(10):
            ang = i * math.pi / 5 - math.pi / 2
            rad = r * 4 // 5 if i % 2 == 0 else r * 2 // 5
            pts.append((cx + int(math.cos(ang) * rad), cy + int(math.sin(ang) * rad)))
        pygame.draw.polygon(surface, (254, 202, 87), pts)
        pygame.draw.polygon(surface, (180, 83, 9), pts, 2)
        pygame.draw.circle(surface, white, (cx - r // 5, cy - r // 5), max(2, r // 8))

    elif item_id == "sun":
        for i in range(8):
            ang = i * math.pi / 4
            p1 = (cx + int(math.cos(ang) * r * 3 // 5), cy + int(math.sin(ang) * r * 3 // 5))
            p2 = (cx + int(math.cos(ang) * r * 9 // 10), cy + int(math.sin(ang) * r * 9 // 10))
            pygame.draw.line(surface, (245, 158, 11), p1, p2, max(2, r // 7))
        pygame.draw.circle(surface, (234, 179, 8), (cx, cy), r // 2)
        pygame.draw.circle(surface, (180, 83, 9), (cx, cy), r // 2, 2)
        pygame.draw.circle(surface, dark, (cx - r // 6, cy - r // 10), max(1, r // 12))
        pygame.draw.circle(surface, dark, (cx + r // 6, cy - r // 10), max(1, r // 12))
        pygame.draw.arc(surface, dark, pygame.Rect(cx - r // 5, cy - r // 10, r * 2 // 5, r // 3), 3.4, 6.0, 2)

    elif item_id == "moon":
        pygame.draw.circle(surface, (253, 224, 71), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx + r // 3, cy - r // 4), r * 3 // 5)
        pygame.draw.circle(surface, (202, 138, 4), (cx, cy), r * 3 // 4, 2)

    elif item_id == "tree":
        pygame.draw.rect(surface, (120, 53, 15), pygame.Rect(cx - r // 6, cy, r // 3, r * 3 // 4))
        pygame.draw.circle(surface, (34, 197, 94), (cx, cy - r // 3), r // 2)
        pygame.draw.circle(surface, (22, 163, 74), (cx - r // 3, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (22, 163, 74), (cx + r // 3, cy - r // 8), r * 2 // 5)
        pygame.draw.circle(surface, (20, 83, 45), (cx, cy - r // 4), r * 3 // 5, 2)

    elif item_id == "butterfly":
        pygame.draw.circle(surface, (236, 72, 153), (cx - r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (236, 72, 153), (cx + r // 2, cy - r // 3), r // 3)
        pygame.draw.circle(surface, (168, 85, 247), (cx - r // 3, cy + r // 4), r // 4)
        pygame.draw.circle(surface, (168, 85, 247), (cx + r // 3, cy + r // 4), r // 4)
        pygame.draw.ellipse(surface, dark, pygame.Rect(cx - r // 8, cy - r // 2, r // 4, r))

    elif item_id == "fish":
        pygame.draw.ellipse(surface, (249, 115, 22), pygame.Rect(cx - r * 3 // 5, cy - r // 3, r * 6 // 5, r * 2 // 3))
        pygame.draw.polygon(surface, (249, 115, 22), [(cx + r // 3, cy), (cx + r * 4 // 5, cy - r // 3), (cx + r * 4 // 5, cy + r // 3)])
        pygame.draw.circle(surface, white, (cx - r // 3, cy - r // 10), max(2, r // 7))
        pygame.draw.circle(surface, dark, (cx - r // 3, cy - r // 10), max(1, r // 12))

    else:
        pygame.draw.circle(surface, (244, 114, 182), (cx, cy), r * 3 // 4)
        pygame.draw.circle(surface, white, (cx, cy), r // 2)
        pygame.draw.circle(surface, dark, (cx, cy), r * 3 // 4, 2)
        pygame.draw.circle(surface, (254, 240, 138), (cx, cy), r // 4)


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


def _compute_grid_layout(grid_cfg: dict[str, Any], card_count: int) -> tuple[int, int, list[pygame.Rect]]:
    cols = grid_cfg["cols"]
    rows = grid_cfg["rows"]
    top_y = 80
    bottom_y = REFERENCE_HEIGHT - 65
    avail_w = REFERENCE_WIDTH - 120
    avail_h = bottom_y - top_y

    gap_x = 12 if cols >= 5 else 16
    gap_y = 10 if rows >= 4 else 14

    card_w = min(170, (avail_w - (cols - 1) * gap_x) // cols)
    card_h = min(210, (avail_h - (rows - 1) * gap_y) // rows)
    grid_w = cols * card_w + (cols - 1) * gap_x
    grid_h = rows * card_h + (rows - 1) * gap_y
    grid_ox = (REFERENCE_WIDTH - grid_w) // 2
    grid_oy = top_y + (avail_h - grid_h) // 2

    rects = []
    for i in range(card_count):
        c = i % cols
        r = i // cols
        rx = grid_ox + c * (card_w + gap_x)
        ry = grid_oy + r * (card_h + gap_y)
        rects.append(pygame.Rect(rx, ry, card_w, card_h))
    return card_w, card_h, rects


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = MemoryAudio()

    try:
        storage = get_storage()
    except Exception:
        storage = None

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    def t(key: str, default: str) -> str:
        if resources is not None:
            try:
                res = resources.string(key)
                if res:
                    return res
            except Exception:
                pass
        return default

    play_again_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 120, REFERENCE_HEIGHT // 2 + 80, 240, 52)
    completion = PygameCompletionScreen(
        typography,
        width=REFERENCE_WIDTH,
        height=REFERENCE_HEIGHT,
        primary_rect=play_again_rect,
    )
    completion_content = CompletionContent(
        title=t("victory.title", "Ottimo lavoro! Coppie trovate! 🌟"),
        body_lines=(t("victory.subtitle", "Che memoria fantastica!"),),
        primary_label=t("btn.play_again", "🎉 Gioca Ancora!"),
        achievement_count=3,
    )
    completion_presented = False

    theme_idx = 0
    grid_idx = 1

    cards: list[dict[str, Any]] = []
    flipped_indices: list[int] = []
    pairs_found = 0
    total_pairs = 3
    moves_count = 0
    unflip_timer = 0.0
    particles: list[dict[str, Any]] = []
    is_victory = False

    def start_new_game() -> None:
        nonlocal cards, flipped_indices, pairs_found, total_pairs, moves_count, unflip_timer, particles, is_victory, completion_presented
        theme_cfg = THEMES[theme_idx]
        grid_cfg = GRID_CONFIGS[grid_idx]
        total_pairs = min(grid_cfg["pairs"], len(theme_cfg["items"]))
        pairs_found = 0
        moves_count = 0
        flipped_indices.clear()
        unflip_timer = 0.0
        particles.clear()
        is_victory = False
        completion.clear()
        completion_presented = False

        selected_items = random.sample(theme_cfg["items"], total_pairs)
        deck_items = selected_items * 2
        random.shuffle(deck_items)

        cards.clear()
        for idx, item in enumerate(deck_items):
            cards.append({
                "id": item["id"],
                "item": item,
                "is_matched": False,
                "is_revealed": False,
                "flip_anim": 0.0,
            })

    start_new_game()

    running = True
    ready_published = False

    while running and not activity_stop_requested():
        theme_cfg = THEMES[theme_idx]
        grid_cfg = GRID_CONFIGS[grid_idx]
        card_w, card_h, card_rects = _compute_grid_layout(grid_cfg, len(cards))

        if not is_victory:
            if unflip_timer > 0.0:
                unflip_timer -= 0.033
                if unflip_timer <= 0.0:
                    for idx in flipped_indices:
                        if not cards[idx]["is_matched"]:
                            cards[idx]["is_revealed"] = False
                    flipped_indices.clear()

            for card in cards:
                target_flip = 1.0 if (card["is_revealed"] or card["is_matched"]) else 0.0
                diff = target_flip - card["flip_anim"]
                if abs(diff) > 0.01:
                    card["flip_anim"] += diff * 0.28
                else:
                    card["flip_anim"] = target_flip

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.get_surface() or screen
                metrics = ChildUiMetrics.for_size(*screen.get_size())
                canvas = PygameReferenceCanvas(screen)
                completion_presented = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN) and is_victory:
                    start_new_game()
                elif event.key == pygame.K_n:
                    start_new_game()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                mx, my = logical

                if is_victory:
                    if completion.primary_contains((int(mx), int(my))):
                        start_new_game()
                    # Terminal input must not fall through into controls underneath.
                    continue

                new_btn = pygame.Rect(REFERENCE_WIDTH - 170, 14, 150, 52)
                if new_btn.collidepoint(mx, my):
                    start_new_game()
                    continue

                theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 150, REFERENCE_HEIGHT - 52, 140, 44)
                if theme_btn.collidepoint(mx, my):
                    theme_idx = (theme_idx + 1) % len(THEMES)
                    start_new_game()
                    continue

                grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 52, 140, 44)
                if grid_btn.collidepoint(mx, my):
                    grid_idx = (grid_idx + 1) % len(GRID_CONFIGS)
                    start_new_game()
                    continue

                if unflip_timer <= 0.0:
                    _, _, active_rects = _compute_grid_layout(GRID_CONFIGS[grid_idx], len(cards))
                    for idx, rect in enumerate(active_rects):
                        if rect.collidepoint(mx, my):
                            card = cards[idx]
                            if not card["is_revealed"] and not card["is_matched"]:
                                card["is_revealed"] = True
                                sounds.play("flip")
                                flipped_indices.append(idx)

                                if len(flipped_indices) == 2:
                                    moves_count += 1
                                    idx1, idx2 = flipped_indices[0], flipped_indices[1]
                                    if cards[idx1]["id"] == cards[idx2]["id"]:
                                        cards[idx1]["is_matched"] = True
                                        cards[idx2]["is_matched"] = True
                                        pairs_found += 1
                                        sounds.play("match")
                                        try:
                                            emit_activity_event("memory.pair_found", {"pairs": pairs_found})
                                        except Exception:
                                            pass
                                        for cr in [card_rects[idx1], card_rects[idx2]]:
                                            for _ in range(16):
                                                ang = random.uniform(0, 6.28)
                                                spd = random.uniform(2.0, 5.5)
                                                particles.append({
                                                    "x": cr.centerx,
                                                    "y": cr.centery,
                                                    "vx": math.cos(ang) * spd,
                                                    "vy": math.sin(ang) * spd,
                                                    "color": (254, 202, 87),
                                                    "size": random.uniform(4.0, 9.0),
                                                    "life": 1.0,
                                                    "decay": 0.03,
                                                })
                                        flipped_indices.clear()

                                        if pairs_found >= total_pairs:
                                            is_victory = True
                                            completion_presented = False
                                            sounds.play("win")
                                            try:
                                                emit_activity_event("memory.game_completed", {"moves": moves_count})
                                            except Exception:
                                                pass
                                    else:
                                        sounds.play("mismatch")
                                        unflip_timer = 0.9
                                break

        if is_victory:
            if not completion_presented:
                completion.prepare(completion_content)
                completion.draw(canvas.surface)
                canvas.present(clear=theme.background)
                pygame.display.flip()
                completion_presented = True
            clock.tick(25)
            continue

        surviving = []
        for p in particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= p["decay"]
            if p["life"] > 0:
                surviving.append(p)
        particles = surviving

        surf = canvas.surface
        surf.fill(THEMES[theme_idx]["bg"])
        theme_cfg = THEMES[theme_idx]
        grid_cfg = GRID_CONFIGS[grid_idx]
        card_w, card_h, card_rects = _compute_grid_layout(grid_cfg, len(cards))

        for bx in range(30, REFERENCE_WIDTH, 80):
            for by in range(30, REFERENCE_HEIGHT, 80):
                pygame.draw.circle(surf, (226, 232, 240), (bx, by), 2)

        for idx, card in enumerate(cards):
            rect = card_rects[idx]
            flip = card["flip_anim"]
            cos_flip = abs(math.cos(flip * math.pi))
            cur_w = max(6, int(card_w * cos_flip))
            cur_rect = pygame.Rect(rect.centerx - cur_w // 2, rect.top, cur_w, card_h)

            pygame.draw.rect(surf, (203, 213, 225), cur_rect.move(3, 5), border_radius=16)

            is_front = flip >= 0.5
            if is_front:
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, border_radius=16)
                border_col = (34, 197, 94) if card["is_matched"] else (203, 213, 225)
                border_w = 4 if card["is_matched"] else 2
                pygame.draw.rect(surf, border_col, cur_rect, width=border_w, border_radius=16)

                if cos_flip > 0.35:
                    item = card["item"]
                    emblem_r = int(min(cur_w, card_h) * 0.34)
                    emblem_cy = cur_rect.top + int(card_h * 0.42)

                    pygame.draw.circle(surf, item["color"], (cur_rect.centerx, emblem_cy), emblem_r)
                    pygame.draw.circle(surf, (30, 41, 59), (cur_rect.centerx, emblem_cy), emblem_r, 2)

                    _draw_card_illustration(surf, item["id"], cur_rect.centerx, emblem_cy, int(emblem_r * 1.5))

                    lbl_text = item["label_it"] if active_locale == "it" else item["label_en"]
                    lbl_surf = typography.render(lbl_text, FontRole.DISPLAY, max(12, min(16, card_h // 12)), (30, 41, 59))
                    surf.blit(lbl_surf, (cur_rect.centerx - lbl_surf.get_width() // 2, cur_rect.bottom - lbl_surf.get_height() - 8))
            else:
                pygame.draw.rect(surf, theme_cfg["card_back"], cur_rect, border_radius=16)
                pygame.draw.rect(surf, (255, 255, 255), cur_rect, width=3, border_radius=16)
                if cos_flip > 0.35:
                    back_r = int(min(cur_w, card_h) * 0.26)
                    pygame.draw.circle(surf, (255, 255, 255), cur_rect.center, back_r, 3)
                    pygame.draw.circle(surf, theme_cfg["back_accent"], cur_rect.center, back_r - 4)
                    _draw_card_illustration(surf, "star", cur_rect.centerx, cur_rect.centery, int(back_r * 1.2))

        for p in particles:
            cur_sz = max(2.0, p["size"] * max(0.0, min(1.0, p["life"])))
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), int(cur_sz))

        star_pill = pygame.Rect(80, 14, 150, 52)
        pygame.draw.rect(surf, (255, 255, 255), star_pill, border_radius=18)
        pygame.draw.rect(surf, (180, 83, 9), star_pill, width=3, border_radius=18)
        _draw_card_illustration(surf, "star", star_pill.left + 28, star_pill.centery, 34)
        s_txt = typography.render(f"{pairs_found}/{total_pairs}", FontRole.DISPLAY, 24, (180, 83, 9))
        surf.blit(s_txt, (star_pill.left + 54, star_pill.centery - s_txt.get_height() // 2))

        new_btn = pygame.Rect(REFERENCE_WIDTH - 170, 14, 150, 52)
        pygame.draw.rect(surf, (51, 65, 85), new_btn, border_radius=18)
        pygame.draw.rect(surf, (30, 41, 59), new_btn, width=2, border_radius=18)
        new_txt = typography.render("🔄 NUOVO", FontRole.DISPLAY, 18, (255, 255, 255))
        surf.blit(new_txt, (new_btn.centerx - new_txt.get_width() // 2, new_btn.centery - new_txt.get_height() // 2))

        theme_btn = pygame.Rect(REFERENCE_WIDTH // 2 - 150, REFERENCE_HEIGHT - 52, 140, 44)
        pygame.draw.rect(surf, (51, 65, 85), theme_btn, border_radius=12)
        pygame.draw.rect(surf, (30, 41, 59), theme_btn, width=2, border_radius=12)
        t_name = theme_cfg["name_it"] if active_locale == "it" else theme_cfg["name_en"]
        theme_lbl = typography.render(t_name, FontRole.BODY, 15, (255, 255, 255))
        surf.blit(theme_lbl, (theme_btn.centerx - theme_lbl.get_width() // 2, theme_btn.centery - theme_lbl.get_height() // 2))

        grid_btn = pygame.Rect(REFERENCE_WIDTH // 2 + 10, REFERENCE_HEIGHT - 52, 140, 44)
        pygame.draw.rect(surf, (51, 65, 85), grid_btn, border_radius=12)
        pygame.draw.rect(surf, (30, 41, 59), grid_btn, width=2, border_radius=12)
        grid_lbl = typography.render("📐 " + grid_cfg["label"], FontRole.BODY, 15, (255, 255, 255))
        surf.blit(grid_lbl, (grid_btn.centerx - grid_lbl.get_width() // 2, grid_btn.centery - grid_lbl.get_height() // 2))

        canvas.present(clear=theme.background)
        pygame.display.flip()

        if not ready_published:
            mark_activity_ready()
            ready_published = True

        clock.tick(30)

    if storage is not None:
        try:
            storage.kv_set(STORAGE_KEY, {
                "theme_idx": theme_idx,
                "grid_idx": grid_idx,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
